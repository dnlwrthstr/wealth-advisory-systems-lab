# Specification: Lookthrough enhances factsheet top-N to full constituent list

<!-- FEATURE_DIR: 004-lookthrough-full-list -->
<!-- FEATURE_ID: 004 -->
<!-- SPEC_NUMBER: 002 -->
<!-- STATUS: clarified -->
<!-- SUPERSEDES: spec-001.md (placeholder skeleton) -->
<!-- CREATED: 2026-05-18T20:45:00Z -->

## Executive Summary

Closes the live-validation gap discovered during spec-003 T011b: for synthetic / swap-based UCITS ETFs where the issuer publishes proper index composition (rather than the substitute basket), `fund_factsheet_skill` correctly extracts a **top-N projection** of holdings (e.g. 10 rows out of `holdingsCount=1310` for the MSCI World). The lookthrough skill's predicate short-circuits on "holdings already populated," so the proxy-fallback never fires, and consumers never see the full constituent list — the very thing a physically-replicated peer ETF (iShares Core MSCI World) publishes daily.

Two-part design change:

1. **Predicate refinement** in `fund_lookthrough_skill` — fire when `len(assetAllocation.holdings) < holdingsCount`, not just when holdings are empty. The intent flips from "fill an empty slot" to "complete a partial list."
2. **Marker-based list replacement** on the merger — add `replace_paths: List[str] = []` to `SourceFetchResult`. A source declares the dot-paths whose list values should override fill-empty-only semantics. Lookthrough sets `replace_paths=["assetAllocation.holdings"]` so its full constituent list wins over the existing top-N. All other sources are unaffected.

Net behavioural change on the canonical test case (Amundi MSCI World Swap LU1681043599):

| Before | After |
|---|---|
| `assetAllocation.holdings` = top-10 from Amundi's page | `assetAllocation.holdings` = ~1310 from the iShares physical proxy |
| `lookthroughProvenance` = `null` | `lookthroughProvenance.proxyIsin` = `IE00B4L5Y983`, `confidence=high\|medium\|low` |
| Risk look-through under-counts exposure by ~99% of constituents | Risk look-through is complete (modulo proxy data freshness) |

What stays the same: the merger's deep fill-empty-only semantic everywhere `replace_paths` does NOT cover; all four existing fund sources keep their current behaviour; the chain order is unchanged.

## Description

### Part 1 — Predicate refinement

`src/pipeline/agentic/sources/fund_lookthrough_skill.py`, function `_predicate_passes`:

```python
# Today (spec-003):
existing_holdings = (current.get("assetAllocation") or {}).get("holdings") or []
if existing_holdings:
    return False
if current.get("holdingsCount"):
    return False

# Proposed (this spec):
existing_holdings = (current.get("assetAllocation") or {}).get("holdings") or []
declared_count = current.get("holdingsCount") or 0
if existing_holdings and declared_count and len(existing_holdings) >= declared_count:
    return False        # we already have the full list
# else: empty OR strict top-N subset → lookthrough is eligible
```

Skip cases that stay unchanged: non-ISIN identifiers, missing `replicationMethod`, `replicationMethod` not in `{synthetic_swap}`, no benchmark identifier/name.

