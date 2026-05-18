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

    client = _opensearch_client()
    if client is None:
        log.debug("fund_lookthrough_skill skipped for %s: OPENSEARCH_URL unset", identifier_value)
        return None

    candidates, reason = _find_proxy_candidates(client, current, identifier_value)
    if not candidates:
        log.info(
            "fund_lookthrough_skill found no proxy for %s: reason=%s",
            identifier_value, reason,
        )
        return None

    pick = _pick_proxy_via_llm(current, candidates, identifier_value)
    if pick is None:
        return None

    confidence = _derive_confidence(current, pick)
    result = _build_patch(pick, confidence)
    log.info(
        "fund_lookthrough_skill resolved %s: proxy=%s confidence=%s holdings=%d",
        identifier_value,
        pick.get("identifierList", [{}])[0].get("identifier", "?")
            if pick.get("identifierList") else pick.get("goldenId", "?"),
        confidence,
        len((pick.get("assetAllocation") or {}).get("holdings") or []),
    )
    return result


# ---------------------------------------------------------------------------
# LLM ranking
# ---------------------------------------------------------------------------

_LLM_PROMPT_TEMPLATE = """You are matching a synthetic (swap-based) ETF to a physically-replicated peer
that tracks the same benchmark, so that the synthetic ETF's economic exposure
can be approximated by the peer's holdings.

Target fund (synthetic):
{target}

Candidate physical peers (ranked by holdings recency):
{candidates}

Return ONLY a JSON object with these keys, no prose:
  picked_isin   — the ISIN of the best peer from the candidate list
  rationale     — one sentence (max 140 chars) explaining the choice

Prefer exact benchmark identifier matches over name matches; among ties,
prefer the most recent `holdingsAsOf`. If no candidate is a reasonable
peer, pick the closest one anyway — confidence will be derived separately.
"""


def _pick_proxy_via_llm(
    current: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    target_isin: str,
) -> Optional[Dict[str, Any]]:
    """Ask the LLM to pick the single best proxy. Returns the candidate dict.

    Output contract is small + strict: `{picked_isin, rationale}`. The LLM
    never emits confidence — that's derived deterministically post-hoc.
    """
    target_summary = {
        "isin": target_isin,
        "longName": current.get("longName"),
        "benchmarkName": current.get("benchmarkName"),
        "benchmarkIdentifier": current.get("benchmarkIdentifier"),
        "replicationMethod": current.get("replicationMethod"),
        "currency": current.get("currencyOfDenomination"),
    }
    candidate_summaries = [
        {
            "isin": _isin_of(c),
            "goldenId": c.get("goldenId"),
            "longName": c.get("longName"),
            "benchmarkName": c.get("benchmarkName"),
            "benchmarkIdentifier": c.get("benchmarkIdentifier"),
            "replicationMethod": c.get("replicationMethod"),
            "holdingsAsOf": c.get("holdingsAsOf"),
            "holdingsCount": c.get("holdingsCount"),
        }
        for c in candidates
    ]

    prompt = _LLM_PROMPT_TEMPLATE.format(
        target=json.dumps(target_summary, indent=2),
        candidates=json.dumps(candidate_summaries, indent=2),
    )

    try:
        text = _run_sdk(prompt)
    except Exception as exc:  # noqa: BLE001 — SDK errors vary
        log.warning(
            "fund_lookthrough_skill: LLM call failed for %s: %s (reason=llm_unavailable)",
            target_isin, exc,
        )
        return None

    parsed = _parse_llm_pick(text)
    if not parsed or not parsed.get("picked_isin"):
        log.warning(
            "fund_lookthrough_skill: LLM returned malformed JSON for %s: %r (reason=llm_invalid_pick)",
            target_isin, (text or "")[:200],
        )
        return None

    picked_isin = parsed["picked_isin"]
    for c in candidates:
        if _isin_of(c) == picked_isin:
            return c

    log.warning(
        "fund_lookthrough_skill: LLM picked %s for %s but it's not in the candidate list (reason=llm_invalid_pick)",
        picked_isin, target_isin,
    )
    return None


def _run_sdk(prompt: str) -> str:
    """Invoke claude-agent-sdk and return the concatenated text output."""
    import asyncio

    async def _go() -> str:
        chunks: List[str] = []
        options = ClaudeAgentOptions(cwd=str(Path.cwd()))
        async for message in _sdk_query(prompt=prompt, options=options):
            # Each message carries a `.content` list of blocks; concatenate
            # any text blocks. Defensive against shape drift.
            content = getattr(message, "content", None) or []
            for block in content:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)

    return asyncio.run(_go())


