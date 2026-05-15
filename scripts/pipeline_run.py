"""
Instrument data refinement pipeline.

Stages:
  bronze  — ingest raw source files, write one parquet per type per source
  silver  — map raw parquets to internal ontology model  (not yet implemented)
  gold    — enrich + deduplicate, index to OpenSearch     (not yet implemented)

Usage:
    python scripts/pipeline_run.py --stage bronze --source finfox
    python scripts/pipeline_run.py --stage bronze --source finfox --csv /path/to/file.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")

# Default CSV locations per source
_DEFAULT_CSV = {
    "finfox": "/Users/danielwirth/PycharmProjects/financial-advisory-project/data/IN_INSTRUMENTS_COMPLETE.csv",
}

# Default bronze output directories per source
_BRONZE_OUT = {
    "finfox": "data/lake/bronze/finfox",
}


def run_bronze(source: str, csv_path: str | None) -> None:
    if source == "finfox":
        from pipeline.bronze.finfox import ingest
        path = csv_path or _DEFAULT_CSV["finfox"]
        out = _BRONZE_OUT["finfox"]
        manifest = ingest(path, out)
        log.info(
            "Bronze complete: %d rows across %d classes",
            manifest["total_rows"],
            len(manifest["row_counts_by_class"]),
        )
    else:
        log.error("Unknown source: %s", source)
        sys.exit(1)


def run_silver(source: str) -> None:
    log.warning("Silver stage not yet implemented — waiting for ontology model")


def run_gold(source: str) -> None:
    log.warning("Gold stage not yet implemented — depends on Silver")


def main() -> None:
    parser = argparse.ArgumentParser(description="Instrument data refinement pipeline")
    parser.add_argument("--stage", choices=["bronze", "silver", "gold", "all"], required=True)
    parser.add_argument("--source", default="finfox", help="Data source identifier")
    parser.add_argument("--csv", default=None, help="Override default CSV path (bronze stage)")
    args = parser.parse_args()

    stages = ["bronze", "silver", "gold"] if args.stage == "all" else [args.stage]

    for stage in stages:
        log.info("─── Stage: %s ───", stage.upper())
        if stage == "bronze":
            run_bronze(args.source, args.csv)
        elif stage == "silver":
            run_silver(args.source)
        elif stage == "gold":
            run_gold(args.source)


if __name__ == "__main__":
    main()
