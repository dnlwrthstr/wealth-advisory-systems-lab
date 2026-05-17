"""fund_factsheet_patch source — reads pre-curated skill output from disk."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.agentic.sources import fund_factsheet_patch as adapter


def test_loads_patch_and_lifts_meta_into_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "PATCHES_DIR", tmp_path)
    patch_file = tmp_path / "FG-IE00B4L5Y983-001.json"
    patch_file.write_text(json.dumps({
        "doc": {
            "totalExpenseRatio": 0.002,
            "riskRating": {"sri": 4},
            "benchmarkName": "MSCI World Index",
            "replicationMethod": "physical_sampling",
        },
        "_meta": {
            "source": "BlackRock PRIIPS KID (ie00b4l5y983-en.pdf)",
            "sourceTimestamp": "2026-04-09T00:00:00Z",
        },
    }), encoding="utf-8")

    result = adapter.fetch("isin", "IE00B4L5Y983", current={})
    assert result is not None
    assert result.patch["totalExpenseRatio"] == 0.002
    assert result.patch["riskRating"] == {"sri": 4}
    assert result.patch["benchmarkName"] == "MSCI World Index"

    sot_field_groups = sorted(r["fieldGroup"] for r in result.source_of_truth_rows)
    assert sot_field_groups == sorted([
        "totalExpenseRatio", "riskRating", "benchmarkName", "replicationMethod",
    ])
    # Every row carries the parsed source label + timestamp.
    for row in result.source_of_truth_rows:
        assert row["source"] == "BlackRock PRIIPS KID (ie00b4l5y983-en.pdf)"
        assert row["sourceTimestamp"] == "2026-04-09T00:00:00Z"


def test_returns_none_when_patch_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "PATCHES_DIR", tmp_path)
    assert adapter.fetch("isin", "IE00ABSENT00", current={}) is None


def test_returns_none_when_patch_has_no_doc(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "PATCHES_DIR", tmp_path)
    (tmp_path / "FG-IE00B4L5Y983-001.json").write_text(json.dumps({"_meta": {"source": "x"}}), encoding="utf-8")
    assert adapter.fetch("isin", "IE00B4L5Y983", current={}) is None


def test_returns_none_for_non_isin_identifier():
    assert adapter.fetch("ticker", "IWDA", current={}) is None
