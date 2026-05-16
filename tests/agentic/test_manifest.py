"""Manifest tests — pydantic ↔ annotation YAML sync, gap + quality math."""
from __future__ import annotations

import pytest

from pipeline.agentic.manifest import (
    VALID_KINDS,
    VALID_REQUIREMENTS,
    compute_gaps,
    manifest_for,
    quality_score,
)


def test_equity_manifest_lists_every_top_level_field():
    """The annotation YAML must enumerate every EquityGolden top-level field."""
    from universe.models import EquityGolden

    manifest = manifest_for("equity")
    assert set(manifest) == set(EquityGolden.model_fields)


def test_equity_manifest_field_specs_are_well_formed():
    manifest = manifest_for("equity")
    for path, spec in manifest.items():
        assert spec.requirement in VALID_REQUIREMENTS, path
        assert spec.kind in VALID_KINDS, path


def test_structurally_required_fields_are_marked_required():
    """If pydantic requires it, the agentic platform must too — no demotions."""
    manifest = manifest_for("equity")
    demoted = [
        path for path, spec in manifest.items()
        if spec.structural_required and spec.requirement != "required"
    ]
    assert not demoted, f"required-in-pydantic but not required-in-YAML: {demoted}"


def test_assembler_owned_fields_are_assembled_kind():
    """`goldenId` and `recordMeta` belong to the assembler, not any source."""
    manifest = manifest_for("equity")
    assert manifest["goldenId"].kind == "assembled"
    assert manifest["recordMeta"].kind == "assembled"


def test_compute_gaps_returns_only_source_fillable_planner_relevant_fields():
    manifest = manifest_for("equity")
    gaps = compute_gaps(manifest, current={})
    # All gaps must be source-fillable + at least 'important' tier.
    for path in gaps:
        spec = manifest[path]
        assert spec.kind == "source", path
        assert spec.requirement in {"required", "important"}, path
    # Filling longName removes it from gaps.
    gaps_after = compute_gaps(manifest, current={"longName": "Apple Inc."})
    assert "longName" in gaps
    assert "longName" not in gaps_after


def test_quality_score_full_and_empty_bounds():
    manifest = manifest_for("equity")
    # Empty current → 0 of N relevant filled.
    assert quality_score(manifest, current={}) == 0.0
    # Fill every planner-relevant field with a sentinel.
    full = {p: "x" for p, s in manifest.items() if s.is_planner_relevant}
    assert quality_score(manifest, full) == 1.0


def test_manifest_raises_for_unknown_scope():
    with pytest.raises(ValueError):
        manifest_for("crypto")
