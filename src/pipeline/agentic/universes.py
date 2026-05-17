"""Named-equity-universe resolver.

`resolve(name)` returns a list of Yahoo-suffixed tickers for one of the
supported named universes (SMI, S&P 500, NASDAQ 100, DAX 40, FTSE 100)
by scraping the Wikipedia constituent table once and caching the result
on disk for 7 days.

This module owns the universe → ticker mapping. Ticker → ISIN resolution
is two-tier:

  * For SIX-listed Swiss tickers the agentic planner's `six_ticker_isin`
    source (cost=file_read) handles ticker → ISIN automatically — the
    batch CLI can pass tickers straight through.
  * For foreign exchanges (S&P 500, NASDAQ, DAX, FTSE) the batch CLI
    uses `tickers_to_isins` here, which goes through OpenFIGI's
    ticker-direction lookup (`pipeline.gold.openfigi.fetch_openfigi_by_ticker`).

The Wikipedia parsing logic was moved here from
`pipeline.gold.equity_yahoo` (which still owns the per-ticker Yahoo
fetch used by `pipeline.agentic.sources.equity_yahoo`).
"""
from __future__ import annotations

import io
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

WIKI_USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
WIKI_FETCH_TIMEOUT = 30

# 7 days — Wikipedia constituent tables change rarely enough that a weekly
# refresh is conservative. The test suite uses pinned HTML fixtures and
# never goes through the cache.
CACHE_TTL_SECONDS = 7 * 24 * 3600

# Wikipedia universe sources. Same shape as the legacy
# `pipeline.gold.equity_yahoo.UNIVERSE_SOURCES` it replaces:
#   url                    — Wikipedia article to scrape
#   table_index            — if set, pick this table directly (S&P 500's
#                            first table is the constituent list)
#   ticker_column          — column name when table_index is set
#   ticker_column_candidates — when scanning all tables, the first table
#                              whose columns include any of these wins
#   suffix                 — appended to bare tickers to form the
#                            Yahoo-suffixed form ('NESN' → 'NESN.SW')
UNIVERSE_SOURCES: Dict[str, Dict[str, Any]] = {
    "smi": {
        "url": "https://en.wikipedia.org/wiki/Swiss_Market_Index",
        "ticker_column_candidates": ["Ticker", "Symbol"],
        "suffix": ".SW",
    },
    "sp500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "table_index": 0,
        "ticker_column": "Symbol",
        "suffix": "",
    },
    "nasdaq100": {
        "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "ticker_column_candidates": ["Ticker", "Symbol"],
        "suffix": "",
    },
    "dax40": {
        "url": "https://en.wikipedia.org/wiki/DAX",
        "ticker_column_candidates": ["Ticker", "Ticker symbol", "Symbol"],
        "suffix": ".DE",
    },
    "ftse100": {
        "url": "https://en.wikipedia.org/wiki/FTSE_100_Index",
        "ticker_column_candidates": ["EPIC", "Ticker", "Symbol"],
        "suffix": ".L",
    },
}


@dataclass(frozen=True)
class Resolution:
    """Outcome of resolving a single ticker to an ISIN."""

    ticker: str
    isin: Optional[str]
    reason: Optional[str] = None  # None on success; explanation on miss.


# ---------------------------------------------------------------------------
# Disk cache
# ---------------------------------------------------------------------------

# Resolves to <repo-root>/data/cache/universe/. The module file lives at
# src/pipeline/agentic/universes.py, so four parents up is the repo root.
_CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache" / "universe"


def _cache_path(name: str) -> Path:
    return _CACHE_DIR / f"{name}.json"


