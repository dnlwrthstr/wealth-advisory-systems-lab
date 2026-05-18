"""Smoke tests for `pipeline.agentic.cli.fund_universe`.

The full assemble path is mocked at the AGENTS["fund"] layer; FIRDS is
mocked at the iter_issuer_records boundary. These tests verify CLI
plumbing — including the fund-specific cost-class default + opt-in
behaviour — not the agentic chain itself (which is covered by
test_assemble_fund.py and test_fund_firds_source.py).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

import pytest

from pipeline.agentic.cli import fund_universe as cli


_FAKE_UMBRELLAS = [
    {
        "umbrellaLei": "549300UM05ATQ0J0V275",
        "umbrellaName": "iShares III plc",
        "managementCompanyLei": "549300MS535KQL2L3F94",
        "managementCompanyName": "BlackRock Asset Management Ireland Limited",
        "country": "IE",
    },
    {
        "umbrellaLei": "5493006ESS9BM09FB892",
        "umbrellaName": "Vanguard Funds plc",
        "managementCompanyLei": "549300L5DPDGB59B0V69",
        "managementCompanyName": "Vanguard Group (Ireland) Limited",
        "country": "IE",
    },
]


# Minimal FIRDS shape: fund_firds.dedupe_by_isin requires gnr_cfi_code
# starting with 'C' (collective investment vehicle).
_FAKE_FIRDS_RECORDS: Dict[str, List[Dict[str, Any]]] = {
    "549300UM05ATQ0J0V275": [
        {"isin": "IE00B4L5Y983", "gnr_cfi_code": "CIVSXX"},
        {"isin": "IE00B5BMR087", "gnr_cfi_code": "CIVSXX"},
        {"isin": "IE00B4ND3602", "gnr_cfi_code": "CIVSXX"},
    ],
    "5493006ESS9BM09FB892": [
        {"isin": "IE00BFMXXD54", "gnr_cfi_code": "CIVSXX"},
        {"isin": "IE00BFMXVN36", "gnr_cfi_code": "CIVSXX"},
    ],
}


@dataclass
class _FakeAssembleResult:
    scope: str
    record: Dict[str, Any]
    quality_score: float
    remaining_gaps: List[str]


class _StubFundAgent:
    """Records every assemble_and_persist call, captures max_cost_class."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.raise_for: Dict[str, Exception] = {}
        self.chained_count: int = 2  # default fund chain: umbrella + managementCompany

    def assemble_and_persist(self, *, client, identifier, status, max_cost_class=None, **_):
        self.calls.append({
            "client": client,
            "identifier": dict(identifier),
            "status": status,
            "max_cost_class": max_cost_class,
        })
        isin = identifier["value"]
        if isin in self.raise_for:
            raise self.raise_for[isin]
        return {
            "primary": _FakeAssembleResult(
                scope="fund",
                record={"goldenId": f"FG-{isin}-001", "longName": f"Stub Fund {isin}"},
                quality_score=0.82,
                remaining_gaps=[],
            ),
            # Simulate the fund-specific 1-3-record issuer chain.
            "chained_issuers": [
                {"lei": f"LEI-{i}", "golden_id": f"ISS-LEI-{i}"}
                for i in range(self.chained_count)
            ],
        }


@pytest.fixture
def stub_umbrellas(monkeypatch):
    monkeypatch.setattr(cli, "load_issuers", lambda path=None: list(_FAKE_UMBRELLAS))
    return _FAKE_UMBRELLAS


@pytest.fixture
def stub_firds(monkeypatch):
    raised_for: Dict[str, Exception] = {}

    def fake_iter(lei: str, fl: List[str]) -> Iterator[Dict[str, Any]]:
        if lei in raised_for:
            raise raised_for[lei]
        yield from _FAKE_FIRDS_RECORDS.get(lei, [])

    monkeypatch.setattr(cli, "iter_issuer_records", fake_iter)
    return raised_for


