"""Agentic adapter for the Yahoo Finance fund overlay.

Wraps `pipeline.gold.fund_yahoo_enrich.fetch_yahoo_fund` and projects its
output into a FundGolden patch. Overlays NAV / market price / OHLCV / TER
/ asset allocation onto whatever fund_firds already established.

Cost class: api_call (cached on disk under ~/.cache/wealth-advisory-systems-lab/yahoo-funds/).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.fund_yahoo_enrich import fetch_yahoo_fund


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],  # noqa: ARG001
) -> Optional[SourceFetchResult]:
    if identifier_kind != "isin":
        return None
    yhoo = fetch_yahoo_fund(identifier_value)
    if not yhoo or yhoo.get("_negative"):
        return None

    market_data = _build_market_data(yhoo)
    patch: Dict[str, Any] = {}
    if market_data:
        patch["marketData"] = market_data
    ter = yhoo.get("expenseRatio")
    if ter is not None:
        # yfinance returns TER as percentage (e.g. 0.20 for 0.20%); the
        # ontology stores it as decimal fraction. Defensive divide-by-100
        # only when the value is unambiguously percentage-shaped.
        patch["totalExpenseRatio"] = float(ter) / 100.0 if float(ter) > 0.05 else float(ter)
    asset_allocation = yhoo.get("assetAllocation") or {}
    if asset_allocation:
        # Project Yahoo's holdings + sectors + asset classes into the
        # FundGolden.assetAllocation shape, dropping the holdings list
        # which is incomplete (top ~10 only).
        proj = {k: v for k, v in asset_allocation.items() if k != "holdings"}
        if proj:
            patch["assetAllocation"] = proj

    sot_rows = [{"fieldGroup": "marketData", "source": "yfinance-funds"}]
    if ter is not None:
        sot_rows.append({"fieldGroup": "totalExpenseRatio", "source": "yfinance-funds"})
    if asset_allocation:
        sot_rows.append({"fieldGroup": "assetAllocation", "source": "yfinance-funds"})

    if not patch:
        return None
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)


def _build_market_data(yhoo: Dict[str, Any]) -> Dict[str, Any]:
    """Map yfinance projection into FundMarketDataSnapshotEmbedded shape."""
    out: Dict[str, Any] = {}
    currency = yhoo.get("currency")
    nav = yhoo.get("navPrice")
    mkt = yhoo.get("regularMarketPrice")
    if nav is not None and currency:
        out["nav"] = {"type": "actual", "value": float(nav), "currency": currency}
        out["navCurrency"] = currency
    if mkt is not None and currency:
        out["marketPrice"] = {"type": "actual", "value": float(mkt), "currency": currency}
    if yhoo.get("totalAssets") is not None and currency:
        out["aum"] = {"amount": float(yhoo["totalAssets"]), "currency": currency}
    for ohlcv_key in ("open", "high", "low", "close", "volume"):
        v = yhoo.get(ohlcv_key)
        if v is not None:
            out[ohlcv_key] = float(v)
    for ret_key in ("ytdReturn", "oneYearReturn", "threeYearAverageReturn", "fiveYearAverageReturn"):
        v = yhoo.get(ret_key)
        if v is not None:
            # Normalise the FundGolden-side return key names.
            target = {
                "ytdReturn": "ytdReturn",
                "oneYearReturn": "oneYearReturn",
                "threeYearAverageReturn": "threeYearReturn",
                "fiveYearAverageReturn": "fiveYearReturn",
            }[ret_key]
            out[target] = float(v)
    return out
