"""Tests for `pipeline.agentic.merger.merge_patch`.

Locks the deep fill-empty-only semantic introduced in spec 003 (Option B
resolution): at every nesting level, the first writer wins; sibling keys
not yet populated still get written even when the parent dict is non-empty.
"""
from __future__ import annotations

from pipeline.agentic.merger import merge_patch


def test_top_level_fill_empty_preserved():
    """A flat patch on empty slots writes; on populated slots, skips."""
    current = {"a": "first"}
    written = merge_patch(current, {"a": "second", "b": "new"})

    assert current == {"a": "first", "b": "new"}
    assert written == ["b"]


def test_deep_merge_existing_partial_dict():
    """fund_yahoo + fund_lookthrough_skill: partial assetAllocation gains holdings."""
    current = {
        "assetAllocation": {
            "byAssetClass": [{"assetClass": "equity", "percentage": 1.0}],
        },
    }
    patch = {
        "assetAllocation": {
            "holdings": [{"identifier": "AAPL", "name": "Apple", "weight": 0.07}],
        },
    }
    written = merge_patch(current, patch)

    assert current["assetAllocation"]["byAssetClass"] == [
        {"assetClass": "equity", "percentage": 1.0}
    ]
    assert current["assetAllocation"]["holdings"] == [
        {"identifier": "AAPL", "name": "Apple", "weight": 0.07}
    ]
    assert written == ["assetAllocation.holdings"]


def test_deep_merge_skips_already_filled_subkey():
    """If a nested key already has data, the patch sub-value is ignored."""
    current = {
        "assetAllocation": {
            "holdings": [{"identifier": "AAPL", "name": "Apple", "weight": 0.07}],
        },
    }
    patch = {
        "assetAllocation": {
            "holdings": [{"identifier": "MSFT", "name": "Microsoft", "weight": 0.06}],
            "byAssetClass": [{"assetClass": "equity", "percentage": 1.0}],
        },
    }
    written = merge_patch(current, patch)

    # holdings unchanged — existing wins.
    assert current["assetAllocation"]["holdings"][0]["identifier"] == "AAPL"
    # byAssetClass was empty → patched in.
    assert current["assetAllocation"]["byAssetClass"] == [
        {"assetClass": "equity", "percentage": 1.0}
    ]
    assert written == ["assetAllocation.byAssetClass"]


def test_lists_are_atomic():
    """Lists are leaves — replaced only if the existing slot is empty/missing."""
    current = {"holdings": [{"identifier": "AAPL", "weight": 0.07}]}
    patch = {"holdings": [{"identifier": "MSFT", "weight": 0.06}]}
    written = merge_patch(current, patch)

    # Atomic — existing list wins.
    assert current["holdings"] == [{"identifier": "AAPL", "weight": 0.07}]
    assert written == []


def test_empty_list_filled_by_patch():
    """Empty existing list is treated as empty slot — patch list written."""
    current = {"holdings": []}
    patch = {"holdings": [{"identifier": "AAPL", "weight": 0.07}]}
    written = merge_patch(current, patch)

    assert current["holdings"] == [{"identifier": "AAPL", "weight": 0.07}]
    assert written == ["holdings"]


def test_three_level_nesting():
    """Deep-merge recurses through arbitrary depth."""
    current = {
        "fees": {
            "ongoing": {"value": 0.0038},
        },
    }
    patch = {
        "fees": {
            "ongoing": {"currency": "EUR"},
            "performance": {"value": 0.20},
        },
    }
    written = merge_patch(current, patch)

    assert current["fees"]["ongoing"] == {"value": 0.0038, "currency": "EUR"}
    assert current["fees"]["performance"] == {"value": 0.20}
    assert sorted(written) == ["fees.ongoing.currency", "fees.performance"]


def test_empty_sentinels_skipped_at_every_level():
    """None / "" / [] / {} sub-values never overwrite existing data."""
    current = {
        "benchmarkName": "MSCI World",
        "assetAllocation": {
            "byAssetClass": [{"assetClass": "equity", "percentage": 1.0}],
        },
    }
    patch = {
        "benchmarkName": None,
        "benchmarkIdentifier": "",
        "assetAllocation": {
            "byAssetClass": [],
            "holdings": None,
            "regionAllocation": [],
        },
        "newField": {},
    }
    written = merge_patch(current, patch)

    # Existing data untouched.
    assert current["benchmarkName"] == "MSCI World"
    assert current["assetAllocation"]["byAssetClass"] == [
        {"assetClass": "equity", "percentage": 1.0}
    ]
    # No new keys created from empty sentinels.
    assert "benchmarkIdentifier" not in current
    assert "holdings" not in current["assetAllocation"]
    assert "regionAllocation" not in current["assetAllocation"]
    assert "newField" not in current
    assert written == []


def test_patch_dict_into_empty_slot_writes_full_dict():
    """Patch dict into an empty/missing slot writes the whole sub-dict atomically."""
    current = {}
    patch = {
        "lookthroughProvenance": {
            "method": "physical_proxy",
            "proxyIsin": "IE00B4L5Y983",
            "confidence": "high",
        },
    }
    written = merge_patch(current, patch)

    assert current["lookthroughProvenance"]["proxyIsin"] == "IE00B4L5Y983"
    assert written == ["lookthroughProvenance"]


