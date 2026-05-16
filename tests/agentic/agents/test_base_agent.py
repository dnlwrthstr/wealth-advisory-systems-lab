"""BaseAgent contract — scope dispatch, defaults, override semantics, critical_gaps."""
from __future__ import annotations

from typing import Any, Dict

import pytest

from pipeline.agentic.agents import AGENTS, BaseAgent, BondAgent, EquityAgent, FundAgent
from pipeline.agentic.assemble import AssembleResult


def test_agents_registry_covers_three_scopes():
    assert set(AGENTS) == {"equity", "bond", "fund"}
    assert AGENTS["equity"] is EquityAgent
    assert AGENTS["bond"] is BondAgent
    assert AGENTS["fund"] is FundAgent


def test_each_agent_binds_its_scope():
    assert EquityAgent.scope == "equity"
    assert BondAgent.scope == "bond"
    assert FundAgent.scope == "fund"


def test_default_cost_caps_match_design():
    """Fund defaults to llm_skill so factsheet skill runs; equity/bond stay cheap."""
    assert EquityAgent.default_max_cost_class == "web_fetch"
    assert BondAgent.default_max_cost_class == "web_fetch"
    assert FundAgent.default_max_cost_class == "llm_skill"


def test_assemble_passes_scope_and_default_cost_cap(monkeypatch):
    """Agent.assemble must forward its scope + default cost cap to the planner."""
    seen: Dict[str, Any] = {}

    def fake_assemble_golden(*, scope, identifier, budget, max_cost_class):
        seen["scope"] = scope
        seen["identifier"] = identifier
        seen["budget"] = budget
        seen["max_cost_class"] = max_cost_class
        return AssembleResult(
            scope=scope,
            identifier=identifier,
            record={"goldenId": "X"},
            quality_score=0.5,
            remaining_gaps=[],
            provenance=[],
            trace=None,
            run_id="t",
        )

    monkeypatch.setattr("pipeline.agentic.agents.base.assemble_golden", fake_assemble_golden)
    EquityAgent.assemble({"kind": "isin", "value": "US0378331005"})
    assert seen["scope"] == "equity"
    assert seen["max_cost_class"] == "web_fetch"
    assert seen["budget"] == EquityAgent.default_budget


def test_assemble_caller_can_override_cost_cap(monkeypatch):
    """Explicit max_cost_class beats the agent default."""
    seen: Dict[str, Any] = {}

    def fake_assemble_golden(*, scope, identifier, budget, max_cost_class):
        seen["max_cost_class"] = max_cost_class
        return AssembleResult(
            scope=scope, identifier=identifier, record={"goldenId": "X"},
            quality_score=0.0, remaining_gaps=[], provenance=[], trace=None, run_id="t",
        )

    monkeypatch.setattr("pipeline.agentic.agents.base.assemble_golden", fake_assemble_golden)
    FundAgent.assemble(
        {"kind": "isin", "value": "IE00B4L5Y983"},
        max_cost_class="web_fetch",
    )
    assert seen["max_cost_class"] == "web_fetch"


def test_assemble_and_persist_stamps_status_and_uses_agent_default(monkeypatch):
    """Agent.assemble_and_persist must forward (scope, status, agent cost cap)."""
    seen: Dict[str, Any] = {}

    def fake(*, client, scope, identifier, budget, max_cost_class, universe_status):
        seen.update(scope=scope, status=universe_status, max_cost_class=max_cost_class)
        primary = AssembleResult(
            scope=scope, identifier=identifier, record={"goldenId": "FG-X-001"},
            quality_score=0.0, remaining_gaps=[], provenance=[], trace=None, run_id="t",
        )
        return {"primary": primary, "chained_issuers": []}

    monkeypatch.setattr("pipeline.agentic.agents.base.assemble_and_persist", fake)
    FundAgent.assemble_and_persist(
        client=object(),
        identifier={"kind": "isin", "value": "IE00B4L5Y983"},
        status="watchlist",
    )
    assert seen == {"scope": "fund", "status": "watchlist", "max_cost_class": "llm_skill"}


def test_critical_gaps_uses_required_floor(monkeypatch):
    """critical_gaps() reports `required`-tier gaps only — never `important`."""
    # Build a fake manifest with one required + one important + one optional field,
    # only the required field is missing in `current`.
    from pipeline.agentic.manifest import FieldSpec

    def fake_manifest_for(scope):
        return {
            "longName": FieldSpec(path="longName", structural_required=True,
                                  requirement="required", kind="source"),
            "marketData": FieldSpec(path="marketData", structural_required=False,
                                    requirement="important", kind="source"),
            "shareClass": FieldSpec(path="shareClass", structural_required=False,
                                    requirement="optional", kind="source"),
        }

    monkeypatch.setattr("pipeline.agentic.agents.base.manifest_for", fake_manifest_for)
    result = AssembleResult(
        scope="equity",
        identifier={"kind": "isin", "value": "X"},
        record={"shareClass": "A"},  # only optional filled
        quality_score=0.0,
        remaining_gaps=[],
        provenance=[],
        trace=None,
        run_id="t",
    )
    gaps = EquityAgent.critical_gaps(result)
    assert gaps == ["longName"]  # important gap (marketData) excluded


def test_base_agent_cannot_be_used_directly_without_scope():
    """BaseAgent.scope is empty — calling assemble on it should raise."""
    with pytest.raises(ValueError, match="unknown scope"):
        BaseAgent.assemble({"kind": "isin", "value": "X"})
