"""Enrich a FundGolden NDJSON file from Yahoo Finance, by ISIN.

For every fund document in the input file we look up the share-class
ISIN via yfinance (`Ticker(isin)`), then fill the fields that FIRDS
doesn't carry: NAV, market price, AUM, OHLCV, the resolved Yahoo
symbol (back into `primaryListing.ticker` plus `identifierList`), TER,
and trailing-period returns. Results are cached on disk so repeat runs
are free.

What this does NOT cover: fees beyond TER, dealing terms, SRRI / SRI,
service providers, prospectus-level static data — those need fact-sheet
parsing (see the `find-and-parse-factsheet` skill).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("fund_yahoo_enrich")

CACHE_DIR = Path.home() / ".cache" / "wealth-advisory-systems-lab" / "yahoo-funds"


def _cache_path(isin: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{isin}.json"


# Sector label mapping: yfinance returns underscored lower-case keys; the
# ontology examples use Title-Case display labels.
_SECTOR_LABEL = {
    "technology": "Information Technology",
    "financial_services": "Financial Services",
    "healthcare": "Health Care",
    "consumer_cyclical": "Consumer Cyclical",
    "consumer_defensive": "Consumer Defensive",
    "industrials": "Industrials",
    "communication_services": "Communication Services",
    "energy": "Energy",
    "basic_materials": "Basic Materials",
    "utilities": "Utilities",
    "realestate": "Real Estate",
}

_ASSET_CLASS_LABEL = {
    "stockPosition": "EQUITY",
    "bondPosition": "FIXED_INCOME",
    "cashPosition": "CASH",
    "preferredPosition": "EQUITY",
    "convertiblePosition": "FIXED_INCOME",
    "otherPosition": "OTHER",
}


def _project_yahoo_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the fields we'll actually use. Smaller cache + easier debugging."""
    return {
        "yahooSymbol": info.get("symbol"),
        "navPrice": info.get("navPrice"),
        "regularMarketPrice": info.get("regularMarketPrice") or info.get("currentPrice"),
        "currency": info.get("currency"),
        "totalAssets": info.get("totalAssets"),
        "expenseRatio": (
            info.get("netExpenseRatio")
            or info.get("annualReportExpenseRatio")
            or info.get("expenseRatio")
        ),
        "yield": info.get("yield"),
        "ytdReturn": info.get("ytdReturn"),
        "oneYearReturn": info.get("oneYearReturn") or info.get("annualizedReturn"),
        "threeYearAverageReturn": info.get("threeYearAverageReturn"),
        "fiveYearAverageReturn": info.get("fiveYearAverageReturn"),
        "beta3Year": info.get("beta3Year"),
        # OHLCV (driving the Market Data sub-panel)
        "open": info.get("regularMarketOpen") or info.get("open"),
        "high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
        "low": info.get("dayLow") or info.get("regularMarketDayLow"),
        "close": info.get("previousClose") or info.get("regularMarketPreviousClose"),
        "volume": info.get("regularMarketVolume") or info.get("volume"),
        # Family / category context (handy for downstream views)
        "fundFamily": info.get("fundFamily"),
        "category": info.get("category"),
        "legalType": info.get("legalType"),
    }


def _project_funds_data(fd: Any) -> Dict[str, Any]:
    """Project Yahoo's funds_data — top holdings, sector + asset-class
    weights — into FundGolden.assetAllocation shape.
    """
    out: Dict[str, Any] = {}

    # Holdings → Holding[] (look-through). yfinance typically gives the top
    # ~10; an issuer-side parser would give the full constituent list. Field
    # naming matches the renamed ontology entity (Fund.yml → FundGolden.holdings).
    try:
        df = fd.top_holdings
        if df is not None and not df.empty:
            out["holdings"] = [
                {
                    "identifier": str(symbol),
                    "name": row.get("Name") or str(symbol),
                    "weight": float(row.get("Holding Percent") or 0.0),
                    "assetClass": "EQUITY",
                }
                for symbol, row in df.iterrows()
                if (row.get("Holding Percent") or 0.0) > 0
            ]
    except Exception:  # noqa: BLE001 — funds_data shapes vary
        pass

    # Sector weightings → bySector[]
    try:
        sw = fd.sector_weightings or {}
        if sw:
            out["bySector"] = [
                {"sector": _SECTOR_LABEL.get(k, k.replace("_", " ").title()), "percentage": float(v)}
                for k, v in sw.items()
                if v is not None and float(v) > 0
            ]
    except Exception:  # noqa: BLE001
        pass

    # Asset-class buckets → byAssetClass[]
    try:
        ac = fd.asset_classes or {}
        if ac:
            agg: Dict[str, float] = {}
            for k, v in ac.items():
                if v is None:
                    continue
                bucket = _ASSET_CLASS_LABEL.get(k, "OTHER")
                agg[bucket] = agg.get(bucket, 0.0) + float(v)
            out["byAssetClass"] = [
                {"type": k, "percentage": round(v, 6)} for k, v in agg.items() if v > 0
            ]
    except Exception:  # noqa: BLE001
        pass

    return out


