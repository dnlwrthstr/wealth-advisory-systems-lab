"""Smoke tests for `pipeline.agentic.cli.bond_universe`.

The full assemble path is mocked at the AGENTS["bond"] layer; FIRDS is
mocked at the iter_issuer_records boundary. These tests verify CLI
plumbing (argparse, dry-run write-suppression, per-issuer error
isolation, per-ISIN error isolation, report shape), not the agentic
chain itself (which is covered by `test_assemble_bond.py` and
`test_bond_firds_source.py`).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

import pytest

from pipeline.agentic.cli import bond_universe as cli


_FAKE_ISSUERS = [
    {
        "lei": "529900AQBND3S6YJLY83",
        "name": "Federal Republic of Germany",
        "issuerType": "government",
        "country": "DE",
        "assetClass": "Fixed Income / Government Bond",
        "assetClassId": "AC-FI-GOVT",
    },
    {
        "lei": "5493001KJTIIGC8Y1R12",  # invented LEI for the test
        "name": "Sample Corp",
        "issuerType": "corporate",
        "country": "CH",
        "assetClass": "Fixed Income / Corporate Bond",
        "assetClassId": "AC-FI-CORP",
    },
]

# Minimal FIRDS shape: dedupe_by_isin requires `gnr_cfi_code` starting with
# 'D' (debt) — anything else gets filtered out as not-a-bond.
_FAKE_FIRDS_RECORDS: Dict[str, List[Dict[str, Any]]] = {
    "529900AQBND3S6YJLY83": [
        {"isin": "DE0001102309", "gnr_cfi_code": "DBFTFR"},
        {"isin": "DE0001102325", "gnr_cfi_code": "DBFTFR"},
        {"isin": "DE0001102341", "gnr_cfi_code": "DBFTFR"},
    ],
    "5493001KJTIIGC8Y1R12": [
        {"isin": "CH0000000001", "gnr_cfi_code": "DBFTFR"},
        {"isin": "CH0000000002", "gnr_cfi_code": "DBFTFR"},
    ],
}


@dataclass
class _FakeAssembleResult:
    scope: str
    record: Dict[str, Any]
    quality_score: float
    remaining_gaps: List[str]


class _StubBondAgent:
    """Records every assemble_and_persist call."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.raise_for: Dict[str, Exception] = {}
        self.gaps_for: Dict[str, List[str]] = {}

    def assemble_and_persist(self, *, client, identifier, status, **_):
        self.calls.append(
            {"client": client, "identifier": dict(identifier), "status": status}
        )
        isin = identifier["value"]
        if isin in self.raise_for:
            raise self.raise_for[isin]
        return {
            "primary": _FakeAssembleResult(
                scope="bond",
                record={"goldenId": f"BG-{isin}-001", "longName": f"Stub Bond {isin}"},
                quality_score=0.80,
                remaining_gaps=self.gaps_for.get(isin, []),
            ),
            "chained_issuers": [
                {"lei": "EXAMPLE-LEI", "golden_id": "ISS-EXAMPLE-LEI"}
            ],
        }


@pytest.fixture
def stub_issuers(monkeypatch):
    monkeypatch.setattr(cli, "load_issuers", lambda path=None: list(_FAKE_ISSUERS))
    return _FAKE_ISSUERS


@pytest.fixture
def stub_firds(monkeypatch):
    """Map iter_issuer_records to canned per-LEI records."""
    raised_for: Dict[str, Exception] = {}

    def fake_iter(lei: str, fl: List[str]) -> Iterator[Dict[str, Any]]:
        if lei in raised_for:
            raise raised_for[lei]
        yield from _FAKE_FIRDS_RECORDS.get(lei, [])

    monkeypatch.setattr(cli, "iter_issuer_records", fake_iter)
    # The dedupe helper is the real one — small + side-effect-free.
    return raised_for


@pytest.fixture
def stub_agent(monkeypatch):
    stub = _StubBondAgent()
    monkeypatch.setitem(cli.AGENTS, "bond", stub)
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
# AC-5: unknown LEI exits non-zero
# ---------------------------------------------------------------------------

