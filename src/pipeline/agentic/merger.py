"""Field-level merge of source patches into the accumulating golden state.

Semantics: **deep fill-empty-only**. At every level of a nested dict, the
first source to populate a leaf wins; later sources patching the same leaf
are ignored. Within a single source's patch, sub-keys missing from the
current state are still written, even when the parent dict already has
other sibling keys populated.

This matches the practical need from spec 003: `fund_yahoo` populates
`assetAllocation` with sector/asset-class buckets but no holdings;
`fund_lookthrough_skill` later contributes the holdings array via a patch
shaped as `{"assetAllocation": {"holdings": [...]}}`. Shallow fill-empty
would silently drop the holdings; deep fill-empty merges them in.

Atomic types and lists are still treated as leaves — a list value is
written only when the existing slot is empty/missing. List-of-objects
deep-merge would need an identity key per source and is out of scope.

The merger never overwrites a populated leaf, regardless of nesting depth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SourceFetchResult:
    """Envelope returned by every agentic source adapter."""
    patch: Dict[str, Any]
    source_of_truth_rows: List[Dict[str, Any]] = field(default_factory=list)


def merge_patch(
    current: Dict[str, Any],
    patch: Dict[str, Any],
) -> List[str]:
    """Apply `patch` to `current` with deep fill-empty-only semantics.

    Returns the list of dot-paths actually written. Nested writes carry
    their full path (e.g. `"assetAllocation.holdings"`); top-level writes
    are unprefixed (`"benchmarkName"`).
    """
    return _merge(current, patch, "")


def _merge(
    current: Dict[str, Any],
    patch: Dict[str, Any],
    prefix: str,
) -> List[str]:
    written: List[str] = []
    for field_name, value in patch.items():
        path = f"{prefix}.{field_name}" if prefix else field_name

        # Skip empty/null sentinels — never write nothing over something.
        if value in (None, "", [], {}):
            continue

        existing = current.get(field_name)

        # Both sides are dicts and existing is populated → recurse.
        if isinstance(value, dict) and isinstance(existing, dict) and existing:
            written.extend(_merge(existing, value, path))
            continue

        # Existing slot empty → write the value (atomic, list, or fresh dict).
        if existing in (None, "", [], {}):
            current[field_name] = value
            written.append(path)
            continue

        # Existing slot populated and not a deep-mergeable dict → skip.
    return written
