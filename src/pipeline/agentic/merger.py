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

**Marker-based override (spec 004)**. A source can opt into list
*replacement* (rather than fill-empty-only) for specific dot-paths by
setting `SourceFetchResult.replace_paths`. The merger replaces the
existing list at each declared path verbatim, regardless of the existing
value. This unblocks the look-through use case: `fund_factsheet_skill`
writes a top-N projection (10 rows); `fund_lookthrough_skill` later
declares `replace_paths=["assetAllocation.holdings"]` to swap in the
full ~1310-row proxy list. Other sources, unaffected, keep deep
fill-empty-only behaviour.

The merger never overwrites a populated leaf outside an opt-in
`replace_paths` entry — regardless of nesting depth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Set


@dataclass(frozen=True)
class SourceFetchResult:
    """Envelope returned by every agentic source adapter.

    `replace_paths` is an opt-in list of dot-paths whose list values
    should fully replace the existing slot instead of falling under the
    default fill-empty-only semantic. Applies only when the patch value
    at that path is a list. Default empty preserves spec-003 behaviour.
    """
    patch: Dict[str, Any]
    source_of_truth_rows: List[Dict[str, Any]] = field(default_factory=list)
    replace_paths: List[str] = field(default_factory=list)


def merge_patch(
    current: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    replace_paths: Iterable[str] = (),
) -> List[str]:
    """Apply `patch` to `current` with deep fill-empty-only semantics.

    Returns the list of dot-paths actually written. Nested writes carry
    their full path (e.g. `"assetAllocation.holdings"`); top-level writes
    are unprefixed (`"benchmarkName"`).

    `replace_paths` (keyword-only) is an iterable of dot-paths whose
    list-valued patches should fully replace the existing value rather
    than fall through to fill-empty-only. The directive is a no-op when
    the patch value at that path is not a list — deep-merge then applies.
    """
    return _merge(current, patch, "", set(replace_paths))


def _merge(
    current: Dict[str, Any],
    patch: Dict[str, Any],
    prefix: str,
    replace_paths: Set[str],
) -> List[str]:
    written: List[str] = []
    for field_name, value in patch.items():
        path = f"{prefix}.{field_name}" if prefix else field_name

        # Skip empty/null sentinels — never write nothing over something.
        if value in (None, "", [], {}):
            continue

        existing = current.get(field_name)

        # Marker override: source opted into full replacement for this list path.
        # List-only — directive is silently ignored when patch value is a dict
        # (falls through to the deep-merge branch) or a scalar (falls through
        # to fill-empty-only). Empty patch values are already skipped above.
        if path in replace_paths and isinstance(value, list):
            current[field_name] = value
            written.append(path)
            continue

        # Both sides are dicts and existing is populated → recurse.
        if isinstance(value, dict) and isinstance(existing, dict) and existing:
            written.extend(_merge(existing, value, path, replace_paths))
            continue

        # Existing slot empty → write the value (atomic, list, or fresh dict).
        if existing in (None, "", [], {}):
            current[field_name] = value
            written.append(path)
            continue

        # Existing slot populated and not a deep-mergeable dict → skip.
    return written
