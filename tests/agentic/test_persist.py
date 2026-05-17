"""Persistence + issuer-chain side effect (mocked OpenSearch + sources)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from pipeline.agentic import assemble_and_persist, extract_leis
from pipeline.agentic.merger import SourceFetchResult


class _RecordingClient:
    """Captures `client.index(...)` calls for assertion."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def index(self, *, index: str, id: str, body: Dict[str, Any], refresh: str = "wait_for"):
        self.calls.append({"index": index, "id": id, "body": body, "refresh": refresh})


def test_extract_leis_walks_nested_dicts_and_dedupes():
    rec = {
        "issuer": {"lei": "AAA", "legalName": "X"},
        "umbrella": {"lei": "AAA"},  # duplicate
        "managementCompany": {"lei": "BBB"},
        "primaryListing": {"mic": "XLON"},
    }
    assert extract_leis(rec) == ["AAA", "BBB"]


def test_extract_leis_handles_lists():
    rec = {
        "secondaryListings": [
            {"mic": "XPAR"},
            {"mic": "XAMS", "lei": "CCC"},
        ],
    }
    assert extract_leis(rec) == ["CCC"]


def test_assemble_and_persist_writes_primary_and_chains_issuer(monkeypatch):
    """Equity assembly writes 1 equity doc + 1 chained issuer doc."""
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
            source_of_truth_rows=[{"fieldGroup": "legal_entity", "source": "gleif"}],
        )

    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", yahoo_fetch)
    monkeypatch.setattr(adapter_gleif, "fetch", gleif_fetch)

    client = _RecordingClient()
    out = assemble_and_persist(
        client=client,
        scope="equity",
        identifier={"kind": "isin", "value": "US0378331005"},
    )

    indices_written = sorted(c["index"] for c in client.calls)
    assert indices_written == ["pms_golden_equity", "pms_golden_issuer"]

    equity_call = next(c for c in client.calls if c["index"] == "pms_golden_equity")
    assert equity_call["id"].startswith("EQG-US0378331005")
    issuer_call = next(c for c in client.calls if c["index"] == "pms_golden_issuer")
    assert issuer_call["id"] == "ISS-HWUPKR0MPOU8FGXBT394"
    assert issuer_call["body"]["legalName"] == "Apple Inc."

    assert len(out["chained_issuers"]) == 1
    assert out["chained_issuers"][0]["lei"] == "HWUPKR0MPOU8FGXBT394"


def test_assemble_and_persist_no_chain_for_issuer_scope(monkeypatch):
    """When the primary scope IS issuer, don't recurse into issuer chain."""
    from pipeline.agentic.sources import issuer_gleif as adapter_gleif

    monkeypatch.setattr(
        adapter_gleif, "fetch",
        lambda k, v, c: SourceFetchResult(
            patch={"legalName": "Whatever Inc."},
            source_of_truth_rows=[],
        ),
    )
    client = _RecordingClient()
    out = assemble_and_persist(
        client=client,
        scope="issuer",
        identifier={"kind": "lei", "value": "AAA"},
    )
    assert [c["index"] for c in client.calls] == ["pms_golden_issuer"]
    assert out["chained_issuers"] == []