def fetch_yahoo_fund(isin: str, *, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Look up `isin` on yfinance, projected and disk-cached.

    Pulls `Ticker.info` (NAV / TER / OHLCV / …) and `Ticker.funds_data`
    (top holdings, sector weights, asset-class split) in one shot. Cache
    entry contains both projections so the frontend can render the
    allocation sub-panels without a second API call.
    """
    cached = _cache_path(isin)
    if use_cache and cached.exists():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    import yfinance as yf

    try:
        ticker = yf.Ticker(isin)
        info = ticker.info or {}
    except Exception as exc:  # noqa: BLE001 — yfinance throws everything
        log.warning("  %s: yfinance error %s", isin, exc)
        return None

    if not info or not info.get("symbol"):
        # Cache negative outcomes too so repeated runs don't re-hit Yahoo.
        cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
        return None

    projected = _project_yahoo_info(info)
    try:
        projected["assetAllocation"] = _project_funds_data(ticker.funds_data)
    except Exception:  # noqa: BLE001 — funds_data may not exist for this ticker
        projected["assetAllocation"] = {}

    try:
        cached.write_text(json.dumps(projected), encoding="utf-8")
    except OSError as exc:
        log.warning("  %s: cache write failed %s", isin, exc)
    return projected


# ---------------------------------------------------------------------------
# NDJSON apply
# ---------------------------------------------------------------------------

def _isin_of(doc: Dict[str, Any]) -> Optional[str]:
    for entry in doc.get("identifierList") or []:
        if (entry.get("type") or "").lower() == "isin":
            return entry.get("identifier")
    return None


def _apply(doc: Dict[str, Any], yhoo: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
    """Fill-missing-only enrichment of a single FundGolden doc."""
    if yhoo.get("_negative"):
        return doc

    currency = doc.get("currencyOfDenomination") or yhoo.get("currency")

    # ── Fees ────────────────────────────────────────────────────────────
    ter = yhoo.get("expenseRatio")
    if ter is not None and doc.get("totalExpenseRatio") is None:
        doc["totalExpenseRatio"] = ter
        fees = doc.setdefault("fees", {})
        ongoing = fees.setdefault("ongoing", {})
        ongoing.setdefault("totalExpenseRatio", ter)

    # ── Market data ─────────────────────────────────────────────────────
    md = doc.get("marketData") or {}
    if yhoo.get("navPrice") is not None and "nav" not in md and currency:
        md["nav"] = {"type": "actual", "value": yhoo["navPrice"], "currency": currency}
        md.setdefault("navCurrency", currency)
    if yhoo.get("regularMarketPrice") is not None and "marketPrice" not in md and currency:
        md["marketPrice"] = {
            "type": "actual",
            "value": yhoo["regularMarketPrice"],
            "currency": currency,
        }
    if yhoo.get("totalAssets") is not None and "aum" not in md and currency:
        md["aum"] = {"amount": yhoo["totalAssets"], "currency": currency}
    for k in ("open", "high", "low", "close", "volume"):
        if yhoo.get(k) is not None and md.get(k) is None:
            md[k] = yhoo[k]
    for src_key, dst_key in (
        ("ytdReturn", "ytdReturn"),
        ("oneYearReturn", "oneYearReturn"),
        ("threeYearAverageReturn", "threeYearReturn"),
        ("fiveYearAverageReturn", "fiveYearReturn"),
    ):
        value = yhoo.get(src_key)
        if value is not None and md.get(dst_key) is None:
            md[dst_key] = value
    if yhoo.get("beta3Year") is not None and md.get("volatility1y") is None:
        md["volatility1y"] = yhoo["beta3Year"]
    md.setdefault("asOf", now_iso)
    md.setdefault("sourceMic", (doc.get("primaryListing") or {}).get("mic"))
    doc["marketData"] = md

    # ── Identifiers + primary-listing ticker ────────────────────────────
    yhoo_symbol = yhoo.get("yahooSymbol")
    listing = doc.get("primaryListing") or {}
    if yhoo_symbol and not listing.get("ticker"):
        listing["ticker"] = yhoo_symbol
        doc["primaryListing"] = listing
    if yhoo_symbol:
        ids: List[Dict[str, str]] = doc.setdefault("identifierList", [])
        if not any(
            (e.get("type") or "").lower() == "tickersymbol" and e.get("identifier") == yhoo_symbol
            for e in ids
        ):
            ids.append({"identifier": yhoo_symbol, "type": "tickerSymbol"})

    # ── Asset allocation + look-through ────────────────────────────────
    alloc = yhoo.get("assetAllocation") or {}
    if alloc:
        existing = doc.get("assetAllocation") or {}
        # Fill missing dimensions only — don't overwrite curated allocations.
        for key in ("holdings", "bySector", "byAssetClass", "byRegion"):
            if alloc.get(key) and not existing.get(key):
                existing[key] = alloc[key]
        if existing:
            doc["assetAllocation"] = existing

    return doc


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich a FundGolden NDJSON file from Yahoo Finance (by ISIN)."
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Input FundGolden NDJSON file.",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output NDJSON (defaults to overwriting --input).",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Bypass the on-disk per-ISIN cache for this run.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out = args.output or args.input

    if not args.input.exists():
        sys.exit(f"Input not found: {args.input}")

    docs: List[Dict[str, Any]] = []
    with args.input.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                docs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.warning("  bad JSON: %s", exc)

    now_iso = datetime.now(timezone.utc).isoformat()
    resolved = 0
    enriched_count = 0
    for doc in docs:
        isin = _isin_of(doc)
        if not isin:
            continue
        yhoo = fetch_yahoo_fund(isin, use_cache=not args.no_cache)
        if not yhoo:
            continue
        resolved += 1
        if yhoo.get("_negative"):
            continue
        _apply(doc, yhoo, now_iso)
        enriched_count += 1
        log.info(
            "  %s → ticker=%s ter=%s nav=%s aum=%s",
            isin,
            yhoo.get("yahooSymbol"),
            yhoo.get("expenseRatio"),
            yhoo.get("navPrice") or yhoo.get("regularMarketPrice"),
            yhoo.get("totalAssets"),
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False))
            fh.write("\n")

    log.info(
        "Wrote %d documents (%d ISINs resolved, %d enriched) to %s",
        len(docs), resolved, enriched_count, out,
    )


if __name__ == "__main__":
    main()