def _parse_llm_pick(text: str) -> Optional[Dict[str, Any]]:
    """Extract the JSON object the LLM was asked to emit.

    The model may wrap the JSON in backticks or include prose around it; be
    tolerant — find the first balanced `{...}` block and json.loads it.
    """
    if not text:
        return None
    # Find first '{' and the matching close. Bounded by lenient indexing —
    # this is a tiny payload, no need for a full parser.
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _isin_of(record: Dict[str, Any]) -> Optional[str]:
    """Extract the ISIN from a FundGolden record's identifierList."""
    for entry in record.get("identifierList") or []:
        if (entry.get("type") or "").lower() == "isin":
            return entry.get("identifier")
    return None


# ---------------------------------------------------------------------------
# Post-hoc confidence derivation (deterministic — no LLM input)
# ---------------------------------------------------------------------------

def _derive_confidence(current: Dict[str, Any], picked: Dict[str, Any]) -> str:
    """Classify match quality from objective fields. high | medium | low.

    Per spec-003 resolution 7: the LLM does NOT emit confidence. The rating
    is computed deterministically so it's reproducible from the candidate
    set and immune to LLM creativity.
    """
    cur_id = current.get("benchmarkIdentifier")
    pick_id = picked.get("benchmarkIdentifier")
    if cur_id and pick_id and cur_id == pick_id:
        return "high"

    cur_name = (current.get("benchmarkName") or "").strip().lower()
    pick_name = (picked.get("benchmarkName") or "").strip().lower()
    if cur_name and pick_name and cur_name == pick_name:
        return "medium"

    return "low"


# ---------------------------------------------------------------------------
# Patch construction
# ---------------------------------------------------------------------------

def _build_patch(picked: Dict[str, Any], confidence: str) -> SourceFetchResult:
    """Compose the SourceFetchResult to hand back to the planner.

    Patch shape (top-level keys the deep-merger writes into ``current``):
      * ``assetAllocation`` — only the ``holdings`` sub-key is supplied;
        the merger deep-merges into any pre-existing sector / asset-class
        / region buckets from fund_yahoo.
      * ``holdingsCount``, ``holdingsAsOf`` — flat top-level scalars.
      * ``lookthroughProvenance`` — the proxy lineage block.

    Every holdings row is deep-copied and stamped ``source: physical_proxy``
    so risk consumers can filter on it.
    """
    raw_holdings = (picked.get("assetAllocation") or {}).get("holdings") or []
    stamped_holdings: List[Dict[str, Any]] = []
    for row in raw_holdings:
        new_row = dict(row)
        new_row["source"] = "physical_proxy"
        stamped_holdings.append(new_row)

    holdings_as_of = picked.get("holdingsAsOf")
    proxy_isin = _isin_of(picked)

    patch: Dict[str, Any] = {
        "assetAllocation": {"holdings": stamped_holdings},
        "holdingsCount": picked.get("holdingsCount") or len(stamped_holdings),
        "lookthroughProvenance": {
            "method": "physical_proxy",
            "proxyIsin": proxy_isin,
            "proxyGoldenId": picked.get("goldenId"),
            "proxyName": picked.get("longName"),
            "benchmarkIdentifier": picked.get("benchmarkIdentifier"),
            "benchmarkName": picked.get("benchmarkName"),
            "asOfDate": holdings_as_of,
            "confidence": confidence,
        },
    }
    if holdings_as_of:
        patch["holdingsAsOf"] = holdings_as_of

    sot_rows = [
        {
            "fieldGroup": "assetAllocation.holdings",
            "source": "fund_lookthrough_skill",
            "method": "physical_proxy",
            "proxyIsin": proxy_isin,
            "confidence": confidence,
        },
        {"fieldGroup": "holdingsCount", "source": "fund_lookthrough_skill"},
        {"fieldGroup": "lookthroughProvenance", "source": "fund_lookthrough_skill"},
    ]
    if holdings_as_of:
        sot_rows.append({"fieldGroup": "holdingsAsOf", "source": "fund_lookthrough_skill"})

    # spec 004: opt into list-replacement at assetAllocation.holdings so that a
    # factsheet-supplied top-N projection (e.g. 10 rows of MSCI World) is
    # replaced by the proxy's full constituent list (~1310 rows). Without this,
    # the merger's deep fill-empty-only would preserve the top-N and silently
    # drop the proxy's expanded list.
    return SourceFetchResult(
        patch=patch,
        source_of_truth_rows=sot_rows,
        replace_paths=["assetAllocation.holdings"],
    )


# ---------------------------------------------------------------------------
# OpenSearch client + proxy lookup
# ---------------------------------------------------------------------------

def _opensearch_client():
    """Lazy-construct the OpenSearch client. Returns None if env is unset."""
    try:
        from instruments.opensearch_store import opensearch_client_from_env
    except ImportError:  # pragma: no cover
        return None
    return opensearch_client_from_env()


