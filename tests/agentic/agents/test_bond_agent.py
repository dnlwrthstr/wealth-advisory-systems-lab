"""BondAgent end-to-end with adapters mocked at the source-module boundary."""
from __future__ import annotations

from pipeline.agentic.agents import BondAgent
from pipeline.agentic.merger import SourceFetchResult


def _stub_firds(monkeypatch):
    from pipeline.agentic.sources import bond_firds as adapter

    def firds_fetch(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "Acme 2030 4.5% Senior",
                "currencyOfDenomination": "EUR",
                "assetClass": "Fixed Income / Corporate",
                "maturityDate": "2030-06-15",
                "couponType": "fixed",
                "currentCouponRate": 0.045,
                "issuer": {"issuerId": "ISS-ACME", "legalName": "Acme SA", "lei": "5493001ACME0000ZX12"},
                "primaryListing": {"mic": "XFRA"},
                "identifierList": [{"identifier": value, "type": "isin"}],
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "firds"}],
        )

    monkeypatch.setattr(adapter, "fetch", firds_fetch)


def test_bond_agent_produces_bond_golden_id_shape(monkeypatch):
    _stub_firds(monkeypatch)
    result = BondAgent.assemble({"kind": "isin", "value": "XS1234567890"})
    assert result.scope == "bond"
    assert result.record["goldenId"].startswith("BG-XS1234567890")
    assert result.record["currencyOfDenomination"] == "EUR"
    assert result.record["maturityDate"] == "2030-06-15"


def test_bond_agent_default_cost_cap_excludes_llm_skill(monkeypatch):
    """BondAgent default is web_fetch — even if an llm_skill bond source were registered."""
    _stub_firds(monkeypatch)
    result = BondAgent.assemble({"kind": "isin", "value": "XS1234567890"})
    for inv in result.trace.invocations:
        assert "factsheet" not in inv["source"]


def test_bond_agent_reports_critical_gaps_when_sources_silent(monkeypatch):
    from pipeline.agentic.sources import bond_firds as adapter

    monkeypatch.setattr(adapter, "fetch", lambda k, v, c: None)
    result = BondAgent.assemble({"kind": "isin", "value": "ZZ9999999999"})
    gaps = BondAgent.critical_gaps(result)
    assert "longName" in gaps
    assert "currencyOfDenomination" in gaps
    assert "maturityDate" in gaps
    assert "issuer" in gaps
