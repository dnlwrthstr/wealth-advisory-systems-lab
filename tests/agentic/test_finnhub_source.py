"""Finnhub source — mocked HTTP, ticker resolution from current state."""
from __future__ import annotations

import pytest

from pipeline.agentic.sources import finnhub as adapter
from pipeline.gold import finnhub as gold


@pytest.fixture
def fake_finnhub(monkeypatch):
    """Patch _get_json + set FINNHUB_API_KEY so fetch_by_ticker proceeds."""
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")

    def fake_get(endpoint, params):
        if endpoint == "/stock/profile2":
            return {
                "ticker": params["symbol"],
                "name": "Apple Inc.",
                "country": "US",
                "currency": "USD",
                "exchange": "NASDAQ NMS - GLOBAL MARKET",
                "ipo": "1980-12-12",
                "marketCapitalization": 3_000_000.0,  # in millions
                "shareOutstanding": 15_400.0,         # in millions
                "finnhubIndustry": "Technology",
            }
        if endpoint == "/quote":
            return {"c": 195.40, "o": 194.0, "h": 196.5, "l": 193.8, "pc": 194.5, "t": 1716000000}
        return None

    monkeypatch.setattr(gold, "_get_json", fake_get)


def test_no_key_skips_source(monkeypatch, tmp_path):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setattr(gold, "CACHE_DIR", tmp_path)
    assert gold.fetch_by_ticker("AAPL") is None


def test_fetch_by_ticker_normalises_units(fake_finnhub, tmp_path, monkeypatch):
    monkeypatch.setattr(gold, "CACHE_DIR", tmp_path)
    rec = gold.fetch_by_ticker("AAPL", use_cache=False)
    assert rec["ticker"] == "AAPL"
    assert rec["country"] == "US"
    assert rec["quote"]["current"] == 195.40
    # Market cap and shares are returned in millions per Finnhub spec — the
    # source preserves this and the adapter scales it up.
    assert rec["marketCapitalization"] == 3_000_000.0


def test_negative_cache_for_unknown_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    monkeypatch.setattr(gold, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(gold, "_get_json", lambda endpoint, params: {})
    assert gold.fetch_by_ticker("ZZZZ", use_cache=False) is None


def test_adapter_resolves_ticker_from_current_identifierList(monkeypatch):
    monkeypatch.setattr(adapter, "fetch_by_ticker", lambda ticker, **kw: {
        "ticker": ticker,
        "name": "Apple Inc.",
        "country": "US",
        "currency": "USD",
        "ipo": "1980-12-12",
        "marketCapitalization": 3_000_000.0,
        "shareOutstanding": 15_400.0,
        "finnhubIndustry": "Technology",
        "quote": {"current": 195.40, "open": 194.0, "high": 196.5, "low": 193.8, "previousClose": 194.5},
    })
    result = adapter.fetch(
        "isin", "US0378331005",
        current={
            "identifierList": [
                {"identifier": "US0378331005", "type": "isin"},
                {"identifier": "AAPL", "type": "tickerSymbol"},
            ],
        },
    )
    assert result is not None
    md = result.patch["marketData"]
    assert md["lastTradePrice"]["value"] == 195.40
    # Adapter scales the millions back to absolute values.
    assert result.patch["keyFigures"]["marketCapitalization"]["amount"] == 3_000_000.0 * 1_000_000
    assert result.patch["keyFigures"]["sharesOutstanding"] == 15_400.0 * 1_000_000
    assert result.patch["incorporationCountry"] == "US"
    assert result.patch["industrySector"]["industryLabel"] == "Technology"
    assert result.patch["firstTradingDate"] == "1980-12-12"


def test_adapter_returns_none_when_no_ticker_resolvable():
    """ISIN with no ticker hint in current → adapter can't call Finnhub."""
    assert adapter.fetch("isin", "ZZ", current={}) is None


def test_adapter_returns_none_for_non_equity_id_kind():
    assert adapter.fetch("lei", "549300VUYUFI3JTUAW28", current={}) is None
