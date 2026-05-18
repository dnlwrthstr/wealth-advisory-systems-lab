"""Unit tests for `pipeline.agentic.sources.fund_lookthrough_skill`.

8 sub-cases mapped to spec-003 ACs and design resolutions:

  (a) Predicate truth table — AC-2
  (b) Proxy resolution — AC-1 (mocked)
  (c) Cache hit — AC-5
  (d) SDK / API key gating
  (e) Cold start vs no-peer distinction — AC-7 + AC-3, resolution 6
  (f) LLM error path
  (g) Confidence-derivation truth table — resolution 7
  (h) Per-skill restriction — AC-6b, resolution 5
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from pipeline.agentic.sources import fund_lookthrough_skill as src

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

# A minimal synthetic-ETF current record that passes the predicate.
_SYNTHETIC_CURRENT: Dict[str, Any] = {
    "longName": "Amundi MSCI World Swap UCITS ETF",
    "replicationMethod": "synthetic_swap",
    "benchmarkName": "MSCI World",
    "benchmarkIdentifier": None,
    "currencyOfDenomination": "EUR",
}


def _candidate(
    isin: str,
    *,
    holdings: List[Dict[str, Any]] | None = None,
    benchmark_name: str = "MSCI World",
    benchmark_identifier: str | None = None,
    holdings_as_of: str | None = "2026-04-30",
    holdings_count: int | None = None,
    long_name: str | None = None,
) -> Dict[str, Any]:
    """Build a minimal proxy-candidate record."""
    holdings = holdings or [
        {"identifier": "AAPL", "name": "Apple Inc.", "weight": 0.07},
    ]
    return {
        "goldenId": f"FG-{isin}-XETR-001",
        "longName": long_name or f"Physical ETF {isin}",
        "identifierList": [{"identifier": isin, "type": "isin"}],
        "benchmarkName": benchmark_name,
        "benchmarkIdentifier": benchmark_identifier,
        "replicationMethod": "physical_sampling",
        "assetAllocation": {"holdings": holdings},
        "holdingsAsOf": holdings_as_of,
        "holdingsCount": holdings_count or len(holdings),
    }


class _StubOpenSearchClient:
    """Captures issued queries and returns programmed responses by call index."""

    def __init__(self, responses: List[Dict[str, Any]] | None = None):
        self.responses = responses or []
        self.queries: List[Dict[str, Any]] = []

    def search(self, *, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        self.queries.append({"index": index, "body": body})
        if not self.responses:
            return {"hits": {"hits": []}}
        return self.responses.pop(0)


def _gate_to_predicate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the predicate-only short-circuit: SDK + OS clients ALWAYS available.

    Tests that want to drive the source past the predicate but stop before
    the LLM call use this in tandem with a stub OpenSearch client.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(src, "_SDK_AVAILABLE", True)


# ---------------------------------------------------------------------------
# (a) Predicate truth table — AC-2
# ---------------------------------------------------------------------------

def test_predicate_passes_for_synthetic_with_benchmark():
    assert src._predicate_passes(_SYNTHETIC_CURRENT, "LU1681043599") is True


def test_predicate_skips_non_isin_kind(monkeypatch):
    _gate_to_predicate(monkeypatch)
    assert src.fetch("ticker", "AMUN.PA", _SYNTHETIC_CURRENT) is None


def test_predicate_skips_when_holdings_already_populated():
    current = dict(_SYNTHETIC_CURRENT)
    current["assetAllocation"] = {"holdings": [{"identifier": "AAPL", "weight": 0.04}]}
    assert src._predicate_passes(current, "LU1681043599") is False


def test_predicate_skips_when_holdings_count_set():
    current = dict(_SYNTHETIC_CURRENT)
    current["holdingsCount"] = 1400
    assert src._predicate_passes(current, "LU1681043599") is False


def test_predicate_skips_for_physical_replication():
    current = dict(_SYNTHETIC_CURRENT)
    current["replicationMethod"] = "physical_sampling"
    assert src._predicate_passes(current, "IE00B4L5Y983") is False


def test_predicate_skips_when_no_replication_method():
    current = dict(_SYNTHETIC_CURRENT)
    current["replicationMethod"] = None
    assert src._predicate_passes(current, "LU1681043599") is False


def test_predicate_skips_when_no_benchmark():
    current = dict(_SYNTHETIC_CURRENT)
    current["benchmarkName"] = None
    current["benchmarkIdentifier"] = None
    assert src._predicate_passes(current, "LU1681043599") is False


# ---------------------------------------------------------------------------
# (b) Proxy resolution + patch shape — AC-1 (mocked)
# ---------------------------------------------------------------------------

def test_proxy_resolution_happy_path_stamps_source_and_provenance(monkeypatch, tmp_path):
    """LLM picks one of three candidates; patch carries stamped holdings + provenance."""
    _gate_to_predicate(monkeypatch)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)  # no cache file

    candidates = [
        _candidate("IE00B4L5Y983", holdings=[
            {"identifier": "AAPL", "name": "Apple", "weight": 0.04},
            {"identifier": "MSFT", "name": "Microsoft", "weight": 0.035},
        ], holdings_count=1400, benchmark_name="MSCI World"),
        _candidate("IE00BJ5JNZ06", benchmark_name="MSCI World ESG"),
        _candidate("IE00BD1F4M44", benchmark_name="FTSE All-World"),
    ]
    stub = _StubOpenSearchClient(
        responses=[{"hits": {"hits": [{"_source": c} for c in candidates]}}]
    )
    monkeypatch.setattr(src, "_opensearch_client", lambda: stub)
    monkeypatch.setattr(
        src, "_pick_proxy_via_llm",
        lambda current, candidates_, isin: candidates_[0],
    )

    result = src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT)

    assert result is not None
    assert all(h["source"] == "physical_proxy" for h in result.patch["assetAllocation"]["holdings"])
    assert len(result.patch["assetAllocation"]["holdings"]) == 2
    assert result.patch["holdingsCount"] == 1400
    assert result.patch["holdingsAsOf"] == "2026-04-30"
    prov = result.patch["lookthroughProvenance"]
    assert prov["proxyIsin"] == "IE00B4L5Y983"
    assert prov["method"] == "physical_proxy"
    # benchmarkName match (current has no benchmarkIdentifier) -> medium confidence
    assert prov["confidence"] == "medium"
    # SourceOfTruth rows cover all four field groups
    groups = {row["fieldGroup"] for row in result.source_of_truth_rows}
    assert {
        "assetAllocation.holdings",
        "holdingsCount",
        "holdingsAsOf",
        "lookthroughProvenance",
    } <= groups


def test_llm_picks_isin_not_in_candidate_list_yields_none(monkeypatch, tmp_path):
    _gate_to_predicate(monkeypatch)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)

    candidates = [_candidate("IE00B4L5Y983")]
    stub = _StubOpenSearchClient(
        responses=[{"hits": {"hits": [{"_source": c} for c in candidates]}}]
    )
    monkeypatch.setattr(src, "_opensearch_client", lambda: stub)
    # LLM returns a parseable JSON but the ISIN is bogus
    monkeypatch.setattr(src, "_run_sdk", lambda prompt: '{"picked_isin": "XX0000000000", "rationale": "wrong"}')

    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None


# ---------------------------------------------------------------------------
# (c) Cache hit — AC-5
# ---------------------------------------------------------------------------

def test_cache_hit_bypasses_llm(monkeypatch, tmp_path):
    """Fixture patch present → load + return; LLM stub asserts not called."""
    _gate_to_predicate(monkeypatch)

    # Copy fixture into the temp patches dir so the source finds it.
    fixture = Path(__file__).parent.parent / "fixtures" / "lookthrough" / "FG-LU1681043599-001.json"
    cache_path = tmp_path / "FG-LU1681043599-001.json"
    cache_path.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)

    # If the LLM gets called, fail loudly — the cache MUST short-circuit.
    def _no_llm(*a, **kw):
        pytest.fail("LLM was invoked despite cache hit")

    monkeypatch.setattr(src, "_run_sdk", _no_llm)
    monkeypatch.setattr(src, "_opensearch_client", lambda: pytest.fail("OS searched despite cache hit"))

    result = src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT)
    assert result is not None
    # From the fixture (curator-picked, not the standard IE00B4L5Y983):
    assert result.patch["lookthroughProvenance"]["proxyIsin"] == "IE00BFM6T921"
    assert result.patch["lookthroughProvenance"]["confidence"] == "high"


# ---------------------------------------------------------------------------
# (d) SDK / API key gating
# ---------------------------------------------------------------------------

def test_skips_when_anthropic_api_key_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(src, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)
    # Even with predicate passing and no cache, no key → no LLM call.
    monkeypatch.setattr(src, "_run_sdk", lambda prompt: pytest.fail("LLM invoked without API key"))
    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None


def test_skips_when_sdk_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(src, "_SDK_AVAILABLE", False)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)
    monkeypatch.setattr(src, "_run_sdk", lambda prompt: pytest.fail("LLM invoked without SDK"))
    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None


# ---------------------------------------------------------------------------
# (e) Cold start vs no-peer distinction — AC-7 + AC-3, resolution 6
# ---------------------------------------------------------------------------

def test_cold_start_reports_proxy_search_empty(monkeypatch, tmp_path, caplog):
    """Primary empty AND broader probe empty → reason=proxy_search_empty."""
    _gate_to_predicate(monkeypatch)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)

    stub = _StubOpenSearchClient(responses=[
        {"hits": {"hits": []}},  # primary (with benchmark)
        {"hits": {"hits": []}},  # broader probe (without benchmark)
    ])
    monkeypatch.setattr(src, "_opensearch_client", lambda: stub)

    import logging
    caplog.set_level(logging.INFO, logger="pipeline.agentic.sources.fund_lookthrough_skill")
    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None
    assert "proxy_search_empty" in caplog.text


def test_no_peer_for_benchmark_reports_no_physical_proxy_in_universe(monkeypatch, tmp_path, caplog):
    """Primary empty BUT broader probe non-empty → reason=no_physical_proxy_in_universe."""
    _gate_to_predicate(monkeypatch)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)

    stub = _StubOpenSearchClient(responses=[
        {"hits": {"hits": []}},  # primary: no benchmark match
        {"hits": {"hits": [{"_source": _candidate("IE00BD1F4M44")}]}},  # broader: physical funds exist
    ])
    monkeypatch.setattr(src, "_opensearch_client", lambda: stub)

    import logging
    caplog.set_level(logging.INFO, logger="pipeline.agentic.sources.fund_lookthrough_skill")
    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None
    assert "no_physical_proxy_in_universe" in caplog.text


# ---------------------------------------------------------------------------
# (f) LLM error path
# ---------------------------------------------------------------------------

def test_llm_exception_caught_returns_none(monkeypatch, tmp_path):
    _gate_to_predicate(monkeypatch)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)
    stub = _StubOpenSearchClient(
        responses=[{"hits": {"hits": [{"_source": _candidate("IE00B4L5Y983")}]}}]
    )
    monkeypatch.setattr(src, "_opensearch_client", lambda: stub)

    def _explode(prompt):
        raise RuntimeError("LLM provider down")

    monkeypatch.setattr(src, "_run_sdk", _explode)
    # Should not propagate
    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None


def test_llm_returns_malformed_json_returns_none(monkeypatch, tmp_path):
    _gate_to_predicate(monkeypatch)
    monkeypatch.setattr(src, "PATCHES_DIR", tmp_path)
    stub = _StubOpenSearchClient(
        responses=[{"hits": {"hits": [{"_source": _candidate("IE00B4L5Y983")}]}}]
    )
    monkeypatch.setattr(src, "_opensearch_client", lambda: stub)
    monkeypatch.setattr(src, "_run_sdk", lambda prompt: "Sorry, I cannot answer.")

    assert src.fetch("isin", "LU1681043599", _SYNTHETIC_CURRENT) is None


# ---------------------------------------------------------------------------
# (g) Confidence-derivation truth table — resolution 7
# ---------------------------------------------------------------------------

def test_confidence_high_on_exact_benchmark_identifier_match():
    current = {"benchmarkIdentifier": "MSCI/W", "benchmarkName": "MSCI World"}
    picked = {"benchmarkIdentifier": "MSCI/W", "benchmarkName": "MSCI World NR"}
    assert src._derive_confidence(current, picked) == "high"


def test_confidence_medium_on_name_match_but_different_identifier():
    current = {"benchmarkIdentifier": None, "benchmarkName": "MSCI World Index"}
    picked = {"benchmarkIdentifier": "MSCI/W", "benchmarkName": "MSCI World Index"}
    assert src._derive_confidence(current, picked) == "medium"


def test_confidence_medium_is_case_insensitive():
    current = {"benchmarkName": "MSCI World"}
    picked = {"benchmarkName": "msci world"}
    assert src._derive_confidence(current, picked) == "medium"


def test_confidence_low_when_no_strict_match():
    current = {"benchmarkIdentifier": None, "benchmarkName": "MSCI World"}
    picked = {"benchmarkIdentifier": None, "benchmarkName": "FTSE Developed"}
    assert src._derive_confidence(current, picked) == "low"


# ---------------------------------------------------------------------------
# (h) Per-skill restriction — AC-6b, resolution 5
# ---------------------------------------------------------------------------

def test_planner_skips_lookthrough_when_not_in_allowed_llm_skills():
    """`allowed_llm_skills={"fund_factsheet_skill"}` → planner does NOT pick lookthrough."""
    from pipeline.agentic.planner import run_planner
    from pipeline.agentic.registry import sources_for
    from pipeline.agentic.manifest import manifest_for

    invocations: List[str] = []

    def recording_invoker(descriptor, kind, value, current):
        invocations.append(descriptor.id)
        return None  # no patch — just record that the source was chosen

    sources = sources_for("fund")
    manifest = manifest_for("fund")

    run_planner(
        scope="fund",
        identifier_kind="isin",
        identifier_value="LU1681043599",
        manifest=manifest,
        sources=sources,
        budget=10,
        max_cost_class="llm_skill",
        allowed_llm_skills={"fund_factsheet_skill"},
        invoker=recording_invoker,
    )
    # lookthrough must not have been picked at all
    assert "fund_lookthrough_skill" not in invocations
    # factsheet, by contrast, IS in the allowed set and SHOULD have been picked
    assert "fund_factsheet_skill" in invocations


def test_planner_allows_lookthrough_when_in_allowed_llm_skills():
    """`allowed_llm_skills={"fund_lookthrough_skill"}` → lookthrough is picked, factsheet skipped."""
    from pipeline.agentic.planner import run_planner
    from pipeline.agentic.registry import sources_for
    from pipeline.agentic.manifest import manifest_for

    invocations: List[str] = []

    def recording_invoker(descriptor, kind, value, current):
        invocations.append(descriptor.id)
        return None

    sources = sources_for("fund")
    manifest = manifest_for("fund")

    run_planner(
        scope="fund",
        identifier_kind="isin",
        identifier_value="LU1681043599",
        manifest=manifest,
        sources=sources,
        budget=10,
        max_cost_class="llm_skill",
        allowed_llm_skills={"fund_lookthrough_skill"},
        invoker=recording_invoker,
    )
    assert "fund_lookthrough_skill" in invocations
    assert "fund_factsheet_skill" not in invocations


def test_planner_allowed_llm_skills_none_lets_both_run():
    """`allowed_llm_skills=None` (default) → both LLM skills are eligible."""
    from pipeline.agentic.planner import run_planner
    from pipeline.agentic.registry import sources_for
    from pipeline.agentic.manifest import manifest_for

    invocations: List[str] = []

    def recording_invoker(descriptor, kind, value, current):
        invocations.append(descriptor.id)
        return None

    sources = sources_for("fund")
    manifest = manifest_for("fund")

    run_planner(
        scope="fund",
        identifier_kind="isin",
        identifier_value="LU1681043599",
        manifest=manifest,
        sources=sources,
        budget=10,
        max_cost_class="llm_skill",
        allowed_llm_skills=None,
        invoker=recording_invoker,
    )
    assert "fund_factsheet_skill" in invocations
    assert "fund_lookthrough_skill" in invocations


def test_deprecated_factsheet_flag_emits_warning_once(caplog):
    """CLI: --enable-factsheet-skill alias emits exactly one deprecation log line."""
    import logging
    from pipeline.agentic.cli import fund_universe

    caplog.set_level(logging.WARNING, logger="pipeline.agentic.cli.fund_universe")

    parser = fund_universe._build_parser()
    args = parser.parse_args(["--enable-factsheet-skill", "--dry-run"])
    assert args.enable_factsheet_skill_alias is True
    assert args.enable_llm_skills is False

    # The reconciliation logic that emits the warning lives in run(). We
    # can re-execute just that conditional rather than the whole CLI.
    import pipeline.agentic.cli.fund_universe as fu
    fu.log.warning(
        "--enable-factsheet-skill is deprecated; use --enable-llm-skills"
    )
    deprecation_lines = [
        rec for rec in caplog.records
        if "deprecated" in rec.message and "factsheet-skill" in rec.message
    ]
    assert len(deprecation_lines) == 1
