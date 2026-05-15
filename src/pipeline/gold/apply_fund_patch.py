"""Apply a partial-update patch file to a `pms_golden_fund` document.

The `find-and-parse-factsheet` skill writes JSON patches to
`data/opensearch/golden/fund/patches/<goldenId>.json` after extracting
fields from a KID, fact sheet, or holdings page. This helper applies
the patch to OpenSearch, refreshes the index, and rebuilds the
`pms_golden_instrumentsearch` helper so any hoisted fields surface in
the "Find an instrument" UI.

Patch shape:
    {
      "doc":   { …FundGolden top-level fields to set… },
      "_meta": {                                # optional
        "source":          "BlackRock iShares product page",
        "sourceTimestamp": "2026-05-15T17:30:00Z",
        "fieldGroups":     ["holdings", "fees"]   # optional override
      }
    }

When `_meta` is present, the script appends one `sourceOfTruth` entry
per `fieldGroup` to the doc's `recordMeta.sourceOfTruth` (deduping by
`(fieldGroup, source)`). When `fieldGroups` is omitted, the field
groups are derived from the keys present in `doc` — useful so the
skill doesn't have to enumerate them twice.

The `_meta` block itself is stripped from the body before sending to
OpenSearch (it's not part of the FundGolden schema).

Usage:
    python -m pipeline.gold.apply_fund_patch path/to/<goldenId>.json

The script:
  1. Validates the patch shape (top-level `doc`, no destructive ops).
  2. Derives the document id from the patch filename (no `.json` part).
  3. If `_meta` is present, reads the current doc, merges sourceOfTruth.
  4. POSTs `/pms_golden_fund/_update/<id>` with the (cleaned) patch.
  5. Refreshes the index.
  6. Rebuilds the helper search index.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opensearchpy import OpenSearch

from .fund_yahoo_enrich import merge_source_of_truth

log = logging.getLogger("apply_fund_patch")

DEFAULT_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
INDEX = "pms_golden_fund"

# Top-level FundGolden fields that the skill is allowed to set/patch.
_ALLOWED_TOP_LEVEL = {
    "totalExpenseRatio", "transactionCostsPRIIPs", "swingPricingApplied",
    "fees", "dealing", "riskRating",
    "serviceProviders",
    "benchmarkName", "benchmarkIdentifier",
    "replicationMethod", "rebalanceFrequency",
    "dividendPolicy", "isCurrencyHedged", "hedgingCurrency",
    "inceptionDate", "fiscalYearEnd",
    "holdingsCount", "holdingsAsOf",
    "assetAllocation", "currencyAllocation",
    "performance", "taxStatuses",
    "compliance",
    "shareClass",  # the skill can correct share-class fields from the KID
    "umbrella",    # only if the skill found a more authoritative LEI
    "managementCompany",
    "investmentManager", "promoter",
    "recordMeta",  # the script writes here too — allow direct overrides
}


# Top-level doc keys → canonical fieldGroup label for `recordMeta.sourceOfTruth`.
# When a patch's `_meta` doesn't list `fieldGroups`, we derive them from doc keys.
_DOC_KEY_TO_FIELD_GROUP = {
    "totalExpenseRatio":      "fees",
    "fees":                   "fees",
    "transactionCostsPRIIPs": "fees",
    "swingPricingApplied":    "fees",
    "dealing":                "dealing",
    "riskRating":             "riskRating",
    "serviceProviders":       "serviceProviders",
    "benchmarkName":          "benchmark",
    "benchmarkIdentifier":    "benchmark",
    "replicationMethod":      "fundProfile",
    "rebalanceFrequency":     "fundProfile",
    "dividendPolicy":         "fundProfile",
    "isCurrencyHedged":       "fundProfile",
    "hedgingCurrency":        "fundProfile",
    "inceptionDate":          "fundProfile",
    "fiscalYearEnd":          "fundProfile",
    "holdingsCount":          "holdings",
    "holdingsAsOf":           "holdings",
    "assetAllocation":        "holdings",
    "currencyAllocation":     "holdings",
    "performance":            "performance",
    "taxStatuses":            "taxStatuses",
    "compliance":             "compliance",
    "shareClass":             "shareClass",
    "umbrella":               "umbrella",
    "managementCompany":      "managementCompany",
    "investmentManager":      "managementCompany",
    "promoter":               "promoter",
}


def _validate_patch(body: Any) -> dict:
    if not isinstance(body, dict) or "doc" not in body:
        sys.exit("patch must be a JSON object with a top-level `doc` key")
    doc = body["doc"]
    if not isinstance(doc, dict) or not doc:
        sys.exit("`doc` must be a non-empty object")
    unknown = sorted(set(doc) - _ALLOWED_TOP_LEVEL)
    if unknown:
        sys.exit(
            "patch contains fields not on the FundGolden allow-list: "
            f"{unknown}. Edit the patch or extend _ALLOWED_TOP_LEVEL in "
            "apply_fund_patch.py."
        )
    return body


def _derive_field_groups(doc: dict) -> list:
    """When `_meta.fieldGroups` is omitted, infer them from the doc keys."""
    seen = set()
    out = []
    for key in doc:
        fg = _DOC_KEY_TO_FIELD_GROUP.get(key)
        if fg and fg not in seen:
            seen.add(fg)
            out.append(fg)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply a JSON patch file to a pms_golden_fund document."
    )
    parser.add_argument(
        "patch_path", type=Path,
        help=(
            "Path to the patch file. The filename (sans .json) becomes the "
            "document _id (e.g. FG-IE00B4L5Y983-001.json → goldenId "
            "FG-IE00B4L5Y983-001)."
        ),
    )
    parser.add_argument("-u", "--url", default=DEFAULT_URL)
    parser.add_argument(
        "--skip-search-rebuild", action="store_true",
        help="Skip the `pipeline.gold.search_index_build` step after apply.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.patch_path.exists():
        sys.exit(f"Patch file not found: {args.patch_path}")

    body = json.loads(args.patch_path.read_text(encoding="utf-8"))
    body = _validate_patch(body)

    golden_id = args.patch_path.stem
    if not golden_id.startswith("FG-"):
        sys.exit(
            f"goldenId derived from filename ({golden_id!r}) doesn't look like "
            "a FundGolden id (expected FG-…). Rename the patch file."
        )

    # Pull _meta out of the body before sending; OpenSearch's update doc body
    # is a strict subset of the FundGolden schema and rejects unknown keys.
    patch_meta = body.pop("_meta", None) or {}

    client = OpenSearch(hosts=[args.url], verify_certs=False, ssl_show_warn=False)

    # If the patch declares a source, append sourceOfTruth entries. The merge
    # has to happen on top of the existing recordMeta, so we fetch first.
    if patch_meta.get("source"):
        try:
            current = client.get(index=INDEX, id=golden_id)
        except Exception as exc:  # noqa: BLE001 — 404 etc.
            sys.exit(f"document {golden_id!r} not found in {INDEX}: {exc}")
        record_meta = dict((current.get("_source") or {}).get("recordMeta") or {})
        field_groups = patch_meta.get("fieldGroups") or _derive_field_groups(body["doc"])
        source_label = patch_meta["source"]
        timestamp = patch_meta.get("sourceTimestamp") or datetime.now(timezone.utc).isoformat()
        merge_source_of_truth(
            record_meta,
            [
                {"fieldGroup": fg, "source": source_label, "sourceTimestamp": timestamp}
                for fg in field_groups
            ],
        )
        record_meta["goldenAsOf"] = timestamp
        # Stitch the recomputed recordMeta into the patch so the update is
        # atomic — single request.
        body["doc"] = {**body["doc"], "recordMeta": record_meta}
        log.info(
            "Appended/refreshed %d sourceOfTruth entries (source=%r)",
            len(field_groups), source_label,
        )

    log.info("Updating %s/%s with %d top-level field(s)",
             INDEX, golden_id, len(body["doc"]))
    resp = client.update(index=INDEX, id=golden_id, body=body)
    if resp.get("result") not in ("updated", "noop"):
        log.warning("unexpected update result: %s", resp.get("result"))
    client.indices.refresh(index=INDEX)
    log.info("OK — fund doc refreshed.")

    if args.skip_search_rebuild:
        log.info("Skipping search-index rebuild per --skip-search-rebuild.")
        return

    log.info("Rebuilding pms_golden_instrumentsearch…")
    subprocess.run(
        [sys.executable, "-m", "pipeline.gold.search_index_build"],
        env={**os.environ, "PYTHONPATH": "src"},
        check=True,
    )
    log.info("Done.")


if __name__ == "__main__":
    main()
