"""Curated SIX ticker→ISIN map + agentic adapter."""
from __future__ import annotations

import pytest

from pipeline.agentic.sources import six_ticker_isin as adapter
from pipeline.gold import six_ticker_isin as gold


def test_known_smi_tickers_resolve():
    assert gold.isin_for_ticker("ABBN.SW") == "CH0012221716"
    assert gold.isin_for_ticker("NESN.SW") == "CH0038863350"
    assert gold.isin_for_ticker("LISN.SW") == "CH0010570767"


def test_unknown_ticker_returns_none():
    assert gold.isin_for_ticker("NOPE.SW") is None
    assert gold.isin_for_ticker("") is None
    assert gold.isin_for_ticker(None) is None


def test_lookup_is_case_insensitive_on_upper_fallback():
    assert gold.isin_for_ticker("abbn.sw") == "CH0012221716"


def test_known_tickers_returns_sorted_list():
    tickers = gold.known_tickers()
    assert tickers == sorted(tickers)
    assert "LISN.SW" in tickers


def test_adapter_skips_isin_input():
    assert adapter.fetch("isin", "CH0012221716", {}) is None


def test_adapter_skips_unknown_ticker():
    assert adapter.fetch("ticker", "NOPE.SW", {}) is None


def test_adapter_emits_isin_ticker_and_valor_for_known_ticker():
    result = adapter.fetch("ticker", "LISN.SW", {})
    assert result is not None
    ids = {(e["type"], e["identifier"]) for e in result.patch["identifierList"]}
    assert ("isin", "CH0010570767") in ids
    assert ("tickerSymbol", "LISN.SW") in ids
    # Valor 1057076 derived from CH0010570767 (digits 2..11, strip leading zeros).
    assert ("valor", "1057076") in ids


def test_adapter_provenance_credits_six_curated():
    result = adapter.fetch("ticker", "ABBN.SW", {})
    assert result is not None
    assert result.source_of_truth_rows == [
        {"fieldGroup": "identifiers", "source": "six-curated"},
    ]
