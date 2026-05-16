"""Agentic adapter for `pipeline.gold.bond_firds`.

Queries ESMA FIRDS for a single ISIN, joins against the curated issuer
LEI map (`pipeline/gold/data/bond_issuers.yml`). The non-FINFOX path
for the bond scope; runs in parallel with bond_parquet (the cheaper but
FINFOX-dependent baseline) and overlays whatever bond_parquet didn't fill.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.bond_firds import fetch_by_isin

_ASSEMBLER_OWNED_FIELDS = {"goldenId", "recordMeta"}


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],  # noqa: ARG001
) -> Optional[SourceFetchResult]:
    if identifier_kind != "isin":
        return None
    golden = fetch_by_isin(identifier_value)
    if golden is None:
        return None
    dumped = golden.model_dump(exclude_none=True, mode="json")
    sot_rows = list((dumped.get("recordMeta") or {}).get("sourceOfTruth", []))
    patch = {k: v for k, v in dumped.items() if k not in _ASSEMBLER_OWNED_FIELDS}
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)
