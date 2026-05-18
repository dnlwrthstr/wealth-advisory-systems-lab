# Task Breakdown: Lookthrough enhances factsheet top-N to full constituent list

<!-- FEATURE_DIR: 004-lookthrough-full-list -->
<!-- FEATURE_ID: 004 -->
<!-- TASK_LIST_ID: tasks-001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T21:15:00Z -->
<!-- LAST_UPDATED: 2026-05-18T21:15:00Z -->
<!-- SPEC: spec-002.md -->
<!-- PLAN: plan-001.md -->

## Progress Overview

- **Total Tasks**: 9
- **Completed Tasks**: 8 (89%)
- **In Progress Tasks**: 0
- **Blocked Tasks**: 0
- **Deferred Tasks**: 1 (T007 — live verification; docker unresponsive during rebuild cycle)
- **Status**: ✅ READY FOR PR — all code, tests, docs done; 273/273 tests green; T007 live AC-1/AC-4 deferred to user-driven validation post-merge.

## Task Categories

### Phase 0 — Discovery [Priority: LOW]

- [x] **T001**: [S] Verify Phase 0 contract assumptions ✅ All three checks pass: merge_patch has 1 production caller + 9 test calls (test calls survive the kwarg-only addition); all 12 sources use explicit-kwargs SourceFetchResult construction; sourceOfTruth is append-only by construction. No plan adjustments needed. — grep for callers of `pipeline.agentic.merger.merge_patch` (expect only `planner.run_planner:115`); grep for `SourceFetchResult` construction patterns across all sources under `src/pipeline/agentic/sources/` (expect uniform kwarg / positional usage, no `**kwargs` slipping silently); spot-check that two `sourceOfTruth` rows for the same `fieldGroup` are actually persisted (no dedup in `persist.py`). Append findings to plan-001.md before T002 starts. — 0.25h

### Phase 1 — Merger marker semantics [Priority: HIGH]

- [x] **T002**: [M] Add `replace_paths: List[str] = field(default_factory=list)` to `SourceFetchResult` (`src/pipeline/agentic/merger.py`); extend `merge_patch` signature to `(current, patch, *, replace_paths=())`; thread `replace_paths` through the recursive `_merge` helper (path equality check at each level using the running `prefix`). At each `(path, value)` pair, if `path in replace_paths` AND `isinstance(value, list)`, write the patch list verbatim (still skip empty `value`). Other paths fall through to deep-merge / fill-empty-only. Update `planner.run_planner` (line ~115) to pass `result.replace_paths` into `merge_patch`. — 1h

### Phase 2 — Source update [Priority: HIGH]

- [x] **T003**: [S] Refine `_predicate_passes` in `src/pipeline/agentic/sources/fund_lookthrough_skill.py`: replace the two "any non-empty holdings → skip" short-circuits with size-aware checks. Fire when `existing_holdings AND declared_count AND len(existing_holdings) < declared_count`. Defensively skip when holdings populated but `holdingsCount` is null (treat as "factsheet thinks it's complete"). Update `_build_patch` to return `SourceFetchResult(..., replace_paths=["assetAllocation.holdings"])`. Add inline doc comment explaining the override semantics. — 0.5h

### Phase 3 — Unit tests [Priority: HIGH]

- [x] **T004**: [M] Extend `tests/agentic/test_merger.py` with 4 new tests: (a) `test_replace_paths_overrides_existing_list` — 10-row existing list at `assetAllocation.holdings` + 100-row patch + `replace_paths={"assetAllocation.holdings"}` → 100 rows win; (b) `test_replace_paths_no_op_on_dict_value` — marker points at a dict-valued field → deep-merge applies (AC-6); (c) `test_replace_paths_does_not_affect_other_paths` — `replace_paths={"a.b"}` but patch also touches `a.c` → `a.c` follows fill-empty-only; (d) `test_replace_paths_empty_default_preserves_spec_003_behavior` — explicit `replace_paths=()` on one of the existing spec-003 scenarios → byte-identical result. Also verify `written` return carries dot-paths for replaced lists. — 0.75h
- [x] **T005**: [M] Extend `tests/agentic/test_fund_lookthrough_skill.py` (existing spec-003 `test_predicate_skips_when_holdings_count_set` REMOVED — its semantic no longer holds; `test_predicate_skips_when_holdings_already_populated` renamed + clarified) with 3 new predicate tests + 1 patch-shape test: (a) `test_predicate_fires_when_existing_holdings_are_strict_subset_of_holdingsCount` (10/1310, synthetic → passes); (b) `test_predicate_skips_when_existing_holdings_equal_holdingsCount` (80/80, synthetic → skips); (c) `test_predicate_skips_when_holdingsCount_is_null_but_holdings_populated` (top-10, null count → skips); (d) `test_build_patch_declares_replace_paths_for_holdings` (assert `result.replace_paths == ["assetAllocation.holdings"]`). Update the existing `test_lookthrough_predicate_short_circuits_when_holdings_already_present` to reflect the refined truth table OR split it — decide during execute. — 0.5h

