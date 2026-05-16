"""Gap-driven planner — picks the next source to call.

The loop:

  1. Compute current gaps from `manifest_for(scope)` + `current` state.
  2. From the registry, find sources that
       (a) cover the scope,
       (b) accept the identifier kind,
       (c) have not been called yet this run,
       (d) produce at least one currently-unfilled field.
  3. Rank candidates by (gap_coverage desc, confidence desc, cost asc).
  4. Invoke the top candidate's adapter; merge the result.
  5. Stop when there are no relevant gaps left, no candidate covers any
     gap, or the budget is exhausted.

Side-effect-free: the planner mutates only its own `current` dict and
returns it; nothing here writes to OpenSearch.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from pipeline.agentic.manifest import FieldSpec, compute_gaps
from pipeline.agentic.merger import SourceFetchResult, merge_patch
from pipeline.agentic.registry import SourceDescriptor

log = logging.getLogger(__name__)


@dataclass
class PlannerTrace:
    """Audit trail of the planner's decisions for a single assembly run."""
    iterations: int = 0
    invocations: List[Dict[str, Any]] = field(default_factory=list)
    stopped_reason: str = ""


def _rank(source: SourceDescriptor, gap_set: set[str]) -> tuple[int, int, int]:
    """Cheap before expensive, high-confidence before low, wide before narrow.

    The intuition: lock in what's easy first (local files, cached lookups),
    then spend network calls and LLM time only on the residual gaps. The
    fill-empty-only merger ensures the cheaper source's values aren't
    overwritten when the expensive one runs later.
    """
    coverage = len(set(source.produces_fields) & gap_set)
    return (source.cost_rank, -source.confidence_rank, -coverage)


def run_planner(
    *,
    scope: str,                    # noqa: ARG001 — reserved for scope-aware ranking
    identifier_kind: str,
    identifier_value: str,
    manifest: Dict[str, FieldSpec],
    sources: List[SourceDescriptor],
    budget: int = 10,
    invoker: Optional[Callable[[SourceDescriptor, str, str, Dict[str, Any]], Optional[SourceFetchResult]]] = None,
) -> tuple[Dict[str, Any], List[Dict[str, Any]], PlannerTrace]:
    """Run the planner loop; return (current, provenance_rows, trace).

    `invoker` is the function that actually calls a source. Defaults to
    `descriptor.load_callable()(identifier_kind, identifier_value, current)`,
    but tests can pass their own to mock real network calls.
    """
    if invoker is None:
        invoker = _default_invoker

    current: Dict[str, Any] = {}
    provenance: List[Dict[str, Any]] = []
    called: set[str] = set()
    trace = PlannerTrace()

    for iteration in range(1, budget + 1):
        trace.iterations = iteration
        gaps = compute_gaps(manifest, current)
        if not gaps:
            trace.stopped_reason = "all important gaps filled"
            break

        candidates = [
            s for s in sources
            if s.id not in called
            and s.accepts_identifier(identifier_kind)
            and set(s.produces_fields) & gaps
        ]
        if not candidates:
            trace.stopped_reason = "no remaining source covers any gap"
            break

        candidates.sort(key=lambda s: _rank(s, gaps))
        chosen = candidates[0]
        called.add(chosen.id)

        try:
            result = invoker(chosen, identifier_kind, identifier_value, current)
        except Exception as exc:  # noqa: BLE001 — adapters surface diverse errors
            log.warning("source %s raised: %s", chosen.id, exc)
            trace.invocations.append({"source": chosen.id, "outcome": "error", "error": str(exc)})
            continue

        if result is None:
            trace.invocations.append({"source": chosen.id, "outcome": "no_data"})
            continue

        written = merge_patch(current, result.patch)
        provenance.extend(result.source_of_truth_rows)
        trace.invocations.append({
            "source": chosen.id,
            "outcome": "ok",
            "fields_written": written,
            "fields_skipped_already_filled": sorted(set(result.patch) - set(written)),
        })
    else:
        trace.stopped_reason = "budget exhausted"

    return current, provenance, trace


def _default_invoker(
    descriptor: SourceDescriptor,
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],
) -> Optional[SourceFetchResult]:
    fn = descriptor.load_callable()
    return fn(identifier_kind, identifier_value, current)
