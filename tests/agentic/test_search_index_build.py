"""Tests for `pipeline.gold.search_index_build.project_search_doc`.

The writer's `ow_type` value has to match the public API contract on
`GET /instruments/search?type=…`, which filters via an exact-match
`term` query on `ow_type.keyword`. Regression for the bond
casing mismatch surfaced during feature 002.
"""
from __future__ import annotations

import pytest

# pipeline.gold.search_index_build imports opensearchpy at module level.
pytest.importorskip("opensearchpy")

from pipeline.gold.search_index_build import _SCOPE_TO_OW_TYPE, project_search_doc  # noqa: E402


# ---------------------------------------------------------------------------
# ow_type contract — writer matches reader for every scope
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scope,expected_ow_type",
    [
        ("equity", "equity"),
        ("bond", "simpleBond"),  # camelCase, matches GET /instruments/search?type=simpleBond
        ("fund", "fund"),
    ],
)
def test_scope_to_ow_type_matches_public_api_contract(scope, expected_ow_type):
    assert _SCOPE_TO_OW_TYPE[scope] == expected_ow_type


def test_project_search_doc_bond_uses_camel_case_ow_type():
    """Direct check on the projector output — the bug lived here."""
    record = {
        "goldenId": "BG-DE0001102309-XFRA-001",
        "longName": "Germany 0% 2025",
        "assetClass": "Fixed Income / Government Bond",
        "primaryListing": {"mic": "XFRA"},
    }
    doc = project_search_doc(record, scope="bond", universe_status="in_universe")
    assert doc["ow_type"] == "simpleBond", (
        f"bond search docs must use camelCase ow_type to match the public API; "
        f"got {doc['ow_type']!r}"
    )
    assert doc["scope"] == "bond"
    assert doc["assetClass"] == "Fixed Income / Government Bond"
    assert doc["universeStatus"] == "in_universe"


def test_project_search_doc_equity_unchanged():
    record = {
        "goldenId": "EQG-CH0038863350-XSWX-001",
        "longName": "Nestlé S.A.",
        "assetClass": "Equity / Common Stock",
        "primaryListing": {"mic": "XSWX"},
    }
    doc = project_search_doc(record, scope="equity")
    assert doc["ow_type"] == "equity"


def test_project_search_doc_fund_unchanged():
    record = {
        "goldenId": "FG-IE00B4L5Y983-XLON-001",
        "longName": "iShares Core MSCI World UCITS ETF",
        "assetClass": "Fund / ETF",
        "primaryListing": {"mic": "XLON"},
    }
    doc = project_search_doc(record, scope="fund")
    assert doc["ow_type"] == "fund"
