"""Build the pms_golden_instrumentsearch helper index.

Scans `pms_golden_{equity,bond,fund}` and emits one denormalised
InstrumentSearch document per per-security record. The doc carries every
known identifier (flattened for substring + exact-match search), the
display names (long + short), the issuer / umbrella / management
company legal name(s), plus a few hoisted filter fields (currency,
country, venue MIC, asset class, lifecycle status, quality score).

A single OpenSearch query against this index lets the UI search by ISIN,
ticker, valor, name fragment, or issuer name without touching the
per-security indices. The full record stays in the source-of-truth
index — `documentId` + `scope` is enough to fetch it on click.

Re-run after any per-security re-load.
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional

from opensearchpy import OpenSearch, helpers

log = logging.getLogger("search_index_build")

DEFAULT_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
TARGET_INDEX = "pms_golden_instrumentsearch"

# OpenWealth FinancialInstrumentType the frontend type tabs filter on.
# Values must match the public API contract: the search-store's ow_type
# filter does an exact-match `term` query on `ow_type.keyword`, so the
# writer here has to use the same casing the caller passes to
# `GET /instruments/search?type=…`. Equity and fund are one word so
# casing was already aligned; bond is two words and the API documents
# camelCase (`simpleBond`), so this map uses camelCase here too.
_SCOPE_TO_OW_TYPE = {
    "equity": "equity",
    "bond": "simpleBond",
    "fund": "fund",
}

SOURCE_INDICES = list(_SCOPE_TO_OW_TYPE.keys())


def _src_index(scope: str) -> str:
    return f"pms_golden_{scope}"


def _issuer_display(src: Dict[str, Any], scope: str) -> tuple[Optional[str], Optional[str]]:
    """For (legalName, LEI) of the display issuer per family."""
    if scope == "fund":
        umb = src.get("umbrella") or {}
        if umb:
            return umb.get("legalName"), umb.get("lei")
        # Fallback to managementCompany if umbrella is missing.
        mc = src.get("managementCompany") or {}
        return mc.get("legalName"), mc.get("lei")
    issuer = src.get("issuer") or {}
    return issuer.get("legalName"), issuer.get("lei")


def _identifiers(src: Dict[str, Any]) -> List[Dict[str, str]]:
    return list(src.get("identifierList") or [])


def _identifier_strings(idents: Iterable[Dict[str, str]]) -> List[str]:
    return sorted({(e.get("identifier") or "") for e in idents if e.get("identifier")})


def _country(src: Dict[str, Any]) -> Optional[str]:
    return (
        src.get("incorporationCountry")
        or src.get("domicile")
        or src.get("countryOfRisk")
    )


def _valor(idents: List[Dict[str, str]]) -> Optional[str]:
    for entry in idents:
        if (entry.get("type") or "").lower() == "valoren":
            return entry.get("identifier")
    return None


def _sector(src: Dict[str, Any]) -> Optional[str]:
    industry = src.get("industrySector") or {}
    return (
        industry.get("sectorLabel")
        or industry.get("canonicalLabel")
        or industry.get("industryLabel")
    )


def _issuer_rating(src: Dict[str, Any]) -> Optional[str]:
    issuer = src.get("issuer") or {}
    credit = issuer.get("creditProfile") or {}
    ratings = credit.get("issuerRatings") or []
    if not ratings:
        return None
    first = ratings[0]
    # Rating is now an object {agency, rating, ratingType, ...}; some legacy
    # docs may still carry a plain string.
    if isinstance(first, str):
        return first
    return first.get("rating") if isinstance(first, dict) else None


def project_search_doc(
    src: Dict[str, Any],
    scope: str,
    *,
    universe_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the pms_golden_instrumentsearch document for one record.

    Exposed publicly so the universe router can index a single doc after
    `POST /universe/{scope}` instead of relying on a periodic full
    rebuild. When `universe_status` is set, it's carried through onto
    the search hit (the front-end's Find-an-instrument can then prefer
    or filter by it).
    """
    primary = src.get("primaryListing") or {}
    idents = _identifiers(src)
    issuer_name, issuer_lei = _issuer_display(src, scope)
    mc = src.get("managementCompany") or {}
    prom = src.get("promoter") or {}
    record_meta = src.get("recordMeta") or {}
    sub_fund = src.get("subFund") or {}
    umbrella = src.get("umbrella") or {}

    doc: Dict[str, Any] = {
        "documentId": src.get("goldenId"),
        "scope": scope,
        "ow_type": _SCOPE_TO_OW_TYPE.get(scope, scope),
        "longName": src.get("longName"),
        "shortName": src.get("shortName"),
        "assetClass": src.get("assetClass"),
        "assetClassId": src.get("assetClassId"),
        "cfiCode": src.get("cfiCode"),
        "currency": src.get("currencyOfDenomination"),
        "country": _country(src),
        "venueMic": primary.get("mic"),
        "ticker": primary.get("ticker"),
        "valor": _valor(idents),
        "issuerLegalName": issuer_name,
        "issuerLei": issuer_lei,
        "identifiers": idents or None,
        "identifierStrings": _identifier_strings(idents) or None,
        "lifecycleStatus": src.get("lifecycleStatus"),
        "qualityScore": record_meta.get("qualityScore"),
        "goldenAsOf": record_meta.get("goldenAsOf"),
        "universeStatus": universe_status,
        # Type-specific
        "sector": _sector(src) if scope == "equity" else None,
        "couponRate": src.get("currentCouponRate") if scope == "bond" else None,
        "maturityDate": src.get("maturityDate") if scope == "bond" else None,
        "issuerRating": _issuer_rating(src) if scope == "bond" else None,
        "managementCompanyName": mc.get("legalName") if scope == "fund" else None,
        "promoterName": prom.get("legalName") if scope == "fund" else None,
        "subFundName": sub_fund.get("name") if scope == "fund" else None,
        "umbrellaName": umbrella.get("legalName") if scope == "fund" else None,
        "fundSubType": src.get("fundSubType") if scope == "fund" else None,
        "dividendPolicy": src.get("dividendPolicy") if scope == "fund" else None,
        "totalExpenseRatio": src.get("totalExpenseRatio") if scope == "fund" else None,
        "primaryAssetClassExposure": src.get("primaryAssetClassExposure") if scope == "fund" else None,
    }
    return {k: v for k, v in doc.items() if v is not None}


