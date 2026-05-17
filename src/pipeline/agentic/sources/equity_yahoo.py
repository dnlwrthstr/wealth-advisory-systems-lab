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
    # If an earlier source (parquet_seed or openfigi) already resolved a
    # ticker, prefer it — saves a redundant ISIN → ticker round-trip and
    # avoids parquet/OpenFIGI lookups yfinance can't do. But OpenFIGI's
    # free ISIN endpoint may hand us a non-Yahoo-compatible venue ticker
    # (e.g. CH0012221716 / ABB → "ABJ" Frankfurt stub instead of
    # "ABBN.SW"); yfinance returns sparse `.info` for those and
    # `fetch_by_identifier` yields None. When that happens — and we
    # still have the original ISIN — retry by ISIN so Yahoo's own
    # ISIN→ticker resolver gets a shot.
    golden = None
    if identifier_kind == "isin":
        existing_ticker = (
            (current.get("primaryListing") or {}).get("ticker")
            or _ticker_from_identifier_list(current.get("identifierList") or [])
        )
        if existing_ticker:
            golden = fetch_by_identifier("ticker", existing_ticker)
        if golden is None:
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


def _ticker_from_identifier_list(identifiers: list) -> Optional[str]:
    """Pick a tickerSymbol entry from a partial identifierList, if any."""
    for entry in identifiers:
        if (entry.get("type") or "").lower() == "ticker_symbol" and entry.get("identifier"):
            return entry["identifier"]
    return None
