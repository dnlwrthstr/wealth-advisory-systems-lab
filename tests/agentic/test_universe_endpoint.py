"""HTTP-level tests for /universe routes against a stub OpenSearch client.

Covers the per-scope POST routes (equity / bond / fund), the cross-scope
and per-scope GET lists, and PATCH status updates.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.instrument_api.universe_router import build_universe_router  # noqa: E402
from pipeline.agentic.merger import SourceFetchResult  # noqa: E402


class _StubClient:
    """Minimal OpenSearch stand-in: records writes, replays canned searches."""

    def __init__(self):
        self.docs: Dict[tuple[str, str], Dict[str, Any]] = {}
        self.update_calls: List[Dict[str, Any]] = []
        self.search_response: Dict[str, Any] = {"hits": {"hits": []}}
        self.search_calls: List[Dict[str, Any]] = []
        self.not_found_on_update: bool = False

    def index(self, *, index: str, id: str, body: Dict[str, Any], refresh: str = "wait_for"):
        self.docs[(index, id)] = body

    def update(self, *, index: str, id: str, body: Dict[str, Any], refresh: str = "wait_for"):
        if self.not_found_on_update:
            class _NotFound(Exception):
                pass
            _NotFound.__name__ = "NotFoundError"
            raise _NotFound("doc not found")
        self.update_calls.append({"index": index, "id": id, "body": body})
        existing = self.docs.get((index, id), {})
        existing.update(body.get("doc", {}))
        self.docs[(index, id)] = existing

    def search(self, *, index: str, body: Dict[str, Any], **kwargs):
        self.search_calls.append({"index": index, "body": body})
        return self.search_response


def _app_with_client(client: _StubClient) -> TestClient:
    app = FastAPI()
    app.include_router(build_universe_router(opensearch_client=client))
    return TestClient(app)


def _stub_equity_sources(monkeypatch):
    from pipeline.agentic.sources import equity_firds as adapter_firds
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo
    from pipeline.agentic.sources import finnhub as adapter_finnhub
    from pipeline.agentic.sources import issuer_gleif as adapter_gleif
    from pipeline.agentic.sources import openfigi as adapter_openfigi
    from pipeline.agentic.sources import six_ticker_isin as adapter_six

    def yahoo_fetch(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "Apple Inc.",
                "currencyOfDenomination": "USD",
                "assetClass": "Equity / Common Stock",
                "issuer": {
                    "issuerId": "ISS-APPLE",
                    "legalName": "Apple Inc.",
                    "lei": "HWUPKR0MPOU8FGXBT394",
                },
                "primaryListing": {"mic": "XNAS", "ticker": "AAPL", "listingCurrency": "USD"},
                "identifierList": [{"identifier": value, "type": "isin"}],
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "yfinance"}],
        )

    def gleif_fetch(kind, value, current):
        return SourceFetchResult(
            patch={"legalName": "Apple Inc.", "domicileCountry": "US", "issuerType": "corporate"},
            source_of_truth_rows=[{"fieldGroup": "legal_entity", "source": "gleif"}],
        )

    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_firds, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_six, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_finnhub, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", yahoo_fetch)
    monkeypatch.setattr(adapter_gleif, "fetch", gleif_fetch)


def test_add_equity_persists_with_status(monkeypatch):
    _stub_equity_sources(monkeypatch)
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/equity",
        json={
            "identifier": {"kind": "isin", "value": "US0378331005"},
            "status": "in_universe",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scope"] == "equity"
    assert body["universeStatus"] == "in_universe"
    assert body["goldenId"].startswith("EQG-US0378331005")
    # Equity doc was persisted with the stamp
    equity_doc = next(d for (idx, _), d in client.docs.items() if idx == "pms_golden_equity")
    assert equity_doc["universeStatus"] == "in_universe"
    # Chained issuer doc was also persisted (without status)
    assert any(idx == "pms_golden_issuer" for (idx, _) in client.docs)
    # And the search-helper index got a mirror so /instruments/search finds it.
    search_docs = [(idx, key, d) for (idx, key), d in client.docs.items() if idx == "pms_golden_instrumentsearch"]
    assert len(search_docs) == 1, "expected one search-helper mirror"
    _, search_id, search_doc = search_docs[0]
    assert search_id.startswith("equity:EQG-US0378331005")
    assert search_doc["scope"] == "equity"
    assert search_doc["ow_type"] == "equity"
    assert search_doc["universeStatus"] == "in_universe"
    assert search_doc["longName"] == "Apple Inc."


def test_update_status_mirrors_to_search_index():
    """PATCH /universe/{scope}/{goldenId}/status keeps the search hit aligned."""
    client = _StubClient()
    resp = _app_with_client(client).patch(
        "/universe/equity/EQG-X-001/status",
        json={"status": "excluded"},
    )
    assert resp.status_code == 200
    # Both indices got a partial update with the new status.
    indices_updated = {call["index"] for call in client.update_calls}
    assert indices_updated == {"pms_golden_equity", "pms_golden_instrumentsearch"}
    search_update = next(c for c in client.update_calls if c["index"] == "pms_golden_instrumentsearch")
    assert search_update["id"] == "equity:EQG-X-001"
    assert search_update["body"] == {"doc": {"universeStatus": "excluded"}}


def test_add_equity_defaults_to_in_universe(monkeypatch):
    _stub_equity_sources(monkeypatch)
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/equity",
        json={"identifier": {"kind": "isin", "value": "US0378331005"}},
    )
    assert resp.status_code == 200
    assert resp.json()["universeStatus"] == "in_universe"


def test_add_equity_rejects_invalid_status():
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/equity",
        json={
            "identifier": {"kind": "isin", "value": "US0378331005"},
            "status": "maybe",
        },
    )
    assert resp.status_code == 400
    assert "status" in resp.json()["detail"]


def test_add_bond_dispatches_to_bond_agent(monkeypatch):
    """The /universe/bond route must run the bond planner, not equity."""
    from pipeline.agentic.agents import BondAgent

    seen: Dict[str, Any] = {}

    def fake_assemble_and_persist(*, client, identifier, status, budget=None, max_cost_class=None):
        seen["scope"] = "bond"
        seen["identifier"] = identifier
        seen["status"] = status
        seen["max_cost_class"] = max_cost_class
        from pipeline.agentic.assemble import AssembleResult

        primary = AssembleResult(
            scope="bond",
            identifier=identifier,
            record={"goldenId": "BG-XS-001"},
            quality_score=0.5,
            remaining_gaps=[],
            provenance=[],
            trace=None,  # not used by the response
            run_id="t",
        )
        return {"primary": primary, "chained_issuers": []}

    monkeypatch.setattr(BondAgent, "assemble_and_persist", classmethod(
        lambda cls, **kw: fake_assemble_and_persist(**kw)
    ))
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/bond",
        json={"identifier": {"kind": "isin", "value": "XS1234567890"}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scope"] == "bond"
    assert body["goldenId"] == "BG-XS-001"
    # Bond agent default cost cap = web_fetch; the route lets it through as None.
    assert seen["max_cost_class"] is None


def test_add_fund_dispatches_to_fund_agent(monkeypatch):
    """The /universe/fund route must run the fund planner, not equity."""
    from pipeline.agentic.agents import FundAgent

    seen: Dict[str, Any] = {}

    def fake_assemble_and_persist(*, client, identifier, status, budget=None, max_cost_class=None):
        seen["scope"] = "fund"
        seen["max_cost_class"] = max_cost_class
        from pipeline.agentic.assemble import AssembleResult

        primary = AssembleResult(
            scope="fund",
            identifier=identifier,
            record={"goldenId": "FG-IE-001"},
            quality_score=0.7,
            remaining_gaps=[],
            provenance=[],
            trace=None,
            run_id="t",
        )
        return {"primary": primary, "chained_issuers": []}

    monkeypatch.setattr(FundAgent, "assemble_and_persist", classmethod(
        lambda cls, **kw: fake_assemble_and_persist(**kw)
    ))
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/fund",
        json={"identifier": {"kind": "isin", "value": "IE00B4L5Y983"}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["scope"] == "fund"
    # invoke_llm_skills not set → router passes None → agent uses its own
    # default ("llm_skill"). The route doesn't override.
    assert seen["max_cost_class"] is None


def test_invoke_llm_skills_true_pins_cost_cap_to_llm_skill(monkeypatch):
    """Body flag True must force max_cost_class='llm_skill' on the agent call."""
    from pipeline.agentic.agents import EquityAgent

    seen: Dict[str, Any] = {}

    def fake(cls, **kw):
        seen.update(kw)
        from pipeline.agentic.assemble import AssembleResult

        primary = AssembleResult(
            scope=cls.scope,
            identifier=kw["identifier"],
            record={"goldenId": "EQG-X-001"},
            quality_score=0.5,
            remaining_gaps=[],
            provenance=[],
            trace=None,
            run_id="t",
        )
        return {"primary": primary, "chained_issuers": []}

    monkeypatch.setattr(EquityAgent, "assemble_and_persist", classmethod(fake))
    resp = _app_with_client(_StubClient()).post(
        "/universe/equity",
        json={
            "identifier": {"kind": "isin", "value": "US0378331005"},
            "invoke_llm_skills": True,
        },
    )
    assert resp.status_code == 200, resp.text
    assert seen["max_cost_class"] == "llm_skill"


def test_invoke_llm_skills_false_pins_cost_cap_to_web_fetch(monkeypatch):
    """Body flag False must force max_cost_class='web_fetch' even for funds."""
    from pipeline.agentic.agents import FundAgent

    seen: Dict[str, Any] = {}

    def fake(cls, **kw):
        seen.update(kw)
        from pipeline.agentic.assemble import AssembleResult

        primary = AssembleResult(
            scope=cls.scope,
            identifier=kw["identifier"],
            record={"goldenId": "FG-X-001"},
            quality_score=0.5,
            remaining_gaps=[],
            provenance=[],
            trace=None,
            run_id="t",
        )
        return {"primary": primary, "chained_issuers": []}

    monkeypatch.setattr(FundAgent, "assemble_and_persist", classmethod(fake))
    resp = _app_with_client(_StubClient()).post(
        "/universe/fund",
        json={
            "identifier": {"kind": "isin", "value": "IE00B4L5Y983"},
            "invoke_llm_skills": False,
        },
    )
    assert resp.status_code == 200, resp.text
    assert seen["max_cost_class"] == "web_fetch"


def test_list_universe_projects_type_specific_fields():
    """Each scope projects its own subset of UniverseMember fields."""
    client = _StubClient()
    client.search_response = {
        "hits": {
            "hits": [
                {
                    "_index": "pms_golden_equity",
                    "_id": "EQG-US0378331005-XNAS-001",
                    "_source": {
                        "goldenId": "EQG-US0378331005-XNAS-001",
                        "universeStatus": "in_universe",
                        "longName": "Apple Inc.",
                        "currencyOfDenomination": "USD",
                        "identifierList": [
                            {"identifier": "US0378331005", "type": "isin"},
                            {"identifier": "AAPL", "type": "ticker_symbol"},
                        ],
                        "industrySector": {"sectorLabel": "Technology"},
                        "recordMeta": {"qualityScore": 0.95, "goldenAsOf": "2026-05-16T10:00:00Z"},
                    },
                },
                {
                    "_index": "pms_golden_bond",
                    "_id": "BG-XS1234567890-001",
                    "_source": {
                        "goldenId": "BG-XS1234567890-001",
                        "universeStatus": "watchlist",
                        "longName": "Acme 4.5% 2030",
                        "currencyOfDenomination": "EUR",
                        "identifierList": [{"identifier": "XS1234567890", "type": "isin"}],
                        "maturityDate": "2030-06-15",
                        "currentCouponRate": 0.045,
                        "seniority": "senior_unsecured",
                        "recordMeta": {"qualityScore": 0.78, "goldenAsOf": "2026-05-16T09:00:00Z"},
                    },
                },
                {
                    "_index": "pms_golden_fund",
                    "_id": "FG-IE00B4L5Y983-001",
                    "_source": {
                        "goldenId": "FG-IE00B4L5Y983-001",
                        "universeStatus": "in_universe",
                        "longName": "iShares Core MSCI World",
                        "currencyOfDenomination": "USD",
                        "identifierList": [{"identifier": "IE00B4L5Y983", "type": "isin"}],
                        "totalExpenseRatio": 0.002,
                        "managementCompany": {"legalName": "BlackRock Asset Management Ireland Ltd"},
                        "recordMeta": {"qualityScore": 0.82, "goldenAsOf": "2026-05-16T08:00:00Z"},
                    },
                },
            ]
        }
    }
    body = _app_with_client(client).get("/universe").json()
    assert body["total"] == 3
    by_scope = {item["scope"]: item for item in body["items"]}

    # Equity gets sector; bond/fund-only fields stay null
    eq = by_scope["equity"]
    assert eq["isin"] == "US0378331005"
    assert eq["ticker"] == "AAPL"
    assert eq["sector"] == "Technology"
    assert eq["maturityDate"] is None
    assert eq["totalExpenseRatio"] is None

    # Bond gets coupon/maturity/seniority
    bond = by_scope["bond"]
    assert bond["maturityDate"] == "2030-06-15"
    assert bond["couponRate"] == 0.045
    assert bond["seniority"] == "senior_unsecured"
    assert bond["sector"] is None

    # Fund gets TER + management company name
    fund = by_scope["fund"]
    assert fund["totalExpenseRatio"] == 0.002
    assert fund["managementCompany"] == "BlackRock Asset Management Ireland Ltd"
    assert fund["sector"] is None


def test_list_universe_by_scope_filters_to_single_index():
    """GET /universe/equity must hit only pms_golden_equity."""
    client = _StubClient()
    resp = _app_with_client(client).get("/universe/equity")
    assert resp.status_code == 200
    assert client.search_calls, "expected an OpenSearch search call"
    assert client.search_calls[-1]["index"] == "pms_golden_equity"


def test_list_universe_by_scope_rejects_unknown_scope():
    resp = _app_with_client(_StubClient()).get("/universe/warrant")
    assert resp.status_code == 400


def test_update_status_calls_partial_update():
    client = _StubClient()
    resp = _app_with_client(client).patch(
        "/universe/equity/EQG-X-001/status",
        json={"status": "excluded"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "scope": "equity",
        "goldenId": "EQG-X-001",
        "universeStatus": "excluded",
    }
    # Per-scope golden index gets the partial update for the new status.
    eq_update = next(c for c in client.update_calls if c["index"] == "pms_golden_equity")
    assert eq_update == {
        "index": "pms_golden_equity",
        "id": "EQG-X-001",
        "body": {"doc": {"universeStatus": "excluded"}},
    }


def test_update_status_returns_404_when_doc_missing():
    client = _StubClient()
    client.not_found_on_update = True
    resp = _app_with_client(client).patch(
        "/universe/equity/EQG-MISSING/status",
        json={"status": "in_universe"},
    )
    assert resp.status_code == 404


def test_generic_add_route_is_gone():
    """The legacy POST /universe/add was deleted in the per-type split.

    FastAPI returns 405 here because GET /universe/{scope} matches the
    path on a different method; either way, no POST handler exists.
    """
    resp = _app_with_client(_StubClient()).post(
        "/universe/add",
        json={"scope": "equity", "identifier": {"kind": "isin", "value": "X"}},
    )
    assert resp.status_code in (404, 405)


def test_universe_endpoints_503_without_opensearch():
    app = FastAPI()
    app.include_router(build_universe_router(opensearch_client=None))
    tc = TestClient(app)
    for path, method, kwargs in (
        ("/universe/equity", "post", {"json": {"identifier": {"kind": "isin", "value": "X"}}}),
        ("/universe/bond", "post", {"json": {"identifier": {"kind": "isin", "value": "X"}}}),
        ("/universe/fund", "post", {"json": {"identifier": {"kind": "isin", "value": "X"}}}),
        ("/universe", "get", {}),
        ("/universe/equity", "get", {}),
        ("/universe/equity/EQG-X/status", "patch", {"json": {"status": "in_universe"}}),
    ):
        resp = getattr(tc, method)(path, **kwargs)
        assert resp.status_code == 503, f"{method.upper()} {path}"