@pytest.fixture
def stub_agent(monkeypatch):
    stub = _StubFundAgent()
    monkeypatch.setitem(cli.AGENTS, "fund", stub)
    return stub


@pytest.fixture
def silence_search_mirror(monkeypatch):
    """Inject a no-op search-index module so the lazy import succeeds without opensearchpy."""
    import types

    fake_mod = types.ModuleType("pipeline.gold.search_index_build")
    fake_mod.index_search_hit = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "pipeline.gold.search_index_build", fake_mod)


@pytest.fixture
def stub_opensearch_client(monkeypatch):
    """Inject a fake opensearch_client_from_env via sys.modules."""
    import types

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: object()
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)


# ---------------------------------------------------------------------------
# AC-5: unknown umbrella LEI exits non-zero
# ---------------------------------------------------------------------------

def test_unknown_umbrella_lei_exits_non_zero(stub_umbrellas):
    with pytest.raises(SystemExit) as excinfo:
        cli.run(["--umbrella-lei", "9999999999999999XXXX"])
    code = excinfo.value.code
    if isinstance(code, str):
        assert "unknown umbrella LEI" in code
    else:
        assert code != 0


def test_unknown_umbrella_lei_lists_known(stub_umbrellas):
    with pytest.raises(SystemExit) as excinfo:
        cli.run(["--umbrella-lei", "9999999999999999XXXX"])
    msg = str(excinfo.value.code) if isinstance(excinfo.value.code, str) else ""
    assert "549300UM05ATQ0J0V275" in msg
    assert "5493006ESS9BM09FB892" in msg


# ---------------------------------------------------------------------------
# AC-4: --dry-run skips persistence
# ---------------------------------------------------------------------------

def test_dry_run_does_not_call_agent(stub_umbrellas, stub_firds, stub_agent):
    rc = cli.run(["--dry-run"])
    assert rc == 0
    assert stub_agent.calls == [], "agent must not be called under --dry-run"


def test_dry_run_still_reports_per_umbrella(stub_umbrellas, stub_firds, stub_agent, capsys):
    cli.run(["--dry-run"])
    out = capsys.readouterr().out
    # 2 umbrellas, 5 total share-class ISINs
    assert "umbrellas=2" in out
    assert "isins=5" in out
    assert "skipped=5" in out


# ---------------------------------------------------------------------------
# AC-6: cost-class default is web_fetch
# ---------------------------------------------------------------------------

def test_cost_class_default_is_web_fetch(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client
):
    rc = cli.run([])  # no --enable-factsheet-skill flag
    assert rc == 0
    assert len(stub_agent.calls) == 5
    # Every call must pass max_cost_class="web_fetch"
    assert all(c["max_cost_class"] == "web_fetch" for c in stub_agent.calls), (
        "default cost-class cap must be web_fetch — see spec AC-6"
    )


def test_cost_class_default_reported_in_summary(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, capsys,
):
    cli.run([])
    out = capsys.readouterr().out
    assert "cost_class=web_fetch" in out


# ---------------------------------------------------------------------------
# AC-6: --enable-factsheet-skill opts into llm_skill cap
# ---------------------------------------------------------------------------

def test_enable_factsheet_skill_promotes_cost_class(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client
):
    rc = cli.run(["--enable-factsheet-skill"])
    assert rc == 0
    assert all(c["max_cost_class"] == "llm_skill" for c in stub_agent.calls), (
        "--enable-factsheet-skill must lift the cap to llm_skill"
    )


def test_enable_factsheet_skill_reported_in_summary(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, capsys,
):
    cli.run(["--enable-factsheet-skill"])
    out = capsys.readouterr().out
    assert "cost_class=llm_skill" in out


# ---------------------------------------------------------------------------
# Happy path: cross-checks per-ISIN identifiers and counts
# ---------------------------------------------------------------------------

