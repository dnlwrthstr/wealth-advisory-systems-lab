"""BaseAgent — typed config over `assemble_golden` / `assemble_and_persist`.

Subclasses bind the scope and pick scope-specific defaults. The planner
engine is unchanged; agents exist to make the per-type entry points
explicit (clearer routing, focused tests, parallel work without
collisions) and to hold defaults that genuinely differ by type — chief
among them the cost-class cap (funds default to `llm_skill` so the
factsheet skill is in scope, equity/bond stay at `web_fetch`).
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from pipeline.agentic.assemble import AssembleResult, assemble_golden
from pipeline.agentic.manifest import compute_gaps, manifest_for
from pipeline.agentic.persist import assemble_and_persist


class BaseAgent:
    """Scope-bound facade over the agentic planner.

    Subclasses set ``scope`` and may override ``default_max_cost_class`` /
    ``default_budget``. Call sites use the class directly — no instance
    state is needed, so methods are classmethods.
    """

    scope: ClassVar[str] = ""
    default_max_cost_class: ClassVar[str] = "web_fetch"
    default_budget: ClassVar[int] = 10

    @classmethod
    def assemble(
        cls,
        identifier: Dict[str, str],
        *,
        budget: Optional[int] = None,
        max_cost_class: Optional[str] = None,
        allowed_llm_skills: Optional[set[str]] = None,
    ) -> AssembleResult:
        return assemble_golden(
            scope=cls.scope,
            identifier=identifier,
            budget=budget if budget is not None else cls.default_budget,
            max_cost_class=max_cost_class or cls.default_max_cost_class,
            allowed_llm_skills=allowed_llm_skills,
        )

    @classmethod
    def assemble_and_persist(
        cls,
        *,
        client: Any,
        identifier: Dict[str, str],
        status: str,
        budget: Optional[int] = None,
        max_cost_class: Optional[str] = None,
        allowed_llm_skills: Optional[set[str]] = None,
    ) -> Dict[str, Any]:
        return assemble_and_persist(
            client=client,
            scope=cls.scope,
            identifier=identifier,
            budget=budget if budget is not None else cls.default_budget,
            max_cost_class=max_cost_class or cls.default_max_cost_class,
            allowed_llm_skills=allowed_llm_skills,
            universe_status=status,
        )

    @classmethod
    def critical_gaps(cls, result: AssembleResult) -> List[str]:
        """Return the `required`-tier source-fillable fields still empty.

        ``result.remaining_gaps`` uses the default `important` floor (which
        is what the planner stops on). This narrower view is useful when
        the caller needs to decide whether the record is shippable at all
        vs. merely incomplete.
        """
        manifest = manifest_for(cls.scope)
        return sorted(compute_gaps(manifest, result.record, requirement_floor="required"))
