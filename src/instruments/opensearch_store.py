"""OpenSearch-backed instrument store.

Reads `EquityGolden` (and later BondGolden / FundGolden) documents from
the `pms_golden_*` indices and projects them into the flat `Instrument`
dataclass that the FastAPI router already serialises. Same interface as
`InstrumentStore` so backend/instrument_api can swap implementations
without router changes.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from opensearchpy import OpenSearch

from .schemas import Instrument


# Map ontology assetClass → OpenWealth FinancialInstrumentType. Keeps the
# /instruments?type=equity filter compatible with the existing frontend.
_ASSET_CLASS_TO_OW_TYPE: Dict[str, str] = {
    "Equity / Common Stock": "equity",
    "Equity / ADR": "equity",
    "Equity / REIT": "equity",
}


def _ow_type_from_doc(src: Dict[str, Any]) -> str:
    asset_class = src.get("assetClass") or ""
    return _ASSET_CLASS_TO_OW_TYPE.get(asset_class, "equity")


def _isin_from_identifier_list(src: Dict[str, Any]) -> str:
    for entry in src.get("identifierList") or []:
        if (entry.get("type") or "").lower() == "isin":
            return entry.get("identifier") or ""
    return ""


def _ticker_from_identifier_list(src: Dict[str, Any]) -> str:
    for entry in src.get("identifierList") or []:
        if (entry.get("type") or "").lower() in ("tickersymbol", "ticker"):
            return entry.get("identifier") or ""
    return ""


def _doc_to_instrument(src: Dict[str, Any]) -> Instrument:
    """Project an EquityGolden source dict onto the flat Instrument shape."""
    primary = src.get("primaryListing") or {}
    market = src.get("marketData") or {}
    last_trade = market.get("lastTradePrice") or {}
    industry = src.get("industrySector") or {}
    issuer = src.get("issuer") or {}

    isin = _isin_from_identifier_list(src) or src.get("isin") or ""
    ticker = primary.get("ticker") or _ticker_from_identifier_list(src)
    short = src.get("shortName") or ticker or src.get("longName") or ""

    return Instrument(
        id=src.get("goldenId") or isin or ticker,
        isin=isin,
        name=src.get("longName") or short,
        short_name=short,
        type=_ow_type_from_doc(src),
        currency=src.get("currencyOfDenomination") or primary.get("listingCurrency") or "",
        price=float(last_trade.get("value") or 0.0),
        exchange=primary.get("mic"),
        country=src.get("incorporationCountry"),
        sector=industry.get("sectorLabel") or industry.get("canonicalLabel"),
        coupon_pct=None,
        maturity_date=None,
        yield_pct=None,
        description=issuer.get("legalName") or "",
    )


class OpenSearchInstrumentStore:
    """Read-side store reading EquityGolden docs from OpenSearch."""

    def __init__(
        self,
        client: OpenSearch,
        index: str = "pms_golden_equity",
    ):
        self._client = client
        self._index = index

    # ── Lookups ────────────────────────────────────────────────────────────

    def get_by_id(self, instrument_id: str) -> Optional[Instrument]:
        try:
            resp = self._client.get(index=self._index, id=instrument_id)
        except Exception:  # noqa: BLE001 — 404s and connection errors both end here
            return None
        if not resp.get("found"):
            return None
        return _doc_to_instrument(resp["_source"])

    def get_by_isin(self, isin: str) -> Optional[Instrument]:
        body = {
            "size": 1,
            "query": {
                "nested": {
                    "path": "identifierList",
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"identifierList.identifier.keyword": isin}},
                                {"term": {"identifierList.type.keyword": "isin"}},
                            ]
                        }
                    },
                }
            },
        }
        resp = self._client.search(index=self._index, body=body)
        hits = resp["hits"]["hits"]
        if not hits:
            # Fallback: try the flat top-level isin field (legacy docs).
            resp = self._client.search(
                index=self._index,
                body={"size": 1, "query": {"term": {"isin.keyword": isin}}},
            )
            hits = resp["hits"]["hits"]
        return _doc_to_instrument(hits[0]["_source"]) if hits else None

    # ── Search ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        type_filter: Optional[str] = None,
        currency: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Instrument], int]:
        must: List[Dict[str, Any]] = []
        filters: List[Dict[str, Any]] = []

        q = (query or "").strip()
        if q:
            must.append(
                {
                    "multi_match": {
                        "query": q,
                        "type": "best_fields",
                        "fields": [
                            "longName^3",
                            "shortName^2",
                            "industrySector.sectorLabel",
                            "industrySector.canonicalLabel",
                            "incorporationCountry",
                        ],
                        "operator": "and",
                    }
                }
            )
            # Also match identifier substrings (ISIN / ticker) via nested.
            must.append(
                {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": q,
                                    "fields": [
                                        "longName^3",
                                        "shortName^2",
                                        "industrySector.sectorLabel",
                                        "industrySector.canonicalLabel",
                                        "incorporationCountry",
                                    ],
                                    "operator": "and",
                                }
                            },
                            {
                                "nested": {
                                    "path": "identifierList",
                                    "query": {
                                        "match": {"identifierList.identifier": q}
                                    },
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
            # Drop the duplicate must[0] — its boolean wrapper above is the
            # authoritative match clause. Keeps the query tree small.
            must = must[1:]

        if currency:
            filters.append({"term": {"currencyOfDenomination.keyword": currency.upper()}})

        if type_filter:
            ow = type_filter.lower()
            asset_classes = [
                ac for ac, mapped in _ASSET_CLASS_TO_OW_TYPE.items() if mapped == ow
            ]
            if asset_classes:
                filters.append(
                    {"terms": {"assetClass.keyword": asset_classes}}
                )
            elif ow != "equity":
                # No equity hits will satisfy a non-equity filter (yet).
                return [], 0

        body: Dict[str, Any] = {
            "from": offset,
            "size": limit,
            "track_total_hits": True,
            "query": {
                "bool": {
                    "must": must or [{"match_all": {}}],
                    "filter": filters,
                }
            },
            "sort": [{"longName.keyword": {"order": "asc"}}],
        }

        resp = self._client.search(index=self._index, body=body)
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]["value"]
        items = [_doc_to_instrument(h["_source"]) for h in hits]
        return items, total

    # ── Aggregations ───────────────────────────────────────────────────────

    def list_types(self) -> List[str]:
        body = {
            "size": 0,
            "aggs": {
                "types": {"terms": {"field": "assetClass.keyword", "size": 50}}
            },
        }
        try:
            resp = self._client.search(index=self._index, body=body)
        except Exception:  # noqa: BLE001
            return ["equity"]
        buckets = resp.get("aggregations", {}).get("types", {}).get("buckets", [])
        seen = sorted({_ASSET_CLASS_TO_OW_TYPE.get(b["key"], "equity") for b in buckets})
        return seen or ["equity"]


def opensearch_client_from_env() -> Optional[OpenSearch]:
    """Return an OpenSearch client if `OPENSEARCH_URL` is set, else None."""
    url = os.environ.get("OPENSEARCH_URL")
    if not url:
        return None
    return OpenSearch(hosts=[url], verify_certs=False, ssl_show_warn=False)
