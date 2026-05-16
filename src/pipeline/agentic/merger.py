"""Field-level merge of source patches into the accumulating golden state.

Semantics (first slice): **fill-empty-only**. The first source to populate
a field wins; subsequent sources that produce the same field are ignored
for that field. This matches what `fund_yahoo_enrich` does and is the
safe default when one source is curated and another is auto-fetched.

Future iterations can replace this with a precedence-aware merger that
overwrites lower-confidence values with higher-confidence ones, using
the `confidence` declared on each SourceDescriptor.
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
    """Apply `patch` to `current` with fill-empty-only semantics.

    Returns the list of field paths actually written (i.e. the ones that
    were empty in `current` and the patch supplied a non-empty value).
    """
    written: List[str] = []
    for field_name, value in patch.items():
        if value in (None, [], {}):
            continue
        existing = current.get(field_name)
        if existing in (None, [], {}):
            current[field_name] = value
            written.append(field_name)
    return written
