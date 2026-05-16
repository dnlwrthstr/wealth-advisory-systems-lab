"""Agentic adapter that loads pre-curated fund factsheet patches.

The `find-and-parse-factsheet` Claude Code skill — an LLM-assisted
process — locates a fund's PRIIPS KID / KIID / factsheet PDF, parses
the long-tail static fields (TER beyond yfinance, SRRI/SRI, fees,
dealing terms, service providers, replication method, benchmark, …)
and writes the result to:

  data/opensearch/golden/fund/patches/FG-{ISIN}-001.json

  { "doc": { …field-level patches… },
    "_meta": { "source": "…", "sourceTimestamp": "…" } }

This source reads that file when the agentic loop runs, returning its
`doc` as a FundGolden patch with the `_meta` lifted into provenance.
The LLM-curated long tail becomes a regular agentic source — no LLM
runtime inside the assemble loop, just on-disk results from prior
skill runs.

Future iteration: trigger the skill on demand if the patch file is
missing. For now, missing patch → source returns None → planner moves on.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult

log = logging.getLogger(__name__)

# Mirrors the convention used by `pipeline.gold.apply_fund_patch` and the
# find-and-parse-factsheet skill: one JSON file per goldenId.
PATCHES_DIR = Path("data/opensearch/golden/fund/patches")


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],  # noqa: ARG001
) -> Optional[SourceFetchResult]:
    if identifier_kind != "isin":
        return None
    patch_path = _patch_path_for_isin(identifier_value)
    if not patch_path.exists():
        return None
    try:
        payload = json.loads(patch_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("factsheet patch unreadable at %s: %s", patch_path, exc)
        return None

    patch = payload.get("doc") or {}
    if not patch:
        return None

    meta = payload.get("_meta") or {}
    source_label = meta.get("source") or "factsheet-skill"
    source_ts = meta.get("sourceTimestamp")
    sot_rows = [
        _row(field, source_label, source_ts)
        for field in patch.keys()
    ]
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)


def _patch_path_for_isin(isin: str) -> Path:
    """FundGolden goldenId convention: FG-{ISIN}-001."""
    return PATCHES_DIR / f"FG-{isin}-001.json"


def _row(field_group: str, source: str, source_timestamp: Optional[str]) -> Dict[str, str]:
    out = {"fieldGroup": field_group, "source": source}
    if source_timestamp:
        out["sourceTimestamp"] = source_timestamp
    return out
