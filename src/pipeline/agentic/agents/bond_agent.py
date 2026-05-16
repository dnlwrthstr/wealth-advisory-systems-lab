"""Bond assembly agent."""
from __future__ import annotations

from pipeline.agentic.agents.base import BaseAgent


class BondAgent(BaseAgent):
    scope = "bond"
    # FIRDS covers the required bond fields; no LLM-skill source for bonds.
    default_max_cost_class = "web_fetch"
