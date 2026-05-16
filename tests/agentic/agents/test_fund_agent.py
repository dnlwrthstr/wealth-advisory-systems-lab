"""FundAgent end-to-end with adapters mocked at the source-module boundary.

FundAgent's default cost cap is `llm_skill` — the most important contract
for funds is that the factsheet skill source is *eligible* at the default
cap; whether it returns data is incidental to this test.
"""
from __future__ import annotations

from pipeline.agentic.agents import FundAgent
from pipeline.agentic.merger import SourceFetchResult


def _stub_fund_sources(monkeypatch):
    """Patch the three fund sources to deterministic shapes."""
    from pipeline.agentic.sources import fund_firds as adapter_firds
    from pipeline.agentic.sources import fund_yahoo as adapter_yahoo
    from pipeline.agentic.sources import fund_factsheet_skill as adapter_factsheet

    def firds_fetch(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "iShares Core MSCI World UCITS ETF USD (Acc)",
                "currencyOfDenomination": "USD",
                "assetClass": "Fund / Equity ETF",
                "umbrella": {"legalName": "iShares VII PLC", "lei": "549300VUYUFI3JTUAW28"},
                "managementCompany": {"legalName": "BlackRock Asset Management Ireland Ltd"},
                "shareClass": {"isin": value, "currency": "USD"},
                "primaryListing": {"mic": "XLON", "ticker": "IWDA"},
                "identifierList": [{"identifier": value, "type": "isin"}],
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "firds"}],
        )

    monkeypatch.setattr(adapter_firds, "fetch", firds_fetch)
    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_factsheet, "fetch", lambda k, v, c: None)


def test_fund_agent_produces_fund_golden_id_shape(monkeypatch):
    _stub_fund_sources(monkeypatch)
    result = FundAgent.assemble({"kind": "isin", "value": "IE00B4L5Y983"})
    assert result.scope == "fund"
    assert result.record["goldenId"].startswith("FG-IE00B4L5Y983")
    assert result.record["currencyOfDenomination"] == "USD"


def test_fund_agent_default_cost_cap_admits_factsheet_skill(monkeypatch):
    """At the default cap (llm_skill), the factsheet skill source must be
    eligible for the planner — i.e. show up in the considered set."""
    # Stub FIRDS to seed an underdetermined record so the planner keeps
    # looking, then assert factsheet was actually attempted.
    from pipeline.agentic.sources import fund_firds as adapter_firds
    from pipeline.agentic.sources import fund_yahoo as adapter_yahoo
    from pipeline.agentic.sources import fund_factsheet_skill as adapter_factsheet

    factsheet_called = {"called": False}

    def factsheet_fetch(kind, value, current):
        factsheet_called["called"] = True
        return None

    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_factsheet, "fetch", factsheet_fetch)

    FundAgent.assemble({"kind": "isin", "value": "IE00B4L5Y983"})
    assert factsheet_called["called"], "factsheet skill should run at FundAgent's default cost cap"


def test_fund_agent_web_fetch_override_excludes_factsheet_skill(monkeypatch):
    """When the caller pins to web_fetch, the llm_skill factsheet source is filtered out."""
    from pipeline.agentic.sources import fund_firds as adapter_firds
    from pipeline.agentic.sources import fund_yahoo as adapter_yahoo
    from pipeline.agentic.sources import fund_factsheet_skill as adapter_factsheet

    factsheet_called = {"called": False}

    def factsheet_fetch(kind, value, current):
        factsheet_called["called"] = True
        return None

    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_factsheet, "fetch", factsheet_fetch)

    FundAgent.assemble(
        {"kind": "isin", "value": "IE00B4L5Y983"},
        max_cost_class="web_fetch",
    )
    assert not factsheet_called["called"]


def test_fund_agent_reports_critical_gaps_when_sources_silent(monkeypatch):
    from pipeline.agentic.sources import fund_firds as adapter_firds
    from pipeline.agentic.sources import fund_yahoo as adapter_yahoo
    from pipeline.agentic.sources import fund_factsheet_skill as adapter_factsheet

    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_factsheet, "fetch", lambda k, v, c: None)

    result = FundAgent.assemble({"kind": "isin", "value": "ZZ0000000000"})
    gaps = FundAgent.critical_gaps(result)
    # `required`-tier source fields per annotations/fund.yml
    for required in ("longName", "currencyOfDenomination", "umbrella", "managementCompany", "shareClass"):
        assert required in gaps
