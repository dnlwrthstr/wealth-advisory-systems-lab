"""Fund scope — manifest in sync + end-to-end with mocked FIRDS."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.manifest import manifest_for


def test_fund_manifest_lists_every_top_level_field():
    from universe.models import FundGolden

    manifest = manifest_for("fund")
    assert set(manifest) == set(FundGolden.model_fields)


@pytest.fixture
def fake_firds(monkeypatch):
    """Patch the FIRDS Solr client + issuer YAML loader with deterministic data."""
    from pipeline.gold import fund_firds

    def fake_solr_get(params, retries=5):
        # The fund_firds.fetch_by_isin sends q=isin:<ISIN>+AND+latest_received_flag:1
        return {
            "response": {
                "docs": [{
                    "isin": "IE00B4L5Y983",
                    "lei": "549300VUYUFI3JTUAW28",
                    "gnr_full_name": "iShares Core MSCI World UCITS ETF USD (Acc)",
                    "gnr_short_name": "IWDA",
                    "gnr_cfi_code": "CEOGGR",
                    "gnr_notional_curr_code": "USD",
                    "mic": "XLON",
                    "upcoming_rca": "IE",
                    "mrkt_trdng_start_date": "2009-09-25T00:00:00Z",
                    "status": "UNCH",
                    "valid_from_date": "2024-01-01T00:00:00Z",
                }]
            }
        }

    def fake_load_issuers(_path):
        return [{
            "umbrellaLei": "549300VUYUFI3JTUAW28",
            "umbrellaName": "iShares VII PLC",
            "managementCompanyLei": "549300MS535KC2WH4Z14",
            "managementCompanyName": "BlackRock Asset Management Ireland Ltd",
            "managementCompanyId": "MGT-BAMI",
            "promoterName": "BlackRock, Inc.",
            "country": "IE",
            "legalFramework": "UCITS",
            "legalStructure": "plc",
        }]

    monkeypatch.setattr(fund_firds, "solr_get", fake_solr_get)
    monkeypatch.setattr(fund_firds, "load_issuers", fake_load_issuers)


def test_assemble_fund_end_to_end(fake_firds):
    result = assemble_golden(
        scope="fund",
        identifier={"kind": "isin", "value": "IE00B4L5Y983"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-fund",
    )
    rec = result.record
    assert rec["goldenId"].startswith("FG-IE00B4L5Y983")
    assert rec["currencyOfDenomination"] == "USD"
    assert rec["umbrella"]["legalName"] == "iShares VII PLC"
    assert rec["managementCompany"]["legalName"] == "BlackRock Asset Management Ireland Ltd"
    assert rec["fundSubType"] == "etf"  # derived from CFI "CE..."
    from universe.models import FundGolden
    FundGolden.model_validate(rec)


def test_assemble_fund_unknown_umbrella_yields_no_data(monkeypatch):
    """If FIRDS returns an LEI we don't have in our curated map, source returns None."""
    from pipeline.gold import fund_firds

    monkeypatch.setattr(fund_firds, "solr_get", lambda params, retries=5: {
        "response": {"docs": [{
            "isin": "LU0000000000",
            "lei": "UNKNOWN-LEI",
            "gnr_full_name": "Mystery Fund",
            "gnr_cfi_code": "CEOIRR",
            "gnr_notional_curr_code": "EUR",
        }]}
    })
    monkeypatch.setattr(fund_firds, "load_issuers", lambda _p: [])

    result = assemble_golden(
        scope="fund",
        identifier={"kind": "isin", "value": "LU0000000000"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-fund-unknown",
    )
    # No usable source data → required fields remain gaps.
    assert "longName" in result.remaining_gaps


# ---------------------------------------------------------------------------
# Chain integration with fund_lookthrough_skill — spec-003 T011 coverage
#
# Verify the deep-merge merger from T002 lets the lookthrough skill
# contribute `assetAllocation.holdings` on top of fund_yahoo's existing
# `assetAllocation` buckets — the original blocker resolved by Option B.
# ---------------------------------------------------------------------------

def test_lookthrough_deep_merges_into_existing_assetAllocation(monkeypatch):
    """fund_yahoo populates assetAllocation buckets; lookthrough fills holdings.

    Old shallow merger would silently drop the holdings (parent dict non-empty).
    With the T002 deep-merge upgrade, holdings land alongside the buckets.
    """
    from pipeline.agentic.sources import fund_lookthrough_skill as lookthrough_src

    # Start from a current state that mimics what fund_yahoo + fund_factsheet
    # would have populated by the time lookthrough's turn comes around.
    current_after_upstream_sources = {
        "longName": "Amundi MSCI World Swap UCITS ETF",
        "replicationMethod": "synthetic_swap",
        "benchmarkName": "MSCI World Index",
        "benchmarkIdentifier": None,
        "currencyOfDenomination": "EUR",
        "assetAllocation": {
            "bySector": [{"sector": "INFORMATION_TECHNOLOGY", "percentage": 0.28}],
            "byAssetClass": [{"type": "equity", "percentage": 1.0}],
        },
    }

    proxy = {
        "goldenId": "FG-IE00B4L5Y983-XETR-001",
        "longName": "iShares Core MSCI World UCITS ETF",
        "identifierList": [{"identifier": "IE00B4L5Y983", "type": "isin"}],
        "benchmarkName": "MSCI World Index",
        "replicationMethod": "physical_sampling",
        "assetAllocation": {"holdings": [
            {"identifier": "AAPL", "name": "Apple", "weight": 0.04},
        ]},
        "holdingsAsOf": "2026-04-30",
        "holdingsCount": 1400,
    }

    # The patch the lookthrough source returns
    confidence = lookthrough_src._derive_confidence(current_after_upstream_sources, proxy)
    patch_result = lookthrough_src._build_patch(proxy, confidence)

    # Hand-merge to verify the deep-merge behaviour from T002
    from pipeline.agentic.merger import merge_patch
    written = merge_patch(current_after_upstream_sources, patch_result.patch)

    aa = current_after_upstream_sources["assetAllocation"]
    # Both pre-existing buckets and the patched holdings are visible:
    assert aa["bySector"] == [{"sector": "INFORMATION_TECHNOLOGY", "percentage": 0.28}]
    assert aa["byAssetClass"] == [{"type": "equity", "percentage": 1.0}]
    assert len(aa["holdings"]) == 1
    assert aa["holdings"][0]["source"] == "physical_proxy"
    # Top-level fields written:
    assert current_after_upstream_sources["holdingsCount"] == 1400
    assert current_after_upstream_sources["lookthroughProvenance"]["proxyIsin"] == "IE00B4L5Y983"
    assert current_after_upstream_sources["lookthroughProvenance"]["confidence"] == "medium"
    # `written` reports the nested holdings path
    assert "assetAllocation.holdings" in written


def test_lookthrough_predicate_short_circuits_when_holdings_already_present(monkeypatch):
    """If an earlier source populated holdings, lookthrough must skip — fill-empty-only safety."""
    from pipeline.agentic.sources import fund_lookthrough_skill as lookthrough_src

    current_with_direct_holdings = {
        "replicationMethod": "synthetic_swap",
        "benchmarkName": "MSCI World",
        "assetAllocation": {
            "holdings": [{"identifier": "AAPL", "name": "Apple", "weight": 0.04, "source": "direct"}],
        },
    }
    # Predicate must short-circuit BEFORE the OpenSearch lookup
    monkeypatch.setattr(lookthrough_src, "_opensearch_client",
                        lambda: pytest.fail("OS searched despite populated holdings"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(lookthrough_src, "_SDK_AVAILABLE", True)

    result = lookthrough_src.fetch("isin", "LU1681043599", current_with_direct_holdings)
    assert result is None


def test_lookthrough_runs_after_factsheet_skill_in_planner_order():
    """Both sources are llm_skill+medium; planner ranks by coverage.

    fund_factsheet_skill covers more fields (16 produces) than
    fund_lookthrough_skill (4 produces), so it gets picked first when both
    are candidates. After factsheet runs, lookthrough's gap-eligibility
    is independently evaluated on the next planner iteration.
    """
    from pipeline.agentic.registry import sources_for

    sources = sources_for("fund")
    by_id = {s.id: s for s in sources}
    fs = by_id["fund_factsheet_skill"]
    lt = by_id["fund_lookthrough_skill"]

    # Same cost class, same confidence → ranking falls to coverage
    assert fs.cost_class == lt.cost_class == "llm_skill"
    assert fs.confidence == lt.confidence == "medium"
    assert len(fs.produces_fields) > len(lt.produces_fields)


# ---------------------------------------------------------------------------
# Spec-004 integration: lookthrough enhances factsheet's top-N to full list
# ---------------------------------------------------------------------------

def test_lookthrough_replaces_factsheet_top_n():
    """Spec-004 AC-1 (integration): factsheet wrote 10/1310 → lookthrough
    overrides with the full proxy list via replace_paths.
    """
    from pipeline.agentic.sources import fund_lookthrough_skill as lookthrough_src
    from pipeline.agentic.merger import merge_patch

    # Simulate the state after factsheet has run:
    #   replicationMethod + benchmark + top-10 holdings + holdingsCount=1310.
    current = {
        "longName": "Amundi MSCI World Swap UCITS ETF",
        "replicationMethod": "synthetic_swap",
        "benchmarkName": "MSCI World Index",
        "benchmarkIdentifier": None,
        "currencyOfDenomination": "EUR",
        "holdingsCount": 1310,
        "assetAllocation": {
            "bySector": [{"sector": "INFORMATION_TECHNOLOGY", "percentage": 0.28}],
            "holdings": [
                {"identifier": f"TOP{i}", "name": f"Top{i}", "weight": 0.05, "source": "direct"}
                for i in range(10)
            ],
        },
    }

    # Spec-004 predicate must now PASS (10 < 1310)
    assert lookthrough_src._predicate_passes(current, "LU1681043599") is True

    # Proxy: physical-replication peer with the full constituent list (100 mock rows
    # standing in for the real ~1310).
    proxy = {
        "goldenId": "FG-IE00B4L5Y983-XETR-001",
        "longName": "iShares Core MSCI World UCITS ETF",
        "identifierList": [{"identifier": "IE00B4L5Y983", "type": "isin"}],
        "benchmarkName": "MSCI World Index",
        "replicationMethod": "physical_sampling",
        "assetAllocation": {"holdings": [
            {"identifier": f"FULL{i}", "name": f"Full{i}", "weight": 0.01}
            for i in range(100)
        ]},
        "holdingsAsOf": "2026-04-30",
        "holdingsCount": 1310,
    }

    confidence = lookthrough_src._derive_confidence(current, proxy)
    result = lookthrough_src._build_patch(proxy, confidence)

    # Sanity: the patch declares replace_paths for the holdings list
    assert result.replace_paths == ["assetAllocation.holdings"]

    written = merge_patch(current, result.patch, replace_paths=result.replace_paths)

    # The full 100-row list replaced the top-10
    aa = current["assetAllocation"]
    assert len(aa["holdings"]) == 100, "expected proxy full list (100), got %d" % len(aa["holdings"])
    assert all(h["source"] == "physical_proxy" for h in aa["holdings"])
    # Sibling buckets preserved (deep-merge protected them)
    assert aa["bySector"] == [{"sector": "INFORMATION_TECHNOLOGY", "percentage": 0.28}]
    # Provenance landed
    assert current["lookthroughProvenance"]["proxyIsin"] == "IE00B4L5Y983"
    # Written reports the replacement
    assert "assetAllocation.holdings" in written


def test_lookthrough_does_not_fire_on_complete_factsheet_holdings():
    """Spec-004 AC-2: factsheet provided the COMPLETE constituent list
    (holdingsCount == len(holdings)) → lookthrough's predicate must skip.
    """
    from pipeline.agentic.sources import fund_lookthrough_skill as lookthrough_src

    current = {
        "replicationMethod": "synthetic_swap",
        "benchmarkName": "MSCI World Index",
        "holdingsCount": 80,
        "assetAllocation": {
            "holdings": [
                {"identifier": f"H{i}", "weight": 1.0 / 80, "source": "direct"}
                for i in range(80)
            ],
        },
    }

    assert lookthrough_src._predicate_passes(current, "LU1681043599") is False
