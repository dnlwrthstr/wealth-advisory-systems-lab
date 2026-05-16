"""EquityAgent end-to-end with adapters mocked at the source-module boundary."""
from __future__ import annotations

from pipeline.agentic.agents import EquityAgent
from pipeline.agentic.merger import SourceFetchResult


def _stub_equity_sources(monkeypatch):
    """Pin all registered equity sources so the test is deterministic."""
    from pipeline.agentic.sources import equity_firds as adapter_firds
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo
    from pipeline.agentic.sources import finnhub as adapter_finnhub
    from pipeline.agentic.sources import openfigi as adapter_openfigi
    from pipeline.agentic.sources import six_ticker_isin as adapter_six

    def yahoo_fetch(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "Apple Inc.",
                "currencyOfDenomination": "USD",
                "assetClass": "Equity / Common Stock",
                "issuer": {"issuerId": "ISS-APPLE", "legalName": "Apple Inc."},
                "primaryListing": {"mic": "XNAS", "ticker": "AAPL", "listingCurrency": "USD"},
                "identifierList": [{"identifier": value, "type": "isin"}],
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "yfinance"}],
        )

    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_six, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_finnhub, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", yahoo_fetch)


def test_equity_agent_produces_equity_golden_id_shape(monkeypatch):
    _stub_equity_sources(monkeypatch)
    result = EquityAgent.assemble({"kind": "isin", "value": "US0378331005"})
    assert result.scope == "equity"
    assert result.record["goldenId"].startswith("EQG-US0378331005")
    assert result.record["longName"] == "Apple Inc."


def test_equity_agent_does_not_invoke_llm_skill_sources(monkeypatch):
    """Equity default cost cap (web_fetch) must keep llm_skill sources out of the trace."""
    _stub_equity_sources(monkeypatch)
    result = EquityAgent.assemble({"kind": "isin", "value": "US0378331005"})
    for inv in result.trace.invocations:
        # No registered equity llm_skill source exists today, but the rule is
        # the contract: the planner must never call one at the agent default.
        assert "factsheet" not in inv["source"]


def test_equity_agent_reports_critical_gaps_when_sources_silent(monkeypatch):
    """When all sources return None, critical_gaps lists the required-tier holes."""
    from pipeline.agentic.sources import equity_firds as adapter_firds
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo
    from pipeline.agentic.sources import finnhub as adapter_finnhub
    from pipeline.agentic.sources import openfigi as adapter_openfigi
    from pipeline.agentic.sources import six_ticker_isin as adapter_six

    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_six, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_finnhub, "fetch", lambda k, v, c: None)
    result = EquityAgent.assemble({"kind": "isin", "value": "ZZ0000000000"})
    gaps = EquityAgent.critical_gaps(result)
    # `required`-tier source fields per annotations/equity.yml
    assert "longName" in gaps
    assert "currencyOfDenomination" in gaps
    assert "issuer" in gaps
    assert "primaryListing" in gaps
