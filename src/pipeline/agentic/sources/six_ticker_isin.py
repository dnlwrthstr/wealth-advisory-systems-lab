"""Agentic adapter for the curated SIX ticker → ISIN map.

When the user enters a SIX-listed ticker (e.g. `LISN.SW`), this is
typically the first source the planner picks (file_read cost). It
resolves the ticker to its ISIN and writes that ISIN into
`identifierList`, unlocking equity_firds and valor derivation for
the rest of the loop.

ISIN-only output. Doesn't touch primaryListing/longName/etc — those
come from equity_yahoo + equity_firds later.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.six_ticker_isin import isin_for_ticker
from pipeline.silver import valor_from_isin


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],  # noqa: ARG001 — required by adapter signature
) -> Optional[SourceFetchResult]:
    if identifier_kind != "ticker":
        return None
    isin = isin_for_ticker(identifier_value)
    if not isin:
        return None
    identifiers = [
        {"identifier": isin, "type": "isin"},
        {"identifier": identifier_value, "type": "tickerSymbol"},
    ]
    valor = valor_from_isin(isin)
    if valor:
        identifiers.append({"identifier": valor, "type": "valor"})
    return SourceFetchResult(
        patch={"identifierList": identifiers},
        source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "six-curated"}],
    )
