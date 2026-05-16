"""fund_yahoo source — projects yfinance fund output into a FundGolden patch."""
from __future__ import annotations

from pipeline.agentic.sources import fund_yahoo


def test_projects_market_data_ter_and_allocation(monkeypatch):
    yhoo = {
        "yahooSymbol": "IWDA.L",
        "navPrice": 75.32,
        "regularMarketPrice": 75.40,
        "currency": "USD",
        "totalAssets": 95_000_000_000,
        "expenseRatio": 0.20,  # percentage form per yfinance
        "ytdReturn": 0.082,
        "oneYearReturn": 0.215,
        "open": 75.00,
        "high": 75.60,
        "low": 74.90,
        "close": 75.40,
        "volume": 1_234_000,
        "assetAllocation": {
            "bySector": [{"sector": "Information Technology", "percentage": 0.25}],
            "byAssetClass": [{"type": "EQUITY", "percentage": 1.0}],
            "holdings": [{"identifier": "AAPL", "weight": 0.05}],
        },
    }
    monkeypatch.setattr(fund_yahoo, "fetch_yahoo_fund", lambda isin: yhoo)

    result = fund_yahoo.fetch("isin", "IE00B4L5Y983", current={})
    assert result is not None
    patch = result.patch

    assert patch["marketData"]["nav"]["value"] == 75.32
    assert patch["marketData"]["marketPrice"]["value"] == 75.40
    assert patch["marketData"]["aum"]["amount"] == 95_000_000_000
    assert patch["marketData"]["ytdReturn"] == 0.082
    assert patch["marketData"]["oneYearReturn"] == 0.215
    # Percentage-form TER (0.20) is normalised to decimal fraction (0.002).
    assert patch["totalExpenseRatio"] == 0.20 / 100.0
    # Holdings list is intentionally dropped — Yahoo only carries top-10.
    assert "holdings" not in patch["assetAllocation"]
    assert patch["assetAllocation"]["bySector"][0]["sector"] == "Information Technology"


def test_returns_none_when_yfinance_has_nothing(monkeypatch):
    monkeypatch.setattr(fund_yahoo, "fetch_yahoo_fund", lambda isin: None)
    assert fund_yahoo.fetch("isin", "ZZ", current={}) is None


def test_returns_none_for_negative_cache(monkeypatch):
    monkeypatch.setattr(fund_yahoo, "fetch_yahoo_fund", lambda isin: {"_negative": True})
    assert fund_yahoo.fetch("isin", "ZZ", current={}) is None


def test_returns_none_for_non_isin_identifier(monkeypatch):
    monkeypatch.setattr(fund_yahoo, "fetch_yahoo_fund", lambda isin: {"navPrice": 1.0, "currency": "USD"})
    assert fund_yahoo.fetch("ticker", "IWDA", current={}) is None