# ---------------------------------------------------------------------------
# spec-004: `replace_paths` marker-based override
# ---------------------------------------------------------------------------

def test_replace_paths_overrides_existing_list():
    """A patch with replace_paths replaces the existing list verbatim — even
    when current already has a non-empty list at that path. This is the
    spec-004 unblock for lookthrough overriding factsheet's top-N.
    """
    current = {
        "assetAllocation": {
            "holdings": [
                {"identifier": "AAPL", "name": "Apple", "weight": 0.06, "source": "direct"},
            ],
        },
    }
    patch = {
        "assetAllocation": {
            "holdings": [
                {"identifier": "NVDA", "name": "NVIDIA", "weight": 0.06, "source": "physical_proxy"},
                {"identifier": "AAPL", "name": "Apple", "weight": 0.045, "source": "physical_proxy"},
                {"identifier": "MSFT", "name": "Microsoft", "weight": 0.035, "source": "physical_proxy"},
            ],
        },
    }
    written = merge_patch(current, patch, replace_paths=["assetAllocation.holdings"])

    # Existing list fully replaced
    assert len(current["assetAllocation"]["holdings"]) == 3
    assert current["assetAllocation"]["holdings"][0]["identifier"] == "NVDA"
    assert all(h["source"] == "physical_proxy" for h in current["assetAllocation"]["holdings"])
    # written carries the nested dot-path
    assert "assetAllocation.holdings" in written


def test_replace_paths_no_op_on_dict_value():
    """replace_paths marker pointing at a dict-valued field is silently
    ignored; deep-merge applies. Defensive against marker misuse (AC-6).
    """
    current = {
        "lookthroughProvenance": {
            "method": "physical_proxy",
            "proxyIsin": "IE00BFM6T921",
            "confidence": "high",
        },
    }
    patch = {
        "lookthroughProvenance": {
            "method": "physical_proxy",
            "proxyIsin": "IE00B4L5Y983",  # different
            "asOfDate": "2026-04-30",     # new sub-key
        },
    }
    written = merge_patch(current, patch, replace_paths=["lookthroughProvenance"])

    # Deep-merge applied — existing method/proxyIsin/confidence preserved,
    # only the new asOfDate sub-key written.
    assert current["lookthroughProvenance"]["proxyIsin"] == "IE00BFM6T921"
    assert current["lookthroughProvenance"]["confidence"] == "high"
    assert current["lookthroughProvenance"]["asOfDate"] == "2026-04-30"
    assert written == ["lookthroughProvenance.asOfDate"]


def test_replace_paths_does_not_affect_other_paths():
    """replace_paths for `a.b` does NOT change semantics for `a.c`."""
    current = {
        "assetAllocation": {
            "holdings": [{"identifier": "OLD", "weight": 1.0}],
            "byAssetClass": [{"type": "equity", "percentage": 1.0}],
        },
    }
    patch = {
        "assetAllocation": {
            "holdings": [{"identifier": "NEW1", "weight": 0.5}, {"identifier": "NEW2", "weight": 0.5}],
            "byAssetClass": [{"type": "fixed_income", "percentage": 1.0}],
        },
    }
    written = merge_patch(current, patch, replace_paths=["assetAllocation.holdings"])

    # holdings replaced (marker applies)
    assert len(current["assetAllocation"]["holdings"]) == 2
    assert current["assetAllocation"]["holdings"][0]["identifier"] == "NEW1"
    # byAssetClass preserved (no marker for that path)
    assert current["assetAllocation"]["byAssetClass"][0]["type"] == "equity"
    assert "assetAllocation.holdings" in written
    assert "assetAllocation.byAssetClass" not in written


def test_replace_paths_empty_default_preserves_spec_003_behavior():
    """Explicit empty replace_paths must behave identically to spec-003's
    deep fill-empty-only. Regression lock against accidental semantic drift.
    """
    current = {"holdings": [{"identifier": "AAPL", "weight": 0.07}]}
    patch = {"holdings": [{"identifier": "MSFT", "weight": 0.06}]}

    # With explicit empty replace_paths — should match spec-003's atomic-list
    # fill-empty-only: existing non-empty list wins.
    written = merge_patch(current, patch, replace_paths=())
    assert current["holdings"] == [{"identifier": "AAPL", "weight": 0.07}]
    assert written == []


def test_replace_paths_skips_empty_list_value():
    """An empty list value at a marked path is still skipped (never write
    nothing). Marker doesn't bypass the empty-sentinel rule.
    """
    current = {"holdings": [{"identifier": "AAPL", "weight": 0.07}]}
    patch = {"holdings": []}

    written = merge_patch(current, patch, replace_paths=["holdings"])
    # Existing list untouched
    assert current["holdings"] == [{"identifier": "AAPL", "weight": 0.07}]
    assert written == []
