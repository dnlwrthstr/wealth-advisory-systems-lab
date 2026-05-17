"""Equity FIRDS source adapter — projection + ISIN-from-state fallback."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from pipeline.agentic.sources import equity_firds as adapter
from pipeline.gold import equity_firds as gold


_LISN_DOCS = [
    {
        # NEWS submission — proper-case clean name (the one we want to pick).
        "isin": "CH0010570767",
        "lei": "529900JYJNNOKKAGK736",
        "gnr_full_name": "Chocoladefabriken Lindt and Spruengli AG",
        "gnr_cfi_code": "ESNUFB",
        "gnr_notional_curr_code": "CHF",
        "mic": "CHIO",
        "mrkt_trdng_start_date": "2017-01-03T00:00:00Z",
        "mrkt_trdng_trmination_date": "2019-06-28T23:59:00Z",
        "status": "TERM",
    },
    {
        # UNCH submission on an active venue — uppercase noisy name.
        "isin": "CH0010570767",
        "lei": "529900JYJNNOKKAGK736",
        "gnr_full_name": "CHOCOLADEFABRIKEN LINDT & SPRUENGLI PAR",
        "gnr_cfi_code": "ESNUFB",
        "gnr_notional_curr_code": "CHF",
        "mic": "XPOS",
        "mrkt_trdng_start_date": "1993-07-19T00:00:00Z",
        "mrkt_trdng_trmination_date": "",
        "status": "UNCH",
    },
]


def test_fetch_by_isin_picks_clean_long_name(monkeypatch):
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: _LISN_DOCS)
    patch = gold.fetch_by_isin("CH0010570767")
    assert patch["longName"] == "Chocoladefabriken Lindt and Spruengli AG"


def test_fetch_by_isin_returns_active_when_any_venue_alive(monkeypatch):
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: _LISN_DOCS)
    patch = gold.fetch_by_isin("CH0010570767")
    assert patch["lifecycleStatus"] == "active"


def test_fetch_by_isin_returns_delisted_when_all_terminated(monkeypatch):
    docs = [dict(d, status="TERM", mrkt_trdng_trmination_date="2020-01-01T00:00:00Z")
            for d in _LISN_DOCS]
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: docs)
    patch = gold.fetch_by_isin("CH0010570767")
    assert patch["lifecycleStatus"] == "delisted"


def test_fetch_by_isin_emits_issuer_snapshot_with_lei(monkeypatch):
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: _LISN_DOCS)
    patch = gold.fetch_by_isin("CH0010570767")
    issuer = patch["issuer"]
    assert issuer["lei"] == "529900JYJNNOKKAGK736"
    assert issuer["issuerId"] == "ISS-529900JYJNNOKKAGK736"


def test_fetch_by_isin_collapses_venues_to_one_listing_per_mic(monkeypatch):
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: _LISN_DOCS)
    patch = gold.fetch_by_isin("CH0010570767")
    mics = [l["mic"] for l in patch["secondaryListings"]]
    assert sorted(mics) == ["CHIO", "XPOS"]


def test_fetch_by_isin_returns_none_when_firds_empty(monkeypatch):
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: [])
    assert gold.fetch_by_isin("CH0000000000") is None


def test_fetch_by_isin_drops_listings_without_currency(monkeypatch):
    """ListingSnapshot's `listingCurrency` is required; rows that can't
    inherit a currency must be dropped, not emitted with None."""
    docs = [
        {"isin": "X", "mic": "MARK", "gnr_notional_curr_code": "", "status": "UNCH"},
    ]
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: docs)
    patch = gold.fetch_by_isin("X")
    assert patch.get("secondaryListings") in (None, [])


def test_adapter_accepts_isin_directly(monkeypatch):
    monkeypatch.setattr(gold, "fetch_firds_by_isin", lambda isin: _LISN_DOCS)
    result = adapter.fetch("isin", "CH0010570767", {})
    assert result is not None
    assert result.patch["issuer"]["lei"] == "529900JYJNNOKKAGK736"


def test_adapter_reads_isin_from_current_state_for_ticker_input(monkeypatch):
    """Lets the planner chain six_ticker_isin → equity_firds for ticker input."""
    seen = []
    def fake(isin):
        seen.append(isin)
        return {"longName": "X", "cfiCode": "ESNUFB"}
    # Patch the adapter's *own* binding — the from-import means the adapter
    # holds its own reference, so patching `gold.fetch_by_isin` doesn't reach it.
    monkeypatch.setattr(adapter, "fetch_by_isin", fake)
    state = {
        "identifierList": [
            {"identifier": "LISN.SW", "type": "ticker_symbol"},
            {"identifier": "CH0010570767", "type": "isin"},
        ],
    }
    result = adapter.fetch("ticker", "LISN.SW", state)
    assert result is not None
    assert seen == ["CH0010570767"]


def test_adapter_returns_none_when_no_isin_anywhere(monkeypatch):
    monkeypatch.setattr(adapter, "fetch_by_isin", lambda isin: {"longName": "X"})
    result = adapter.fetch("ticker", "LISN.SW", {})
    assert result is None
