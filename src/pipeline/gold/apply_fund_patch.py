"""Apply a partial-update patch file to a `pms_golden_fund` document.

The `find-and-parse-factsheet` skill writes JSON patches to
`data/opensearch/golden/fund/patches/<goldenId>.json` after extracting
fields from a KID, fact sheet, or holdings page. This helper applies
the patch to OpenSearch, refreshes the index, and rebuilds the
`pms_golden_instrumentsearch` helper so any hoisted fields surface in
the "Find an instrument" UI.

Usage:
    python -m pipeline.gold.apply_fund_patch path/to/<goldenId>.json

The script:
  1. Validates the patch shape (top-level `doc`, no destructive ops).
  2. Derives the document id from the patch filename (no `.json` part).
  3. POSTs `/pms_golden_fund/_update/<id>` with the patch body.
  4. Refreshes the index.
  5. Rebuilds the helper search index.

It does NOT apply patches that target fields outside the FundGolden
shape — the OpenSearch mapping is dynamic=false and will reject
unknown fields, but the helper catches obvious typos here too.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from opensearchpy import OpenSearch

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

    client = OpenSearch(hosts=[args.url], verify_certs=False, ssl_show_warn=False)
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
