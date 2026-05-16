"""Field manifest = pydantic golden model crossed with an annotation YAML.

The ontology stays purely descriptive (per `ontology/`). Agentic-platform
annotations — which fields the planner should care about, whether a field
is sourced externally vs derived/assembled — live in the YAML files under
`pipeline/agentic/annotations/`. They are self-documenting: every
top-level field of the golden model is listed explicitly.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import yaml
from pydantic import BaseModel

_ANNOTATIONS_DIR = Path(__file__).parent / "annotations"

# Scope → fully qualified pydantic model. New scopes register here.
_SCOPE_MODELS: Dict[str, Tuple[str, str]] = {
    "equity": ("universe.models", "EquityGolden"),
    "bond": ("universe.models", "BondGolden"),
    "fund": ("universe.models", "FundGolden"),
    "issuer": ("universe.models", "IssuerGolden"),
}

VALID_REQUIREMENTS = {"required", "important", "optional"}
VALID_KINDS = {"source", "derived", "assembled"}


@dataclass(frozen=True)
class FieldSpec:
    """One row of the manifest — what we know about a single golden field."""
    path: str
    structural_required: bool        # whether pydantic itself marks it required
    requirement: str                 # planner tier: required | important | optional
    kind: str                        # source | derived | assembled
    description: Optional[str] = None
    notes: Optional[str] = None

    @property
    def is_source_fillable(self) -> bool:
        return self.kind == "source"

    @property
    def is_planner_relevant(self) -> bool:
        """A field the planner should actively try to fill via sources."""
        return self.kind == "source" and self.requirement != "optional"


def _load_model(scope: str) -> type[BaseModel]:
    if scope not in _SCOPE_MODELS:
        raise ValueError(f"unknown scope {scope!r}; known: {sorted(_SCOPE_MODELS)}")
    module_name, class_name = _SCOPE_MODELS[scope]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def _load_annotations(scope: str) -> Dict[str, Dict[str, Any]]:
    path = _ANNOTATIONS_DIR / f"{scope}.yml"
    if not path.exists():
        raise FileNotFoundError(f"annotation file missing for scope {scope!r}: {path}")
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    return doc.get("fields", {}) or {}


def manifest_for(scope: str) -> Dict[str, FieldSpec]:
    """Build the per-scope manifest by overlaying annotations onto pydantic.

    Raises `ValueError` if the annotation file does not list exactly the
    top-level fields of the pydantic model — the self-documenting format
    is a hard contract: a mismatch means either the ontology evolved or
    the annotation file drifted, and the agent should not run with a stale
    view of the world.
    """
    model = _load_model(scope)
    annotations = _load_annotations(scope)

    model_fields = set(model.model_fields)
    annotated = set(annotations)
    missing_in_yaml = model_fields - annotated
    extra_in_yaml = annotated - model_fields
    if missing_in_yaml or extra_in_yaml:
        raise ValueError(
            f"annotation file for scope {scope!r} is out of sync with pydantic.\n"
            f"  missing in YAML : {sorted(missing_in_yaml)}\n"
            f"  extra in YAML   : {sorted(extra_in_yaml)}"
        )

    out: Dict[str, FieldSpec] = {}
    for name, info in model.model_fields.items():
        ann = annotations[name] or {}
        req = ann.get("requirement", "optional")
        kind = ann.get("kind", "source")
        if req not in VALID_REQUIREMENTS:
            raise ValueError(f"{scope}.{name}: invalid requirement {req!r}; want one of {VALID_REQUIREMENTS}")
        if kind not in VALID_KINDS:
            raise ValueError(f"{scope}.{name}: invalid kind {kind!r}; want one of {VALID_KINDS}")
        out[name] = FieldSpec(
            path=name,
            structural_required=info.is_required(),
            requirement=req,
            kind=kind,
            description=ann.get("description"),
            notes=ann.get("notes"),
        )
    return out


def compute_gaps(
    manifest: Dict[str, FieldSpec],
    current: Dict[str, Any],
    *,
    requirement_floor: str = "important",
) -> set[str]:
    """Return the planner-relevant field paths still null in `current`.

    `requirement_floor` controls the minimum tier the planner cares about:
    "important" includes required+important; "optional" includes everything.
    Only `kind=source` fields are considered — derived/assembled are the
    assembler's responsibility.
    """
    tiers = _tiers_at_or_above(requirement_floor)
    return {
        path
        for path, spec in manifest.items()
        if spec.is_source_fillable
        and spec.requirement in tiers
        and current.get(path) in (None, [], {})
    }


def quality_score(manifest: Dict[str, FieldSpec], current: Dict[str, Any]) -> float:
    """Fraction of `important`+`required` source-fillable fields populated."""
    relevant = [spec for spec in manifest.values() if spec.is_planner_relevant]
    if not relevant:
        return 1.0
    filled = sum(1 for s in relevant if current.get(s.path) not in (None, [], {}))
    return round(filled / len(relevant), 3)


def _tiers_at_or_above(floor: str) -> Iterable[str]:
    if floor == "required":
        return {"required"}
    if floor == "important":
        return {"required", "important"}
    if floor == "optional":
        return VALID_REQUIREMENTS
    raise ValueError(f"unknown requirement floor {floor!r}")
