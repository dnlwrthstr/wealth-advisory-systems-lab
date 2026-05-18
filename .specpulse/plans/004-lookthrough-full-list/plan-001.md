# Implementation Plan: Lookthrough enhances factsheet top-N to full constituent list

<!-- FEATURE_DIR: 004-lookthrough-full-list -->
<!-- FEATURE_ID: 004 -->
<!-- PLAN_NUMBER: 001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T21:00:00Z -->

## Specification Reference

- **Spec**: `.specpulse/specs/004-lookthrough-full-list/spec-002.md` (status: clarified)
- **Plan Version**: 1.0
- **Builds on**: spec-003 (merged via PR #6) — `fund_lookthrough_skill` exists with strict "holdings empty" predicate; deep-merge merger from spec-003 T002 in place.

## Architecture Overview

### High-Level Design

```
   Today (spec-003)                          After spec-004
   ─────────────────                          ──────────────
   merge_patch(current, patch)                merge_patch(current, patch, *, replace_paths=())
        ↓                                            ↓
   deep fill-empty-only at every            same as before, EXCEPT for dot-paths
   nested-dict level; lists atomic          listed in replace_paths whose patch
                                            value is a list — those override.

   SourceFetchResult(patch, sot_rows)        SourceFetchResult(patch, sot_rows,
                                                                replace_paths=[])

   fund_lookthrough_skill._predicate_passes:
     skip if existing_holdings non-empty       skip only if existing_holdings
     skip if holdingsCount set                 already cover declared holdingsCount

   fund_lookthrough_skill._build_patch:
     returns SourceFetchResult                returns SourceFetchResult with
                                              replace_paths=["assetAllocation.holdings"]

   planner.run_planner:
     written = merge_patch(current, result.patch)
                                              written = merge_patch(
                                                  current, result.patch,
                                                  replace_paths=result.replace_paths,
                                              )
```

The change surface is tight: 3 files in `src/pipeline/agentic/`, plus 3 test files. No ontology changes, no HTTP schema changes, no frontend changes.

### Technical Stack

Unchanged from spec-003: Python 3.x, pydantic, pytest, `claude-agent-sdk` runtime (only the lookthrough source touches it). No new requirements.txt additions.

### Key Files

**Modified:**
- `src/pipeline/agentic/merger.py` — `SourceFetchResult` gains `replace_paths: List[str]`; `merge_patch` accepts a `replace_paths` keyword.
- `src/pipeline/agentic/planner.py` — `run_planner` passes `result.replace_paths` into `merge_patch`.
- `src/pipeline/agentic/sources/fund_lookthrough_skill.py` — `_predicate_passes` refined; `_build_patch` returns `replace_paths=["assetAllocation.holdings"]`.
- `tests/agentic/test_merger.py` — 4 new tests for the marker semantics + 1 regression-lock for the default-empty path.
- `tests/agentic/test_fund_lookthrough_skill.py` — 3 new predicate tests (top-N subset, complete-list, null-count).
- `tests/agentic/test_assemble_fund.py` — 2 new integration tests.
- `src/pipeline/agentic/README.md` — Merge policy section gains a paragraph on `replace_paths`.

**Read-only references:**
- `src/pipeline/agentic/sources/fund_factsheet_skill.py` — confirms what factsheet writes (no behaviour change here).
- `src/pipeline/agentic/agents/base.py` and `persist.py` — no changes needed; they pass through `result.replace_paths` implicitly via the planner.

**No new files.**

## Implementation Phases

### Phase 0: Discovery & contract verification — `[LOW]`

**Timeline**: ~15 min
**Dependencies**: None

#### Tasks

1. [ ] Confirm `SourceFetchResult` is the canonical envelope returned by every source — grep callers under `src/pipeline/agentic/sources/`. Expect uniformly positional / kwarg construction; verify no source uses `**kwargs` patterns that would silently swallow the new field.
2. [ ] Confirm `merge_patch`'s only caller is `planner.run_planner:115` (grep). Any other caller (e.g. a notebook or script) would need updating too.
3. [ ] Inspect a recent assemble trace (`POST /instruments/assemble` for any fund) and verify the `recordMeta.sourceOfTruth` append behaviour: spec-003 documented append-only, but worth a one-shot confirmation that two rows for the same `fieldGroup` are actually persisted (no implicit de-dup in `persist.py`).

#### Deliverables

- [ ] Phase 0 findings appended below if any assumption fails. If all green, proceed straight to Phase 1.

### Phase 1: Merger marker semantics — `[HIGH]`

**Timeline**: ~1 h
**Dependencies**: Phase 0

#### Tasks

1. [ ] Extend `SourceFetchResult` in `src/pipeline/agentic/merger.py`:
   ```python
   @dataclass(frozen=True)
   class SourceFetchResult:
       patch: Dict[str, Any]
       source_of_truth_rows: List[Dict[str, Any]] = field(default_factory=list)
       replace_paths: List[str] = field(default_factory=list)   # NEW
   ```
   Keep `frozen=True`; the field-default-factory pattern handles immutability for the list correctly.

2. [ ] Update `merge_patch` signature + recursion:
   - Public entry: `def merge_patch(current, patch, *, replace_paths=())` — accept any iterable, convert to `set` internally for O(1) lookups.
   - Recursive helper: `_merge(current, patch, prefix, replace_paths)` — `replace_paths` is the same set, propagated unchanged through nested frames; path equality check uses the running `prefix.field_name` (with dot join, as today).
   - Replacement rule: at each (path, value) pair, if `path in replace_paths` AND `isinstance(value, list)`, write the list verbatim (regardless of existing value, except an empty patch list is still skipped — never write nothing). Otherwise fall through to the existing deep-merge / fill-empty rules.

3. [ ] Defensive case (covered by AC-6): `replace_paths` entry pointing at a dict-valued field → ignored; deep-merge proceeds. Document inline.

4. [ ] Update `planner.run_planner` (line ~115 of `src/pipeline/agentic/planner.py`):
   ```python
   written = merge_patch(current, result.patch, replace_paths=result.replace_paths)
   ```
   No other planner changes — the existing `written_top` extraction and trace formatting already handle dot-paths.

#### Deliverables

- [ ] `SourceFetchResult.replace_paths` field exists with `field(default_factory=list)`.
- [ ] `merge_patch` accepts `replace_paths` keyword.
- [ ] Planner threads it through.
- [ ] `python -c "from pipeline.agentic.merger import SourceFetchResult; r = SourceFetchResult(patch={}, replace_paths=['a.b']); print(r.replace_paths)"` works.

### Phase 2: Source update — predicate + patch shape — `[HIGH]`

**Timeline**: ~30 min
**Dependencies**: Phase 1

#### Tasks

1. [ ] Refine `_predicate_passes` in `src/pipeline/agentic/sources/fund_lookthrough_skill.py`. Replace the two short-circuits:
   ```python
   existing_holdings = (current.get("assetAllocation") or {}).get("holdings") or []
   if existing_holdings:
       return False
   if current.get("holdingsCount"):
       return False
   ```
   With the size-aware check:
   ```python
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
   ```
   Other skip cases unchanged.

2. [ ] Update `_build_patch` return — single-line change:
   ```python
   return SourceFetchResult(
       patch=patch,
       source_of_truth_rows=sot_rows,
       replace_paths=["assetAllocation.holdings"],   # NEW
   )
   ```

3. [ ] Inline doc comment explaining when lookthrough overrides factsheet (top-N → full list) vs defers (complete or unknown-count).

#### Deliverables

- [ ] `_predicate_passes` truth table matches spec FR-1.
- [ ] `_build_patch` declares `replace_paths`.
- [ ] Manual smoke from a Python REPL: build a fake "current" with 10 holdings + holdingsCount=1310 → predicate returns True. Same with 80/80 → False.

### Phase 3: Unit tests — `[HIGH]`

**Timeline**: ~1 h
**Dependencies**: Phase 2

#### Tasks

1. [ ] Extend `tests/agentic/test_merger.py` with 4 new cases:
   - `test_replace_paths_overrides_existing_list` — 10-row list at `assetAllocation.holdings` in current, patch has 100-row list + `replace_paths=["assetAllocation.holdings"]` → current ends with 100 rows.
   - `test_replace_paths_no_op_on_dict_value` — `replace_paths=["a.b"]` but patch value at `a.b` is a dict → deep-merge applies (AC-6).
   - `test_replace_paths_does_not_affect_other_paths` — patch with `replace_paths=["a.b"]` also touches `a.c` → `a.c` is fill-empty-only.
   - `test_replace_paths_empty_default_preserves_spec_003_behavior` — replay one of the existing spec-003 cases with explicit `replace_paths=()` → byte-identical result (regression lock).
   - Also verify `written` return: dot-paths for replaced lists exist in the output list.

2. [ ] Extend `tests/agentic/test_fund_lookthrough_skill.py` with 3 new cases:
   - `test_predicate_fires_when_existing_holdings_are_strict_subset_of_holdingsCount` — 10 holdings, holdingsCount=1310, synthetic → predicate passes.
   - `test_predicate_skips_when_existing_holdings_equal_holdingsCount` — 80 holdings, holdingsCount=80, synthetic → predicate skips.
   - `test_predicate_skips_when_holdingsCount_is_null_but_holdings_populated` — top-10, holdingsCount=null → predicate skips (defensive).

3. [ ] Update the existing `test_lookthrough_predicate_short_circuits_when_holdings_already_present` test to also assert holdingsCount semantics. Or replace it with the more nuanced new cases — decide during execute.

4. [ ] Add one new case verifying `_build_patch` returns the right `replace_paths`:
   - `test_build_patch_declares_replace_paths_for_holdings` — assert `result.replace_paths == ["assetAllocation.holdings"]`.

#### Deliverables

- [ ] `pytest tests/agentic/test_merger.py -v` — all green, including the 4 new tests.
- [ ] `pytest tests/agentic/test_fund_lookthrough_skill.py -v` — all green, including the 3 new predicate tests + 1 patch-shape test.
- [ ] Full `pytest` green — regression-locked.

### Phase 4: Integration tests — `[MEDIUM]`

**Timeline**: ~30 min
**Dependencies**: Phase 3

#### Tasks

1. [ ] Extend `tests/agentic/test_assemble_fund.py` with 2 new cases:
   - `test_lookthrough_replaces_factsheet_top_n` — mock fund_factsheet_skill to return top-10 + holdingsCount=1310 + replicationMethod=synthetic_swap + benchmarkName; mock lookthrough's OpenSearch + LLM stubs to return a 100-row proxy. After assemble, `current.assetAllocation.holdings.length == 100`, every row `source=physical_proxy`, `lookthroughProvenance.proxyIsin` set.
   - `test_lookthrough_does_not_fire_on_complete_factsheet_holdings` — mock factsheet to return 80 holdings + holdingsCount=80; assert lookthrough.fetch is never called (or returns None via predicate).

2. [ ] Optional: `test_sourceOfTruth_carries_both_factsheet_and_lookthrough_rows_for_holdings` — locks AC-7 at the integration level. Pluggable into the AC-1 test via assertion-only addition.

#### Deliverables

- [ ] `pytest tests/agentic/test_assemble_fund.py -v` — green incl. new tests.
- [ ] Total agentic test count ≥ 270.

### Phase 5: Live verification + docs — `[MEDIUM]`

**Timeline**: ~1 h
**Dependencies**: Phase 4

#### Tasks

1. [ ] **Pre-step — seed a physical proxy**:
   ```bash
   # Source .env so ANTHROPIC_API_KEY propagates
   set -a && . ./.env && set +a
   # Rebuild + recreate instrument-api so the new code is in the image
   docker compose build instrument-api && docker compose up -d --force-recreate instrument-api
   # Assemble an iShares MSCI World ETF — factsheet skill writes the patch
   curl -X POST localhost:8003/instruments/assemble -H 'content-type: application/json' \
     -d '{"scope":"fund","identifier":{"kind":"isin","value":"IE00B4L5Y983"},"persist":true,"invoke_llm_skills":true}'
   ```
   Cost: ~$0.02 one-time; the resulting patch is cached on disk for free re-use.

2. [ ] Verify the iShares record landed:
   ```bash
   curl -s 'localhost:9200/pms_golden_fund/_search' -H 'content-type: application/json' \
     -d '{"query":{"match":{"longName":"iShares Core MSCI World"}},"size":3}' \
     | jq '.hits.hits[]._source | {goldenId, replicationMethod, benchmarkName, holdingsCount, holdings_len: (.assetAllocation.holdings|length)}'
   ```
   Expect: replicationMethod=physical_full or physical_sampling, benchmarkName contains "MSCI World", holdings_len > 0.

3. [ ] **AC-1 live**: assemble LU1681043599 (Amundi MSCI World Swap) with persist + LLM skills. Compare `holdings.length` and `lookthroughProvenance.proxyIsin` before/after. Cost: 1 LLM call if factsheet cache cold for this ISIN (cached after spec-003 PR #9 if patch file remains on disk), else free.

4. [ ] **AC-4 live (idempotency)**: re-run the same assemble — verify `lookthroughProvenance` unchanged, `holdings.length` unchanged.

5. [ ] **Doc updates**:
   - `src/pipeline/agentic/README.md` — Merge policy section: append a paragraph on `replace_paths` (when to use it, list-only semantic, no-op on dicts).
   - Optional: update `CLAUDE.md` "Agentic data engineering" fund-chain enumeration to clarify that lookthrough now enhances (rather than only fills) holdings.

#### Deliverables

- [ ] AC-1 live result documented in plan-001.md or in the PR body: holdings.length pre/post + proxyIsin.
- [ ] AC-4 live confirmed.
- [ ] README updated.

### Phase 6: Sign-off — `[LOW]`

**Timeline**: ~15 min
**Dependencies**: Phase 5

#### Tasks

1. [ ] Full `pytest` clean across the repo.
2. [ ] `POST /instruments/assemble` regression — assemble a physical fund (e.g. one of the existing 22 records) without LLM skills → no behavioural change vs spec-003.
3. [ ] Tick spec-002 DoD checkboxes for items completed.
4. [ ] `git log --oneline -10` review.
5. [ ] Push branch, open PR, merge.

#### Deliverables

- [ ] `pytest`: ≥ 270/270 green.
- [ ] spec-002 DoD ticked.
- [ ] Branch `feat/lookthrough-full-list` merged.

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `replace_paths` accidentally hits paths in other sources via shared `assetAllocation` namespace | Low | Medium | V1 has exactly one source using it (lookthrough). Phase 3's "no_op_on_dict_value" and "does_not_affect_other_paths" tests pin the behaviour. Code review checks for any new `replace_paths=` declarations. |
| Predicate refinement makes lookthrough fire on funds with degenerate `holdingsCount` (e.g. holdingsCount=1 + holdings=[]) | Low | Low | The check is `existing_holdings AND declared_count AND len(existing) >= declared` — degenerate values short-circuit safely. Phase 3 tests cover null and zero. |
| Frozen dataclass + mutable list default — pydantic / dataclasses might warn | Low | Low | `field(default_factory=list)` is the canonical pattern and works with `frozen=True`. Phase 1's smoke check catches any tooling complaint. |
| `merge_patch` keyword-only change breaks any external caller | Low | Low | Phase 0 grep confirmed only the planner calls it. The change uses keyword-only (`*, replace_paths=`) so positional callers stay broken at type-check time, not silent-wrong. |
| Provenance trail growth — 2 rows per fund where lookthrough overrides | Confirmed | Low | Append-only is the documented convention; consumer-side dedup (if needed) is downstream concern. |
| Phase 5 live verification needs a fresh iShares assemble — $0.02 cost | Confirmed | Low | One-time. Patch caches. Budget approved by user during spec-003 cycle. |

### External Dependencies

| Dependency | Risk | Contingency |
|---|---|---|
| Docker stack + instrument-api rebuilt against spec-003 + spec-004 code | Low | Standard `docker compose build && up -d --force-recreate` cycle. |
| `ANTHROPIC_API_KEY` propagation from `.env` | Confirmed | Source `.env` before `docker compose up` (per spec-003 debug session). |
| iShares Core MSCI World factsheet skill works | Confirmed | Validated during spec-003 T011b. |

## Resource Requirements

### Development

- 1 backend developer. ~4 hours total (~half a working day).

### Infrastructure

- Local Docker stack for Phase 5.
- `ANTHROPIC_API_KEY` in `.env` for Phase 5 step 1 (seeding iShares — one-time $0.02 if cache cold).

## Success Metrics

- AC-1 through AC-7 all pass (AC-1, AC-4 live; rest unit/integration).
- `pytest`: ≥ 270/270.
- `holdings.length` for the canonical test fund (LU1681043599) increases from 10 (spec-003) to ≥ 50 (a meaningful proxy fallback).
- No regression on the existing 263 tests at any phase.
- Net lines added: ~150 (50 production, 100 tests). No deletions.

## Rollout Plan

Standard SpecPulse flow:
1. Phases 1–6 on `feat/lookthrough-full-list`.
2. PR opened against `main`, body summarises predicate change + merger marker semantic + live AC-1 evidence.
3. Review in PyCharm. Merge. Delete branch.

## Definition of Done

- [ ] Phases 0–6 complete.
- [ ] All seven spec-002 acceptance criteria met.
- [ ] `SourceFetchResult.replace_paths` field exists; `merge_patch` honours it; planner threads it.
- [ ] `fund_lookthrough_skill` predicate refined + `_build_patch` declares the marker.
- [ ] README Merge policy section updated.
- [ ] `pytest` green at ≥ 270.
- [ ] Branch merged.

## Open Questions for /sp-task

1. **Provenance row deduplication policy** — spec-002 AC-7 asserts append behaviour. Should the merger automatically emit a SoT row for replaced paths, or is the source responsible (current behaviour)? Default: source-responsible, no merger change. Decide whether AC-7's two-row trail comes from factsheet's row + lookthrough's existing row (already in the source), or needs explicit merger help.
2. **Existing predicate test `test_lookthrough_predicate_short_circuits_when_holdings_already_present`** — this test currently asserts that ANY non-empty holdings short-circuits the predicate. With the refinement, it stays correct only when `holdingsCount` is null or `<= len(holdings)`. Update or split?
3. **Frontend** — spec-002 marked frontend out of scope. Worth confirming: the existing badge from spec-003 will render `via {proxyIsin} ({confidence})` with the new larger holdings list automatically. The holdings table subtitle will say `1310 · via physical proxy` instead of `10 · via physical proxy`. Acceptable without further work.

## Additional Notes

- **Inherits from spec-003** the full LLM-skill cost-gate infrastructure (`--enable-llm-skills`, `allowed_llm_skills`), the deep-merge merger from T002, and the `find-and-parse-factsheet` skill working end-to-end in docker (after PRs #7, #8, #9).
- **Single-service feature** — no decomposition directory needed.
- **No new requirements.txt entries.**

## Phase 0 findings (T001, 2026-05-18)

All three contract checks pass cleanly — no plan adjustments needed.

**1. `merge_patch` callers**: production code has exactly one caller (`planner.py:124`). Tests call it directly 9 times in `test_merger.py` — those use the positional 2-arg form and will continue to work unchanged with the new keyword-only `replace_paths=` argument (default empty).

**2. `SourceFetchResult` construction patterns**: every one of the 12 sources under `src/pipeline/agentic/sources/` constructs via explicit kwargs (`SourceFetchResult(patch=..., source_of_truth_rows=...)`). No `**kwargs` unpacking anywhere — adding a third optional kwarg with `default_factory=list` is fully backward-compatible.

**3. `sourceOfTruth` append behaviour**: confirmed via the spec-003 live trace earlier in this session — the persist layer writes the whole record verbatim, no dedup logic on `sourceOfTruth`. AC-7 (two rows for the same fieldGroup) holds by construction.

**No plan adjustments required.** Proceed to T002.

---

*Generated by /sp-plan on 2026-05-18. Plans the implementation of spec-002 (predicate refinement + `replace_paths` marker on merger). 6 phases, ~4h estimated, single serial chain. Phase 0 findings appended 2026-05-18 during /sp-execute T001.*
