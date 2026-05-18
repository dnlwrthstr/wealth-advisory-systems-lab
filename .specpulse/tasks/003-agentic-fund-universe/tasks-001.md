# Task Breakdown: Agentic fund universe

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- TASK_LIST_ID: tasks-001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T11:15:00Z -->
<!-- LAST_UPDATED: 2026-05-18T11:15:00Z -->
<!-- SPEC: spec-002.md -->
<!-- PLAN: plan-001.md -->

## Progress Overview

- **Total Tasks**: 11
- **Completed Tasks**: 0 (0%)
- **In Progress Tasks**: 0
- **Blocked Tasks**: 0

## Task Categories

### Phase 0 — Discovery [Priority: HIGH]

- [ ] **T001**: [S] Verify Phase 0 contract assumptions — confirm `fund_firds.dedupe_by_isin` filters CFI=C*; grep for external callers of `fund_firds.main` / `write_ndjson`; spot-check existing fund tests use only library APIs that survive the strip; confirm `BaseAgent.assemble_and_persist` threads `max_cost_class` into `persist.assemble_and_persist` and then into the planner; confirm `persist.extract_leis` walks the umbrella / managementCompany / promoter LEI paths from a FundGolden record. — 0.5h

### Phase 1 — Documentation [Priority: HIGH]

- [ ] **T002**: [S] Extend `src/pipeline/agentic/README.md` with a **Fund universe data flow** subsection alongside the existing Equity + Bond sections: `fund_umbrellas.yml` shape (umbrellaLei + managementCompanyLei + promoter), per-umbrella FIRDS enumeration, the four-source order (fund_firds → fund_yahoo → fund_factsheet_patch → fund_factsheet_skill), the three-record issuer chain (umbrella + managementCompany + promoter), and the cost-class default semantics (`FundAgent.default_max_cost_class="llm_skill"` overridden by the CLI to `"web_fetch"`). — 0.5h
- [ ] **T003**: [S] CLAUDE.md edit — add a one-line pointer to `python -m pipeline.agentic.cli.fund_universe` under "Agentic data engineering" next to the equity + bond pointers. (Legacy `fund_firds` bullet rewrite happens in T010 after the strip.) — 0.25h

### Phase 2 — Batch CLI [Priority: HIGH]

- [ ] **T004**: [L] Create `src/pipeline/agentic/cli/fund_universe.py`. Argparse: `--umbrella-lei LEI` (single, mutually exclusive with `--all`), `--all` (default), `--umbrellas PATH`, `--limit-per-umbrella N`, `--enable-factsheet-skill` (boolean opt-in), `--dry-run`, `--universe-status STATUS` (default `in_universe`), `--report-out PATH`, `--log-level LEVEL`. `_Outcome` has `umbrella_lei` + `isin` + standard fields; `_UmbrellaReport` groups outcomes per umbrella; `_RunReport` has totals. Main loop: `load_issuers` → optional filter → for each umbrella: `iter_issuer_records(lei, FIRDS_FL)` + `dedupe_by_isin`, apply `--limit-per-umbrella`, then per-ISIN `AGENTS["fund"].assemble_and_persist(..., max_cost_class=max_cost_class)` + `index_search_hit`. `max_cost_class` is `"web_fetch"` by default, `"llm_skill"` when `--enable-factsheet-skill`. Lazy opensearch imports; `load_dotenv()` at module top. — 2.5h

### Phase 3 — Smoke tests [Priority: HIGH]

- [ ] **T005**: [M] Create `tests/agentic/test_fund_universe_cli.py`. Mirror bond CLI tests. Cover: AC-5 (`--umbrella-lei <unknown>` non-zero exit); AC-4 (`--dry-run` no agent calls); happy path (2 umbrellas × 3 share-classes) with `max_cost_class="web_fetch"` by default; AC-6 cost-class default (verify agent called with `max_cost_class="web_fetch"`); AC-6 cost-class opt-in (`--enable-factsheet-skill` → `max_cost_class="llm_skill"`); umbrella-level FIRDS failure isolated; per-ISIN error isolation (exit code 1); `--limit-per-umbrella` cap; `--report-out` per-umbrella-grouped JSON; chained_issuers=3 surfaces correctly when stub returns 3. Fixtures need `gnr_cfi_code: "CIVSXX"` (starts with 'C') to survive `fund_firds.dedupe_by_isin`. — 1.5h

### Phase 4a — Verification [Priority: HIGH]

