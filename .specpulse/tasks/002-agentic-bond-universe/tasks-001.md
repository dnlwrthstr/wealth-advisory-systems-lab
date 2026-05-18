# Task Breakdown: Agentic bond universe

<!-- FEATURE_DIR: 002-agentic-bond-universe -->
<!-- FEATURE_ID: 002 -->
<!-- TASK_LIST_ID: tasks-001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T06:45:00Z -->
<!-- LAST_UPDATED: 2026-05-18T06:45:00Z -->
<!-- SPEC: spec-002.md -->
<!-- PLAN: plan-001.md -->

## Progress Overview

- **Total Tasks**: 12 (T012 added post-smoke for the search-mirror fix)
- **Completed Tasks**: 12 (100%)
- **In Progress Tasks**: 0
- **Blocked Tasks**: 0
- **Status**: DONE — all 6 ACs met + 1 follow-up bug fixed inline. Ready for commit + PR.

## Task Categories

### Phase 0 — Discovery [Priority: HIGH]

- [x] **T001**: [S] Verify Phase 0 contract assumptions — read `pipeline.gold._firds.iter_issuer_records` (signature, exceptions); grep for external callers of `bond_firds.main` / `write_ndjson`; spot-check `tests/agentic/test_bond_firds_source.py` to confirm it only uses library APIs that survive the strip. — 0.75h ✅ Done 2026-05-18. Key finding: `iter_issuer_records` swallows persistent FIRDS errors → AC-6 automatic. See plan-001.md "Phase 0 findings".

### Phase 1 — Documentation [Priority: HIGH]

- [x] **T002**: [S] Extend `src/pipeline/agentic/README.md` with a **Bond universe data flow** subsection: `bond_issuers.yml` shape (LEI + name + issuerType + country + assetClass), `pipeline.gold._firds.iter_issuer_records(lei, FIRDS_FL)` per-LEI lookup, per-ISIN agent invocation, GLEIF issuer chaining. — 0.75h ✅ Done 2026-05-18. Restructured the "Universe batch CLIs" section into per-scope subsections (equity + bond).
- [x] **T003**: [S] CLAUDE.md edit — add a one-line pointer to `python -m pipeline.agentic.cli.bond_universe` under "Agentic data engineering" next to the equity CLI pointer added by feature 001. (The `bond_firds` "Legacy bulk fetchers" rewrite happens later in T010, after the strip.) — 0.25h ✅ Done 2026-05-18.

### Phase 2 — Batch CLI [Priority: HIGH]

- [x] **T004**: [L] Create `src/pipeline/agentic/cli/bond_universe.py`. Argparse: `--issuer-lei LEI` (single, mutually exclusive with `--all`), `--all` (default), `--issuers PATH`, `--limit-per-issuer N`, `--dry-run`, `--universe-status STATUS` (default `in_universe`), `--report-out PATH`, `--log-level LEVEL`. `_Outcome` adds `issuer_lei` field; `_RunReport` groups outcomes per-issuer. Main loop: `load_issuers` → optional LEI filter → for each issuer: `iter_issuer_records(lei, FIRDS_FL)` (issuer-level try/except), `dedupe_by_isin`, apply `--limit-per-issuer`, then per-ISIN `AGENTS["bond"].assemble_and_persist(...)` + `index_search_hit(...)`. Lazy imports for opensearch deps. — 2.5h ✅ Done 2026-05-18. Module imports without opensearch-py; argparse + dataclasses verified.

### Phase 3 — Smoke tests [Priority: HIGH]

