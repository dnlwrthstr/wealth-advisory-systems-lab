"""Verify max_cost_class filters out higher-cost sources from the planner."""
from __future__ import annotations

from datetime import datetime, timezone

from pipeline.agentic.assemble import assemble_golden


def test_default_cost_cap_excludes_llm_skill_for_fund(monkeypatch):
    """fund_factsheet_skill is llm_skill cost — default cap is web_fetch, so
    the source is filtered out and is never invoked."""
    from pipeline.agentic.sources import fund_firds as adapter_firds
    from pipeline.agentic.sources import fund_yahoo as adapter_yahoo
    from pipeline.agentic.sources import fund_factsheet_patch as adapter_patch
    from pipeline.agentic.sources import fund_factsheet_skill as adapter_skill

    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_patch, "fetch", lambda k, v, c: None)

    skill_calls = []
    monkeypatch.setattr(adapter_skill, "fetch", lambda k, v, c: skill_calls.append((k, v)))

    assemble_golden(
        scope="fund",
        identifier={"kind": "isin", "value": "IE00B4L5Y983"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="cost-cap-default",
    )
    assert skill_calls == []


def test_raised_cost_cap_admits_llm_skill(monkeypatch):
    """max_cost_class='llm_skill' lets fund_factsheet_skill into the candidate set."""
    from pipeline.agentic.sources import fund_firds as adapter_firds
    from pipeline.agentic.sources import fund_yahoo as adapter_yahoo
    from pipeline.agentic.sources import fund_factsheet_patch as adapter_patch
    from pipeline.agentic.sources import fund_factsheet_skill as adapter_skill

    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_patch, "fetch", lambda k, v, c: None)

    skill_calls = []
    monkeypatch.setattr(adapter_skill, "fetch", lambda k, v, c: skill_calls.append((k, v)) or None)

    assemble_golden(
        scope="fund",
        identifier={"kind": "isin", "value": "IE00B4L5Y983"},
        max_cost_class="llm_skill",
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="cost-cap-raised",
    )
    assert skill_calls == [("isin", "IE00B4L5Y983")]