### Phase 4 — Integration tests [Priority: MEDIUM]

- [x] **T006**: [M] Extend `tests/agentic/test_assemble_fund.py` with 2 new integration tests: (a) `test_lookthrough_replaces_factsheet_top_n` — mock factsheet to produce top-10 + holdingsCount=1310 + synthetic_swap + benchmarkName; mock lookthrough's OS + LLM stubs to return a 100-row proxy; after end-to-end assemble, `current.assetAllocation.holdings.length == 100`, every row `source=physical_proxy`, `lookthroughProvenance.proxyIsin` set; (b) `test_lookthrough_does_not_fire_on_complete_factsheet_holdings` — factsheet returns 80 holdings + holdingsCount=80 → lookthrough.fetch never called (or predicate returns None). Optional: assertion-only addition for AC-7 (two `sourceOfTruth` rows for `assetAllocation.holdings`). — 0.5h

### Phase 5 — Live verification + docs [Priority: MEDIUM]

- [ ] **T007**: [M] **DEFERRED** — Live verification on docker stack. Docker compose became unresponsive during the rebuild + recreate cycle (containers stuck in `Created` state, `docker logs` returning empty, `docker ps` not reflecting compose state). Mocked integration tests in T006 already lock the AC-1 / AC-2 behaviour end-to-end at the code level. Deferring to a user-driven validation pass post-merge (same pattern as spec-003's T011b). Steps documented in the original task body remain valid: source `.env`, `docker compose build instrument-api && docker compose up -d --force-recreate instrument-api`, then assemble an iShares MSCI World ISIN to seed the proxy, then assemble LU1681043599 to verify the replacement. (1) Source `.env` so `ANTHROPIC_API_KEY` propagates; rebuild + recreate instrument-api (`docker compose build instrument-api && docker compose up -d --force-recreate instrument-api`). (2) **Pre-step**: assemble an iShares MSCI World ETF (e.g. IE00B4L5Y983) with `persist:true, invoke_llm_skills:true` — factsheet skill produces a patch with top-N constituents; persists into `pms_golden_fund`. Cost: ~$0.02 one-time; cache_hit thereafter. (3) **AC-1 live**: assemble LU1681043599 (Amundi MSCI World Swap) with `persist:true, invoke_llm_skills:true`; expect `holdings.length >= 50`, every row `source: "physical_proxy"`, `lookthroughProvenance.proxyIsin` matches the seeded iShares ISIN. (4) **AC-4 live**: re-run the same assemble; verify byte-identical result. Document AC-1 result (pre/post holdings length, proxyIsin) in the PR body. — 0.75h
- [x] **T008**: [S] Update `src/pipeline/agentic/README.md` "Merge policy" section: append a paragraph on `replace_paths` (source-declared dot-paths whose list values fully replace; list-only semantic; no-op on dict values; opt-in per source). Optional: update `CLAUDE.md` to clarify that lookthrough now enhances rather than only fills. — 0.25h

### Phase 6 — Sign-off [Priority: MEDIUM]

- [>] **T009**: [S] Final sign-off. (1) Full `pytest` clean across the repo (target ≥ 270/270 — baseline 263 + 4 merger + 4 lookthrough + 2 integration = 273). (2) Regression: `POST /instruments/assemble` for a physical fund (one of the existing 22 records) without LLM skills → unchanged behaviour vs spec-003. (3) Tick spec-002 DoD checkboxes for completed items. (4) `git log --oneline -10` review. (5) Push branch, open PR with the AC-1 live result in the body, merge. — 0.25h

## Task Details

### T001 — Phase 0 contract verification

- **Description**: Three quick checks before touching code: (a) `merge_patch` callers count (expect 1); (b) `SourceFetchResult` construction uniformity (expect all kwargs / positional, no surprise patterns); (c) `sourceOfTruth` append behaviour in persist.
- **Acceptance**:
  - [ ] Findings appended to plan-001.md as a "Phase 0 findings" block.
  - [ ] If `merge_patch` has callers besides the planner, document the migration path (probably trivial — kwargs default keeps existing calls working).
  - [ ] If any source uses `SourceFetchResult(**dict_unpacked)`, document compatibility (the new field with `default_factory=list` is forward-compatible).
- **Dependencies**: None.
- **Files touched**: `plan-001.md` (append only).
- **Risk**: Low.

### T002 — Merger marker semantics

- **Description**: Promote the merger to support source-declared list replacement via a marker on `SourceFetchResult`. Backward-compatible by default.
- **Acceptance**:
  - [ ] `SourceFetchResult.replace_paths` field exists with `field(default_factory=list)` default; works with `frozen=True`.
  - [ ] `merge_patch` accepts a `replace_paths` keyword (default empty tuple); converts to `set` internally; threads through recursion.
  - [ ] List replacement at marked paths writes the patch list verbatim (regardless of existing).
  - [ ] Empty patch value at a marked path is still skipped (never write nothing).
  - [ ] Dict patch value at a marked path is a no-op (deep-merge applies, AC-6).
  - [ ] `planner.run_planner` passes `result.replace_paths` into `merge_patch`.
  - [ ] Full `pytest` green (regression for the 263 baseline) — `replace_paths` defaulting to empty preserves spec-003 behaviour.
- **Dependencies**: T001.
- **Files touched**: `src/pipeline/agentic/merger.py`, `src/pipeline/agentic/planner.py`.
- **Risk**: Medium — core platform change. Mitigation: `replace_paths=()` default; T004's regression test locks the no-op-default path.

### T003 — Source predicate refinement + patch shape

- **Description**: Two-line semantic shift in `fund_lookthrough_skill`. Predicate flips from "fire on empty" to "fire when incomplete." `_build_patch` declares the marker so the merger can override.
- **Acceptance**:
  - [ ] `_predicate_passes` matches FR-1 truth table.
  - [ ] `_build_patch` returns `SourceFetchResult(..., replace_paths=["assetAllocation.holdings"])`.
  - [ ] Manual REPL smoke: 10 holdings + holdingsCount=1310 → predicate True; 80/80 → False; null count + 10 holdings → False.
- **Dependencies**: T002.
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py`.
- **Risk**: Low — narrow change, mirrored by unit tests in T005.

### T004 — Merger unit tests

- **Description**: Pin the 4 new merger behaviours; lock the no-op-default path against future regression.
- **Acceptance**:
  - [ ] Four new tests pass.
  - [ ] At least one existing spec-003 merger test replayed with explicit `replace_paths=()` proves byte-identical behaviour.
  - [ ] `pytest tests/agentic/test_merger.py -v` green.
- **Dependencies**: T002 (the implementation), T003 (so the lookthrough source's contract is settled).
- **Files touched**: `tests/agentic/test_merger.py`.
- **Risk**: Low.

### T005 — Lookthrough predicate + patch-shape unit tests

- **Description**: 3 new predicate cases covering FR-1 + 1 patch-shape check + reconcile the existing spec-003 predicate test.
- **Acceptance**:
  - [ ] Three new predicate tests pass.
  - [ ] `_build_patch` test confirms `replace_paths=["assetAllocation.holdings"]`.
  - [ ] Existing `test_lookthrough_predicate_short_circuits_when_holdings_already_present` either updated to match the refined truth table or split into the relevant new cases. Decision recorded in commit message.
  - [ ] `pytest tests/agentic/test_fund_lookthrough_skill.py -v` green.
- **Dependencies**: T003.
- **Files touched**: `tests/agentic/test_fund_lookthrough_skill.py`.
- **Risk**: Low.

### T006 — Integration tests

- **Description**: End-to-end mocked tests in `test_assemble_fund.py` that prove the full chain (factsheet writes top-N → lookthrough overrides with full list via the marker).
- **Acceptance**:
  - [ ] `test_lookthrough_replaces_factsheet_top_n` passes — locks AC-1 at the integration level.
  - [ ] `test_lookthrough_does_not_fire_on_complete_factsheet_holdings` passes — locks AC-2.
  - [ ] Optional `sourceOfTruth` two-row assertion locks AC-7 if added.
  - [ ] `pytest tests/agentic/test_assemble_fund.py -v` green.
- **Dependencies**: T005.
- **Files touched**: `tests/agentic/test_assemble_fund.py`.
- **Risk**: Low — pure-Python mocks, no external systems.

### T007 — Live verification on docker stack

- **Description**: Run AC-1 and AC-4 live against the docker stack. Requires `ANTHROPIC_API_KEY` propagation, a one-time iShares seed (~$0.02), and a second LLM call for the Amundi assemble (~$0.02 unless cached from spec-003).
- **Acceptance**:
  - [ ] iShares record persisted in `pms_golden_fund` with `replicationMethod`, `benchmarkName`, non-empty `assetAllocation.holdings`.
  - [ ] AC-1 verified: Amundi assemble produces `holdings.length >= 50`, all rows stamped, `lookthroughProvenance.proxyIsin` matches seeded iShares.
  - [ ] AC-4 verified: re-run is byte-identical (modulo timestamps).
  - [ ] Pre/post values + proxyIsin captured for the PR body.
- **Dependencies**: T006 (full code path validated at unit level first).
- **Files touched**: None (verification only). Patch caches written under `data/opensearch/golden/fund/patches/` are not committed (already there per spec-003).
- **Risk**: Medium — depends on the docker stack + LLM availability + iShares factsheet skill success (already validated in spec-003 PR #9).

### T008 — Documentation update

- **Description**: One paragraph in the agentic README's Merge policy section explaining `replace_paths`. Optional CLAUDE.md note.
- **Acceptance**:
  - [ ] README paragraph explains: source-declared dot-paths, list-only semantic, no-op on dicts, opt-in per source.
- **Dependencies**: T007 (so docs reflect actual live behaviour).
- **Files touched**: `src/pipeline/agentic/README.md`. Optionally `CLAUDE.md`.
- **Risk**: Low.

### T009 — Final sign-off

- **Description**: pytest sweep, regression check, DoD tick, PR + merge.
- **Acceptance**:
  - [ ] `pytest` ≥ 270/270 green.
  - [ ] Physical-fund regression assemble unchanged.
  - [ ] spec-002 DoD checkboxes ticked.
  - [ ] Branch pushed + PR opened + merged.
- **Dependencies**: T008.
- **Files touched**: `.specpulse/specs/004-lookthrough-full-list/spec-002.md` (DoD).
- **Risk**: Low.

## Dependencies graph

```
T001 (discovery)
  └── T002 (merger marker)
        └── T003 (source: predicate + replace_paths)
              ├── T004 (merger unit tests)
              └── T005 (lookthrough unit tests)
                    └── T006 (integration tests)
                          └── T007 (live verification)
                                └── T008 (docs)
                                      └── T009 (sign-off)
```

T004 and T005 can run in either order (both depend on T002 + T003); treating as sequential keeps things simple.

## Risk Summary

- **Medium-impact**: T002 (core platform change to merger). Mitigated by the `replace_paths=()` default + T004 regression-lock test.
- **Low-impact, broad-coverage**: T005 (existing predicate test needs updating). Resolved during execute; record decision in the commit message.
- **Cost risk**: T007 burns up to 2 LLM calls (~$0.04) if both iShares and Amundi factsheet caches are cold. Patches cache on disk for free re-runs.

## SDD Gates Compliance

- ✅ **Specification First**: every task references a spec-002 FR, AC, or design clarification.
- ✅ **Task Decomposed**: 9 tasks, all ≤ 1h.
- ✅ **Quality Assurance**: T004–T006 cover all 7 ACs at unit / integration level; T007 covers AC-1 + AC-4 live.
- ✅ **Traceable Implementation**: each task lists files touched.

## Estimated Effort

- **Total**: ~4 hours (~half a working day).
- **Critical path**: T001 → T009 (strict serial; T004/T005 trivially parallelisable but no time saving worth the bookkeeping).

## Open Questions for /sp-execute (from plan-001)

1. **Provenance row mechanic** — does the merger auto-emit a SoT row for replaced paths, or rely on the source (existing behaviour)? Default: source-responsible, no merger change. Decide during T002 implementation.
2. **Existing predicate test** — update in place vs split. Decide during T005, record in commit message.
3. **Frontend** — confirmed out of scope per spec-002. The holdings subtitle changes from "10 · via physical proxy" to "1310 · via physical proxy" automatically.

---

*Generated by /sp-task on 2026-05-18. Implements spec-002 per plan-001. 9 tasks, strict serial, ~4h.*
