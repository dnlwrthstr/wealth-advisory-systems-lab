"""Verify the equity_parquet_seed + equity_yahoo split composes correctly.

Cost-first ranking: parquet_seed (file_read) runs first, equity_yahoo
(api_call) overlays the remaining gaps. Fill-empty-only merge ensures
yahoo doesn't clobber what parquet provided.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pytest

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.merger import SourceFetchResult


def _now() -> datetime:
    return datetime(2026, 5, 16, tzinfo=timezone.utc)


def test_parquet_seed_runs_before_yahoo_when_both_have_data(monkeypatch):
    """parquet_seed fills identifiers + currency; yahoo overlays market data."""
    from pipeline.agentic.sources import equity_parquet_seed as adapter_seed
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo

    def fake_seed(kind, value, current):
        return SourceFetchResult(
            patch={
                "identifierList": [
                    {"identifier": value, "type": "isin"},
                    {"identifier": "AAPL", "type": "tickerSymbol"},
                ],
                "longName": "Apple Inc. (from parquet)",
                "currencyOfDenomination": "USD",
                "issuer": {"issuerId": "ISS-APPLE", "legalName": "Apple Inc."},
                "primaryListing": {"mic": "XNAS", "ticker": "AAPL", "listingCurrency": "USD"},
                "assetClass": "Equity / Common Stock",
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "finfox-parquet"}],
        )

    def fake_yahoo(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "Apple Inc. (from yahoo)",  # should NOT overwrite parquet
                "marketData": {"lastTradePrice": {"value": 195.0, "currency": "USD"}},
                "keyFigures": {"marketCapitalization": {"amount": 3_000_000_000_000, "currency": "USD"}},
                "sharesOutstanding": 15_400_000_000,
            },
            source_of_truth_rows=[{"fieldGroup": "marketData", "source": "yfinance"}],
        )

    monkeypatch.setattr(adapter_seed, "fetch", fake_seed)
    monkeypatch.setattr(adapter_yahoo, "fetch", fake_yahoo)

    result = assemble_golden(
        scope="equity",
        identifier={"kind": "isin", "value": "US0378331005"},
        now=_now(),
        run_id="test-split",
    )

    sources = [inv["source"] for inv in result.trace.invocations]
    assert sources[0] == "equity_parquet_seed"
    assert sources[1] == "equity_yahoo"

    # Parquet's value survives fill-empty-only merge.
    assert result.record["longName"] == "Apple Inc. (from parquet)"
    # Yahoo's market data fills a field parquet didn't have.
    assert result.record["marketData"]["lastTradePrice"]["value"] == 195.0


def test_yahoo_uses_ticker_from_current_when_parquet_resolved_it(monkeypatch):
    """If parquet_seed sets primaryListing.ticker, yahoo's adapter uses it
    instead of re-resolving from ISIN."""
    from pipeline.agentic.sources import equity_parquet_seed as adapter_seed
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo

    def fake_seed(kind, value, current):
        return SourceFetchResult(
            patch={
                "longName": "Apple Inc.",
                "currencyOfDenomination": "USD",
                "issuer": {"issuerId": "ISS-APPLE", "legalName": "Apple Inc."},
                "primaryListing": {"mic": "XNAS", "ticker": "AAPL", "listingCurrency": "USD"},
                "assetClass": "Equity / Common Stock",
                "lifecycleStatus": "active",
            },
            source_of_truth_rows=[],
        )

    monkeypatch.setattr(adapter_seed, "fetch", fake_seed)

    captured: Dict[str, Any] = {}

    def spy_fetch_by_identifier(kind, value, run_id=None, now=None):
        captured["kind"] = kind
        captured["value"] = value
        return None  # we only care about how it was called

    # The adapter imported fetch_by_identifier at module load — patch its
    # local reference, not the source module's.
    monkeypatch.setattr(adapter_yahoo, "fetch_by_identifier", spy_fetch_by_identifier)

    assemble_golden(
        scope="equity",
        identifier={"kind": "isin", "value": "US0378331005"},
        now=_now(),
        run_id="test-ticker-chain",
    )
    # The yahoo adapter should have called fetch_by_identifier with the
    # ticker resolved by parquet_seed, not the original ISIN.
    assert captured["kind"] == "ticker"
    assert captured["value"] == "AAPL"
