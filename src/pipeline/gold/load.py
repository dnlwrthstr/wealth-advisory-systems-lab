"""Bulk-load a NDJSON file of golden records into OpenSearch.

Each line of the input file is a single JSON document. The script reads
all documents, then ships them to OpenSearch via the `_bulk` API in
chunks. The `_id` is taken from `goldenId` when present so re-runs are
idempotent (upsert behaviour).

The script is intentionally thin — it doesn't know anything about the
EquityGolden / BondGolden / FundGolden shape. The index mapping is what
enforces structure; this loader just trusts the file.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

from opensearchpy import OpenSearch, helpers

log = logging.getLogger("gold_load")

DEFAULT_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
DEFAULT_CHUNK = 500


def iter_docs(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                log.error("  line %d: invalid JSON (%s); skipped", lineno, exc)


def _actions(docs: Iterable[dict], index: str) -> Iterator[dict]:
    for doc in docs:
        doc_id = doc.get("goldenId") or doc.get("_id")
        action: dict = {"_op_type": "index", "_index": index, "_source": doc}
        if doc_id:
            action["_id"] = doc_id
        yield action


def bulk_load(
    client: OpenSearch, index: str, docs: Iterable[dict], chunk_size: int = DEFAULT_CHUNK
) -> Tuple[int, List[dict]]:
    success, errors = helpers.bulk(
        client,
        _actions(docs, index),
        chunk_size=chunk_size,
        raise_on_error=False,
        raise_on_exception=False,
    )
    return success, errors  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-load NDJSON golden records into an OpenSearch index."
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="NDJSON file.")
    parser.add_argument("-x", "--index", required=True, help="Target OpenSearch index.")
    parser.add_argument(
        "-u", "--url", default=DEFAULT_URL,
        help=f"OpenSearch URL (default: {DEFAULT_URL}; env OPENSEARCH_URL overrides).",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=DEFAULT_CHUNK,
        help=f"Bulk chunk size (default: {DEFAULT_CHUNK}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and count documents without indexing.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.input.exists():
        sys.exit(f"Input file not found: {args.input}")

    docs = list(iter_docs(args.input))
    log.info("Read %d documents from %s", len(docs), args.input)

    if args.dry_run:
        log.info("Dry run — not indexing.")
        return

    client = OpenSearch(hosts=[args.url], verify_certs=False, ssl_show_warn=False)
    success, errors = bulk_load(client, args.index, docs, chunk_size=args.chunk_size)
    log.info("Indexed %d / %d into %r", success, len(docs), args.index)
    if errors:
        log.warning("  %d errors; first: %s", len(errors), errors[0])
        sys.exit(1)


if __name__ == "__main__":
    main()
