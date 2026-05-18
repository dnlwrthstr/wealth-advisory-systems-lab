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
