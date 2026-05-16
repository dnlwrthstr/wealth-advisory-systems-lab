"""Agentic adapter for `pipeline.gold.equity_firds.fetch_by_isin`.

Slots between openfigi (which seeds the FIGI + ticker) and equity_yahoo
(which overlays live market data). Adds LEI + multi-venue listings +
regulator-quality naming when an ISIN is available.

Accepts both isin and ticker inputs. For ticker inputs it expects an
earlier source (typically `six_ticker_isin`) to have already populated
the ISIN into `current.identifierList`; if no ISIN is on the record yet,
the adapter returns None and the planner moves on.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.equity_firds import fetch_by_isin


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],
) -> Optional[SourceFetchResult]:
    if identifier_kind == "isin":
        isin = identifier_value
    else:
        isin = _isin_from_identifier_list(current.get("identifierList") or [])
    if not isin:
        return None
    patch = fetch_by_isin(isin)
    if patch is None:
        return None

    sot_rows = [
        {"fieldGroup": fg, "source": "esma-firds"}
        for fg in _field_groups_in(patch)
    ]
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)


def _isin_from_identifier_list(identifiers: List[Dict[str, Any]]) -> Optional[str]:
    for entry in identifiers:
        if (entry.get("type") or "").lower() == "isin" and entry.get("identifier"):
            return entry["identifier"]
    return None


def _field_groups_in(patch: Dict[str, Any]) -> list[str]:
    """Map the patch keys to the SourceAttribution field-group names."""
    groups: list[str] = []
    if "longName" in patch or "cfiCode" in patch:
        groups.append("naming")
    if "currencyOfDenomination" in patch:
        groups.append("currency")
    if "issuer" in patch:
        groups.append("issuer")
    if "secondaryListings" in patch:
        groups.append("listings")
    if "lifecycleStatus" in patch or "firstTradingDate" in patch:
        groups.append("lifecycle")
    return groups
