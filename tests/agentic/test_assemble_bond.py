"""Bond scope — manifest in sync + end-to-end with mocked parquet."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.manifest import manifest_for


def test_bond_manifest_lists_every_top_level_field():
    from universe.models import BondGolden

    manifest = manifest_for("bond")
    assert set(manifest) == set(BondGolden.model_fields)


@pytest.fixture
def fake_bond_master(monkeypatch):
    """Patch bond_parquet's parquet loader with an in-memory dataframe."""
    df = pd.DataFrame([
        {
            "isin": "DE0001102309",
            "name": "1.5 Bundesrepublik Deutschland 14-24",
            "nominal_currency": "EUR",
            "issuer_name": "Bundesrepublik Deutschland",
            "issuer_country": "DE",
            "sector": "Government",
            "rating": "AAA",
            "rating_agency": "S&P",
            "coupon_rate": 0.015,
            "interest_type": "fixed",
            "seniority": "senior_unsecured",
            "maturity_date": date(2034, 8, 15).isoformat(),
            "face_value": 100,
            "valor_nr": 12345678,
        }
    ])
    from pipeline.gold import bond_parquet
    monkeypatch.setattr(bond_parquet, "load_bond_master", lambda *_a, **_kw: df)
    return df


def test_assemble_bond_end_to_end(fake_bond_master):
    result = assemble_golden(
        scope="bond",
        identifier={"kind": "isin", "value": "DE0001102309"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-bond",
    )
    rec = result.record
    assert rec["goldenId"].startswith("BG-DE0001102309")
    assert rec["currencyOfDenomination"] == "EUR"
    assert rec["maturityDate"] == "2034-08-15"
    assert rec["issuer"]["legalName"] == "Bundesrepublik Deutschland"
    assert rec["assetClass"] == "Fixed Income / Government Bond"
    # And the record actually validates against the canonical pydantic model.
    from universe.models import BondGolden
    BondGolden.model_validate(rec)


def test_assemble_bond_missing_isin_yields_gaps(fake_bond_master):
    """An ISIN not in the parquet master returns the empty-source path."""
    result = assemble_golden(
        scope="bond",
        identifier={"kind": "isin", "value": "ZZ9999999999"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-bond-missing",
    )
    # No source had the bond → required fields remain gaps.
    assert "longName" in result.remaining_gaps or "currencyOfDenomination" in result.remaining_gaps
    assert result.quality_score == 0.0
