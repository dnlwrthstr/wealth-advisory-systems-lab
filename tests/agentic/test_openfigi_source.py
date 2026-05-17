"""OpenFIGI source — mocked HTTP, picks composite-FIGI match."""
from __future__ import annotations

import json

import pytest

from pipeline.agentic.sources import openfigi as adapter
from pipeline.gold import openfigi as gold_openfigi


@pytest.fixture
def fake_post_json(monkeypatch):
    """Patch the HTTP POST so no network calls happen during tests."""
    payloads = {}

    def fake(payload):
        payloads["last"] = payload
        return [{"data": [
            {
                "figi": "BBG001S5N8V8",
                "compositeFIGI": "BBG000B9XRY4",
                "ticker": "AAPL UN",
                "name": "APPLE INC",
                "securityType": "Common Stock",
                "exchCode": "UN",
            },
            {
                "figi": "BBG000B9XRY4",
                "compositeFIGI": "BBG000B9XRY4",
                "ticker": "AAPL",
                "name": "APPLE INC",
                "securityType": "Common Stock",
                "exchCode": "US",
                "marketSector": "Equity",
            },
        ]}]

    monkeypatch.setattr(gold_openfigi, "_post_json", fake)
    return payloads


def test_picks_composite_figi_match(fake_post_json, tmp_path, monkeypatch):
    monkeypatch.setattr(gold_openfigi, "CACHE_DIR", tmp_path)
    rec = gold_openfigi.fetch_openfigi_by_isin("US0378331005", use_cache=False)
    assert rec["figi"] == "BBG000B9XRY4"
    assert rec["ticker"] == "AAPL"
    assert rec["name"] == "APPLE INC"
    # Confirm the request was shaped correctly.
    assert fake_post_json["last"] == [{"idType": "ID_ISIN", "idValue": "US0378331005"}]


def test_negative_cache_for_unknown_isin(monkeypatch, tmp_path):
    monkeypatch.setattr(gold_openfigi, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(gold_openfigi, "_post_json", lambda payload: [{"data": []}])
    assert gold_openfigi.fetch_openfigi_by_isin("ZZ0000000000") is None
    # The negative is cached, so a second call doesn't re-hit the network.
    assert (tmp_path / "ZZ0000000000.json").exists()


def test_adapter_builds_identifier_patch(monkeypatch):
    monkeypatch.setattr(adapter, "fetch_openfigi_by_isin", lambda isin: {
        "figi": "BBG000B9XRY4",
        "compositeFIGI": "BBG000B9XRY4",
        "ticker": "AAPL",
        "name": "APPLE INC",
        "securityType": "Common Stock",
    })
    result = adapter.fetch("isin", "US0378331005", current={})
    assert result is not None
    types_seen = [e["type"] for e in result.patch["identifierList"]]
    assert "isin" in types_seen
    assert "figi" in types_seen
    assert "ticker_symbol" in types_seen
    assert result.patch["longName"] == "APPLE INC"
    assert result.patch["equitySubType"] == "common_stock"


def test_adapter_returns_none_for_non_isin(monkeypatch):
    monkeypatch.setattr(adapter, "fetch_openfigi_by_isin", lambda isin: {"figi": "X"})
    assert adapter.fetch("ticker", "AAPL", current={}) is None


def test_adapter_derives_valor_for_swiss_isin(monkeypatch):
    """CH ISINs encode the valor in digits 3..11; openfigi should surface it
    alongside the ISIN/FIGI/ticker so downstream SIX-focused UIs have both."""
    monkeypatch.setattr(adapter, "fetch_openfigi_by_isin", lambda isin: {
        "figi": "BBG000BXQHQ0", "compositeFIGI": "BBG000BXQHQ0",
        "ticker": "ABJ", "name": "ABB LTD-REG", "securityType": "Common Stock",
    })
    result = adapter.fetch("isin", "CH0012221716", current={})
    valor_entries = [e for e in result.patch["identifierList"] if e["type"] == "valor"]
    assert valor_entries == [{"identifier": "1222171", "type": "valor"}]


def test_adapter_omits_valor_for_non_swiss_isin(monkeypatch):
    monkeypatch.setattr(adapter, "fetch_openfigi_by_isin", lambda isin: {
        "figi": "X", "ticker": "AAPL", "name": "APPLE INC",
    })
    result = adapter.fetch("isin", "US0378331005", current={})
    types_seen = [e["type"] for e in result.patch["identifierList"]]
    assert "valor" not in types_seen