def _find_proxy_candidates(
    client: Any,
    current: Dict[str, Any],
    current_isin: str,
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """Search pms_golden_fund for physically-replicated peers tracking the
    same benchmark.

    Returns ``(candidates, reason)``:
      * candidates is the list of physical-fund records (top-N by holdings
        recency) with non-empty `assetAllocation.holdings`.
      * reason is None on success. On empty result it distinguishes:
        - "proxy_search_empty" — the index has no physical funds at all
          (cold start; need to seed the universe).
        - "no_physical_proxy_in_universe" — physical funds exist but none
          match this benchmark.

    Uses at most two OpenSearch queries: the primary (with benchmark
    filter), and on empty primary, a broader probe (without benchmark).
    """
    primary = _proxy_query(current, current_isin, include_benchmark=True)
    primary_hits = _run_search(client, primary)
    primary_hits = _filter_non_empty_holdings(primary_hits)
    if primary_hits:
        return primary_hits, None

    # Distinguish cold start vs no-peer-for-this-benchmark.
    broader = _proxy_query(current, current_isin, include_benchmark=False)
    broader_hits = _run_search(client, broader)
    broader_hits = _filter_non_empty_holdings(broader_hits)
    if not broader_hits:
        return [], "proxy_search_empty"
    return [], "no_physical_proxy_in_universe"


def _proxy_query(
    current: Dict[str, Any],
    current_isin: str,
    *,
    include_benchmark: bool,
) -> Dict[str, Any]:
    """Compose the OpenSearch query body for the proxy search.

    Benchmark name match is the primary discriminator (the iShares MSCI
    World patch carries `benchmarkName` but null `benchmarkIdentifier`,
    so we can't rely on identifier-exact). When current carries a
    `benchmarkIdentifier`, it's added as a stricter `should` clause that
    raises the score for exact-identifier matches — but is not required.
    """
    must: List[Dict[str, Any]] = []
    if include_benchmark:
        should: List[Dict[str, Any]] = []
        bench_name = current.get("benchmarkName")
        if bench_name:
            should.append({"match": {"benchmarkName": bench_name}})
        bench_id = current.get("benchmarkIdentifier")
        if bench_id:
            should.append({"term": {"benchmarkIdentifier.keyword": bench_id}})
        must.append({"bool": {"should": should, "minimum_should_match": 1}})

    body: Dict[str, Any] = {
        "size": 10,
        "query": {
            "bool": {
                "must": must,
                "filter": [
                    {"terms": {"replicationMethod": sorted(PHYSICAL_REPLICATION_VALUES)}},
                    {"exists": {"field": "assetAllocation.holdings"}},
                ],
                "must_not": [
                    {"term": {"identifierList.identifier.keyword": current_isin}},
                ],
            },
        },
        "sort": [
            {"holdingsAsOf": {"order": "desc", "missing": "_last", "unmapped_type": "date"}},
        ],
    }
    if not must:
        # bool query needs something — `match_all` keeps the filter+must_not
        # clauses meaningful when no benchmark clause is set.
        body["query"]["bool"]["must"] = [{"match_all": {}}]
    return body


def _run_search(client: Any, body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute the query against pms_golden_fund and return _source dicts."""
    try:
        response = client.search(index="pms_golden_fund", body=body)
    except Exception as exc:  # noqa: BLE001 — OpenSearch errors vary
        log.warning("fund_lookthrough_skill: OpenSearch query failed: %s", exc)
        return []
    return [hit.get("_source") or {} for hit in response.get("hits", {}).get("hits", [])]


def _filter_non_empty_holdings(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop records whose `assetAllocation.holdings` is empty.

    OpenSearch's `exists` check returns true for empty arrays under some
    mappings — this Python-side filter is a safety net so we don't waste
    an LLM call on a "candidate" with no actual holdings to copy.
    """
    return [
        r for r in records
        if (r.get("assetAllocation") or {}).get("holdings")
    ]


# ---------------------------------------------------------------------------
# Predicate
# ---------------------------------------------------------------------------

def _predicate_passes(current: Dict[str, Any], isin: str) -> bool:
    """Return True iff this fund is eligible for proxy-based look-through.

    Cheap in-memory check. No I/O, no LLM. Runs first so the source bails
    out without burning any cost when the fund isn't a synthetic ETF or
    when upstream sources already populated the full constituent list.

    Spec 004 refinement: fire when factsheet's holdings are a strict
    subset of the declared `holdingsCount` — e.g. top-10 of 1310 MSCI
    World constituents. Skip when holdings are already complete
    (`len >= holdingsCount`) or when factsheet didn't declare a count
    (we treat that as "factsheet thinks it's done" — defensive).
    """
    asset_allocation = current.get("assetAllocation") or {}
    existing_holdings = asset_allocation.get("holdings") or []
    declared_count = current.get("holdingsCount") or 0

    if existing_holdings and declared_count and len(existing_holdings) >= declared_count:
        log.debug(
            "fund_lookthrough_skill skipped for %s: holdings already complete (%d/%d)",
            isin, len(existing_holdings), declared_count,
        )
        return False
    if existing_holdings and not declared_count:
        log.debug(
            "fund_lookthrough_skill skipped for %s: holdings populated without holdingsCount — treating as complete",
            isin,
        )
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
