"""Agentic adapter for OpenFIGI ISIN resolution.

Produces a minimal EquityGolden partial — identifierList (FIGI + ticker),
longName, equitySubType. Doesn't populate market data or venue; that's
equity_yahoo's job once the ticker is known.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.openfigi import SECURITY_TYPE_TO_SUBTYPE, fetch_openfigi_by_isin
from pipeline.silver import valor_from_isin


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],  # noqa: ARG001
) -> Optional[SourceFetchResult]:
    if identifier_kind != "isin":
        return None
    rec = fetch_openfigi_by_isin(identifier_value)
    if rec is None:
        return None

    identifiers: List[Dict[str, str]] = [
        {"identifier": identifier_value, "type": "isin"},
    ]
    valor = valor_from_isin(identifier_value)
    if valor:
        identifiers.append({"identifier": valor, "type": "valor"})
    if rec.get("figi"):
        identifiers.append({"identifier": rec["figi"], "type": "figi"})
    if rec.get("compositeFIGI") and rec["compositeFIGI"] != rec.get("figi"):
        identifiers.append({"identifier": rec["compositeFIGI"], "type": "figi"})
    if rec.get("ticker"):
        identifiers.append({"identifier": rec["ticker"], "type": "tickerSymbol"})

    patch: Dict[str, Any] = {"identifierList": identifiers}
    if rec.get("name"):
        patch["longName"] = rec["name"]
    sub_type = SECURITY_TYPE_TO_SUBTYPE.get(rec.get("securityType") or "")
    if sub_type:
        patch["equitySubType"] = sub_type

    sot_rows = [{"fieldGroup": "identifiers", "source": "openfigi"}]
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)