def test_unknown_lei_exits_non_zero(stub_issuers, capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.run(["--issuer-lei", "9999999999999999XXXX"])
    code = excinfo.value.code
    # SystemExit can carry int or str
    if isinstance(code, str):
        assert "unknown issuer LEI" in code
    else:
        assert code != 0


def test_unknown_lei_lists_known_leis(stub_issuers):
    with pytest.raises(SystemExit) as excinfo:
        cli.run(["--issuer-lei", "9999999999999999XXXX"])
    msg = str(excinfo.value.code) if isinstance(excinfo.value.code, str) else ""
    # Known LEIs should appear in the error message
    assert "529900AQBND3S6YJLY83" in msg
    assert "5493001KJTIIGC8Y1R12" in msg


# ---------------------------------------------------------------------------
# AC-4: --dry-run skips persistence
# ---------------------------------------------------------------------------

def test_dry_run_does_not_call_agent(stub_issuers, stub_firds, stub_agent):
    rc = cli.run(["--dry-run"])
    assert rc == 0
    assert stub_agent.calls == [], "agent must not be called under --dry-run"


def test_dry_run_still_reports_per_issuer(stub_issuers, stub_firds, stub_agent, capsys):
    cli.run(["--dry-run"])
    out = capsys.readouterr().out
    # Two issuers, 5 total ISINs (3 + 2)
    assert "issuers=2" in out
    assert "isins=5" in out
    assert "skipped=5" in out


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_happy_path_calls_agent_per_isin(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client
):
    rc = cli.run([])  # --all is the default
    assert rc == 0
    # 3 + 2 = 5 agent calls
    assert len(stub_agent.calls) == 5
    isins = [c["identifier"]["value"] for c in stub_agent.calls]
    assert isins == [
        "DE0001102309", "DE0001102325", "DE0001102341",
        "CH0000000001", "CH0000000002",
    ]
    assert all(c["status"] == "in_universe" for c in stub_agent.calls)
    assert all(c["identifier"]["kind"] == "isin" for c in stub_agent.calls)


def test_happy_path_summary_counts(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, capsys,
):
    cli.run([])
    out = capsys.readouterr().out
    assert "success=5" in out
    assert "failed=0" in out


# ---------------------------------------------------------------------------
# AC-6: issuer-level FIRDS failure isolated
# ---------------------------------------------------------------------------

def test_issuer_level_firds_failure_isolated(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client,
):
    # Make iter_issuer_records raise for the first issuer.
    stub_firds["529900AQBND3S6YJLY83"] = RuntimeError("firds 503")
    rc = cli.run([])
    # Second issuer's 2 ISINs still processed
    assert len(stub_agent.calls) == 2
    assert all(
        c["identifier"]["value"].startswith("CH") for c in stub_agent.calls
    )
    # No per-ISIN failures means rc=0 even though one issuer failed at the FIRDS level
    assert rc == 0


# ---------------------------------------------------------------------------
# Per-ISIN error isolation
# ---------------------------------------------------------------------------

def test_per_isin_failure_isolated(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, capsys,
):
    stub_agent.raise_for["DE0001102325"] = RuntimeError("yfinance timeout")
    rc = cli.run([])
    # All 5 ISINs attempted
    assert len(stub_agent.calls) == 5
    out = capsys.readouterr().out
    assert "success=4" in out
    assert "failed=1" in out
    # Exit code 1 because at least one ISIN failed
    assert rc == 1


# ---------------------------------------------------------------------------
# --limit-per-issuer
# ---------------------------------------------------------------------------

def test_limit_per_issuer_caps_count(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client,
):
    cli.run(["--limit-per-issuer", "1"])
    # 1 + 1 = 2 ISINs total
    assert len(stub_agent.calls) == 2


# ---------------------------------------------------------------------------
# --report-out: per-issuer grouped JSON
# ---------------------------------------------------------------------------

def test_report_out_writes_per_issuer_grouped_json(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror,
    stub_opensearch_client, tmp_path,
):
    out = tmp_path / "report.json"
    cli.run(["--report-out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["requested_issuers"] == 2
    assert data["total_isins"] == 5
    assert data["success"] == 5
    assert len(data["issuers"]) == 2
    # First issuer's outcomes
    ir0 = data["issuers"][0]
    assert ir0["lei"] == "529900AQBND3S6YJLY83"
    assert ir0["isins_found"] == 3
    assert len(ir0["outcomes"]) == 3
    assert all(o["status"] == "success" for o in ir0["outcomes"])


# ---------------------------------------------------------------------------
# --issuer-lei: single-issuer scoping
# ---------------------------------------------------------------------------

def test_issuer_lei_scopes_to_one_issuer(
    stub_issuers, stub_firds, stub_agent, silence_search_mirror, stub_opensearch_client,
):
    cli.run(["--issuer-lei", "5493001KJTIIGC8Y1R12"])
    assert len(stub_agent.calls) == 2
    isins = [c["identifier"]["value"] for c in stub_agent.calls]
    assert all(i.startswith("CH") for i in isins)


# ---------------------------------------------------------------------------
# Missing OPENSEARCH_URL → exit code 2 (live mode only)
# ---------------------------------------------------------------------------

def test_missing_opensearch_url_returns_2(
    stub_issuers, stub_firds, stub_agent, monkeypatch,
):
    import types

    fake_store = types.ModuleType("instruments.opensearch_store")
    fake_store.opensearch_client_from_env = lambda: None
    monkeypatch.setitem(sys.modules, "instruments.opensearch_store", fake_store)

    rc = cli.run([])
    assert rc == 2
    assert stub_agent.calls == []
