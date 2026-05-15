"""
Bronze layer — FINFOX CSV ingestion.

Reads a FINFOX semicolon-delimited export, splits by instrument class,
and writes one raw parquet per class to the target directory.

Nothing is transformed: all values are kept as strings exactly as received.
Two metadata columns are added to every row:
  _source_file   — basename of the CSV that produced the row
  _ingested_at   — ISO UTC datetime of the ingestion run

A _manifest.json is written alongside the parquets with provenance metadata
(source path, MD5 hash, row counts, column list, ingested_at).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

# Columns that identify a row's origin — prepended with _ to distinguish from source fields
_META_SOURCE_FILE = "_source_file"
_META_INGESTED_AT = "_ingested_at"


def ingest(csv_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """
    Parse a FINFOX CSV and write one parquet per instrument class.

    Returns the manifest dict (also written as _manifest.json in out_dir).
    """
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ingested_at = datetime.now(timezone.utc).isoformat()
    source_hash = _md5(csv_path)

    log.info("Bronze ingest: %s  (md5=%s)", csv_path.name, source_hash[:8])

    raw_df = _parse_finfox_csv(csv_path)
    log.info("  Parsed %d rows, %d columns", len(raw_df), len(raw_df.columns))

    # Attach provenance columns
    raw_df[_META_SOURCE_FILE] = csv_path.name
    raw_df[_META_INGESTED_AT] = ingested_at

    # Split by class, write one parquet per class
    row_counts: dict[str, int] = {}
    for cls, group in raw_df.groupby("class", sort=True):
        cls_name = str(cls)
        out_path = out_dir / f"{cls_name}.parquet"
        group = group.reset_index(drop=True)
        group.to_parquet(out_path, index=False)
        row_counts[cls_name] = len(group)
        log.info("  %-30s %4d rows → %s", cls_name, len(group), out_path.name)

    manifest: dict[str, Any] = {
        "source_path": str(csv_path.resolve()),
        "source_file": csv_path.name,
        "source_md5": source_hash,
        "ingested_at": ingested_at,
        "total_rows": len(raw_df),
        "columns": [c for c in raw_df.columns if not c.startswith("_")],
        "row_counts_by_class": row_counts,
        "out_dir": str(out_dir.resolve()),
    }

    manifest_path = out_dir / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("  Manifest → %s", manifest_path.name)

    return manifest


# ── Internal helpers ───────────────────────────────────────────────────────────

def _parse_finfox_csv(path: Path) -> pd.DataFrame:
    """
    Parse the FINFOX semicolon-delimited format.

    Line structure:
      # comment lines  (skip)
      IN_SECTION_NAME  (skip — section header, no semicolons)
      id;col1;col2;... (first non-comment, non-section line = column headers)
      val;val;val;...  (data rows)
    """
    headers: list[str] = []
    rows: list[dict[str, str]] = []

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n\r")

            if line.startswith("#"):
                continue

            # Section marker: a line with no semicolons that names the data block
            if ";" not in line:
                continue

            parts = line.split(";")

            if not headers:
                headers = parts
                continue

            # Pad short rows so zip doesn't drop trailing empty fields
            if len(parts) < len(headers):
                parts.extend([""] * (len(headers) - len(parts)))

            rows.append(dict(zip(headers, parts[:len(headers)])))

    if not rows:
        raise ValueError(f"No data rows found in {path}")

    return pd.DataFrame(rows)


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