# Backwards-compatible alias for the in-module callers (iter_search_docs).
_project = project_search_doc


def index_search_hit(
    client: Any,
    scope: str,
    record: Dict[str, Any],
    *,
    universe_status: Optional[str] = None,
) -> None:
    """Index one record into `pms_golden_instrumentsearch`.

    Called from the universe router right after `assemble_and_persist`
    so additions show up in the Find-an-instrument search immediately —
    no separate rebuild needed.
    """
    doc = project_search_doc(record, scope, universe_status=universe_status)
    if not doc.get("documentId"):
        return  # nothing to key on; skip silently
    client.index(
        index=TARGET_INDEX,
        id=f"{scope}:{doc['documentId']}",
        body=doc,
        refresh="wait_for",
    )


def iter_search_docs(client: OpenSearch) -> Iterator[Dict[str, Any]]:
    for scope in SOURCE_INDICES:
        index = _src_index(scope)
        try:
            cursor = helpers.scan(client, index=index, query={"query": {"match_all": {}}})
        except Exception as exc:  # noqa: BLE001
            log.warning("scan failed for %s: %s", index, exc)
            continue
        n = 0
        for hit in cursor:
            src = hit.get("_source") or {}
            if not src.get("goldenId"):
                continue
            yield _project(src, scope)
            n += 1
        log.info("scanned %s: %d records projected", index, n)


def bulk_index(client: OpenSearch, docs: Iterable[Dict[str, Any]]) -> int:
    def actions():
        for doc in docs:
            yield {
                "_op_type": "index",
                "_index": TARGET_INDEX,
                "_id": f"{doc['scope']}:{doc['documentId']}",
                "_source": doc,
            }

    success, errors = helpers.bulk(
        client, actions(), raise_on_error=False, raise_on_exception=False
    )
    if errors:
        log.warning("  %d errors; first: %s", len(errors), errors[0])
    return success  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild the pms_golden_instrumentsearch helper index."
    )
    parser.add_argument(
        "-u", "--url", default=DEFAULT_URL,
        help=f"OpenSearch URL (default: {DEFAULT_URL}; env OPENSEARCH_URL).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Project and count documents without indexing.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    client = OpenSearch(hosts=[args.url], verify_certs=False, ssl_show_warn=False)
    docs = list(iter_search_docs(client))
    log.info("Built %d search documents", len(docs))

    if args.dry_run:
        return

    n = bulk_index(client, docs)
    log.info("Indexed %d / %d into %r", n, len(docs), TARGET_INDEX)


if __name__ == "__main__":
    main()
