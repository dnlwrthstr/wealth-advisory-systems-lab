"""Fund assembly agent."""
from __future__ import annotations

from pipeline.agentic.agents.base import BaseAgent


class FundAgent(BaseAgent):
    scope = "fund"
    # Funds default to llm_skill so the find-and-parse-factsheet patch
    # source is eligible — it carries TER, SRRI/SRI, dealing terms, and
    # service providers that nothing else surfaces. Callers can pin the
    # cap back down via max_cost_class="web_fetch" when running cheap.
    default_max_cost_class = "llm_skill"