- [ ] **T006**: [S] Capture legacy NDJSON snapshot — `python -m pipeline.gold.fund_firds --output data/cache/parity/legacy_funds.ndjson`. Pre-strip baseline. — 0.5h
- [ ] **T007**: [M] Live run new CLI — rebuild instrument-api (new module only, no new deps), single-umbrella smoke (smallest umbrella in `fund_umbrellas.yml` with `--limit-per-umbrella 3`), then `--all --limit-per-umbrella 3` for AC-1 verification. Verify counts in `pms_golden_fund` + `pms_golden_issuer` (expect +1 to +3 per umbrella) + `pms_golden_instrumentsearch`. Re-run for AC-2 idempotency. Finally **AC-6 LLM verification**: pick one ISIN without a pre-curated patch, run `--umbrella-lei <LEI> --enable-factsheet-skill --limit-per-umbrella 1`, confirm `find-and-parse-factsheet` skill fires (log evidence or new patch file). — 1.5h
- [ ] **T008**: [M] Parity diff — write `data/cache/parity/diff_funds.py` (mirror of `diff_bonds.py`, joins on ISIN since new chain adds MIC suffix to goldenId). Run against legacy NDJSON vs new OpenSearch records. Document divergences for PR body (AC-3). — 1h

### Phase 4b — Legacy strip [Priority: HIGH]

