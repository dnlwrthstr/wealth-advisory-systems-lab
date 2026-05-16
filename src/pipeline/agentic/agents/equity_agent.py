"""Equity assembly agent."""
from __future__ import annotations

from pipeline.agentic.agents.base import BaseAgent


class EquityAgent(BaseAgent):
    scope = "equity"
    # web_fetch is sufficient — openfigi + yfinance + FIRDS cover the
    # required equity fields; no LLM-skill source is registered for equity.
    default_max_cost_class = "web_fetch"