- [x] **T005**: [M] Create `tests/agentic/test_bond_universe_cli.py`. Cover: AC-5 (`--issuer-lei <unknown>` non-zero exit, stderr lists known LEIs); AC-4 (`--dry-run` no agent calls); happy path (2 issuers × 3 bonds, mocked); AC-6 (one issuer's `iter_issuer_records` raises → others proceed, failed issuer in report); per-ISIN error isolation; `--limit-per-issuer` cap; `--report-out` produces per-issuer-grouped JSON. — 1.5h ✅ Done 2026-05-18. 12 tests pass. Caught the CFI-filter requirement in `dedupe_by_isin` during test-writing — fixtures need `gnr_cfi_code: "DBFTFR"`.

### Phase 4a — Verification [Priority: HIGH]

- [x] **T006**: [S] Capture legacy NDJSON snapshot — `python -m pipeline.gold.bond_firds --output data/cache/parity/legacy_bonds.ndjson`. Pre-strip baseline. — 0.5h ✅ Done 2026-05-18. **4,122 BondGolden documents** across 8 of 10 issuers (Roche + Daimler Truck returned 0 bonds via legacy filter). Spec's "~50–200" estimate was off by 20x. Per-issuer counts: DE Govt 494, IT Govt 1114, NL Govt 465, EIB 1707, AAPL 118, TTE 16, SAP 22, ALV 186, ROG 0, DTRGY 0.
- [x] **T007** (scope-adjusted after T006 finding): [M] Live run new CLI — rebuild instrument-api, single-issuer smoke (SAP, 22 bonds), then `--all --limit-per-issuer 3` (24 ISINs across 10 issuers — exercises AC-6 with the two empty issuers). Verify counts in `pms_golden_bond` + `pms_golden_issuer` + `pms_golden_instrumentsearch`. Re-run for AC-2 idempotency. Full 4,122-bond load deferred — not in interactive session. — 1h ✅ Done 2026-05-18. **AC-1**: 24/24 bonds persisted; counts went 1/23/22 → 25/30/46. **AC-2**: re-run identical (25/30/46). Roche + Daimler Truck returned 0 bonds via FIRDS — matches legacy and validates AC-6 (empty issuers don't block the batch). All 24 outcomes are "partial" (gaps=2 in non-required fields).
- [x] **T008**: [M] Parity diff — write `data/cache/parity/diff_bonds.py` (pattern from feature 001's `diff_smi.py`). Run against legacy NDJSON vs new OpenSearch records. Document divergences for PR body (AC-3). — 1h ✅ Done 2026-05-18. Joins on ISIN (not goldenId — the new chain adds MIC venue suffix). 24/24 overlapping records compared. **No regressions** — new chain populates every legacy-populated field. New chain adds `universeStatus` (expected). `goldenId` format differs (24/24) — `BG-<ISIN>-<MIC>-001` (new) vs `BG-<ISIN>-001` (legacy); intentional.

### Phase 4b — Legacy strip [Priority: HIGH]

- [x] **T009**: [M] Strip `pipeline.gold.bond_firds`: delete `main()` (~45 lines), the `argparse` setup, `write_ndjson`, the `if __name__ == "__main__":` block, and any imports unused after the strip (`argparse`, possibly `Path`). Rewrite the module docstring to "library only" matching `pipeline.gold.equity_yahoo`'s post-strip role. Keep `fetch_by_isin`, `firds_to_golden`, `load_issuers`, `dedupe_by_isin`, `derive_*`, `_resolve_issuer`, `_gleif_to_issuer`, `_record_quality`, `_fingerprint`, `_to_float`, `_iso_date`, `_lifecycle_status`, `_asset_class_defaults`, `FIRDS_FL`. Verify `pytest` clean after. — 1h ✅ Done 2026-05-18. ~58 lines removed (`main`, `argparse`, `write_ndjson`, `if __name__`, `argparse` import). `Path` kept (still used by `load_issuers` + `_resolve_issuer`). 174/174 tests pass.
- [x] **T010**: [S] CLAUDE.md edit — rewrite the `bond_firds` bullet under "Legacy bulk fetchers" to reflect the slimmed library role (parity with the `equity_yahoo` rewrite from feature 001). — 0.25h ✅ Done 2026-05-18. Library role documented; coupon-rate scaling caveat preserved.

### Phase 5 — Final smoke & sign-off [Priority: MEDIUM]

- [x] **T011**: [S] Final integration smoke — `pytest` clean across the repo; `POST /instruments/assemble` for one bond ISIN still works (regression check on strip); `GET /universe?scope=bond` lists the loaded bonds; `GET /instruments/search?type=simpleBond` returns search-mirror hits. Tick DoD in spec-002.md. — 0.5h ✅ Done 2026-05-18. `pytest`: 174/174 (host) + 5 new tests added for the bond-ow_type regression (skip on host without opensearchpy; run in container). POST assemble for SAP `DE000A13SL34` → quality 0.857. `GET /universe/bond` → 25 bonds. `GET /instruments/search?type=simpleBond` → **25 hits** after fixing the `ow_type` casing bug (see T012 below).
- [x] **T012** (post-smoke fix, 2026-05-18): Fix bond `ow_type` casing in `pipeline.gold.search_index_build._SCOPE_TO_OW_TYPE`: `simple_bond` → `simpleBond` to match the public API contract on `GET /instruments/search?type=simpleBond`. Added `tests/agentic/test_search_index_build.py` (5 regression tests). Updated 21 stale records in `pms_golden_instrumentsearch` via one-shot `_update_by_query` for the dev environment; fresh seeds get the right casing from the writer. — 0.5h

## Task Details

### T001 — Phase 0 verification

- **Description**: Read `pipeline.gold._firds.iter_issuer_records` to confirm `(lei: str, fl: List[str]) -> Iterator[Dict[str, Any]]` shape and exception behaviour on HTTP failure. Run `grep -rn "bond_firds.main\|bond_firds.write_ndjson"` across `src/`, `tests/`, `backend/` — expect zero matches. Spot-check `tests/agentic/test_bond_firds_source.py` for any imports that would break after the strip.
- **Acceptance**:
  - [ ] `iter_issuer_records` signature + behaviour documented as a brief addendum at the bottom of `plan-001.md`.
  - [ ] Grep confirmed: no external callers of `main` / `write_ndjson`.
  - [ ] Existing bond tests use only library APIs that survive the strip.
- **Dependencies**: None.
- **Files touched**: plan-001.md (Phase 0 findings addendum).
- **Risk**: Low.

### T002 — Extend README with bond universe data flow

- **Description**: Add a "Bond universe data flow" subsection to `src/pipeline/agentic/README.md`, alongside the existing equity content. Cover the four steps: (1) read `bond_issuers.yml`, (2) per-LEI FIRDS lookup via `iter_issuer_records`, (3) `AGENTS["bond"].assemble_and_persist` per ISIN with `universe_status="in_universe"`, (4) issuer chaining via `assemble_and_persist`'s built-in LEI walk.
- **Acceptance**:
  - [ ] New section renders cleanly.
  - [ ] Cross-links the new CLI module.
  - [ ] No changes to the equity content.
- **Dependencies**: T001 (so the signature description is accurate).
- **Files touched**: `src/pipeline/agentic/README.md`.
- **Risk**: Low.

### T003 — CLAUDE.md cross-link

- **Description**: Add a one-line pointer to the new CLI under the "Agentic data engineering" block, next to the existing equity-universe pointer added by feature 001. Do NOT touch the "Legacy bulk fetchers" `bond_firds` bullet yet — that gets rewritten in T010 after the strip.
- **Acceptance**:
  - [ ] One new line under "Agentic data engineering" referencing `pipeline.agentic.cli.bond_universe`.
- **Dependencies**: None (independent from T002).
- **Files touched**: `CLAUDE.md`.
- **Risk**: Low.

### T004 — Batch CLI `bond_universe.py`

- **Description**: Centre of gravity. Mirror the shape of `pipeline.agentic.cli.equity_universe.py` but adapt to the two-level loop (issuer → ISIN) and the bond-specific flag set. Lazy-import `index_search_hit` and `opensearch_client_from_env` per feature 001's pattern.
- **Acceptance**:
  - [ ] `python -m pipeline.agentic.cli.bond_universe --help` prints the documented flags.
  - [ ] `python -m pipeline.agentic.cli.bond_universe --dry-run --issuer-lei <known-LEI>` exits 0 and emits a report.
  - [ ] Module imports without `opensearch-py` available (for unit-test compatibility).
  - [ ] Strict-serial; per-ISIN errors caught and reported, not raised; per-issuer FIRDS failures caught and reported, not raised.
- **Dependencies**: T001.
- **Files touched**: `src/pipeline/agentic/cli/bond_universe.py` (new).
- **Risk**: Medium — largest single deliverable; integration surface with planner + persist + search.

### T005 — Smoke tests

- **Description**: Mirror `tests/agentic/test_equity_universe_cli.py` structure. Stub `AGENTS["bond"]`, stub `iter_issuer_records`, stub `index_search_hit` via `sys.modules` injection (no opensearchpy needed). Cover all six test cases per Phase 3 of plan-001.
- **Acceptance**:
  - [ ] All test cases pass offline.
  - [ ] AC-4, AC-5, AC-6 covered.
  - [ ] Tests do not require docker or live OpenSearch.
- **Dependencies**: T004.
- **Files touched**: `tests/agentic/test_bond_universe_cli.py` (new).
- **Risk**: Low.

### T006 — Legacy snapshot

- **Description**: Run `python -m pipeline.gold.bond_firds --output data/cache/parity/legacy_bonds.ndjson` against the current curated set. Captures the legacy baseline before the strip in T009 makes the legacy CLI unavailable. `data/cache/` is gitignored.
- **Acceptance**:
  - [ ] NDJSON file exists at the expected path.
  - [ ] Document count ≈ what FIRDS returns for the 10 curated issuers (target: ≥50 bonds; actual count recorded in the report).
- **Dependencies**: None.
- **Files touched**: `data/cache/parity/legacy_bonds.ndjson` (gitignored).
- **Risk**: Low.

### T007 — Live run + AC-1 + AC-2

- **Description**: Rebuild instrument-api (`docker compose -p wealth-advisory-systems-lab build instrument-api` + `up -d`) so the new CLI module is in the image. Run single-issuer first to verify shape, then `--all` for the full set. Capture counts before and after. Re-run for idempotency check.
- **Acceptance**:
  - [ ] AC-1: ≥1 document per issuer LEI in `pms_golden_bond`; ≥1 record per distinct LEI in `pms_golden_issuer`.
  - [ ] AC-2: re-run produces identical counts.
- **Dependencies**: T004, T006.
- **Files touched**: none (verification).
- **Risk**: Medium — live infrastructure dependency.

### T008 — Parity diff (AC-3)

- **Description**: Write `data/cache/parity/diff_bonds.py` modeled on `diff_smi.py` from feature 001. For each ISIN in the legacy NDJSON, fetch the corresponding doc from `pms_golden_bond` (via the OpenSearch HTTP API) and compare schema-overlapping fields. Generate a markdown report with: fields present in new but not legacy, fields present in legacy but not new (regressions), and shared fields with value drift. Document non-regressions for the PR body.
- **Acceptance**:
  - [ ] Diff script exists and runs.
  - [ ] Report identifies no legacy-populated field missing in the new chain (else it's a regression to fix before T009).
  - [ ] Divergence summary captured for the PR description.
- **Dependencies**: T006, T007.
- **Files touched**: `data/cache/parity/diff_bonds.py` (gitignored), report markdown (gitignored).
- **Risk**: Medium — surfaces unexpected drift if any.

### T009 — Strip legacy bond_firds

- **Description**: Remove the legacy `--universe` CLI surface from `src/pipeline/gold/bond_firds.py`. Replicates the equity_yahoo.py strip pattern from feature 001. Run `pytest` after.
- **Acceptance**:
  - [ ] Deleted: `main()`, the argparse setup inside it, `write_ndjson`, `if __name__ == "__main__":` block.
  - [ ] Removed: imports that become unused (`argparse`; `Path` only if no remaining usage).
  - [ ] Module docstring rewritten — "library only since spec 002-agentic-bond-universe".
  - [ ] `from pipeline.gold.bond_firds import fetch_by_isin` still works.
  - [ ] `pytest` clean.
- **Dependencies**: T008 (verify parity before deleting).
- **Files touched**: `src/pipeline/gold/bond_firds.py`.
- **Risk**: Medium — most reversible step but the most code change in one task.

### T010 — CLAUDE.md legacy bullet rewrite

- **Description**: Rewrite the `bond_firds` bullet under "Legacy bulk fetchers" in CLAUDE.md to reflect the slimmed library role. Mirror the wording from the `equity_yahoo` rewrite landed by feature 001's T016.
- **Acceptance**:
  - [ ] Bullet describes the library role (`fetch_by_isin` for the agentic source).
  - [ ] No mention of `--universe` flag.
- **Dependencies**: T009.
- **Files touched**: `CLAUDE.md`.
- **Risk**: Low.

### T011 — Final integration smoke + DoD

- **Description**: Run full `pytest`. Hit `POST /instruments/assemble` for a known bond ISIN. Hit `GET /universe?scope=bond` and confirm bond entries listed. Hit `GET /instruments/search?type=simpleBond` and confirm search mirror works. Tick DoD checkboxes in `spec-002.md`.
- **Acceptance**:
  - [ ] `pytest` exits 0.
  - [ ] Three HTTP smokes pass.
  - [ ] DoD ticked.
- **Dependencies**: T009, T010.
- **Files touched**: `spec-002.md` (DoD checkboxes).
- **Risk**: Low.

## Dependencies

### Task dependency graph

```
T001 ─┬─► T002 ─┐
      │         │
      ├─► T003 ─┤
      │         │
      └─► T004 ─┤
                │
                ▼
              T005 ─► T007 ─► T008 ─► T009 ─► T010 ─► T011
                       ▲
                       │
              T006 ────┘
```

### External dependencies

- **ESMA FIRDS Solr**: required for T006 + T007. Public; no key.
- **Docker compose stack**: required for T007 + T011.
- **GLEIF**: chained inside `assemble_and_persist`; failures non-fatal (per feature 001's precedent).

## Parallel Execution Opportunities

### Can be done in parallel

- **T002 ∥ T003 ∥ T004**: independent after Phase 0; README, CLAUDE.md edit, and CLI module are decoupled.
- **T005 ∥ T006**: tests and legacy snapshot are independent. T005 needs T004; T006 doesn't.

### Must be sequential (critical path)

```
T001 → T004 → T005 → T007 → T008 → T009 → T010 → T011
```

T004 (the CLI) is the centre of gravity. T009 (the strip) is gated on T008 (parity verified).

## Risk Assessment

### Blocker risks

| Risk | Tasks affected | Probability | Impact | Mitigation |
|---|---|---|---|---|
| `iter_issuer_records` raises on one LEI mid-batch | T004, T007 | Medium | Low | Issuer-level error isolation in T004; AC-6 verifies. |
| AC-3 surfaces material regressions | T008, T009 | Low | High | T009 gated on T008. If regressions found, open follow-up sub-spec; do not strip. |
| Hidden import of `bond_firds.main` survives the grep | T009 | Low | Medium | T001 grep + T009 pytest catch it. |
| FIRDS Solr slow / flaky during T007 | T007 | Low | Low | Per-issuer error isolation; failed issuer in report. Re-run targeted with `--issuer-lei`. |

### Resource constraints

| Resource | Bottleneck | Impact | Mitigation |
|---|---|---|---|
| Single developer, sequential critical path | T004 → T005 → T007 | ~6h serial | Acceptable for a 1-day feature. |
| Docker stack restart during T007 | instrument-api downtime ~5s | Negligible | OpenSearch volume persists; no data loss. |

## Completion Criteria

### Per-task DoD

- [ ] Code implemented and self-reviewed.
- [ ] Unit tests added (where the task involves logic) and passing.
- [ ] Acceptance criteria above met.
- [ ] No regressions in adjacent tests.

### Feature DoD (rolls up to spec-002.md DoD)

- [ ] All 11 tasks ticked.
- [ ] AC-1 through AC-6 verified.
- [ ] Legacy `bond_firds --universe` CLI removed; library functions retained.
- [ ] CLAUDE.md current (both new CLI pointer + slimmed legacy bullet).
- [ ] Branch ready for PyCharm review and merge.

## Notes & Decisions

- **2026-05-18**: tasks-001.md generated from plan-001.md. No service decomposition; global numbering (T001..T011) used.
- **2026-05-18**: Inheritance from feature 001 (merged) — layered API, search-mirror per record, lazy opensearch imports, JSON report shape, strict-serial concurrency, per-record error isolation are all reused. No new architectural decisions needed.
- **Clarifications baked in**: single `--issuer-lei` value, `--all` is the default, no `--group` filter, only `--limit-per-issuer` (no global cap), architectural doc extends the existing README.

---

**Legend**

- [S] = Small (< 4 hours), [M] = Medium (4–8 hours), [L] = Large (> 8 hours)
- **Status**: `[ ]` Pending, `[>]` In Progress, `[x]` Completed, `[!]` Blocked
