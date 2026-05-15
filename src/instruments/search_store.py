"""Search-and-autocomplete store on top of `pms_golden_instrumentsearch`.

Powers the new "Find an instrument" UI: a single OpenSearch query covers
identifier, name and issuer-name across every instrument family with one
optional `type` narrowing filter (and an arbitrary number of `filters`
for the advanced panel). Returns the denormalised search-projection
shape — `documentId` + `scope` is the pointer back into the per-security
golden index when the user clicks through.

Distinct from the legacy `OpenSearchInstrumentStore` (which queries the
per-security indices directly and projects onto the flat Instrument
dataclass). The two coexist while the old `/instruments` endpoint stays
backwards-compatible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from opensearchpy import OpenSearch


SEARCH_INDEX = "pms_golden_instrumentsearch"


@dataclass(frozen=True)
class SearchHit:
    """Single search result. JSON-serializable via dataclasses.asdict()."""
    document_id: str
    scope: str                  # equity / bond / fund
    ow_type: str                # OpenWealth FinancialInstrumentType
    long_name: str
    short_name: Optional[str]
    asset_class: Optional[str]
    asset_class_id: Optional[str]
    cfi_code: Optional[str]
    currency: Optional[str]
    country: Optional[str]
    venue_mic: Optional[str]
    ticker: Optional[str]
    issuer_legal_name: Optional[str]
    issuer_lei: Optional[str]
    management_company_name: Optional[str]
    promoter_name: Optional[str]
    identifiers: List[Dict[str, str]]
    lifecycle_status: Optional[str]
    quality_score: Optional[float]
    score: float


def _hit_to_search(hit: Dict[str, Any]) -> SearchHit:
    src = hit["_source"]
    return SearchHit(
        document_id=src["documentId"],
        scope=src["scope"],
        ow_type=src.get("ow_type") or src["scope"],
        long_name=src.get("longName") or "",
        short_name=src.get("shortName"),
        asset_class=src.get("assetClass"),
        asset_class_id=src.get("assetClassId"),
        cfi_code=src.get("cfiCode"),
        currency=src.get("currency"),
        country=src.get("country"),
        venue_mic=src.get("venueMic"),
        ticker=src.get("ticker"),
        issuer_legal_name=src.get("issuerLegalName"),
        issuer_lei=src.get("issuerLei"),
        management_company_name=src.get("managementCompanyName"),
        promoter_name=src.get("promoterName"),
        identifiers=list(src.get("identifiers") or []),
        lifecycle_status=src.get("lifecycleStatus"),
        quality_score=src.get("qualityScore"),
        score=float(hit.get("_score") or 0.0),
    )


def _identifier_subquery(value: str) -> Dict[str, Any]:
    """Match an identifier substring across schemes — also accepts exact
    matches against the keyword-mapped `identifierStrings.keyword` field
    so users typing the full ISIN/ticker get a top hit immediately.
    """
    value = value.strip()
    return {
        "bool": {
            "should": [
                {"term": {"identifierStrings.keyword": value}},
                {"term": {"identifierStrings.keyword": value.upper()}},
                {"match": {"identifierStrings": {"query": value, "operator": "and"}}},
                {"match_phrase_prefix": {"ticker": value}},
            ],
            "minimum_should_match": 1,
        }
    }


def _name_subquery(value: str) -> Dict[str, Any]:
    return {
        "multi_match": {
            "query": value,
            "type": "best_fields",
            "fields": ["longName^3", "shortName^2"],
            "operator": "and",
        }
    }


def _issuer_subquery(value: str) -> Dict[str, Any]:
    return {
        "multi_match": {
            "query": value,
            "type": "best_fields",
            "fields": [
                "issuerLegalName^3",
                "managementCompanyName",
                "promoterName",
            ],
            "operator": "and",
        }
    }


class OpenSearchInstrumentSearch:
    """Search-side store reading the helper index."""

    def __init__(self, client: OpenSearch, index: str = SEARCH_INDEX):
        self._client = client
        self._index = index

    def search(
        self,
        identifier: str = "",
        name: str = "",
        issuer: str = "",
        ow_type: Optional[str] = None,
        filters: Optional[Mapping[str, str]] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Dict[str, Any]:
        must: List[Dict[str, Any]] = []
        if identifier:
            must.append(_identifier_subquery(identifier))
        if name:
            must.append(_name_subquery(name))
        if issuer:
            must.append(_issuer_subquery(issuer))

        filter_clauses: List[Dict[str, Any]] = []
        if ow_type and ow_type.lower() != "all":
            filter_clauses.append({"term": {"ow_type.keyword": ow_type}})
        if filters:
            for key, value in filters.items():
                if value is None or value == "":
                    continue
                filter_clauses.append({"term": {f"{key}.keyword": value}})

        body: Dict[str, Any] = {
            "from": offset,
            "size": limit,
            "track_total_hits": True,
            "query": {
                "bool": {
                    "must": must or [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"longName.keyword": {"order": "asc"}},
            ],
        }

        resp = self._client.search(index=self._index, body=body)
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]["value"]
        items = [_hit_to_search(h) for h in hits]
        return {"items": items, "total": total}


def opensearch_client_from_env() -> Optional[OpenSearch]:
    url = os.environ.get("OPENSEARCH_URL")
    if not url:
        return None
    return OpenSearch(hosts=[url], verify_certs=False, ssl_show_warn=False)