- [ ] **T009**: [M] Strip `pipeline.gold.fund_firds`: delete `main()`, the `argparse` setup, `write_ndjson`, the `if __name__ == "__main__":` block, and unused imports (`argparse`; check `Path`). Rewrite the module docstring to "library only" matching `pipeline.gold.equity_yahoo` (feature 001) and `pipeline.gold.bond_firds` (feature 002). Keep `fetch_by_isin`, `firds_to_golden`, `load_issuers`, `dedupe_by_isin`, `derive_*`, `_resolve_issuer`, `_record_quality`, `_fingerprint`, `_to_float`, `_iso_date`, `_lifecycle_status`, `_asset_class_defaults`, `FIRDS_FL`. Verify `pytest` clean. — 1h
- [ ] **T010**: [S] CLAUDE.md edit — rewrite the `fund_firds` bullet under "Legacy bulk fetchers" to reflect the slimmed library role (parity with feature 001 + feature 002's rewrites). — 0.25h

### Phase 5 — Final smoke & sign-off [Priority: MEDIUM]

- [ ] **T011**: [S] Final integration smoke — `pytest` clean across the repo; `POST /instruments/assemble` for a fund ISIN works (regression on strip); `GET /universe/fund` lists the loaded funds; `GET /instruments/search?type=fund` returns search-mirror hits (no casing bug — fund is single-word). Tick DoD in spec-002.md. — 0.5h

## Task Details

### T001 — Phase 0 verification

- **Description**: Five-part check covering the spec's assumptions. `dedupe_by_isin` CFI filter direction; legacy-CLI caller grep; existing-test compatibility; agent → persist → planner `max_cost_class` wiring; `extract_leis` traversal for fund records.
- **Acceptance**:
  - [ ] Findings appended to plan-001.md as **Phase 0 findings**.
  - [ ] If `max_cost_class` is NOT correctly threaded, log it as a blocker; T004 cannot proceed without it.
  - [ ] If extract_leis won't find all three LEIs, document the actual chain count expected (1 vs 2 vs 3).
- **Dependencies**: None.
- **Files touched**: plan-001.md only (read-only inspection).
- **Risk**: Low.

### T002 — README fund-universe subsection

- **Description**: Extend the existing "Universe batch CLIs" section in `src/pipeline/agentic/README.md` with a sibling "Fund" subsection. Cover the four-source chain, the three-LEI issuer fan-out, and the cost-class default override.
- **Acceptance**:
  - [ ] New "Fund — `cli/fund_universe.py`" subsection renders.
  - [ ] Cross-links the YAML (`src/pipeline/gold/data/fund_umbrellas.yml`) and the agent (`AGENTS["fund"]`).
  - [ ] Equity and Bond subsections unchanged.
- **Dependencies**: T001.
- **Files touched**: `src/pipeline/agentic/README.md`.
- **Risk**: Low.

### T003 — CLAUDE.md cross-link

- **Description**: One-line pointer under "Agentic data engineering" referencing `pipeline.agentic.cli.fund_universe`. Mirrors the equity + bond pointers added by features 001 + 002.
- **Acceptance**:
  - [ ] One new line in the right paragraph.
  - [ ] Existing equity + bond pointers untouched.
- **Dependencies**: None (independent from T002).
- **Files touched**: `CLAUDE.md`.
- **Risk**: Low.

### T004 — Batch CLI `fund_universe.py`

- **Description**: Centre of gravity. Mirror `pipeline.agentic.cli.bond_universe.py` almost verbatim but: rename `issuer_lei` → `umbrella_lei` everywhere; `_IssuerReport` → `_UmbrellaReport`; `_RunReport.issuers` → `_RunReport.umbrellas`; argparse flags use `--umbrella-lei` / `--limit-per-umbrella`; add the `--enable-factsheet-skill` flag; pass `max_cost_class` into `assemble_and_persist`. `load_dotenv()` at module top per PR #3 convention.
- **Acceptance**:
  - [ ] `python -m pipeline.agentic.cli.fund_universe --help` shows all documented flags.
  - [ ] `--dry-run --umbrella-lei <known-LEI>` exits 0 with a report.
  - [ ] Module imports without `opensearch-py` available (unit-test compatibility).
  - [ ] Default `max_cost_class` passed to agent is `"web_fetch"`; with `--enable-factsheet-skill`, it's `"llm_skill"`.
- **Dependencies**: T001.
- **Files touched**: `src/pipeline/agentic/cli/fund_universe.py` (new).
- **Risk**: Medium.

### T005 — Smoke tests

- **Description**: Mirror `tests/agentic/test_bond_universe_cli.py`. Stub `AGENTS["fund"]` (records `max_cost_class` per call), stub `iter_issuer_records`, stub `index_search_hit` via `sys.modules` injection. Fixtures use `gnr_cfi_code: "CIVSXX"` to satisfy fund's CFI=C* filter.
- **Acceptance**:
  - [ ] All 10 test cases pass offline.
  - [ ] AC-4, AC-5, AC-6 (both default and opt-in branches) explicitly covered.
  - [ ] Chained-issuer count of 3 surfaces correctly in the report.
- **Dependencies**: T004.
- **Files touched**: `tests/agentic/test_fund_universe_cli.py` (new).
- **Risk**: Low.

### T006 — Legacy snapshot

- **Description**: Run `python -m pipeline.gold.fund_firds --output data/cache/parity/legacy_funds.ndjson` against the current curated set. Captures the legacy baseline before T009. `data/cache/` is gitignored.
- **Acceptance**:
  - [ ] NDJSON file exists at the expected path.
  - [ ] Document count recorded (expected 50–500 based on umbrella sizes).
- **Dependencies**: None.
- **Files touched**: `data/cache/parity/legacy_funds.ndjson` (gitignored).
- **Risk**: Low.

### T007 — Live run + AC-1 + AC-2 + AC-6

- **Description**: Rebuild instrument-api (`docker compose -p wealth-advisory-systems-lab build instrument-api && up -d`). Three sub-runs:
  1. Single-umbrella smoke (smallest umbrella, `--limit-per-umbrella 3`) — shape check.
  2. `--all --limit-per-umbrella 3` — AC-1 + AC-2 verification.
  3. `--umbrella-lei <LEI> --enable-factsheet-skill --limit-per-umbrella 1` for one ISIN that lacks a pre-curated patch — AC-6 LLM verification. Expect ~$0.05 LLM cost.
- **Acceptance**:
  - [ ] AC-1: ≥1 doc per umbrella with share-classes; up to 3 records per umbrella in `pms_golden_issuer`.
  - [ ] AC-2: re-run identical counts.
  - [ ] AC-6: LLM-skill run produces a new patch file or visible log evidence the skill fired.
- **Dependencies**: T004, T006.
- **Files touched**: none (verification).
- **Risk**: Medium.

### T008 — Parity diff (AC-3)

- **Description**: Write `data/cache/parity/diff_funds.py` modeled on `diff_bonds.py` from feature 002. Join on ISIN (new chain adds MIC suffix to goldenId). Generate report; document divergences in PR body.
- **Acceptance**:
  - [ ] Diff script exists and runs.
  - [ ] Report shows no legacy-populated field missing in the new chain.
  - [ ] Expected divergences captured (universeStatus, factsheet fields when applicable, goldenId format).
- **Dependencies**: T006, T007.
- **Files touched**: `data/cache/parity/diff_funds.py` (gitignored).
- **Risk**: Medium.

### T009 — Strip legacy fund_firds

- **Description**: Apply the equity_yahoo / bond_firds strip pattern. Replicate verbatim where it fits.
- **Acceptance**:
  - [ ] `main()`, `write_ndjson`, argparse, `__main__` removed.
  - [ ] Unused imports removed (`argparse`; possibly `Path`).
  - [ ] Module docstring rewritten to "library only since spec 003-agentic-fund-universe".
  - [ ] `from pipeline.gold.fund_firds import fetch_by_isin` still works.
  - [ ] `pytest` clean.
- **Dependencies**: T008 (gated on parity verified).
- **Files touched**: `src/pipeline/gold/fund_firds.py`.
- **Risk**: Medium.

### T010 — CLAUDE.md legacy bullet rewrite

- **Description**: Rewrite the `fund_firds` bullet under "Legacy bulk fetchers" to reflect the slimmed library role. Mirror feature 002's bond_firds rewrite.
- **Acceptance**:
  - [ ] Bullet describes the library role.
  - [ ] No mention of `--universe` flag.
- **Dependencies**: T009.
- **Files touched**: `CLAUDE.md`.
- **Risk**: Low.

### T011 — Final integration smoke + DoD

- **Description**: Full pytest. `POST /instruments/assemble` for a fund ISIN. `GET /universe/fund` lists funds. `GET /instruments/search?type=fund` returns hits. Tick DoD in spec-002.md.
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

- **ESMA FIRDS Solr**: required for T006 + T007.
- **Docker compose stack**: required for T007 + T011.
- **LLM API**: required for the AC-6 sub-step of T007. Skip if `ANTHROPIC_API_KEY` is unavailable (mark AC-6 partial).
- **GLEIF**: chained inside `assemble_and_persist`; failures non-fatal.

## Parallel Execution Opportunities

### Can be done in parallel

- **T002 ∥ T003 ∥ T004**: independent after Phase 0.
- **T005 ∥ T006**: tests + legacy snapshot. T005 needs T004; T006 has no Phase-0 dependency.

### Must be sequential (critical path)

```
T001 → T004 → T005 → T007 → T008 → T009 → T010 → T011
```

T004 (the CLI) is the centre of gravity. T009 (the strip) gated on T008 (parity verified).

## Risk Assessment

### Blocker risks

| Risk | Tasks affected | Probability | Impact | Mitigation |
|---|---|---|---|---|
| `max_cost_class` not threaded through correctly | T001 finding → T004 | Low | High | T001 verifies upfront. Fix is in `BaseAgent` if broken. |
| AC-3 surfaces regressions | T008 → T009 | Low | High | T009 gated on T008. |
| LLM-skill verification (T007) exceeds budget | T007 | Low | Low | Capped to 1 ISIN. Skip if no API key. |
| Volume per umbrella >> expected (iShares can be huge) | T007 | Medium | Low | `--limit-per-umbrella 3` for verification. Full-set production runs documented as long. |
| Three-LEI chain doesn't materialise (some umbrellas missing managementCompany/promoter LEIs) | T007 AC-1 | Medium | Low | Curated YAML comments explicitly note some promoters lack LEIs. Chain count of 1–2 is acceptable per spec AC-1. |

### Resource constraints

| Resource | Bottleneck | Impact | Mitigation |
|---|---|---|---|
| Single developer, sequential critical path | T004 → T005 → T007 | ~5h serial | Acceptable for a 1-day feature. |
| Docker stack restart during T007 | instrument-api ~5s downtime | Negligible | OpenSearch volume persists. |
| LLM cost during AC-6 verification | T007 sub-step | ~$0.05 budget | One-shot; cached afterward via the patch on disk. |

## Completion Criteria

### Per-task DoD

- [ ] Code implemented and self-reviewed.
- [ ] Unit tests added (where applicable) and passing.
- [ ] Acceptance criteria above met.
- [ ] No regressions in adjacent tests.

### Feature DoD (rolls up to spec-002.md DoD)

- [ ] All 11 tasks ticked.
- [ ] AC-1 through AC-6 verified.
- [ ] Legacy `fund_firds --universe` CLI removed; library functions retained.
- [ ] CLAUDE.md current (new CLI pointer + slimmed legacy bullet).
- [ ] Branch ready for PyCharm review and merge.

## Notes & Decisions

- **2026-05-18**: tasks-001.md generated from plan-001.md. No service decomposition; global numbering (T001..T011) used.
- **2026-05-18**: Inheritance from features 001 + 002 (both merged) — layered API, search-mirror per record, lazy opensearch imports, JSON report shape, strict-serial, per-record isolation, `load_dotenv()` at module top. The fund CLI extends — not redesigns — the bond CLI's pattern.
- **Clarifications baked in**: boolean `--enable-factsheet-skill` opt-in (default `web_fetch`); no patch pre-check; no `--limit-per-umbrella` default cap; raw chained-issuer counts only.

---

**Legend**

- [S] = Small (< 4 hours), [M] = Medium (4–8 hours), [L] = Large (> 8 hours)
- **Status**: `[ ]` Pending, `[>]` In Progress, `[x]` Completed, `[!]` Blocked