def _cache_fresh(path: Path, ttl_seconds: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_seconds


def _read_cache(path: Path) -> Optional[List[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("universe cache read failed at %s: %s", path, exc)
        return None
    if not isinstance(data, list) or not all(isinstance(t, str) for t in data):
        log.warning("universe cache at %s has unexpected shape; ignoring", path)
        return None
    return data


def _write_cache(path: Path, tickers: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tickers, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Wikipedia fetch + parse
# ---------------------------------------------------------------------------

def _fetch_wikipedia(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
    with urllib.request.urlopen(req, timeout=WIKI_FETCH_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_tickers(html: str, spec: Dict[str, Any]) -> List[str]:
    """Parse a Wikipedia HTML page into a list of suffixed tickers.

    pandas.read_html is used to extract every table; we then pick the
    table either by index (when `spec["table_index"]` is set) or by
    column-name match against `spec["ticker_column_candidates"]`.
    """
    import pandas as pd  # local import — pandas isn't always loaded at module init

    tables = pd.read_html(io.StringIO(html))

    df = None
    ticker_col: Optional[str] = None
    if spec.get("table_index") is not None:
        df = tables[spec["table_index"]]
        ticker_col = spec.get("ticker_column")
    else:
        for candidate in spec["ticker_column_candidates"]:
            for table in tables:
                cols = [
                    " ".join(str(c) for c in col).strip()
                    if isinstance(col, tuple)
                    else str(col).strip()
                    for col in table.columns
                ]
                table.columns = cols
                if candidate in cols:
                    df, ticker_col = table, candidate
                    break
            if df is not None:
                break

    if df is None or ticker_col is None:
        raise RuntimeError(
            f"ticker column not found at {spec['url']}. "
            f"Tried: {spec.get('ticker_column_candidates') or spec.get('ticker_column')}"
        )

    raw = df[ticker_col].astype(str).str.strip()
    suffix = spec.get("suffix", "")
    tickers: List[str] = []
    for t in raw.tolist():
        if not t or t.lower() == "nan":
            continue
        full = t if (not suffix or t.endswith(suffix)) else t + suffix
        if full not in tickers:
            tickers.append(full)
    return tickers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve(name: str, *, use_cache: bool = True) -> List[str]:
    """Return the ticker list for `name`, fetching from Wikipedia if needed.

    Results are cached on disk for 7 days. Pass `use_cache=False` to force
    a fresh fetch.

    Raises:
      ValueError on unknown universe names.
      RuntimeError on parser failure (table format drifted at the source).
      urllib.error.URLError on transport failure.
    """
    if name not in UNIVERSE_SOURCES:
        raise ValueError(
            f"unknown universe {name!r}; supported: {sorted(UNIVERSE_SOURCES)}"
        )
    spec = UNIVERSE_SOURCES[name]
    cache_path = _cache_path(name)

    if use_cache and _cache_fresh(cache_path, CACHE_TTL_SECONDS):
        cached = _read_cache(cache_path)
        if cached is not None:
            log.debug("universe %s: %d tickers from cache", name, len(cached))
            return cached

    html = _fetch_wikipedia(spec["url"])
    tickers = _parse_tickers(html, spec)

    if use_cache:
        try:
            _write_cache(cache_path, tickers)
        except OSError as exc:
            log.warning("universe cache write failed at %s: %s", cache_path, exc)

    log.info("universe %s: %d tickers from %s", name, len(tickers), spec["url"])
    return tickers


def supported_universes() -> List[str]:
    """Return the list of supported universe names (for CLI --help, errors)."""
    return sorted(UNIVERSE_SOURCES)


def tickers_to_isins(tickers: List[str]) -> List[Resolution]:
    """Resolve a list of Yahoo-suffixed tickers to ISINs via OpenFIGI.

    Used by the batch CLI for non-SIX universes (S&P 500, NASDAQ 100,
    DAX 40, FTSE 100) where the agentic planner's `six_ticker_isin`
    source can't help.

    Returns one Resolution per input ticker (preserves order). On miss,
    `Resolution.isin` is None and `Resolution.reason` carries the
    explanation. Network failures don't abort the batch — they appear
    as misses with `reason="openfigi: <error>"`.
    """
    # Imported here so the module is importable even before the OpenFIGI
    # extension lands (T008 may add the function in a follow-up step).
    from pipeline.gold.openfigi import fetch_openfigi_by_ticker

    out: List[Resolution] = []
    for ticker in tickers:
        try:
            rec = fetch_openfigi_by_ticker(ticker)
        except Exception as exc:  # noqa: BLE001 — surface as soft miss, don't abort
            out.append(Resolution(ticker=ticker, isin=None, reason=f"openfigi: {exc}"))
            continue
        if rec is None:
            out.append(Resolution(ticker=ticker, isin=None, reason="openfigi: no match"))
            continue
        isin = rec.get("isin") or _isin_from_identifiers(rec)
        if not isin:
            out.append(
                Resolution(
                    ticker=ticker,
                    isin=None,
                    reason="openfigi: response missing ISIN",
                )
            )
            continue
        out.append(Resolution(ticker=ticker, isin=isin))
    return out


def _isin_from_identifiers(rec: Dict[str, Any]) -> Optional[str]:
    """Best-effort: some OpenFIGI shapes carry ISIN nested under identifiers."""
    for entry in rec.get("identifierList") or []:
        if entry.get("type") == "isin" and entry.get("identifier"):
            return entry["identifier"]
    return None
