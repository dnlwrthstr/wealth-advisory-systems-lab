"""Enrich a FundGolden NDJSON file from Yahoo Finance, by ISIN.

For every fund document in the input file we look up the share-class
ISIN via yfinance (`Ticker(isin)`), then fill the fields that FIRDS
doesn't carry: NAV, market price, AUM, OHLCV, the resolved Yahoo
symbol (back into `primaryListing.ticker` plus `identifierList`), TER,
trailing-period returns (both `marketData.{ytdReturn,…}` headline
fields and the structured `performance.returns` block on the
PerformanceSnapshot), and a coarse `performance.volatility1y` proxy
from beta3Year. Results are cached on disk so repeat runs are free.

What this does NOT cover: fees beyond TER, dealing terms, SRRI / SRI,
service providers, Sharpe / Sortino / information ratios, tracking
error, max drawdown, prospectus-level static data — those need
fact-sheet parsing (see the `find-and-parse-factsheet` skill) or a
returns time-series we don't pull here.
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


def merge_source_of_truth(
    record_meta: Dict[str, Any],
    entries: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Merge `entries` into `record_meta.sourceOfTruth`, deduping by
    (fieldGroup, source). When a duplicate is found, the *new* entry's
    sourceTimestamp wins so the audit trail reflects the most recent
    enrichment. Returns the updated record_meta.
    """
    sot: List[Dict[str, Any]] = list(record_meta.get("sourceOfTruth") or [])
    index = {
        (e.get("fieldGroup"), e.get("source")): i
        for i, e in enumerate(sot)
    }
    for entry in entries:
        key = (entry.get("fieldGroup"), entry.get("source"))
        if key in index:
            sot[index[key]] = entry
        else:
            sot.append(entry)
            index[key] = len(sot) - 1
    record_meta["sourceOfTruth"] = sot
    return record_meta


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
    "stock_position": "EQUITY",
    "bond_position": "FIXED_INCOME",
    "cash_position": "CASH",
    "preferred_position": "EQUITY",
    "convertible_position": "FIXED_INCOME",
    "other_position": "OTHER",
}


