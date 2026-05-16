"""Universe membership: persist stamping + status update helper."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from pipeline.agentic import assemble_and_persist
from pipeline.agentic.merger import SourceFetchResult
from pipeline.agentic.persist import (
    ALLOWED_UNIVERSE_STATUSES,
    persist_record,
    update_universe_status,
)


class _RecordingClient:
    def __init__(self):
        self.index_calls: List[Dict[str, Any]] = []
        self.update_calls: List[Dict[str, Any]] = []

    def index(self, *, index: str, id: str, body: Dict[str, Any], refresh: str = "wait_for"):
        self.index_calls.append({"index": index, "id": id, "body": body, "refresh": refresh})

    def update(self, *, index: str, id: str, body: Dict[str, Any], refresh: str = "wait_for"):
        self.update_calls.append({"index": index, "id": id, "body": body, "refresh": refresh})


def test_persist_record_stamps_universe_status_when_set():
    client = _RecordingClient()
    persist_record(
        client,
        "equity",
        {"goldenId": "EQG-X-001", "longName": "X Inc."},
        universe_status="watchlist",
    )
    assert len(client.index_calls) == 1
    body = client.index_calls[0]["body"]
    assert body["universeStatus"] == "watchlist"
    assert body["goldenId"] == "EQG-X-001"
    assert body["longName"] == "X Inc."


def test_persist_record_omits_universe_status_when_not_set():
    """Default behaviour for non-universe writers (e.g. the chained issuer
    path) must not stamp anything."""
    client = _RecordingClient()
    persist_record(client, "issuer", {"goldenId": "ISS-AAA"})
    body = client.index_calls[0]["body"]
    assert "universeStatus" not in body


def test_persist_record_rejects_invalid_universe_status():
    client = _RecordingClient()
    with pytest.raises(ValueError, match="universe_status must be one of"):
        persist_record(
            client, "equity", {"goldenId": "EQG-X-001"}, universe_status="bogus"
        )
    assert client.index_calls == []


def test_update_universe_status_uses_partial_update():
    client = _RecordingClient()
    update_universe_status(client, "equity", "EQG-X-001", "excluded")
    assert client.update_calls == [
        {
            "index": "pms_golden_equity",
            "id": "EQG-X-001",
            "body": {"doc": {"universeStatus": "excluded"}},
            "refresh": "wait_for",
        }
    ]


def test_update_universe_status_rejects_invalid_status():
    client = _RecordingClient()
    with pytest.raises(ValueError, match="status must be one of"):
        update_universe_status(client, "equity", "EQG-X-001", "bogus")
    assert client.update_calls == []


def test_allowed_universe_statuses_matches_design():
    assert ALLOWED_UNIVERSE_STATUSES == {"watchlist", "in_universe", "excluded"}


def test_assemble_and_persist_stamps_universe_status_on_primary_only(monkeypatch):
    """Universe membership is per-PMS, so it belongs on the instrument record
    — not on chained issuer records (which are platform-shared)."""
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
                    "issuerId": "ISS-APPLE-LEI",
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
            patch={
                "legalName": "Apple Inc.",
                "domicileCountry": "US",
                "headquartersCountry": "US",
                "issuerType": "corporate",
            },
            source_of_truth_rows=[{"fieldGroup": "legalEntity", "source": "gleif"}],
        )

    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", yahoo_fetch)
    monkeypatch.setattr(adapter_gleif, "fetch", gleif_fetch)

    client = _RecordingClient()
    assemble_and_persist(
        client=client,
        scope="equity",
        identifier={"kind": "isin", "value": "US0378331005"},
        universe_status="in_universe",
    )

    equity_call = next(c for c in client.index_calls if c["index"] == "pms_golden_equity")
    issuer_call = next(c for c in client.index_calls if c["index"] == "pms_golden_issuer")
    assert equity_call["body"]["universeStatus"] == "in_universe"
    assert "universeStatus" not in issuer_call["body"]
