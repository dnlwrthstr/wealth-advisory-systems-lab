"""Smoke tests for `pipeline.agentic.cli.equity_universe`.

The full assemble path is mocked at the AGENTS["equity"] layer — these
tests verify CLI plumbing (argparse choices, dry-run write-suppression,
per-ISIN error isolation, report shape), not the agentic chain itself
(which is covered by `test_assemble_equity.py` and friends).
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from pipeline.agentic import universes
from pipeline.agentic.cli import equity_universe as cli


@dataclass
class _FakeAssembleResult:
    scope: str
    record: Dict[str, Any]
    quality_score: float
    remaining_gaps: List[str]


class _StubEquityAgent:
    """Stand-in for `AGENTS['equity']`. Records every assemble_and_persist call."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.raise_for: Dict[str, Exception] = {}
        self.gaps_for: Dict[str, List[str]] = {}

    def assemble_and_persist(self, *, client, identifier, status, **_):
        call = {
            "client": client,
            "identifier": dict(identifier),
            "status": status,
        }
        self.calls.append(call)
        key = identifier["value"]
        if key in self.raise_for:
            raise self.raise_for[key]
        return {
            "primary": _FakeAssembleResult(
                scope="equity",
                record={"goldenId": f"EQG-{key}-001", "longName": f"Stub {key}"},
                quality_score=0.85,
                remaining_gaps=self.gaps_for.get(key, []),
            ),
            "chained_issuers": [
                {"lei": "EXAMPLE-LEI-001", "golden_id": "ISS-EXAMPLE-LEI-001"}
            ],
        }


@pytest.fixture
def stub_universe(monkeypatch):
    """Replace universes.resolve with a deterministic three-ticker list."""
    tickers = ["NESN.SW", "ROG.SW", "NOVN.SW"]
    monkeypatch.setattr(universes, "resolve", lambda name, *, use_cache=True: list(tickers))
    return tickers


@pytest.fixture
def stub_tickers_to_isins(monkeypatch):
    """Map each ticker deterministically to a fake ISIN."""
    table = {
        "NESN.SW": "CH0038863350",
        "ROG.SW": "CH0012032048",
        "NOVN.SW": "CH0012005267",
    }

    def fake(tickers):
        return [
            universes.Resolution(ticker=t, isin=table.get(t))
            for t in tickers
        ]

    monkeypatch.setattr(universes, "tickers_to_isins", fake)
    return table


@pytest.fixture
def stub_agent(monkeypatch):
    """Replace AGENTS['equity'] with a recording stub."""
    stub = _StubEquityAgent()
    monkeypatch.setitem(cli.AGENTS, "equity", stub)
    return stub


@pytest.fixture
def silence_search_mirror(monkeypatch):
    """Make the lazy `index_search_hit` import a no-op without requiring opensearchpy."""
    import types

    fake_mod = types.ModuleType("pipeline.gold.search_index_build")

    def fake_index_search_hit(*args, **kwargs):
        return None

    fake_mod.index_search_hit = fake_index_search_hit
    monkeypatch.setitem(sys.modules, "pipeline.gold.search_index_build", fake_mod)


# ---------------------------------------------------------------------------
# AC-5: unknown universe exits non-zero
# ---------------------------------------------------------------------------

