"""fund_factsheet_skill — guard conditions + skill-then-read-patch flow."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.agentic.sources import fund_factsheet_patch
from pipeline.agentic.sources import fund_factsheet_skill as adapter


def test_skipped_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(fund_factsheet_patch, "PATCHES_DIR", tmp_path)
    monkeypatch.setattr(adapter, "_SDK_AVAILABLE", True)
    assert adapter.fetch("isin", "IE00B4L5Y983", current={}) is None


def test_skipped_when_sdk_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(fund_factsheet_patch, "PATCHES_DIR", tmp_path)
    monkeypatch.setattr(adapter, "_SDK_AVAILABLE", False)
    assert adapter.fetch("isin", "IE00B4L5Y983", current={}) is None


def test_skipped_when_patch_already_exists(monkeypatch, tmp_path):
    """When the on-disk patch is already there, defer to fund_factsheet_patch."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(fund_factsheet_patch, "PATCHES_DIR", tmp_path)
    monkeypatch.setattr(adapter, "_SDK_AVAILABLE", True)
    (tmp_path / "FG-IE00B4L5Y983-001.json").write_text(json.dumps({"doc": {"x": 1}}), encoding="utf-8")

    invoked = []
    async def _no_invoke(*a, **kw):
        invoked.append(True)
    monkeypatch.setattr(adapter, "_invoke_skill", _no_invoke)

    assert adapter.fetch("isin", "IE00B4L5Y983", current={}) is None
    assert invoked == []  # the existing patch short-circuits the skill call


def test_invokes_skill_then_reads_resulting_patch(monkeypatch, tmp_path):
    """Skill is invoked, writes the patch file, source returns the projection."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(fund_factsheet_patch, "PATCHES_DIR", tmp_path)
    monkeypatch.setattr(adapter, "_SDK_AVAILABLE", True)

    async def _fake_invoke(isin, current):
        # Simulate the skill writing the patch file as its side effect.
        (tmp_path / f"FG-{isin}-001.json").write_text(
            json.dumps({
                "doc": {"totalExpenseRatio": 0.002, "benchmarkName": "MSCI World"},
                "_meta": {"source": "blackrock-kid", "sourceTimestamp": "2026-05-01T00:00:00Z"},
            }),
            encoding="utf-8",
        )

    monkeypatch.setattr(adapter, "_invoke_skill", _fake_invoke)

    result = adapter.fetch("isin", "IE00B4L5Y983", current={"longName": "iShares Core MSCI World"})
    assert result is not None
    assert result.patch["totalExpenseRatio"] == 0.002
    assert result.patch["benchmarkName"] == "MSCI World"
    assert any(row["source"] == "blackrock-kid" for row in result.source_of_truth_rows)


def test_returns_none_when_skill_produces_no_patch(monkeypatch, tmp_path):
    """The skill ran but no file was written — source signals no_data."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(fund_factsheet_patch, "PATCHES_DIR", tmp_path)
    monkeypatch.setattr(adapter, "_SDK_AVAILABLE", True)

    async def _empty(isin, current):
        pass

    monkeypatch.setattr(adapter, "_invoke_skill", _empty)
    assert adapter.fetch("isin", "IE00B4L5Y983", current={}) is None
