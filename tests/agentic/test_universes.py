"""Tests for `pipeline.agentic.universes`.

Wikipedia fetch is monkeypatched; pandas.read_html does the real parsing
against minimal synthetic HTML so the parser contract is exercised
without hitting the network. The fixtures intentionally use a handful
of constituents per universe — full counts are validated at integration
time, not here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

pytest.importorskip("pandas")

from pipeline.agentic import universes


def _make_html(headers: List[str], rows: List[List[str]]) -> str:
    """Build a minimal HTML page containing one table pandas can parse."""
    head = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows
    )
    return f"<html><body><table>{head}{body}</table></body></html>"


# Fixtures keyed by universe name — small, deterministic, parser-exercising.
_FIXTURE_HTML: Dict[str, str] = {
    "smi": _make_html(
        ["Company", "Ticker", "ISIN"],
        [
            ["Nestlé", "NESN", "CH0038863350"],
            ["Roche Holding", "ROG", "CH0012032048"],
            ["Novartis", "NOVN", "CH0012005267"],
        ],
    ),
    "sp500": _make_html(
        ["Symbol", "Security", "GICS Sector"],
        [
            ["AAPL", "Apple Inc.", "Information Technology"],
            ["MSFT", "Microsoft Corp.", "Information Technology"],
            ["JNJ", "Johnson & Johnson", "Health Care"],
        ],
    ),
    "nasdaq100": _make_html(
        ["Ticker", "Company"],
        [
            ["AAPL", "Apple Inc."],
            ["GOOGL", "Alphabet"],
            ["NVDA", "NVIDIA Corp."],
        ],
    ),
    "dax40": _make_html(
        ["Ticker symbol", "Company"],
        [
            ["SAP", "SAP SE"],
            ["SIE", "Siemens AG"],
            ["BMW", "Bayerische Motoren Werke"],
        ],
    ),
    "ftse100": _make_html(
        ["EPIC", "Company"],
        [
            ["AZN", "AstraZeneca"],
            ["HSBA", "HSBC Holdings"],
            ["SHEL", "Shell plc"],
        ],
    ),
}


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point the universes cache at a per-test temp directory."""
    monkeypatch.setattr(universes, "_CACHE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_wikipedia(monkeypatch):
    """Replace _fetch_wikipedia with a lookup against _FIXTURE_HTML."""
    fetched: List[str] = []

    def fake_fetch(url: str) -> str:
        fetched.append(url)
        for name, spec in universes.UNIVERSE_SOURCES.items():
            if spec["url"] == url:
                return _FIXTURE_HTML[name]
        raise AssertionError(f"unexpected URL requested by test: {url}")

    monkeypatch.setattr(universes, "_fetch_wikipedia", fake_fetch)
    return fetched


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name,expected_first,expected_count",
    [
        ("smi", "NESN.SW", 3),
        ("sp500", "AAPL", 3),
        ("nasdaq100", "AAPL", 3),
        ("dax40", "SAP.DE", 3),
        ("ftse100", "AZN.L", 3),
    ],
)
def test_resolve_each_universe(
    name, expected_first, expected_count, isolated_cache, fake_wikipedia
):
    tickers = universes.resolve(name, use_cache=False)
    assert len(tickers) == expected_count, tickers
    assert tickers[0] == expected_first
    # Every ticker should be uniquely suffixed exactly once.
    suffix = universes.UNIVERSE_SOURCES[name].get("suffix", "")
    if suffix:
        for t in tickers:
            assert t.endswith(suffix), t
            assert t.count(suffix) == 1, t


def test_resolve_unknown_universe_raises(isolated_cache):
    with pytest.raises(ValueError, match="unknown universe"):
        universes.resolve("does_not_exist")


def test_resolve_uses_disk_cache_on_second_call(isolated_cache, fake_wikipedia):
    first = universes.resolve("smi")
    second = universes.resolve("smi")
    assert first == second
    # Wikipedia should have been hit exactly once — second call comes from cache.
    assert fetched_count_for(fake_wikipedia, "smi") == 1


def test_resolve_bypasses_cache_when_use_cache_false(isolated_cache, fake_wikipedia):
    universes.resolve("smi", use_cache=False)
    universes.resolve("smi", use_cache=False)
    assert fetched_count_for(fake_wikipedia, "smi") == 2


def test_resolve_repairs_corrupted_cache(isolated_cache, fake_wikipedia):
    cache_file = isolated_cache / "smi.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{not valid json", encoding="utf-8")
    tickers = universes.resolve("smi")
    assert tickers[0] == "NESN.SW"


def test_resolve_writes_cache_in_json_array_form(isolated_cache, fake_wikipedia):
    tickers = universes.resolve("smi")
    cached = json.loads((isolated_cache / "smi.json").read_text(encoding="utf-8"))
    assert cached == tickers


def fetched_count_for(fetched: List[str], name: str) -> int:
    url = universes.UNIVERSE_SOURCES[name]["url"]
    return sum(1 for u in fetched if u == url)


# ---------------------------------------------------------------------------
# supported_universes()
# ---------------------------------------------------------------------------

def test_supported_universes_lists_all_five():
    names = universes.supported_universes()
    assert set(names) == {"smi", "sp500", "nasdaq100", "dax40", "ftse100"}
    assert names == sorted(names), "supported_universes must return a sorted list"


# ---------------------------------------------------------------------------
# tickers_to_isins()
# ---------------------------------------------------------------------------

def test_tickers_to_isins_happy_path(monkeypatch):
    table = {
        "AAPL": {"isin": "US0378331005", "ticker": "AAPL"},
        "MSFT": {"isin": "US5949181045", "ticker": "MSFT"},
    }

    def fake_lookup(ticker, exchange_code=None, *, use_cache=True):
        return table.get(ticker)

    monkeypatch.setattr(
        "pipeline.gold.openfigi.fetch_openfigi_by_ticker", fake_lookup, raising=False
    )

    out = universes.tickers_to_isins(["AAPL", "MSFT"])
    assert [r.isin for r in out] == ["US0378331005", "US5949181045"]
    assert all(r.reason is None for r in out)


def test_tickers_to_isins_missing_returns_soft_miss(monkeypatch):
    def fake_lookup(ticker, exchange_code=None, *, use_cache=True):
        return None

    monkeypatch.setattr(
        "pipeline.gold.openfigi.fetch_openfigi_by_ticker", fake_lookup, raising=False
    )

    out = universes.tickers_to_isins(["UNKNOWN"])
    assert out[0].isin is None
    assert "no match" in out[0].reason


def test_tickers_to_isins_swallows_network_errors(monkeypatch):
    def boom(ticker, exchange_code=None, *, use_cache=True):
        raise RuntimeError("network down")

    monkeypatch.setattr(
        "pipeline.gold.openfigi.fetch_openfigi_by_ticker", boom, raising=False
    )

    out = universes.tickers_to_isins(["AAPL"])
    assert out[0].isin is None
    assert "openfigi" in out[0].reason
    assert "network down" in out[0].reason
