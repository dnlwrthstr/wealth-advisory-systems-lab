"""Enrich the pms_golden_issuer index from the GLEIF public API.

For every IssuerGolden document that carries a non-null `lei`, fetch the
GLEIF record + ultimate-parent LEI, then backfill `legalName`,
`domicileCountry`, `headquartersCountry`, `ultimateParentLei`, and refine
`issuerType` from GLEIF's `entity.category`. Results are cached on disk
under `~/.cache/wealth-advisory-systems-lab/gleif/` keyed by LEI so
re-runs are free.

The enricher *adds to* the issuer record (it does not blank existing
fields). Pre-existing values are preserved unless GLEIF clearly
contradicts them — only `issuerType` is refined when the current value
is the generic `corporate` default, matching pms-ontology's behaviour.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from opensearchpy import OpenSearch, helpers

log = logging.getLogger("issuer_gleif")

DEFAULT_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
INDEX = "pms_golden_issuer"

GLEIF_API = "https://api.gleif.org/api/v1/lei-records"
USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
TIMEOUT = 30
CACHE_DIR = Path.home() / ".cache" / "wealth-advisory-systems-lab" / "gleif"


# GLEIF entity.category → IssuerSnapshot.issuerType mapping. Matches the
# pms-ontology convention.
CATEGORY_TO_ISSUER_TYPE: Dict[str, str] = {
    "BANK": "bank",
    "FUND": "fund_company",
    "INSURANCE": "insurance_company",
    "GENERAL": "corporate",
    "RESIDENT_GOVERNMENT_ENTITY": "government",
    "INTERNATIONAL_ORGANIZATION": "supranational",
    "BRANCH": "corporate",
    "SOLE_PROPRIETOR": "corporate",
}


# ---------------------------------------------------------------------------
# GLEIF HTTP
# ---------------------------------------------------------------------------

def _cache_path(lei: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{lei}.json"


def _http_get_json(url: str) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.api+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code == 429:
            time.sleep(2.0)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        raise


def fetch_gleif(lei: str, *, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Fetch a LEI's main record + ultimate-parent LEI, cached on disk."""
    cached = _cache_path(lei)
    if use_cache and cached.exists():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    main = _http_get_json(f"{GLEIF_API}/{lei}")
    if main is None:
        cached.write_text(json.dumps({"main": None, "ultimate_parent_lei": None}), encoding="utf-8")
        return {"main": None, "ultimate_parent_lei": None}

    parent_lei: Optional[str] = None
    try:
        parent_record = _http_get_json(f"{GLEIF_API}/{lei}/ultimate-parent")
        if parent_record is not None:
            parent_lei = ((parent_record or {}).get("data") or {}).get("attributes", {}).get("lei")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            log.warning("ultimate-parent for %s: %s", lei, exc)

    result = {"main": main, "ultimate_parent_lei": parent_lei}
    try:
        cached.write_text(json.dumps(result), encoding="utf-8")
    except OSError as exc:
        log.warning("cache write failed for %s: %s", lei, exc)
    return result


def gleif_fields(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Project the parts of a GLEIF record we care about into a flat dict."""
    if not record or not record.get("main"):
        return {}
    attrs = (record["main"].get("data") or {}).get("attributes") or {}
    entity = attrs.get("entity") or {}
    legal_address = entity.get("legalAddress") or {}
    hq_address = entity.get("headquartersAddress") or {}
    out: Dict[str, Any] = {
        "legalName": (entity.get("legalName") or {}).get("name"),
        "domicileCountry": legal_address.get("country"),
        "headquartersCountry": hq_address.get("country"),
        "issuerTypeFromGleif": CATEGORY_TO_ISSUER_TYPE.get(entity.get("category") or ""),
    }
    if record.get("ultimate_parent_lei"):
        out["ultimateParentLei"] = record["ultimate_parent_lei"]
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------------------
# Apply enrichment in place
# ---------------------------------------------------------------------------

def apply_to_doc(doc: Dict[str, Any], gleif: Dict[str, Any]) -> Dict[str, Any]:
    """Backfill blanks + refine generic issuerType. Existing non-generic values
    are preserved.
    """
    updated = dict(doc)
    for field in ("legalName", "domicileCountry", "headquartersCountry", "ultimateParentLei"):
        v = gleif.get(field)
        if v and not updated.get(field):
            updated[field] = v
    new_type = gleif.get("issuerTypeFromGleif")
    if new_type and (not updated.get("issuerType") or updated["issuerType"] == "corporate"):
        updated["issuerType"] = new_type
    return updated


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def iter_issuers_with_lei(client: OpenSearch) -> Iterable[Dict[str, Any]]:
    query = {"query": {"exists": {"field": "lei"}}}
    yield from helpers.scan(client, index=INDEX, query=query)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GLEIF-enrich pms_golden_issuer documents that carry an LEI."
    )
    parser.add_argument("-u", "--url", default=DEFAULT_URL)
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Cap on number of issuers to enrich (smoke testing).",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Bypass the on-disk LEI cache for this run.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch + log only, do not re-index.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    client = OpenSearch(hosts=[args.url], verify_certs=False, ssl_show_warn=False)
    actions = []
    fetched = 0
    enriched = 0
    missing = 0

    for hit in iter_issuers_with_lei(client):
        src = hit["_source"]
        lei = src.get("lei")
        if not lei:
            continue
        if args.limit and fetched >= args.limit:
            break

        try:
            record = fetch_gleif(lei, use_cache=not args.no_cache)
        except Exception as exc:  # noqa: BLE001
            log.warning("  %s GLEIF failed: %s", lei, exc)
            continue
        fetched += 1

        fields = gleif_fields(record)
        if not fields:
            missing += 1
            log.info("  %s: GLEIF has no record", lei)
            continue

        updated = apply_to_doc(src, fields)
        if updated == src:
            log.info("  %s (%s): no changes", lei, src.get("legalName"))
            continue

        log.info(
            "  %s (%s) → domicile=%s parent=%s type=%s",
            lei, fields.get("legalName"),
            fields.get("domicileCountry"),
            fields.get("ultimateParentLei"),
            fields.get("issuerTypeFromGleif"),
        )
        enriched += 1
        actions.append(
            {
                "_op_type": "index",
                "_index": INDEX,
                "_id": src["issuerId"],
                "_source": updated,
            }
        )

    log.info("Fetched %d LEIs; %d enriched; %d not in GLEIF", fetched, enriched, missing)

    if args.dry_run:
        log.info("Dry run — not indexing.")
        return

    if not actions:
        log.info("Nothing to update.")
        return

    success, errors = helpers.bulk(
        client, actions, raise_on_error=False, raise_on_exception=False
    )
    log.info("Re-indexed %d / %d", success, len(actions))
    if errors:
        log.warning("  %d errors; first: %s", len(errors), errors[0])
        sys.exit(1)


if __name__ == "__main__":
    main()
