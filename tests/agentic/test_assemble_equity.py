"""End-to-end: assemble_golden(scope='equity', ...) with yfinance mocked."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from pipeline.agentic.assemble import assemble_golden


class _FakeTicker:
    """Stand-in for `yfinance.Ticker` — returns canned `.info` and `.isin`."""

    def __init__(self, info: Dict[str, Any], isin: str):
        self._info = info
        self.isin = isin

    @property
    def info(self) -> Dict[str, Any]:
        return self._info


@pytest.fixture(autouse=True)
def _disable_network_sources(monkeypatch):
    """Stop network-hitting equity sources from running during these tests."""
    from pipeline.agentic.sources import openfigi as openfigi_adapter
    from pipeline.agentic.sources import equity_firds as firds_adapter
    monkeypatch.setattr(openfigi_adapter, "fetch_openfigi_by_isin", lambda isin, **kw: None)
    monkeypatch.setattr(firds_adapter, "fetch_by_isin", lambda isin: None)


@pytest.fixture
def fake_yfinance(monkeypatch):
    """Patch yfinance so equity_yahoo never hits the network."""
    info = {
        "longName": "Apple Inc.",
        "shortName": "Apple",
        "currency": "USD",
        "exchange": "NMS",
        "country": "United States",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "quoteType": "EQUITY",
        "currentPrice": 195.12,
        "regularMarketOpen": 194.0,
        "dayHigh": 196.5,
        "dayLow": 193.8,
        "previousClose": 194.5,
        "volume": 50_000_000,
        "marketCap": 3_000_000_000_000,
        "trailingEps": 6.12,
        "trailingPE": 31.8,
        "beta": 1.25,
        "sharesOutstanding": 15_400_000_000,
        "firstTradeDateEpochUtc": 345_513_600,
        "uuid": "apple-uuid",
    }
    isin = "US0378331005"

    import sys
    import types

    fake_module = types.SimpleNamespace(Ticker=lambda symbol: _FakeTicker(info, isin))
    sys.modules["yfinance"] = fake_module
    yield
    sys.modules.pop("yfinance", None)


def _assemble(isin: str = "US0378331005"):
    return assemble_golden(
        scope="equity",
        identifier={"kind": "isin", "value": isin},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-run",
    )


def test_assemble_populates_required_fields(fake_yfinance):
    result = _assemble()
    record = result.record
    for required in ("goldenId", "longName", "assetClass", "currencyOfDenomination", "issuer", "primaryListing", "recordMeta"):
        assert record.get(required) is not None, f"required field {required} missing"
    assert record["longName"] == "Apple Inc."
    assert record["currencyOfDenomination"] == "USD"


def test_assemble_builds_golden_id_from_isin_and_mic(fake_yfinance):
    result = _assemble()
    assert result.record["goldenId"].startswith("EQG-US0378331005-")


def test_assemble_record_validates_against_pydantic_model(fake_yfinance):
    """The assembled dict must round-trip through the canonical EquityGolden."""
    from universe.models import EquityGolden

    result = _assemble()
    EquityGolden.model_validate(result.record)


def test_assemble_records_provenance_and_quality(fake_yfinance):
    result = _assemble()
    assert result.provenance, "expected at least one SourceAttribution row"
    assert 0.0 < result.quality_score <= 1.0
    yahoo_inv = next(inv for inv in result.trace.invocations if inv["source"] == "equity_yahoo")
    assert yahoo_inv["outcome"] == "ok"


def test_equity_yahoo_falls_back_to_isin_when_existing_ticker_yields_nothing(monkeypatch):
    """Regression: OpenFIGI may set a non-Yahoo ticker (e.g. CH ISIN → "ABJ").
    yfinance returns sparse `.info` for it and fetch_by_identifier yields
    None — the adapter must retry by ISIN so Yahoo's own ISIN resolver runs."""
    from pipeline.agentic.sources import equity_yahoo as adapter

    seen: list[tuple[str, str]] = []

    def fake_fetch(kind: str, value: str):
        seen.append((kind, value))
        return None

    monkeypatch.setattr(adapter, "fetch_by_identifier", fake_fetch)
    state = {"identifierList": [{"identifier": "ABJ", "type": "tickerSymbol"}]}
    result = adapter.fetch("isin", "CH0012221716", state)

    assert result is None
    assert seen == [("ticker", "ABJ"), ("isin", "CH0012221716")]


def test_assemble_returns_remaining_gaps_when_source_underdelivers(monkeypatch):
    """If both registered equity sources return nothing, the assembled record
    reports the gaps."""
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo

    monkeypatch.setattr(adapter_yahoo, "fetch", lambda k, v, c: None)
    result = assemble_golden(
        scope="equity",
        identifier={"kind": "isin", "value": "ZZ0000000000"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-run-empty",
    )
    # No source data → important fields remain gaps.
    assert "longName" in result.remaining_gaps
    assert result.quality_score == 0.0
    # Assembler still fills its owned fields so the structure exists.
    assert result.record["recordMeta"]["ingestionRunId"] == "test-run-empty"
