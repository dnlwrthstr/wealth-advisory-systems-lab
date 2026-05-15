"""Aggregate per-instrument issuer references into IssuerGolden documents.

Scans the per-security golden indices (`pms_golden_equity`,
`pms_golden_bond`, `pms_golden_fund`) and produces one IssuerGolden
document per distinct issuer, keyed by `issuerId`. Counts how many
instruments reference each issuer per class.

This script is the lab's persistent issuer layer — when the embedded
IssuerSnapshot on an instrument carries an LEI, GLEIF enrichment can
later be layered on top of the aggregated document before re-indexing.
Today GLEIF enrichment is a hook left for follow-up; the aggregator
simply consolidates whatever was emitted by the source-of-truth
pipelines (parquet, FIRDS, yfinance).
"""

from __future__ import annotations

import argparse
import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from opensearchpy import OpenSearch, helpers
from pydantic import ValidationError

from universe.models import (
    Country,
    CreditProfile,
    GoldenRecordMeta,
    IssuerGolden,
    LegalEntityIdentifier,
    SourceAttribution,
)

log = logging.getLogger("issuer_aggregate")

DEFAULT_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
SOURCE_INDICES = ["pms_golden_equity", "pms_golden_bond", "pms_golden_fund"]
TARGET_INDEX = "pms_golden_issuer"


# Fund records carry the issuer in `managementCompany` rather than `issuer`.
def _extract_issuer_block(src: Dict[str, Any], class_name: str) -> Optional[Dict[str, Any]]:
    if class_name == "fund":
        return src.get("managementCompany") or src.get("issuer")
    return src.get("issuer")


def _class_from_index(index_name: str) -> str:
    # "pms_golden_equity" → "equity"
    return index_name.split("_", 2)[-1] if "_" in index_name else index_name


def scan_issuers(client: OpenSearch) -> Dict[str, Dict[str, Any]]:
    """Return {issuerId → aggregated dict} across the source indices."""
    aggregated: Dict[str, Dict[str, Any]] = {}

    for index in SOURCE_INDICES:
        class_name = _class_from_index(index)
        try:
            cursor = helpers.scan(client, index=index, query={"query": {"match_all": {}}})
        except Exception as exc:  # noqa: BLE001
            log.warning("scan failed for %s: %s", index, exc)
            continue

        seen_in_index = 0
        for hit in cursor:
            src = hit.get("_source") or {}
            issuer = _extract_issuer_block(src, class_name)
            if not issuer:
                continue
            issuer_id = issuer.get("issuerId") or (
                f"ISS-{issuer['lei']}" if issuer.get("lei") else None
            )
            if not issuer_id:
                continue

            entry = aggregated.setdefault(
                issuer_id,
                {
                    "issuerId": issuer_id,
                    "lei": issuer.get("lei"),
                    "legalName": issuer.get("legalName"),
                    "issuerType": issuer.get("issuerType"),
                    "domicileCountry": issuer.get("domicileCountry"),
                    "headquartersCountry": issuer.get("headquartersCountry"),
                    "ultimateParentLei": issuer.get("ultimateParentLei"),
                    "guarantorLei": issuer.get("guarantorLei"),
                    "creditProfile": issuer.get("creditProfile"),
                    "esgProfile": issuer.get("esgProfile"),
                    "instrumentsByClass": defaultdict(int),
                    "instrumentCount": 0,
                },
            )
            entry["instrumentsByClass"][class_name] += 1
            entry["instrumentCount"] += 1
            # Fill blanks from later sources without overwriting earlier values.
            for field in (
                "lei", "legalName", "issuerType",
                "domicileCountry", "headquartersCountry",
                "ultimateParentLei", "guarantorLei",
                "creditProfile", "esgProfile",
            ):
                if entry.get(field) is None and issuer.get(field) is not None:
                    entry[field] = issuer[field]
            seen_in_index += 1
        log.info("scanned %s: %d issuer references", index, seen_in_index)

    return aggregated


def build_golden(entry: Dict[str, Any], run_id: str, now: datetime) -> Optional[IssuerGolden]:
    legal_name = entry.get("legalName")
    if not legal_name:
        return None

    lei = entry.get("lei")
    golden_id = f"ISG-{lei}-001" if lei else f"ISG-{entry['issuerId']}-001"

    domicile = entry.get("domicileCountry")
    headquarters = entry.get("headquartersCountry")
    credit = entry.get("creditProfile")

    meta = GoldenRecordMeta(
        schemaVersion="0.1.0",
        goldenAsOf=now.isoformat(),
        ingestionRunId=run_id,
        sourceOfTruth=[
            SourceAttribution(
                fieldGroup="aggregated", source="pms_golden_{equity,bond,fund}"
            )
        ],
        isActive=True,
    )

    try:
        return IssuerGolden(
            goldenId=golden_id,
            issuerId=entry["issuerId"],
            lei=LegalEntityIdentifier(lei) if lei else None,
            legalName=legal_name,
            issuerType=entry.get("issuerType"),
            domicileCountry=Country(domicile) if domicile else None,
            headquartersCountry=Country(headquarters) if headquarters else None,
            ultimateParentLei=entry.get("ultimateParentLei"),
            guarantorLei=entry.get("guarantorLei"),
            creditProfile=CreditProfile(**credit) if credit else None,
            instrumentsByClass=dict(entry["instrumentsByClass"]),
            instrumentCount=entry["instrumentCount"],
            recordMeta=meta,
        )
    except ValidationError as exc:
        log.warning("validation failed for %s: %s", golden_id, exc.errors()[0]["msg"])
        return None


def bulk_index(client: OpenSearch, docs: Iterable[IssuerGolden]) -> int:
    def actions():
        for doc in docs:
            yield {
                "_op_type": "index",
                "_index": TARGET_INDEX,
                "_id": doc.issuerId,
                "_source": doc.model_dump(mode="json", exclude_none=True),
            }

    success, errors = helpers.bulk(
        client, actions(), raise_on_error=False, raise_on_exception=False
    )
    if errors:
        log.warning("  %d index errors; first: %s", len(errors), errors[0])
    return success  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate per-instrument issuer blocks from pms_golden_{equity,bond,fund} "
            "into pms_golden_issuer."
        )
    )
    parser.add_argument(
        "-u", "--url", default=DEFAULT_URL,
        help=f"OpenSearch URL (default: {DEFAULT_URL}; env OPENSEARCH_URL).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count distinct issuers and exit without indexing.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    client = OpenSearch(hosts=[args.url], verify_certs=False, ssl_show_warn=False)
    aggregated = scan_issuers(client)
    log.info("Aggregated %d distinct issuers", len(aggregated))

    run_id = f"issuer-aggregate-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    docs = [d for d in (build_golden(e, run_id, now) for e in aggregated.values()) if d]
    log.info("Built %d valid IssuerGolden documents", len(docs))

    if args.dry_run:
        log.info("Dry run — not indexing.")
        return

    n = bulk_index(client, docs)
    log.info("Indexed %d / %d into %r", n, len(docs), TARGET_INDEX)


if __name__ == "__main__":
    main()
