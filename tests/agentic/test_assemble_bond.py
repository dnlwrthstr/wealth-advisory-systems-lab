"""Bond scope — manifest in sync with pydantic; end-to-end is in test_bond_firds_source."""
from __future__ import annotations

from datetime import datetime, timezone

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.manifest import manifest_for


def test_bond_manifest_lists_every_top_level_field():
    from universe.models import BondGolden

    manifest = manifest_for("bond")
    assert set(manifest) == set(BondGolden.model_fields)


def test_assemble_bond_missing_isin_yields_gaps(monkeypatch):
    """An ISIN no registered source can resolve returns the empty-source path."""
    from pipeline.agentic.sources import bond_firds as adapter
    monkeypatch.setattr(adapter, "fetch", lambda k, v, c: None)
    result = assemble_golden(
        scope="bond",
        identifier={"kind": "isin", "value": "ZZ9999999999"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-bond-missing",
    )
    assert "longName" in result.remaining_gaps or "currencyOfDenomination" in result.remaining_gaps
    assert result.quality_score == 0.0