def test_happy_path_calls_agent_per_share_class(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client
):
    rc = cli.run([])
    assert rc == 0
    assert len(stub_agent.calls) == 5
    isins = [c["identifier"]["value"] for c in stub_agent.calls]
    assert isins == [
        "IE00B4L5Y983", "IE00B5BMR087", "IE00B4ND3602",
        "IE00BFMXXD54", "IE00BFMXVN36",
    ]
    assert all(c["status"] == "in_universe" for c in stub_agent.calls)
    assert all(c["identifier"]["kind"] == "isin" for c in stub_agent.calls)


# ---------------------------------------------------------------------------
# Three-record issuer chain surfaces correctly
# ---------------------------------------------------------------------------

def test_chained_issuer_count_surfaces(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, tmp_path,
):
    stub_agent.chained_count = 3  # umbrella + managementCompany + promoter
    out_path = tmp_path / "report.json"
    cli.run(["--report-out", str(out_path)])
    data = json.loads(out_path.read_text(encoding="utf-8"))
    first_outcome = data["umbrellas"][0]["outcomes"][0]
    assert first_outcome["chained_issuers"] == 3


# ---------------------------------------------------------------------------
# AC-6 (umbrella-level FIRDS failure isolated)
# ---------------------------------------------------------------------------

def test_umbrella_level_firds_failure_isolated(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client,
):
    stub_firds["549300UM05ATQ0J0V275"] = RuntimeError("firds 503")
    rc = cli.run([])
    # Second umbrella's 2 ISINs still processed
    assert len(stub_agent.calls) == 2
    assert all(
        c["identifier"]["value"].startswith("IE00BFMX")
        for c in stub_agent.calls
    )
    assert rc == 0  # no per-ISIN failures even though one umbrella failed


# ---------------------------------------------------------------------------
# Per-ISIN error isolation
# ---------------------------------------------------------------------------

def test_per_isin_failure_isolated(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, capsys,
):
    stub_agent.raise_for["IE00B5BMR087"] = RuntimeError("yfinance timeout")
    rc = cli.run([])
    assert len(stub_agent.calls) == 5
    out = capsys.readouterr().out
    assert "success=4" in out
    assert "failed=1" in out
    assert rc == 1


# ---------------------------------------------------------------------------
# --limit-per-umbrella
# ---------------------------------------------------------------------------

def test_limit_per_umbrella_caps_count(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client,
):
    cli.run(["--limit-per-umbrella", "1"])
    assert len(stub_agent.calls) == 2  # 1 + 1 = 2


# ---------------------------------------------------------------------------
# --report-out: per-umbrella grouped JSON
# ---------------------------------------------------------------------------

def test_report_out_writes_per_umbrella_grouped_json(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, tmp_path,
):
    out = tmp_path / "report.json"
    cli.run(["--report-out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["requested_umbrellas"] == 2
    assert data["total_isins"] == 5
    assert data["success"] == 5
    assert data["cost_class"] == "web_fetch"
    assert len(data["umbrellas"]) == 2
    u0 = data["umbrellas"][0]
    assert u0["lei"] == "549300UM05ATQ0J0V275"
    assert u0["isins_found"] == 3
    assert len(u0["outcomes"]) == 3


# ---------------------------------------------------------------------------
# --umbrella-lei: single-umbrella scoping
# ---------------------------------------------------------------------------

def test_umbrella_lei_scopes_to_one(
    stub_umbrellas, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client,
):
    cli.run(["--umbrella-lei", "5493006ESS9BM09FB892"])
    assert len(stub_agent.calls) == 2
    isins = [c["identifier"]["value"] for c in stub_agent.calls]
    assert all(i.startswith("IE00BFMX") for i in isins)


# ---------------------------------------------------------------------------
# Missing OPENSEARCH_URL → exit code 2 (live mode only)
# ---------------------------------------------------------------------------

def test_missing_opensearch_url_returns_2(
    stub_umbrellas, stub_firds, stub_agent, monkeypatch,
):
    import types

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: None
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    rc = cli.run([])
    assert rc == 2
    assert stub_agent.calls == []
