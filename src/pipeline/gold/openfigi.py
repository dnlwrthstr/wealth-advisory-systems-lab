"""OpenFIGI mapping client — ISIN → FIGI / ticker / name / security type.

Bloomberg's OpenFIGI API is the free, key-optional path to resolve a
12-digit ISIN into the FIGI + venue-specific ticker. The lab uses it as
the identifier bootstrap for the equity scope: given just an ISIN, this
source supplies enough identifiers and naming for `equity_yahoo` to
overlay live market data on top.

Endpoint: https://api.openfigi.com/v3/mapping (POST, JSON array body)

Rate limits: 25 requests/minute without an API key, 250/min with a free
key (set `OPENFIGI_API_KEY` env var). The disk cache keyed by ISIN keeps
re-runs free.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("openfigi")

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
TIMEOUT = 30
CACHE_DIR = Path.home() / ".cache" / "wealth-advisory-systems-lab" / "openfigi"

# OpenFIGI securityType → ontology equitySubType. The free text on the API
# is somewhat noisy; map only the cases we've seen recurring.
SECURITY_TYPE_TO_SUBTYPE: Dict[str, str] = {
    "Common Stock": "common_stock",
    "ADR": "adr",
    "GDR": "gdr",
    "REIT": "reit",
    "Preferred Stock": "preferred_stock",
}


def _cache_path(isin: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{isin}.json"


def _post_json(payload: List[Dict[str, str]]) -> Optional[Any]:
    """POST `payload` to OpenFIGI, return the parsed JSON response."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    api_key = os.environ.get("OPENFIGI_API_KEY")
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OPENFIGI_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        log.warning("openfigi HTTP %s for payload %s", exc.code, payload)
        return None
    except urllib.error.URLError as exc:
        log.warning("openfigi URL error %s for payload %s", exc, payload)
        return None


def fetch_openfigi_by_isin(isin: str, *, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Resolve `isin` to a single best-match record from OpenFIGI.

    OpenFIGI returns multiple matches (one per venue listing); we pick the
    composite FIGI when present (security across exchanges), otherwise the
    first result. Caches the chosen record on disk.

    Returns a flat projection: {figi, ticker, name, securityType, exchCode,
    compositeFIGI}. Returns None when OpenFIGI has no match.
    """
    cached = _cache_path(isin)
    if use_cache and cached.exists():
        try:
            data = json.loads(cached.read_text(encoding="utf-8"))
            return None if data.get("_negative") else data
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    response = _post_json([{"idType": "ID_ISIN", "idValue": isin}])
    if response is None:
        # Transient HTTP error — don't poison the cache.
        return None

    # OpenFIGI returns an array of results in the same order as the request.
    if not isinstance(response, list) or not response:
        cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
        return None
    result = response[0] or {}
    matches = result.get("data") or []
    if not matches:
        cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
        return None

    chosen = _pick_best_match(matches)
    projected = {
        "figi": chosen.get("figi"),
        "compositeFIGI": chosen.get("compositeFIGI"),
        "ticker": chosen.get("ticker"),
        "name": chosen.get("name"),
        "securityType": chosen.get("securityType"),
        "securityType2": chosen.get("securityType2"),
        "exchCode": chosen.get("exchCode"),
        "marketSector": chosen.get("marketSector"),
    }
    try:
        cached.write_text(json.dumps(projected), encoding="utf-8")
    except OSError as exc:
        log.warning("openfigi cache write failed for %s: %s", isin, exc)
    return projected


def fetch_openfigi_by_ticker(
    ticker: str,
    exchange_code: Optional[str] = None,
    *,
    use_cache: bool = True,
) -> Optional[Dict[str, Any]]:
    """Resolve a Yahoo-suffixed ticker to a single best-match OpenFIGI record.

    The reverse direction of `fetch_openfigi_by_isin`. Used by the
    universe batch loader to map Wikipedia-sourced tickers (S&P 500 etc.)
    onto ISINs before handing them to the agentic equity chain.

    The Yahoo suffix (`.SW`, `.DE`, `.L`, …) is stripped before the
    OpenFIGI call — OpenFIGI expects the bare ticker plus an optional
    `exchCode` filter. When `exchange_code` is None, OpenFIGI returns
    the best composite-FIGI match across all venues.

    Returns the same flat projection as `fetch_openfigi_by_isin`, plus
    the `isin` field when OpenFIGI's response carries it on the chosen
    match. Returns None on no-match or transient HTTP error.
    """
    bare = _strip_yahoo_suffix(ticker)
    cache_key = f"ticker:{bare}" + (f":{exchange_code}" if exchange_code else "")
    cached = _cache_path(cache_key)
    if use_cache and cached.exists():
        try:
            data = json.loads(cached.read_text(encoding="utf-8"))
            return None if data.get("_negative") else data
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    body: Dict[str, str] = {"idType": "TICKER", "idValue": bare}
    if exchange_code:
        body["exchCode"] = exchange_code
    response = _post_json([body])
    if response is None:
        return None

    if not isinstance(response, list) or not response:
        cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
        return None
    result = response[0] or {}
    matches = result.get("data") or []
    if not matches:
        cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
        return None

    chosen = _pick_best_match(matches)
    projected = {
        "figi": chosen.get("figi"),
        "compositeFIGI": chosen.get("compositeFIGI"),
        "ticker": chosen.get("ticker"),
        "name": chosen.get("name"),
        "securityType": chosen.get("securityType"),
        "securityType2": chosen.get("securityType2"),
        "exchCode": chosen.get("exchCode"),
        "marketSector": chosen.get("marketSector"),
        "isin": chosen.get("isin"),
    }
    try:
        cached.write_text(json.dumps(projected), encoding="utf-8")
    except OSError as exc:
        log.warning("openfigi ticker cache write failed for %s: %s", cache_key, exc)
    return projected


# Yahoo venue suffixes used by the named universes the batch loader
# supports (SMI=.SW, DAX 40=.DE, FTSE 100=.L). Share-class indicators on
# US tickers (BRK.B, BF.B) are NOT venue suffixes and must not be
# stripped — they're part of the OpenFIGI ticker.
_YAHOO_VENUE_SUFFIXES = frozenset({"SW", "DE", "L"})


def _strip_yahoo_suffix(ticker: str) -> str:
    """Drop the Yahoo venue suffix (`.SW`, `.DE`, `.L`) before hitting OpenFIGI.

    Bare tickers (no dot) and US share-class tickers (`BRK.B`, `BF.B`) pass
    through unchanged — only known venue suffixes are removed.
    """
    if "." not in ticker:
        return ticker
    head, tail = ticker.rsplit(".", 1)
    if tail in _YAHOO_VENUE_SUFFIXES:
        return head
    return ticker


def _pick_best_match(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prefer the composite-FIGI record; otherwise the first match.

    The composite FIGI represents the security across all exchanges and is
    the right anchor for an instrument golden record. The per-venue FIGIs
    are useful for listings, which we don't model from OpenFIGI directly.
    """
    for m in matches:
        if m.get("figi") and m.get("figi") == m.get("compositeFIGI"):
            return m
    return matches[0]
