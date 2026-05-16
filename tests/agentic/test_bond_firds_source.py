"""bond_firds per-ISIN source — mocked Solr + curated issuer."""
from __future__ import annotations

from datetime import datetime, timezone

from pipeline.agentic.assemble import assemble_golden
from pipeline.agentic.sources import bond_firds as adapter


def test_bond_firds_end_to_end(monkeypatch):
    from pipeline.gold import bond_firds as gold

    def fake_solr_get(params, retries=5):
        return {"response": {"docs": [{
            "isin": "DE0001102309",
            "lei": "529900AQBND3S6YJLY83",
            "gnr_full_name": "1.5 Bundesrepublik Deutschland 14-24",
            "gnr_short_name": "BUND 1.5 24",
            "gnr_cfi_code": "DBFTFR",  # category D = debt
            "gnr_notional_curr_code": "EUR",
            "bnd_maturity_date": "2034-08-15T00:00:00Z",
            "bnd_fixed_rate": 1.5,
            "bnd_seniority": "SNDB",
            "bnd_nmnl_value_unit": 100,
            "mic": "XFRA",
            "upcoming_rca": "DE",
            "mrkt_trdng_start_date": "2014-08-15T00:00:00Z",
            "status": "UNCH",
            "valid_from_date": "2024-01-01T00:00:00Z",
        }]}}

    fake_issuers = [{
        "lei": "529900AQBND3S6YJLY83",
        "name": "Federal Republic of Germany",
        "issuerType": "government",
        "country": "DE",
        "assetClass": "Fixed Income / Government Bond",
        "assetClassId": "AC-FI-GOVT",
    }]

    monkeypatch.setattr(gold, "solr_get", fake_solr_get)
    monkeypatch.setattr(gold, "load_issuers", lambda _path: fake_issuers)

    result = assemble_golden(
        scope="bond",
        identifier={"kind": "isin", "value": "DE0001102309"},
        now=datetime(2026, 5, 16, tzinfo=timezone.utc),
        run_id="test-bond-firds",
    )
    rec = result.record
    assert rec["goldenId"].startswith("BG-DE0001102309")
    assert rec["currencyOfDenomination"] == "EUR"
    assert rec["maturityDate"] == "2034-08-15"
    assert rec["issuer"]["legalName"] == "Federal Republic of Germany"
    assert rec["issuer"]["lei"] == "529900AQBND3S6YJLY83"
    assert rec["currentCouponRate"] == 0.015  # 1.5% → 0.015 decimal
    assert rec["seniority"] == "senior_unsecured"

    from universe.models import BondGolden
    BondGolden.model_validate(rec)


def test_bond_firds_skips_unknown_issuer(monkeypatch):
    from pipeline.gold import bond_firds as gold

    monkeypatch.setattr(gold, "solr_get", lambda params, retries=5: {
        "response": {"docs": [{
            "isin": "ZZ0000000000",
            "lei": "UNKNOWN-LEI",
            "gnr_cfi_code": "DBFTFR",
            "gnr_notional_curr_code": "EUR",
            "bnd_maturity_date": "2030-01-01T00:00:00Z",
        }]}
    })
    monkeypatch.setattr(gold, "load_issuers", lambda _p: [])

    assert adapter.fetch("isin", "ZZ0000000000", current={}) is None