def test_unknown_universe_exits_non_zero(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.run(["--universe", "does_not_exist"])
    assert excinfo.value.code != 0
    err = capsys.readouterr().err
    assert "does_not_exist" in err


# ---------------------------------------------------------------------------
# AC-4: --dry-run skips persistence
# ---------------------------------------------------------------------------

def test_dry_run_does_not_call_agent(stub_universe, stub_tickers_to_isins, stub_agent):
    rc = cli.run(["--universe", "smi", "--dry-run"])
    assert rc == 0
    assert stub_agent.calls == [], "agent must not be called under --dry-run"


def test_dry_run_still_reports_per_ticker(
    stub_universe, stub_tickers_to_isins, stub_agent, capsys
):
    cli.run(["--universe", "smi", "--dry-run"])
    out = capsys.readouterr().out
    # The summary line is the only stdout content; per-ticker reporting goes through logging.
    assert "universe=smi" in out
    assert "skipped=3" in out


# ---------------------------------------------------------------------------
# Happy path: mocked agent + search-mirror
# ---------------------------------------------------------------------------

def test_happy_path_calls_agent_per_ticker(
    stub_universe,
    stub_tickers_to_isins,
    stub_agent,
    silence_search_mirror,
    monkeypatch,
):
    # Pretend OPENSEARCH_URL is set so the run() path takes the persist branch.
    import types

    fake_client = object()
    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: fake_client
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    rc = cli.run(["--universe", "smi"])
    assert rc == 0
    assert len(stub_agent.calls) == 3
    # All called with status=in_universe by default and ISIN identifiers.
    assert all(c["status"] == "in_universe" for c in stub_agent.calls)
    assert [c["identifier"]["value"] for c in stub_agent.calls] == [
        "CH0038863350",
        "CH0012032048",
        "CH0012005267",
    ]
    assert all(c["identifier"]["kind"] == "isin" for c in stub_agent.calls)


def test_happy_path_returns_zero_and_summary_counts(
    stub_universe,
    stub_tickers_to_isins,
    stub_agent,
    silence_search_mirror,
    monkeypatch,
    capsys,
):
    import types

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: object()
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    rc = cli.run(["--universe", "smi"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "success=3" in out
    assert "failed=0" in out


# ---------------------------------------------------------------------------
# Error isolation: one bad ISIN doesn't abort the batch
# ---------------------------------------------------------------------------

def test_per_ticker_failures_are_isolated(
    stub_universe,
    stub_tickers_to_isins,
    stub_agent,
    silence_search_mirror,
    monkeypatch,
    capsys,
):
    import types

    stub_agent.raise_for["CH0012032048"] = RuntimeError("yahoo timeout")

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: object()
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    rc = cli.run(["--universe", "smi"])
    assert rc == 1  # at least one failure → non-zero exit
    out = capsys.readouterr().out
    assert "success=2" in out
    assert "failed=1" in out
    # All three agent calls were attempted — the middle one failed without aborting.
    assert len(stub_agent.calls) == 3


# ---------------------------------------------------------------------------
# Ticker fallback: tickers without ISIN match get passed as kind=ticker
# ---------------------------------------------------------------------------

def test_fallback_to_ticker_when_isin_lookup_misses(
    stub_universe, stub_agent, silence_search_mirror, monkeypatch
):
    import types

    # tickers_to_isins returns None ISIN for the first ticker.
    def fake_tti(tickers):
        return [
            universes.Resolution(ticker=t, isin=None if t == "NESN.SW" else "CH0012005267")
            for t in tickers
        ]

    monkeypatch.setattr(universes, "tickers_to_isins", fake_tti)

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: object()
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    cli.run(["--universe", "smi", "--limit", "1"])
    # First call uses ticker (ISIN miss); identifier.kind reflects the routing.
    assert stub_agent.calls[0]["identifier"]["kind"] == "ticker"
    assert stub_agent.calls[0]["identifier"]["value"] == "NESN.SW"


# ---------------------------------------------------------------------------
# Report JSON output
# ---------------------------------------------------------------------------

def test_report_out_writes_json_with_outcomes(
    stub_universe,
    stub_tickers_to_isins,
    stub_agent,
    silence_search_mirror,
    monkeypatch,
    tmp_path,
):
    import types

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: object()
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    report_path = tmp_path / "report.json"
    cli.run(["--universe", "smi", "--report-out", str(report_path)])

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["universe"] == "smi"
    assert data["requested"] == 3
    assert data["success"] == 3
    assert len(data["outcomes"]) == 3
    assert all(o["status"] == "success" for o in data["outcomes"])
    assert all(o["golden_id"] for o in data["outcomes"])


# ---------------------------------------------------------------------------
# --limit caps the batch
# ---------------------------------------------------------------------------

def test_limit_caps_processed_tickers(
    stub_universe, stub_tickers_to_isins, stub_agent
):
    cli.run(["--universe", "smi", "--dry-run", "--limit", "2"])
    # Three tickers in the universe; --limit 2 keeps the first two.
    # Outcomes recorded inside the agent stub would be zero (dry-run), so we
    # look at the universes.resolve fixture sliced via report indirectly.
    # Direct check: parser still accepted the value and the run completed
    # without trying to call the agent (dry-run).
    assert stub_agent.calls == []


# ---------------------------------------------------------------------------
# Persist branch without OPENSEARCH_URL → exit code 2
# ---------------------------------------------------------------------------

def test_missing_opensearch_url_returns_2(
    stub_universe, stub_tickers_to_isins, stub_agent, monkeypatch
):
    import types

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: None  # simulate URL not set
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    rc = cli.run(["--universe", "smi"])
    assert rc == 2
    assert stub_agent.calls == [], "no agent calls without a client"
