"""HTTP-level tests for /universe routes against a stub OpenSearch client."""
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
        return self.search_response


def _app_with_client(client: _StubClient) -> TestClient:
    app = FastAPI()
    app.include_router(build_universe_router(opensearch_client=client))
    return TestClient(app)


def _stub_equity_sources(monkeypatch):
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo
    from pipeline.agentic.sources import issuer_gleif as adapter_gleif
    from pipeline.agentic.sources import openfigi as adapter_openfigi

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
            source_of_truth_rows=[{"fieldGroup": "legalEntity", "source": "gleif"}],
        )

    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", yahoo_fetch)
    monkeypatch.setattr(adapter_gleif, "fetch", gleif_fetch)


def test_add_to_universe_persists_with_status(monkeypatch):
    _stub_equity_sources(monkeypatch)
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/add",
        json={
            "scope": "equity",
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


def test_add_to_universe_defaults_to_in_universe(monkeypatch):
    _stub_equity_sources(monkeypatch)
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/add",
        json={"scope": "equity", "identifier": {"kind": "isin", "value": "US0378331005"}},
    )
    assert resp.status_code == 200
    assert resp.json()["universeStatus"] == "in_universe"


def test_add_to_universe_rejects_invalid_scope():
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/add",
        json={"scope": "warrant", "identifier": {"kind": "isin", "value": "X"}},
    )
    assert resp.status_code == 400
    assert "scope" in resp.json()["detail"]


def test_add_to_universe_rejects_invalid_status():
    client = _StubClient()
    resp = _app_with_client(client).post(
        "/universe/add",
        json={
            "scope": "equity",
            "identifier": {"kind": "isin", "value": "US0378331005"},
            "status": "maybe",
        },
    )
    assert resp.status_code == 400
    assert "status" in resp.json()["detail"]


def test_list_universe_projects_search_hits():
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
                            {"identifier": "AAPL", "type": "tickerSymbol"},
                        ],
                        "recordMeta": {
                            "qualityScore": 0.95,
                            "goldenAsOf": "2026-05-16T10:00:00Z",
                        },
                    },
                }
            ]
        }
    }
    resp = _app_with_client(client).get("/universe")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["scope"] == "equity"
    assert item["isin"] == "US0378331005"
    assert item["ticker"] == "AAPL"
    assert item["universeStatus"] == "in_universe"
    assert item["qualityScore"] == 0.95


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
    assert client.update_calls == [
        {
            "index": "pms_golden_equity",
            "id": "EQG-X-001",
            "body": {"doc": {"universeStatus": "excluded"}},
        }
    ]


def test_update_status_returns_404_when_doc_missing():
    client = _StubClient()
    client.not_found_on_update = True
    resp = _app_with_client(client).patch(
        "/universe/equity/EQG-MISSING/status",
        json={"status": "in_universe"},
    )
    assert resp.status_code == 404


def test_universe_endpoints_503_without_opensearch():
    app = FastAPI()
    app.include_router(build_universe_router(opensearch_client=None))
    tc = TestClient(app)
    for path, method, kwargs in (
        ("/universe/add", "post", {"json": {"scope": "equity", "identifier": {"kind": "isin", "value": "X"}}}),
        ("/universe", "get", {}),
        ("/universe/equity/EQG-X/status", "patch", {"json": {"status": "in_universe"}}),
    ):
        resp = getattr(tc, method)(path, **kwargs)
        assert resp.status_code == 503, f"{method.upper()} {path}"
