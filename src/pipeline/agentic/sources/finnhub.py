"""Agentic adapter for Finnhub equity quote + profile.

Second equity overlay alongside equity_yahoo. Like equity_yahoo, this
adapter pulls the ticker from current state (primaryListing.ticker or
identifierList[tickerSymbol]) when given an ISIN, since Finnhub's free
tier has no direct ISIN lookup.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.finnhub import fetch_by_ticker

# Finnhub returns country names like "US" (already ISO 3166 alpha-2 for most).
# Free-text industry → IndustrySector source label.
_SOURCE_LABEL = "finnhub"


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],
) -> Optional[SourceFetchResult]:
    ticker = _resolve_ticker(identifier_kind, identifier_value, current)
    if ticker is None:
        return None
    rec = fetch_by_ticker(ticker)
    if rec is None:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    patch: Dict[str, Any] = {}
    sot_rows: List[Dict[str, str]] = []

    market_data = _build_market_data(rec, now_iso)
    if market_data:
        patch["marketData"] = market_data
        sot_rows.append({"fieldGroup": "marketData", "source": _SOURCE_LABEL, "sourceTimestamp": now_iso})

    key_figures = _build_key_figures(rec)
    if key_figures:
        patch["keyFigures"] = key_figures
        sot_rows.append({"fieldGroup": "keyFigures", "source": _SOURCE_LABEL, "sourceTimestamp": now_iso})

    if rec.get("country") and len(rec["country"]) == 2:
        patch["incorporationCountry"] = rec["country"]
        sot_rows.append({"fieldGroup": "incorporationCountry", "source": _SOURCE_LABEL})

    if rec.get("finnhubIndustry"):
        patch["industrySector"] = {
            "industryLabel": rec["finnhubIndustry"],
            "source": _SOURCE_LABEL,
        }
        sot_rows.append({"fieldGroup": "industrySector", "source": _SOURCE_LABEL})

    if rec.get("ipo"):
        patch["firstTradingDate"] = rec["ipo"]
        sot_rows.append({"fieldGroup": "firstTradingDate", "source": _SOURCE_LABEL})

    if not patch:
        return None
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)


def _resolve_ticker(kind: str, value: str, current: Dict[str, Any]) -> Optional[str]:
    if kind == "ticker":
        return value
    if kind != "isin":
        return None
    # Prefer the listing ticker; fall back to the identifierList entry.
    ticker = (current.get("primaryListing") or {}).get("ticker")
    if ticker:
        return ticker
    for entry in current.get("identifierList") or []:
        if (entry.get("type") or "").lower() == "tickersymbol" and entry.get("identifier"):
            return entry["identifier"]
    return None


def _build_market_data(rec: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
    quote = rec.get("quote") or {}
    currency = rec.get("currency")
    out: Dict[str, Any] = {}
    if quote.get("current") is not None and currency:
        out["lastTradePrice"] = {
            "type": "actual",
            "value": float(quote["current"]),
            "currency": currency,
        }
    for k_src, k_dst in (("open", "open"), ("high", "high"), ("low", "low"), ("previousClose", "close")):
        v = quote.get(k_src)
        if v is not None:
            out[k_dst] = float(v)
    if out:
        out["asOf"] = now_iso
    return out


def _build_key_figures(rec: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    mc = rec.get("marketCapitalization")
    if mc is not None and rec.get("currency"):
        # Finnhub reports market cap in millions of the local currency.
        out["marketCapitalization"] = {
            "amount": float(mc) * 1_000_000,
            "currency": rec["currency"],
        }
    so = rec.get("shareOutstanding")
    if so is not None:
        # Also in millions.
        out["sharesOutstanding"] = float(so) * 1_000_000
    return out
