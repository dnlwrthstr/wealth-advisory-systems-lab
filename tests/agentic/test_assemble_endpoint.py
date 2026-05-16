"""HTTP-level test for POST /instruments/assemble.

Skipped gracefully when fastapi isn't installed in the local env (the
production Docker image carries it; this lets the suite stay green for
contributors without it).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from pipeline.agentic.merger import SourceFetchResult  # noqa: E402


def _client():
    from backend.instrument_api.main import app
    return TestClient(app)


def test_assemble_endpoint_happy_path(monkeypatch):
    """Mock the equity sources and verify the endpoint returns the composed record."""
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo
    from pipeline.agentic.sources import openfigi as adapter_openfigi

    def yahoo_fetch(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "Apple Inc.",
                "currencyOfDenomination": "USD",
                "issuer": {"issuerId": "ISS-APPLE", "legalName": "Apple Inc."},
                "primaryListing": {"mic": "XNAS", "ticker": "AAPL", "listingCurrency": "USD"},
                "assetClass": "Equity / Common Stock",
                "identifierList": [{"identifier": value, "type": "isin"}],
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "yfinance"}],
        )

    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: None)
    monkeypatch.setattr(adapter_yahoo, "fetch", yahoo_fetch)

    resp = _client().post(
        "/instruments/assemble",
        json={"scope": "equity", "identifier": {"kind": "isin", "value": "US0378331005"}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scope"] == "equity"
    assert body["record"]["longName"] == "Apple Inc."
    assert body["record"]["goldenId"].startswith("EQG-US0378331005")
    assert body["trace"]["iterations"] >= 1


def test_assemble_endpoint_rejects_missing_identifier_value():
    resp = _client().post(
        "/instruments/assemble",
        json={"scope": "equity", "identifier": {"kind": "isin", "value": ""}},
    )
    assert resp.status_code == 400
    assert "identifier.value" in resp.json()["detail"]
