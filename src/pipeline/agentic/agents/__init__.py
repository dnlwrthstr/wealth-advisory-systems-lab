"""Per-type agents over the agentic planner.

Each agent is a thin typed entry point that binds a scope and carries the
scope-specific defaults (cost cap, budget). The planner stays the engine;
agents do not duplicate its loop.

Use:

    from pipeline.agentic.agents import EquityAgent, BondAgent, FundAgent, AGENTS

    result = EquityAgent.assemble({"kind": "isin", "value": "US0378331005"})
    AGENTS["fund"].assemble_and_persist(client=os, identifier=..., status="in_universe")
"""
from pipeline.agentic.agents.base import BaseAgent
from pipeline.agentic.agents.bond_agent import BondAgent
from pipeline.agentic.agents.equity_agent import EquityAgent
from pipeline.agentic.agents.fund_agent import FundAgent

AGENTS: dict[str, type[BaseAgent]] = {
    EquityAgent.scope: EquityAgent,
    BondAgent.scope: BondAgent,
    FundAgent.scope: FundAgent,
}

__all__ = ["BaseAgent", "EquityAgent", "BondAgent", "FundAgent", "AGENTS"]
