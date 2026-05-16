"""Agentic adapter for `pipeline.gold.equity_yahoo`.

Wraps `fetch_by_identifier`, strips assembler-owned fields (`goldenId`,
`recordMeta`), and returns the rest as a SourceFetchResult patch plus the
SourceAttribution rows recorded by the underlying fetcher.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.equity_yahoo import fetch_by_identifier

_ASSEMBLER_OWNED_FIELDS = {"goldenId", "recordMeta"}


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],
) -> Optional[SourceFetchResult]:
    # If an earlier source (e.g. equity_parquet_seed) already resolved a
    # ticker, prefer it — saves a redundant ISIN → ticker round-trip and
    # avoids the parquet lookup yfinance can't do.
    if identifier_kind == "isin":
        existing_ticker = (current.get("primaryListing") or {}).get("ticker")
        if existing_ticker:
            golden = fetch_by_identifier("ticker", existing_ticker)
        else:
            golden = fetch_by_identifier("isin", identifier_value)
    else:
        golden = fetch_by_identifier(identifier_kind, identifier_value)
    if golden is None:
        return None

    dumped = golden.model_dump(exclude_none=True, mode="json")
    record_meta = dumped.get("recordMeta", {}) or {}
    sot_rows = list(record_meta.get("sourceOfTruth", []))
    patch = {k: v for k, v in dumped.items() if k not in _ASSEMBLER_OWNED_FIELDS}

    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)