def _normalize_return(value: Optional[float]) -> Optional[float]:
    """Coerce a yfinance return value to a decimal fraction.

    yfinance is internally inconsistent: `threeYearAverageReturn` and
    `fiveYearAverageReturn` come back as decimals (0.21 = 21 %), but
    `ytdReturn` comes back as a percent-form value (5.68 = 5.68 %) for
    funds / ETFs. The ontology declares all of these as decimals
    (`ReturnsBreakdown` and `MarketDataSnapshot` both use `type: number`
    described as "decimal"), so we normalise here. Any value strictly
    greater than 1.0 is assumed to be the percent form and divided by
    100; a real annual return above 100 % would be extraordinary for a
    diversified fund and out of scope.
    """
    if value is None:
        return None
    return value / 100.0 if value > 1.0 else value


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
        "ytdReturn": _normalize_return(info.get("ytdReturn")),
        "oneYearReturn": _normalize_return(
            info.get("oneYearReturn") or info.get("annualizedReturn")
        ),
        "threeYearAverageReturn": _normalize_return(info.get("threeYearAverageReturn")),
        "fiveYearAverageReturn": _normalize_return(info.get("fiveYearAverageReturn")),
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
    touched_groups: List[str] = []

    # ── Fees ────────────────────────────────────────────────────────────
    # yfinance returns `netExpenseRatio` in percentage form (0.2 = 0.20 %).
    # The ontology schema is decimal (0.002 = 0.20 %), so divide. Sanity bound
    # at 5 % — anything higher is definitely the yfinance percentage form;
    # anything ≤ 0.05 is already a decimal (this also catches re-runs against
    # docs we wrote pre-fix).
    ter = yhoo.get("expenseRatio")
    if ter is not None:
        ter_decimal = ter / 100.0 if ter > 0.05 else ter
        existing = doc.get("totalExpenseRatio")
        if existing is None or existing > 0.05:
            doc["totalExpenseRatio"] = round(ter_decimal, 6)
            fees = doc.setdefault("fees", {})
            ongoing = fees.setdefault("ongoing", {})
            ongoing["totalExpenseRatio"] = round(ter_decimal, 6)
            touched_groups.append("fees")

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
        if value is not None:
            existing = md.get(dst_key)
            # Overwrite a stale percent-form value (> 1.0 — legacy pre-
            # normalisation runs wrote ytdReturn = 5.68 instead of 0.0568).
            if existing is None or (isinstance(existing, (int, float)) and existing > 1.0):
                md[dst_key] = value
    if yhoo.get("beta3Year") is not None and md.get("volatility1y") is None:
        md["volatility1y"] = yhoo["beta3Year"]
    md.setdefault("asOf", now_iso)
    md.setdefault("sourceMic", (doc.get("primaryListing") or {}).get("mic"))
    doc["marketData"] = md
    if any(yhoo.get(k) is not None for k in
           ("navPrice", "regularMarketPrice", "totalAssets",
            "open", "high", "low", "close", "volume",
            "ytdReturn", "oneYearReturn",
            "threeYearAverageReturn", "fiveYearAverageReturn", "beta3Year")):
        touched_groups.append("marketData")

    # ── Performance snapshot ────────────────────────────────────────────
    # FundGolden.performance is a structured PerformanceSnapshot
    # (`returns: ReturnsBreakdown`, plus tracking error, info / Sharpe /
    # Sortino ratios, volatility, drawdown). yfinance gives us trailing
    # total returns and a 3-year beta only — Sharpe/Sortino/tracking error
    # need a benchmark series we don't pull here. So we populate just
    # what we honestly have:
    #
    #   returns.ytd, oneYear, threeYearAnn, fiveYearAnn  ← yfinance trailing
    #   volatility1y                                      ← beta3Year as a
    #                                                       coarse risk proxy
    #                                                       (same approximation
    #                                                       marketData.volatility1y
    #                                                       already uses — beta
    #                                                       is not realised vol,
    #                                                       it's the slope vs
    #                                                       market; we keep it
    #                                                       until a real vol
    #                                                       feed is wired)
    perf_returns: Dict[str, float] = {}
    for src_key, dst_key in (
        ("ytdReturn", "ytd"),
        ("oneYearReturn", "oneYear"),
        ("threeYearAverageReturn", "threeYearAnn"),
        ("fiveYearAverageReturn", "fiveYearAnn"),
    ):
        value = yhoo.get(src_key)
        if value is not None:
            perf_returns[dst_key] = value
    if perf_returns or yhoo.get("beta3Year") is not None:
        perf = doc.get("performance") or {}
        if perf_returns and not perf.get("returns"):
            perf["returns"] = perf_returns
        if yhoo.get("beta3Year") is not None and perf.get("volatility1y") is None:
            perf["volatility1y"] = yhoo["beta3Year"]
        perf.setdefault("asOf", now_iso[:10])  # PerformanceSnapshot.asOf is a date
        doc["performance"] = perf
        touched_groups.append("performance")

    # ── Identifiers + primary-listing ticker ────────────────────────────
    yhoo_symbol = yhoo.get("yahooSymbol")
    listing = doc.get("primaryListing") or {}
    if yhoo_symbol and not listing.get("ticker"):
        listing["ticker"] = yhoo_symbol
        doc["primaryListing"] = listing
        touched_groups.append("primaryListing")
    if yhoo_symbol:
        ids: List[Dict[str, str]] = doc.setdefault("identifierList", [])
        if not any(
            (e.get("type") or "").lower() == "ticker_symbol" and e.get("identifier") == yhoo_symbol
            for e in ids
        ):
            ids.append({"identifier": yhoo_symbol, "type": "ticker_symbol"})
            touched_groups.append("identifiers")

    # ── Asset allocation + look-through ────────────────────────────────
    alloc = yhoo.get("assetAllocation") or {}
    if alloc:
        existing = doc.get("assetAllocation") or {}
        added_any = False
        # Fill missing dimensions only — don't overwrite curated allocations.
        for key in ("holdings", "bySector", "byAssetClass", "byRegion"):
            if alloc.get(key) and not existing.get(key):
                existing[key] = alloc[key]
                added_any = True
        if existing:
            doc["assetAllocation"] = existing
        if added_any:
            if alloc.get("holdings"):
                touched_groups.append("holdings")
            if alloc.get("bySector") or alloc.get("byAssetClass") or alloc.get("byRegion"):
                touched_groups.append("assetAllocation")

    # ── Provenance: append/refresh sourceOfTruth for the groups we filled ──
    if touched_groups:
        record_meta = doc.setdefault("recordMeta", {
            "schemaVersion": "0.2.0",
            "goldenAsOf": now_iso,
            "sourceOfTruth": [],
            "isActive": True,
        })
        record_meta["goldenAsOf"] = now_iso  # most recent enrichment
        merge_source_of_truth(
            record_meta,
            [
                {"fieldGroup": fg, "source": "yfinance", "sourceTimestamp": now_iso}
                for fg in sorted(set(touched_groups))
            ],
        )

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
