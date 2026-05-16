"""Agentic adapter for `pipeline.gold.issuer_gleif`.

Per-LEI fetch against the GLEIF public API, projected into an IssuerGolden
partial patch. Cached on disk under ~/.cache/wealth-advisory-systems-lab/gleif/.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.gold.issuer_gleif import fetch_gleif, gleif_fields


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],  # noqa: ARG001
) -> Optional[SourceFetchResult]:
    if identifier_kind != "lei":
        return None
    record = fetch_gleif(identifier_value)
    if record is None:
        return None
    projected = gleif_fields(record)
    if not projected:
        return None

    patch: Dict[str, Any] = {}
    for src_key, dst_key in (
        ("legalName", "legalName"),
        ("domicileCountry", "domicileCountry"),
        ("headquartersCountry", "headquartersCountry"),
        ("ultimateParentLei", "ultimateParentLei"),
        ("issuerTypeFromGleif", "issuerType"),
    ):
        v = projected.get(src_key)
        if v:
            patch[dst_key] = v
    if not patch:
        return None
    sot_rows = [{"fieldGroup": "legalEntity", "source": "gleif"}]
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)
