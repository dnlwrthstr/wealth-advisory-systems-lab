"""Source registry — every agentic source is one YAML descriptor in here.

A `SourceDescriptor` declares which scopes the source covers, which
identifier kinds it accepts, which top-level golden fields it can
populate, plus confidence / cost class used by the planner to break ties.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

_REGISTRY_DIR = Path(__file__).parent

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}
_COST_RANK = {"file_read": 0, "api_call": 1, "web_fetch": 2, "llm_skill": 3}


def cost_rank_of(cost_class: str) -> int:
    """Public accessor for the planner's max_cost_class cap."""
    return _COST_RANK[cost_class]

_REQUIRED_KEYS = {
    "id", "module", "entrypoint", "covers",
    "requires_identifier", "produces_fields", "confidence", "cost_class",
}


@dataclass(frozen=True)
class SourceDescriptor:
    id: str
    module: str
    entrypoint: str
    covers: Tuple[str, ...]
    requires_identifier_any_of: Tuple[str, ...]
    produces_fields: Tuple[str, ...]
    confidence: str
    cost_class: str
    description: Optional[str] = None

    def covers_scope(self, scope: str) -> bool:
        return scope in self.covers

    def accepts_identifier(self, kind: str) -> bool:
        return kind in self.requires_identifier_any_of

    @property
    def confidence_rank(self) -> int:
        return _CONFIDENCE_RANK.get(self.confidence, 0)

    @property
    def cost_rank(self) -> int:
        return _COST_RANK.get(self.cost_class, 99)

    def load_callable(self) -> Callable[..., Any]:
        mod = importlib.import_module(self.module)
        try:
            return getattr(mod, self.entrypoint)
        except AttributeError as exc:
            raise RuntimeError(
                f"source {self.id!r}: {self.module}.{self.entrypoint} not found"
            ) from exc


def _parse(doc: Dict[str, Any], origin: Path) -> SourceDescriptor:
    missing = _REQUIRED_KEYS - set(doc)
    if missing:
        raise ValueError(f"{origin}: descriptor missing keys {sorted(missing)}")
    ri = doc["requires_identifier"]
    if not isinstance(ri, dict) or "any_of" not in ri:
        raise ValueError(f"{origin}: requires_identifier must be a mapping with `any_of`")
    return SourceDescriptor(
        id=doc["id"],
        module=doc["module"],
        entrypoint=doc["entrypoint"],
        covers=tuple(doc["covers"]),
        requires_identifier_any_of=tuple(ri["any_of"]),
        produces_fields=tuple(doc["produces_fields"]),
        confidence=doc["confidence"],
        cost_class=doc["cost_class"],
        description=doc.get("description"),
    )


def load_registry(directory: Optional[Path] = None) -> List[SourceDescriptor]:
    """Load all *.yml descriptors under `directory` (defaults to this package).

    Idempotent and read-only — safe to call repeatedly.
    """
    target = directory or _REGISTRY_DIR
    sources: List[SourceDescriptor] = []
    for yml in sorted(target.glob("*.yml")):
        with yml.open(encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        if doc is None:
            continue
        sources.append(_parse(doc, yml))
    return sources


def sources_for(scope: str, directory: Optional[Path] = None) -> List[SourceDescriptor]:
    return [s for s in load_registry(directory) if s.covers_scope(scope)]
