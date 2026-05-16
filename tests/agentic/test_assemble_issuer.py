"""Issuer scope — manifest sync + end-to-end with mocked GLEIF."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.manifest import manifest_for


def test_issuer_manifest_lists_every_top_level_field():
    from universe.models import IssuerGolden

    manifest = manifest_for("issuer")
    assert set(manifest) == set(IssuerGolden.model_fields)


@pytest.fixture
def fake_gleif(monkeypatch):
    """Patch the adapter's bound `fetch_gleif` reference (not the source module's).

    `pipeline.agentic.sources.issuer_gleif` does `from ... import fetch_gleif`
    at module load time, so the binding lives on the *adapter*; patching the
    source module has no effect once the adapter is imported.
    """
    from pipeline.agentic.sources import issuer_gleif as adapter

    record = {
        "main": {"data": {"attributes": {"entity": {
            "legalName": {"name": "BlackRock, Inc."},
            "legalAddress": {"country": "US"},
            "headquartersAddress": {"country": "US"},
            "category": "GENERAL",
        }}}},
        "ultimate_parent_lei": "PARENT-LEI-XYZ",
    }
    monkeypatch.setattr(adapter, "fetch_gleif", lambda lei, use_cache=True: record)


def test_assemble_issuer_end_to_end(fake_gleif):
    result = assemble_golden(
        scope="issuer",
        identifier={"kind": "lei", "value": "549300VUYUFI3JTUAW28"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-issuer",
    )
    rec = result.record
    assert rec["issuerId"] == "ISS-549300VUYUFI3JTUAW28"
    assert rec["lei"] == "549300VUYUFI3JTUAW28"
    assert rec["goldenId"] == "ISS-549300VUYUFI3JTUAW28"
    assert rec["legalName"] == "BlackRock, Inc."
    assert rec["domicileCountry"] == "US"
    assert rec["ultimateParentLei"] == "PARENT-LEI-XYZ"

    from universe.models import IssuerGolden
    IssuerGolden.model_validate(rec)


def test_assemble_issuer_when_gleif_silent(monkeypatch):
    from pipeline.agentic.sources import issuer_gleif as adapter

    monkeypatch.setattr(adapter, "fetch_gleif", lambda lei, use_cache=True: None)
    result = assemble_golden(
        scope="issuer",
        identifier={"kind": "lei", "value": "UNKNOWNLEI"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-issuer-blank",
    )
    # legalName is required by pydantic; GLEIF silent → still a gap.
    assert "legalName" in result.remaining_gaps
    # But assembler still set issuerId / lei from the identifier.
    assert result.record["lei"] == "UNKNOWNLEI"
    assert result.record["issuerId"] == "ISS-UNKNOWNLEI"
