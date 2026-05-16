"""equity_yahoo picks up a ticker set by OpenFIGI (via identifierList) too.

Earlier turn: parquet_seed → set primaryListing.ticker → yahoo reads it.
This turn: openfigi → set identifierList[tickerSymbol] → yahoo reads it too.
"""
from __future__ import annotations

from typing import Any, Dict

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.merger import SourceFetchResult


def test_yahoo_uses_ticker_from_identifierList_when_no_primary_listing(monkeypatch):
    from pipeline.agentic.sources import openfigi as adapter_openfigi
    from pipeline.agentic.sources import equity_parquet_seed as adapter_seed
    from pipeline.agentic.sources import equity_yahoo as adapter_yahoo

    # parquet_seed has nothing — simulates the no-FINFOX environment.
    monkeypatch.setattr(adapter_seed, "fetch", lambda k, v, c: None)

    # openfigi resolves the ISIN to a ticker, no primaryListing.
    monkeypatch.setattr(adapter_openfigi, "fetch", lambda k, v, c: SourceFetchResult(
        patch={
            "identifierList": [
                {"identifier": v, "type": "isin"},
                {"identifier": "BBG000B9XRY4", "type": "figi"},
                {"identifier": "AAPL", "type": "tickerSymbol"},
            ],
            "longName": "APPLE INC",
            "equitySubType": "commonStock",
        },
        source_of_truth_rows=[{"fieldGroup": "identifiers", "source": "openfigi"}],
    ))

    captured: Dict[str, Any] = {}
    monkeypatch.setattr(adapter_yahoo, "fetch_by_identifier", lambda kind, value, **kw: captured.setdefault("call", {"kind": kind, "value": value}))

    assemble_golden(
        scope="equity",
        identifier={"kind": "isin", "value": "US0378331005"},
        run_id="test-openfigi-chain",
    )

    assert captured["call"]["kind"] == "ticker"
    assert captured["call"]["value"] == "AAPL"
