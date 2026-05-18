"""Agentic adapter that resolves look-through holdings for synthetic ETFs.

Swap-based / synthetic UCITS ETFs (e.g. Amundi MSCI World Swap UCITS ETF,
LU1681043599) don't physically hold the index constituents. Their official
holdings page reports the *substitute basket* — counterparty collateral —
not the economic exposure. For portfolio-risk look-through, that is the
wrong number.

This source resolves the right number indirectly: it locates a physically-
replicated peer ETF tracking the same benchmark in our own pms_golden_fund
and copies its constituent holdings. Every copied row is stamped
``source: physical_proxy``; a top-level ``lookthroughProvenance`` block
records the proxy ISIN, benchmark match, snapshot date, and a deterministic
confidence rating (high/medium/low). Risk and compliance consumers can
filter on these fields without guessing.

Gating — the source returns ``None`` (no-op, no LLM call) when any of:

  * identifier kind isn't ISIN
  * ``assetAllocation.holdings`` already populated upstream
  * ``holdingsCount`` already set upstream
  * ``replicationMethod`` is not ``synthetic_swap``
  * no benchmark identifier or name in ``current``
  * pre-curated patch on disk (cache hit; loaded + returned without LLM)
  * ``ANTHROPIC_API_KEY`` unset
  * ``claude-agent-sdk`` not installed
  * any exception bubbles up from the SDK

The patch file shape mirrors ``fund_factsheet_patch``'s wrapper
(``{"doc": {...}, "_meta": {...}}``) so a curator can hand-write proxy
mappings under ``data/opensearch/golden/fund/patches/lookthrough/`` and
bypass the LLM entirely.

This source is cost-class ``llm_skill``. It runs only when the caller
opens the cost gate (via ``--enable-llm-skills`` on the CLI or
``max_cost_class="llm_skill"`` on the assemble API).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.agentic.merger import SourceFetchResult

log = logging.getLogger(__name__)

# Cache files live in a sub-directory of the existing factsheet patches
# location so curators can manage them independently.
PATCHES_DIR = Path("data/opensearch/golden/fund/patches/lookthrough")

# Replication methods, per the ontology enum
# (`ontology/securities/fund/Fund.yml` → `replicationMethod`).
SYNTHETIC_REPLICATION_VALUES = {"synthetic_swap"}
PHYSICAL_REPLICATION_VALUES = {"physical_full", "physical_sampling"}

# Surface the SDK lazily so the source module imports cleanly without the
# optional dependency installed (tests + minimal deployments).
try:  # pragma: no cover — import availability is environment-dependent
    from claude_agent_sdk import ClaudeAgentOptions, query as _sdk_query
    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    ClaudeAgentOptions = None  # type: ignore
    _sdk_query = None  # type: ignore
    _SDK_AVAILABLE = False


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],
) -> Optional[SourceFetchResult]:
    """Adapter entrypoint called by the planner.

    Order of checks (cheapest first):
      1. ISIN required.
      2. Predicate — short-circuit on populated holdings / wrong replication / no benchmark.
      3. On-disk patch cache — bypass LLM entirely.
      4. SDK + API key gates — required to actually run the proxy-ranking call.
      5. (Later tasks) — proxy lookup, LLM rank, patch build.
    """
    if identifier_kind != "isin":
        return None

    if not _predicate_passes(current, identifier_value):
        return None

    cached = _load_cached_patch(identifier_value)
    if cached is not None:
        return cached

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.debug("fund_lookthrough_skill skipped for %s: ANTHROPIC_API_KEY unset", identifier_value)
        return None
    if not _SDK_AVAILABLE:
        log.debug("fund_lookthrough_skill skipped for %s: claude-agent-sdk not installed", identifier_value)
        return None

    # Proxy lookup + LLM rank + patch construction land in subsequent tasks.
    # For now the skeleton stops here — the source predicate-and-cache half
    # is fully wired and unit-testable.
    return None


# ---------------------------------------------------------------------------
# Predicate
# ---------------------------------------------------------------------------

def _predicate_passes(current: Dict[str, Any], isin: str) -> bool:
    """Return True iff this fund is eligible for proxy-based look-through.

    Cheap in-memory check. No I/O, no LLM. Runs first so the source bails
    out without burning any cost when the fund isn't a synthetic ETF or
    when upstream sources already populated holdings.
    """
    asset_allocation = current.get("assetAllocation") or {}
    existing_holdings = asset_allocation.get("holdings") or []
    if existing_holdings:
        log.debug("fund_lookthrough_skill skipped for %s: holdings already populated", isin)
        return False

    if current.get("holdingsCount"):
        log.debug("fund_lookthrough_skill skipped for %s: holdingsCount already set", isin)
        return False

    rep = (current.get("replicationMethod") or "").lower()
    if rep not in SYNTHETIC_REPLICATION_VALUES:
        log.debug(
            "fund_lookthrough_skill skipped for %s: replicationMethod=%r not synthetic",
            isin, rep,
        )
        return False

    benchmark_id = current.get("benchmarkIdentifier")
    benchmark_name = current.get("benchmarkName")
    if not benchmark_id and not benchmark_name:
        log.debug("fund_lookthrough_skill skipped for %s: no benchmark identifier or name", isin)
        return False

    return True


# ---------------------------------------------------------------------------
# Patch cache
# ---------------------------------------------------------------------------

def _patch_path_for_isin(isin: str) -> Path:
    """Mirror the convention used by fund_factsheet_patch: FG-{ISIN}-001.json."""
    return PATCHES_DIR / f"FG-{isin}-001.json"


def _load_cached_patch(isin: str) -> Optional[SourceFetchResult]:
    """Read a pre-curated lookthrough patch from disk; return None if absent.

    The on-disk wrapper is ``{"doc": {...}, "_meta": {...}}`` — same shape
    as fund_factsheet_patch's cache. A cache hit completely bypasses the
    LLM call: curator-authored patches always win.
    """
    patch_file = _patch_path_for_isin(isin)
    if not patch_file.exists():
        return None

    try:
        payload = json.loads(patch_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("fund_lookthrough_skill: cached patch at %s unreadable: %s", patch_file, exc)
        return None

    patch = payload.get("doc") or {}
    if not patch:
        return None

    meta = payload.get("_meta") or {}
    source_label = meta.get("source") or "lookthrough-skill-cache"
    as_of = meta.get("sourceTimestamp")

    sot_rows: List[Dict[str, Any]] = []
    for top_field in patch.keys():
        sot_rows.append({
            "fieldGroup": top_field,
            "source": source_label,
            "asOf": as_of,
        })

    log.info(
        "fund_lookthrough_skill cache hit for %s: %d top-level fields from %s",
        isin, len(patch), patch_file.name,
    )
    return SourceFetchResult(patch=patch, source_of_truth_rows=sot_rows)
