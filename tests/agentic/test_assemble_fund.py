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
