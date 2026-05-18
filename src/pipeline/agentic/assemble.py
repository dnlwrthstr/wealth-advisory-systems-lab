"""Top-level entrypoint — assemble a golden record from a single identifier.

`assemble_golden(scope, identifier)` runs the planner loop, then fills the
assembler-owned fields (`goldenId`, `recordMeta`) from accumulated state
before returning. It does NOT write to OpenSearch — the caller (an
`instrument-api` endpoint, a CLI, or a skill) decides whether to PUT.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pipeline.agentic.manifest import compute_gaps, manifest_for, quality_score
from pipeline.agentic.planner import DEFAULT_MAX_COST_CLASS, PlannerTrace, run_planner
from pipeline.agentic.registry import sources_for

# Bumped in lockstep with the per-scope ontology — see equity_yahoo.SCHEMA_VERSION.
_SCHEMA_VERSION = "0.2.0"


@dataclass
class AssembleResult:
    scope: str
    identifier: Dict[str, str]
    record: Dict[str, Any]
    quality_score: float
    remaining_gaps: List[str]
    provenance: List[Dict[str, Any]]
    trace: PlannerTrace
    run_id: str


def assemble_golden(
    scope: str,
    identifier: Dict[str, str],
    *,
    budget: int = 10,
    max_cost_class: str = DEFAULT_MAX_COST_CLASS,
    allowed_llm_skills: Optional[set[str]] = None,
    run_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> AssembleResult:
    """Assemble a golden record for the given (scope, identifier).

    `identifier` is `{"kind": "isin"|"ticker"|..., "value": "..."}`.
    `max_cost_class` caps which sources are eligible — defaults to
    "web_fetch" so LLM-skill sources are opt-in (callers pass
    "llm_skill" to enable them). `allowed_llm_skills` further restricts
    which llm_skill sources may run; see `planner.run_planner`.
    """
    _validate_identifier(identifier)
    run_id = run_id or f"agentic-{scope}-{uuid.uuid4().hex[:8]}"
    now = now or datetime.now(timezone.utc)

    manifest = manifest_for(scope)
    sources = sources_for(scope)

    current, provenance, trace = run_planner(
        scope=scope,
        identifier_kind=identifier["kind"],
        identifier_value=identifier["value"],
        manifest=manifest,
        sources=sources,
        budget=budget,
        max_cost_class=max_cost_class,
        allowed_llm_skills=allowed_llm_skills,
    )

    quality = quality_score(manifest, current)
    _fill_assembled(scope, current, identifier, provenance, run_id, now, quality)

    return AssembleResult(
        scope=scope,
        identifier=dict(identifier),
        record=current,
        quality_score=quality,
        remaining_gaps=sorted(compute_gaps(manifest, current)),
        provenance=provenance,
        trace=trace,
        run_id=run_id,
    )


def _validate_identifier(identifier: Dict[str, str]) -> None:
    if not isinstance(identifier, dict) or "kind" not in identifier or "value" not in identifier:
        raise ValueError("identifier must be {'kind': ..., 'value': ...}")
    if not identifier["value"]:
        raise ValueError("identifier.value must be non-empty")


def _fill_assembled(
    scope: str,
    current: Dict[str, Any],
    identifier: Dict[str, str],
    provenance: List[Dict[str, Any]],
    run_id: str,
    now: datetime,
    quality: float,
) -> None:
    """Populate assembler-owned fields (`goldenId`, `recordMeta`, scope extras)."""
    now_iso = now.isoformat()

    # Scope-specific identity fields. For issuer, the LEI identifier is also
    # the canonical issuerId + lei value; the per-instrument scopes derive
    # goldenId from the ISIN already in `current.identifierList`.
    if scope == "issuer" and identifier.get("kind") == "lei":
        lei_value = identifier["value"]
        current.setdefault("lei", lei_value)
        current.setdefault("issuerId", f"ISS-{lei_value}")

    if "goldenId" not in current:
        current["goldenId"] = _derive_golden_id(scope, current, identifier)

    current["recordMeta"] = {
        "schemaVersion": _SCHEMA_VERSION,
        "goldenAsOf": now_iso,
        "ingestionRunId": run_id,
        "sourceOfTruth": provenance or [
            # Sentinel row so the required list is non-empty even when no source ran.
            {"fieldGroup": "assembler", "source": "agentic-platform", "sourceTimestamp": now_iso}
        ],
        "qualityScore": quality,
        "isActive": True,
    }


def _derive_golden_id(scope: str, current: Dict[str, Any], identifier: Dict[str, str]) -> str:
    """Mirror the goldenId conventions used by the legacy fetchers."""
    prefix = {"equity": "EQG", "bond": "BG", "fund": "FG", "issuer": "ISS"}.get(scope, scope.upper())
    if scope == "issuer" and identifier.get("kind") == "lei":
        return f"ISS-{identifier['value']}"
    isin = _identifier_of_type(current.get("identifierList") or [], "isin")
    mic = ((current.get("primaryListing") or {}).get("mic"))
    if isin and mic:
        return f"{prefix}-{isin}-{mic}-001"
    if isin:
        return f"{prefix}-{isin}-001"
    return f"{prefix}-{identifier['value']}-001"


def _identifier_of_type(identifiers: List[Dict[str, Any]], kind: str) -> Optional[str]:
    for entry in identifiers:
        if entry.get("type") == kind and entry.get("identifier"):
            return entry["identifier"]
    return None