Edge case: if `holdingsCount` is null but `holdings` is non-empty, treat as "complete enough" (the source isn't claiming more than it shipped). Predicate skips. This preserves the spec-003 behaviour on funds where factsheet returned a definitive list without a count.

### Part 2 — Merger: marker-based list replacement

`src/pipeline/agentic/merger.py`:

```python
@dataclass(frozen=True)
class SourceFetchResult:
    patch: Dict[str, Any]
    source_of_truth_rows: List[Dict[str, Any]] = field(default_factory=list)
    replace_paths: List[str] = field(default_factory=list)   # ← NEW
```

`merge_patch` signature unchanged; a thin wrapper threads `replace_paths` through:

```python
def merge_patch(current, patch, *, replace_paths=()):
    return _merge(current, patch, "", set(replace_paths))

def _merge(current, patch, prefix, replace_paths):
    written = []
    for field_name, value in patch.items():
        path = f"{prefix}.{field_name}" if prefix else field_name
        if value in (None, "", [], {}):
            continue
        existing = current.get(field_name)
        if path in replace_paths and isinstance(value, list):
            current[field_name] = value      # full replace, regardless of existing
            written.append(path)
            continue
        if isinstance(value, dict) and isinstance(existing, dict) and existing:
            written.extend(_merge(existing, value, path, replace_paths))
            continue
        if existing in (None, "", [], {}):
            current[field_name] = value
            written.append(path)
    return written
```

Constraints on `replace_paths`:
- Only applies when the patch's value at that path is a `list`. A `replace_paths` entry pointing at a dict is a no-op (no semantic change).
- Empty list as a patch value still no-ops (existing behaviour — never write nothing over something).
- Paths are dot-separated and resolve against the FundGolden (or scope-equivalent) shape. Invalid paths are silently no-ops; tests cover this.

Planner change (`src/pipeline/agentic/planner.py`): pass `result.replace_paths` into the `merge_patch` call. The existing `written_top` computation already extracts top-level prefixes correctly for the trace.

### Part 3 — Lookthrough patch shape update

`fund_lookthrough_skill._build_patch` returns the same patch as before but the `SourceFetchResult` now declares:

```python
return SourceFetchResult(
    patch={...},                            # unchanged
    source_of_truth_rows=[...],             # unchanged
    replace_paths=["assetAllocation.holdings"],   # NEW — full replace
)
```

Note: `holdingsCount` and `holdingsAsOf` continue to merge via fill-empty-only — they're top-level scalars, and the existing top-N source's values are typically already-correct counts. If factsheet wrote `holdingsCount=1310` and lookthrough's proxy also has 1310, the existing slot is non-empty and the merger preserves factsheet's row. Acceptable; consumers see the same number either way.

## Functional Requirements

### FR-1 — Predicate refinement

- [ ] `_predicate_passes` returns `True` when `replicationMethod=synthetic_swap`, benchmark known, AND `len(existing_holdings) < declared_count`.
- [ ] `_predicate_passes` returns `False` when `existing_holdings` is empty AND `declared_count` is null/0 (unchanged from spec-003 — no benchmark guidance).
- [ ] `_predicate_passes` returns `False` when `len(existing_holdings) >= declared_count` (we already have the full list).
- [ ] All other skip cases unchanged: non-ISIN identifier, missing/non-synthetic `replicationMethod`, missing benchmark.

### FR-2 — Merger marker semantics

- [ ] `SourceFetchResult` gains optional `replace_paths: List[str]` (default empty).
- [ ] `merge_patch` accepts a `replace_paths` set and, for each path in it, performs a full replace of the patch's list value over the existing list (even when existing is non-empty).
- [ ] `replace_paths` entries pointing at non-list patch values are no-ops.
- [ ] Empty/null patch values are still skipped at every level (no inadvertent zero-out).
- [ ] Sources that don't set `replace_paths` see identical behaviour to spec-003 (deep fill-empty-only at every level).

### FR-3 — Planner threads the marker

- [ ] `run_planner` reads `result.replace_paths` from each `SourceFetchResult` and passes it to `merge_patch`.
- [ ] The trace's `fields_written` carries dot-paths for replaced lists (already supported by the existing dot-path output).

### FR-4 — Lookthrough source uses the marker

- [ ] `fund_lookthrough_skill._build_patch` returns `replace_paths=["assetAllocation.holdings"]`.
- [ ] No other source in any scope sets `replace_paths` in V1.

### FR-5 — Provenance row clarity

- [ ] When lookthrough replaces an existing holdings list, the `recordMeta.sourceOfTruth` row for `assetAllocation.holdings` reflects `fund_lookthrough_skill` as the new authoritative source. The previous source row from factsheet is retained for audit (sourceOfTruth is append-only by convention; consumers reading "latest" use list order).

### Non-Functional Requirements

- **Performance**: predicate is in-memory dict checks; no new I/O. Merger change is `path in replace_paths` lookup per field — O(1). No runtime cost.
- **Reliability**: empty `replace_paths` (the default) preserves spec-003 behaviour byte-for-byte across the existing 235+ tests.
- **Reproducibility**: `_replace`-marked writes are deterministic from `(source.replace_paths, patch.value)`; no LLM-creativity surface introduced.
- **Cost**: lookthrough's LLM call cost unchanged from spec-003 (~$0.02 per fire). Patches under `data/opensearch/golden/fund/patches/lookthrough/` continue to cache LLM output.

## User Stories

- **US-1** — As a portfolio risk analyst, when I assemble Amundi MSCI World Swap (LU1681043599) with LLM skills enabled, I want the persisted record's `assetAllocation.holdings` to carry the **full ~1310** MSCI World constituents (from the iShares physical-proxy fallback), every row stamped `source: physical_proxy`, so my factor model sees the right economic exposure rather than a top-10 projection.
- **US-2** — As a data engineer, when factsheet has already produced the complete constituent list for a given fund (e.g. a small target-date fund where the issuer publishes all 80 holdings and `holdingsCount=80`), I want the lookthrough skill to NOT fire — no wasted LLM call, no risk of replacing accurate factsheet data with proxy data.
- **US-3** — As an auditor inspecting `recordMeta.sourceOfTruth`, when I look at a record where lookthrough replaced factsheet's holdings, I want both source attributions present in the trail (factsheet wrote first, lookthrough overrode) so I can reconstruct what happened.

## Acceptance Criteria

- [ ] **AC-1** Given a synthetic ETF (LU1681043599) where `fund_factsheet_skill` already populated `assetAllocation.holdings` with a top-10 projection and `holdingsCount=1310`, when I `POST /instruments/assemble {persist:true, invoke_llm_skills:true}`, then the persisted record's `holdings.length` ≥ 50 (proxy provided substantially more than 10), every row carries `source: "physical_proxy"`, and `lookthroughProvenance.proxyIsin` matches the iShares MSCI World ISIN seeded in the index.
- [ ] **AC-2** Given a fund where `fund_factsheet_skill` populated `holdings.length == holdingsCount` (complete list), when I assemble with LLM skills enabled, then `fund_lookthrough_skill` returns no_data (predicate short-circuits) and the persisted `holdings` is unchanged.
- [ ] **AC-3** Given a synthetic ETF where `holdingsCount` is null but `assetAllocation.holdings` is populated, when I assemble, then lookthrough returns no_data (we don't override an apparently-complete factsheet output without a contradicting count).
- [ ] **AC-4** Given the same conditions as AC-1, when I re-run the assemble immediately (idempotency), then `assetAllocation.holdings` is byte-identical to the first run (proxy didn't refresh, fill-empty-only on `lookthroughProvenance` short-circuits the predicate the second time).
- [ ] **AC-5** Given a non-lookthrough source patch with no `replace_paths` set, when the merger applies it over a current state with a non-empty list at the same path, then the existing list wins (spec-003 fill-empty-only behaviour preserved).
- [ ] **AC-6** Given `merge_patch` called with `replace_paths=["a.b"]` but patch value at `a.b` is a dict (not a list), then the merger ignores the directive and falls back to deep-merge — defensive against accidental marker misuse.
- [ ] **AC-7** Given lookthrough fires and replaces factsheet's holdings, when I inspect `recordMeta.sourceOfTruth`, then I see two rows for `fieldGroup=assetAllocation.holdings` — first the factsheet attribution, then the lookthrough attribution — in append order.

## Technical Constraints

### In scope

- Scope=fund only (lookthrough is fund-scoped).
- Predicate refinement in `fund_lookthrough_skill._predicate_passes`.
- Merger gains optional `replace_paths` parameter; `SourceFetchResult` gains the field; planner threads it through.
- Provenance rows append (don't deduplicate).
- Backward-compatible: `replace_paths=None` (default) preserves spec-003 behaviour.

### Out of scope

- Length-aware automatic merge (no `if len(patch) > len(existing): replace` logic — explicitly rejected via clarification 2).
- Cross-scope use of `replace_paths` (equity / bond / issuer sources continue to use fill-empty-only).
- Stale-proxy refresh: re-running assemble doesn't re-fetch the proxy's holdings; existing `lookthroughProvenance` short-circuits via the predicate. Refresh is a separate "stale-data sweep" concern.
- Frontend changes — the existing "Look-through" badge from spec-003 surfaces the result correctly with the larger list.
- Ontology changes — `replace_paths` lives on the source contract, not on FundGolden.

### Dependencies

- **External**: none new. No new requirements.txt additions.
- **Database**: no schema changes.
- **Tests**: existing test_merger.py + test_fund_lookthrough_skill.py extended.

### Implementation notes

- The marker is `replace_paths: List[str]`, NOT a set, in the `SourceFetchResult` dataclass — `field(default_factory=list)` is the standard pydantic-compatible default. The merger internally converts to `set` for O(1) lookup.
- Path semantics: dot-separated, prefixes match the merger's recursion depth. So `"assetAllocation.holdings"` matches the holdings field inside the assetAllocation dict, not a top-level field named "assetAllocation.holdings".
- The merger does NOT propagate `replace_paths` to nested recursion frames (the path equality check happens at each level via the running prefix).
- No new methods on `SourceFetchResult`; callers use positional or keyword args directly.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `replace_paths` accidentally set by a future source that shouldn't fully replace | Low | Medium | V1 has exactly one source using it; review checks for new `replace_paths=` declarations. Tests cover empty `replace_paths` (default) preserving spec-003 behaviour. |
| Predicate refinement makes lookthrough fire on funds where it shouldn't (e.g. close-to-complete top-N where factsheet's holdingsCount was over-stated) | Medium | Low | LLM-skill cost is bounded by the cache hit path: re-runs against the same ISIN are free. AC-2/AC-3 cover the non-firing cases. |
| Provenance trail confusion — two rows for the same fieldGroup | Low | Low | Documented append-only convention; AC-7 locks the trail shape; UI/audit consumers read newest by list order. |
| Merger change breaks an existing source whose patches incidentally rely on shallow override | Low | Medium | Default `replace_paths=()` makes the new code path entirely opt-in. Full pytest sweep on every change. |
| Proxy data on the iShares MSCI World ETF goes stale relative to the synthetic ETF being assembled | Medium | Low | `lookthroughProvenance.asOfDate` carries the proxy's snapshot date verbatim; downstream consumers decide staleness thresholds. Same risk surface as spec-003. |
| Live AC-1 needs an iShares ETF seeded with non-empty holdings — environmental concern | Medium | Low | Phase 5 task spells out the seeding step (run factsheet skill on the host for an iShares MSCI World ISIN). Cached once; subsequent runs free. |

## Testing Strategy

- **Unit tests — predicate** (`tests/agentic/test_fund_lookthrough_skill.py`):
  - `test_predicate_fires_when_existing_holdings_are_strict_subset_of_holdingsCount` — 10 holdings, holdingsCount=1310 → predicate passes.
  - `test_predicate_skips_when_existing_holdings_equal_holdingsCount` — 80 holdings, holdingsCount=80 → predicate skips.
  - `test_predicate_skips_when_holdingsCount_is_null_but_holdings_populated` — top-10, holdingsCount=null → predicate skips.
  - Existing tests (empty holdings, physical replication, missing benchmark, etc.) continue to pass unchanged.
- **Unit tests — merger** (`tests/agentic/test_merger.py`):
  - `test_replace_paths_overrides_existing_list` — current has 10-row list at `a.b`, patch has 100-row list at `a.b` with `replace_paths={"a.b"}` → current ends with 100 rows.
  - `test_replace_paths_no_op_on_dict_value` — current has dict at `a.b`, patch has dict with `replace_paths={"a.b"}` → falls back to deep-merge.
  - `test_replace_paths_does_not_affect_other_paths` — patch with `replace_paths={"a.b"}` but also touches `a.c` → `a.c` follows fill-empty-only.
  - `test_replace_paths_empty_default_preserves_spec_003_behavior` — replay one of the existing spec-003 merger tests with explicit `replace_paths=()` → identical result.
- **Integration tests** (`tests/agentic/test_assemble_fund.py`):
  - `test_lookthrough_replaces_factsheet_top_n` — simulate the canonical case end-to-end with mocked sources.
  - `test_lookthrough_does_not_fire_on_complete_factsheet_holdings` — locks AC-2.
- **Live verification** (Phase 5):
  - Pre-step: assemble an iShares MSCI World ISIN on the host (e.g. IE00B4L5Y983), persisting → seeds a physical proxy with non-empty holdings via the factsheet skill that spec-003 already validated.
  - AC-1 live: re-assemble LU1681043599 with LLM skills → verify `holdings.length` jump and `lookthroughProvenance.proxyIsin` populated.

## Definition of Done

- [x] FR-1 through FR-5 implemented.
- [x] AC-2, AC-3, AC-5, AC-6, AC-7 met via unit + integration tests.
- [ ] **AC-1 + AC-4 live verification deferred** — docker stack was unresponsive during the rebuild + recreate cycle. Mocked integration tests in T006 (`test_lookthrough_replaces_factsheet_top_n`, `test_lookthrough_does_not_fire_on_complete_factsheet_holdings`) prove the chain end-to-end at the code level. To be re-run by the user post-merge.
- [x] `SourceFetchResult.replace_paths` added to the merger dataclass.
- [x] `merge_patch` honours `replace_paths` and remains backward-compatible (explicit `replace_paths=()` regression-lock test).
- [x] `fund_lookthrough_skill._build_patch` declares `replace_paths=["assetAllocation.holdings"]`.
- [x] `tests/agentic/test_merger.py` and `tests/agentic/test_fund_lookthrough_skill.py` cover the new behaviour.
- [x] `src/pipeline/agentic/README.md` "Merge policy" section gains a paragraph on `replace_paths`.
- [x] `pytest` green: **273/273** (baseline 263 + 5 merger + 4 lookthrough + 2 integration − 1 obsolete).
- [ ] Branch `feat/lookthrough-full-list` merged into `main` via PR.

## Clarifications (resolved 2026-05-18)

1. ✅ **CLARIFIED — Marker placement**: `SourceFetchResult.replace_paths: List[str]`. Keeps the patch dict pure-data; directive lives at the source-contract level; easy to type-validate; merger reads it from the result envelope.
2. ✅ **CLARIFIED — Length-aware automatic merge is rejected**: a list is replaced ONLY when the source explicitly opts in via `replace_paths`. No `if len(patch) > len(existing)` heuristic — too magical, changes semantics for every source, surprises downstream consumers.
3. ✅ **CLARIFIED — Phase 5 seed approach**: run `fund_factsheet_skill` on the host for an iShares MSCI World ISIN (e.g. IE00B4L5Y983). The skill now works end-to-end after spec-003 PR #9, and the resulting patch is cached for free re-use. No new repo fixtures, no synthetic seed file.
4. ✅ **CLARIFIED — Marker scope**: applies at the list-value level only, on a specific dot-path. Dict / scalar values at the same path remain governed by deep-merge / fill-empty-only.

### Deferred to a future iteration (NOT blocking V1)

- Proxy-data refresh on subsequent runs (re-fetching when `lookthroughProvenance.asOfDate` is stale).
- Cross-scope `replace_paths` use (e.g. equity sources with shared identifier lists).
- A higher-confidence source (`index_provider` direct ingestion) that doesn't need a peer ETF as proxy.

---

*Generated by /sp-spec on 2026-05-18. Supersedes spec-001.md (placeholder). Closes the live-validation gap discovered during spec-003 T011b. Recommended next step: /sp-plan.*
