"""Agentic adapter for `pipeline.gold.equity_parquet_seed`.

Cheap (file-read), high-confidence identifier baseline. Runs first under
the cost-first planner; equity_yahoo then overlays the rest.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.equity_parquet_seed import fetch_by_isin

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
