# Task Breakdown: Agentic equity universe

<!-- FEATURE_DIR: 001-agentic-equity-universe -->
<!-- FEATURE_ID: 001 -->
<!-- TASK_LIST_ID: tasks-001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-17T11:30:00Z -->
<!-- LAST_UPDATED: 2026-05-17T11:30:00Z -->
<!-- SPEC: spec-002.md -->
<!-- PLAN: plan-001.md -->

## Progress Overview

- **Total Tasks**: 17
- **Completed Tasks**: 17 (100%)
- **In Progress Tasks**: 0
- **Blocked Tasks**: 0
- **Status**: DONE — all 5 acceptance criteria met. Ready for PR.

## Task Categories

### Phase 0 — Discovery & contract verification [Priority: HIGH]

- [x] **T001**: [S] Verify agentic planner is importable as a Python function (read `assemble.py`, `planner.py`; confirm callable surface). — 0.5h ✅ Done 2026-05-17. Entry point: `pipeline.agentic.persist.assemble_and_persist`. See plan-001.md "Phase 0 findings".
- [x] **T002**: [S] Determine OpenFIGI source ticker → ISIN support (read `sources/openfigi.py`; document direction in plan-001.md as a **Phase 0 findings** addendum). — 0.5h ✅ Done 2026-05-17. NOT supported; needs `fetch_openfigi_by_ticker` extension in `gold/openfigi.py`. See plan-001.md.

### Phase 1 — Architectural reference [Priority: HIGH]

- [x] **T003**: [M] Write `src/pipeline/agentic/README.md` covering chain contract (sources, cost ordering, merge, persistence, issuer chaining, manifest invariant, Python + HTTP entry points). — 2h ✅ Done 2026-05-17.
- [x] **T004**: [S] Add cross-link to the new README from CLAUDE.md "Agentic data engineering" section. — 0.5h ✅ Done 2026-05-17.

### Phase 2 — Universe resolver [Priority: HIGH]

- [x] **T005**: [M] Create `src/pipeline/agentic/universes.py` with `resolve(universe) -> list[str]` (tickers). Move Wikipedia table-parsing logic verbatim from `src/pipeline/gold/equity_yahoo.py`. Cover smi, sp500, nasdaq100, dax40, ftse100. — 2h ✅ Done 2026-05-17.
- [x] **T006**: [S] Add disk cache under `data/cache/universe/<name>.json` with 7-day TTL; add `--no-cache` escape hatch wired into the future CLI. — 1h ✅ Done 2026-05-17. `data/cache/` gitignored.
- [x] **T007**: [M] Write `tests/agentic/test_universes.py` with pinned HTML fixtures per universe. Assert ticker counts (SMI=20, S&P 500≈500, etc.) and known-sample tickers. — 1.5h ✅ Done 2026-05-17. 14 tests pass.

### Phase 3 — Ticker → ISIN bridge [Priority: HIGH]

- [x] **T008**: [S/M] Bridge tickers → ISINs via OpenFIGI. Implementation branches on T002 finding: thin wrapper if source already supports the direction, else minimal extension of `sources/openfigi.py` (`lookup_by_ticker`). Honour `OPENFIGI_API_KEY` env var. — 1-3h ✅ Done 2026-05-17. `fetch_openfigi_by_ticker` added to `pipeline.gold.openfigi`; `_strip_yahoo_suffix` whitelist-based (preserves `BRK.B` / `BF.B`).
- [x] **T009**: [S] Unit tests for the new lookup direction against a pinned OpenFIGI JSON fixture. — 0.5h ✅ Done 2026-05-17. 7 new tests in `test_openfigi_source.py`.

### Phase 4 — Batch CLI [Priority: HIGH]

- [x] **T010**: [S] Create `src/pipeline/agentic/cli/__init__.py` (empty marker for sub-package). — 0.1h ✅ Done 2026-05-17.
- [x] **T011**: [L] Create `src/pipeline/agentic/cli/equity_universe.py`. Argparse flags: `--universe`, `--limit`, `--dry-run`, `--no-cache`, `--universe-status` (default `in_universe`), `--report-out`. Strict-serial loop. Per-ISIN error isolation. Per-ISIN search-index mirror via `index_search_hit`. JSON report emission. — 3h ✅ Done 2026-05-17. Opensearch-dependent imports lazy for test compatibility.
- [x] **T012**: [M] Smoke test `tests/agentic/test_equity_universe_cli.py` with planner + OpenFIGI + yfinance mocked. Cover: AC-4 (`--dry-run` no writes), AC-5 (unknown universe non-zero exit), basic happy path. — 1.5h ✅ Done 2026-05-17. 10 tests pass.

### Phase 5 — Parity verification & legacy removal [Priority: HIGH]

- [x] **T013**: [M] Capture legacy `equity_yahoo --universe smi` output (NDJSON or per-ISIN JSON) for the parity diff. Pre-deletion snapshot. — 1h ✅ Done 2026-05-18. 20 docs at `data/cache/parity/legacy_smi.ndjson`.
- [x] **T014**: [M] Run new CLI `--universe smi` against local OpenSearch; verify AC-1 (≥18/20 in `pms_golden_equity`, distinct LEIs in `pms_golden_issuer`) and AC-2 (idempotent re-run, no duplicates). — 1h ✅ Done 2026-05-18. AC-1: 20/20 persisted (19 success + 1 partial). AC-2: re-run identical counts. Findings: OpenFIGI ticker direction misses on SIX listings (expected); planner's `six_ticker_isin` recovers all 20 ISINs via the ticker-fallback path built into T011.
- [x] **T015**: [M] Diff legacy vs new `pms_golden_equity` documents on schema-overlapping fields; document the divergence list in the eventual PR body (AC-3). — 1h ✅ Done 2026-05-18. No regressions. New chain populates `universeStatus`, `secondaryListings`, `firstTradingDate` (by design); shared fields differ on `identifierList` (FIGI/CFI/valor added), `issuer` (richer FIRDS data), `cfiCode` (FIRDS authoritative vs yfinance heuristic). **Found one legacy data bug**: yfinance returned `JP3869930002` as ISIN for PGHN.SW; the curated `six_ticker_isin.yml` correctly maps it to `CH0024608827`. Diff script + report at `data/cache/parity/diff_smi.py` and `diff_smi_report.md` (gitignored).
- [x] **T016** (revised): [S] Strip the universe-loader CLI surface from `src/pipeline/gold/equity_yahoo.py` — delete `UNIVERSE_SOURCES`, `load_universe`, `_fetch_wikipedia`, `WIKI_USER_AGENT`, `WIKI_FETCH_TIMEOUT`, `main()`, the `argparse` setup, and `write_ndjson` if unused. **Keep** `fetch_by_identifier`, `fetch_one`, `yahoo_info_to_golden`, and supporting helpers — they're imported by `pipeline.agentic.sources.equity_yahoo`. Update CLAUDE.md: rewrite the `equity_yahoo` bullet under "Legacy bulk fetchers" to reflect the slimmed-down library role. — 1h ✅ Done 2026-05-18. 99 lines removed. Module docstring rewritten. CLAUDE.md updated. 162/162 tests still pass.

### Phase 6 — Integration & sign-off [Priority: MEDIUM]

- [x] **T017**: [S] Final integration smoke: `pytest` clean, `docker compose up --build`, `POST /instruments/assemble` for one SMI ISIN still works, `GET /instruments/search?identifier=NESN.SW` returns the new agentic record. Tick DoD in spec-002.md. — 1h ✅ Done 2026-05-18. `pytest`: 162/162. `POST /instruments/assemble` for CH0038863350 → quality_score 0.933. `GET /instruments/search?identifier=NESN.SW` → finds EQG-CH0038863350-XSWX-001. `GET /universe` → 23 in_universe items.

## Task Details

### T001 — Verify planner is importable as a Python function

- **Description**: Read `src/pipeline/agentic/assemble.py` and `planner.py`. Confirm there is a Python-callable entry point (e.g. `assemble(identifier, scope, persist)`), not just an HTTP route. If only HTTP-bound, file the refactor as a sub-task of T011.
- **Acceptance Criteria**:
  - [ ] Notes appended to plan-001.md under **Phase 0 findings** identifying the function name and signature.
  - [ ] Decision recorded: "ready to import" or "needs Phase 4 refactor".
- **Dependencies**: None.
- **Files touched**: plan-001.md (read-only review of `src/pipeline/agentic/`).
- **Risk**: Low.

### T002 — Determine OpenFIGI ticker → ISIN direction

- **Description**: Inspect `src/pipeline/agentic/sources/openfigi.py`. Determine if the source already handles ticker → ISIN or only ISIN → ticker. Determines whether T008 is a wrapper or a small extension.
- **Acceptance Criteria**:
  - [ ] Notes appended to plan-001.md under **Phase 0 findings**: "supports both directions" / "needs `lookup_by_ticker` extension".
- **Dependencies**: None.
- **Files touched**: plan-001.md (read-only review).
- **Risk**: Low.

### T003 — Write `src/pipeline/agentic/README.md`

- **Description**: Architectural reference for the agentic platform with the equity scope as the worked example. Sections per plan-001.md Phase 1.
- **Acceptance Criteria**:
  - [ ] File exists and renders.
  - [ ] Covers: what it does; cost-ordered sources for `equity` (named, with what each populates); merge policy; persistence + issuer chaining; manifest-loader invariant; entry points (Python + HTTP).
  - [ ] Bond/fund scopes are stubbed (one line each) for future contributors.
- **Dependencies**: T001 (need to name the Python entry point accurately).
- **Files touched**: `src/pipeline/agentic/README.md` (new).
- **Risk**: Low.

### T004 — Cross-link from CLAUDE.md

- **Description**: One-line pointer under "Agentic data engineering" in `CLAUDE.md` directing readers to the new README for deeper detail.
- **Acceptance Criteria**:
  - [ ] CLAUDE.md links to `src/pipeline/agentic/README.md` once.
- **Dependencies**: T003.
- **Files touched**: `CLAUDE.md`.
- **Risk**: Low.

### T005 — Create `pipeline.agentic.universes` with `resolve()`

- **Description**: New module with `resolve(universe: str) -> list[str]` returning tickers. Move parsing logic verbatim from `src/pipeline/gold/equity_yahoo.py` — function names recognisable. All 5 universes covered.
- **Acceptance Criteria**:
  - [ ] `pipeline.agentic.universes.resolve("smi")` returns 20 tickers.
  - [ ] All 5 universes import-able and resolve-able.
  - [ ] Module is the **only** owner of Wikipedia parsing — legacy `equity_yahoo.py` no longer imported by anything new.
- **Dependencies**: None (independent from Phase 0/1).
- **Files touched**: `src/pipeline/agentic/universes.py` (new).
- **Risk**: Low (logic is being moved, not redesigned).

### T006 — Add 7-day disk cache for universe lookups

- **Description**: Cache resolved ticker lists under `data/cache/universe/<name>.json` with a 7-day TTL. Honour a `--no-cache` flag passed through from the CLI (wired in T011).
- **Acceptance Criteria**:
  - [ ] Second call within 7 days reads from cache (verified via timing or by deleting the live network call in tests).
  - [ ] `data/cache/universe/` is gitignored if it isn't already.
- **Dependencies**: T005.
- **Files touched**: `src/pipeline/agentic/universes.py`, `.gitignore` (if needed).
- **Risk**: Low.

### T007 — Tests for `pipeline.agentic.universes`

- **Description**: Pinned-fixture tests so the parser doesn't break silently if Wikipedia drifts. One HTML fixture per universe under `tests/agentic/fixtures/universe/`.
- **Acceptance Criteria**:
  - [ ] Test asserts ticker count per universe.
  - [ ] Test asserts a known sample (e.g. SMI contains `NESN`, S&P 500 contains `AAPL`).
  - [ ] Test runs offline (no network).
- **Dependencies**: T005.
- **Files touched**: `tests/agentic/test_universes.py`, `tests/agentic/fixtures/universe/*.html`.
- **Risk**: Low.

### T008 — Ticker → ISIN bridge via OpenFIGI

- **Description**: Conditional implementation per T002:
  - If existing source supports the direction → thin wrapper in `universes.py`: `tickers_to_isins(tickers) -> list[Resolution]`.
  - Else → add `lookup_by_ticker(ticker, exchange_code=None) -> str | None` to `sources/openfigi.py`. Same env-var posture, same retry behaviour.
- **Acceptance Criteria**:
  - [ ] Given a list of tickers, returns a list of `(ticker, isin | None, reason | None)` tuples or equivalent.
  - [ ] Unknown / ambiguous tickers fail soft, surfacing in the report.
- **Dependencies**: T002, T005.
- **Files touched**: `src/pipeline/agentic/universes.py` and possibly `src/pipeline/agentic/sources/openfigi.py`.
- **Risk**: Medium — branch is unresolved until T002.

### T009 — Unit tests for ticker → ISIN lookup

- **Description**: Pinned OpenFIGI JSON response fixtures; verify lookup parses the response and handles 0-match / multi-match cases.
- **Acceptance Criteria**:
  - [ ] Happy path → returns the expected ISIN.
  - [ ] No match → returns `None` with a reason.
  - [ ] Rate-limit (429) → raises or returns a specific failure marker (whichever matches the existing source's contract).
- **Dependencies**: T008.
- **Files touched**: `tests/agentic/test_universes.py` (or a sibling file).
- **Risk**: Low.

### T010 — CLI sub-package marker

- **Description**: Trivial `__init__.py` so `python -m pipeline.agentic.cli.equity_universe` resolves.
- **Acceptance Criteria**:
  - [ ] File exists.
- **Dependencies**: None.
- **Files touched**: `src/pipeline/agentic/cli/__init__.py` (new, empty).
- **Risk**: None.

### T011 — Batch CLI `equity_universe.py`

- **Description**: Main deliverable. Argparse flags per plan-001.md Phase 4. Strict-serial loop per clarification #3. Per-ISIN outcome captured (`success | partial | failed (reason)`). Calls `pipeline.gold.search_index_build` at end unless suppressed. JSON report emission.
- **Acceptance Criteria**:
  - [ ] `python -m pipeline.agentic.cli.equity_universe --universe smi --limit 3 --dry-run` runs without writes.
  - [ ] On a real run, `pms_golden_equity` is populated and `pms_golden_issuer` receives chained writes for distinct LEIs.
  - [ ] Report (stdout) lists per-ISIN outcomes + summary line.
  - [ ] 429 from OpenFIGI is retried once with backoff before marking failed.
- **Dependencies**: T005, T008, T010 (and Phase 0 findings).
- **Files touched**: `src/pipeline/agentic/cli/equity_universe.py` (new).
- **Risk**: Medium — most logic in the feature; integration surface with existing planner.

### T012 — CLI smoke tests

- **Description**: Tests against a fully-mocked planner + OpenFIGI + yfinance. Cover AC-4 (`--dry-run` writes nothing), AC-5 (unknown universe non-zero exit), happy path (mocked successes), retry-on-429.
- **Acceptance Criteria**:
  - [ ] AC-4 covered by an assertion that the mocked persist function is not called.
  - [ ] AC-5 covered by an assertion on `SystemExit` non-zero + stderr content.
  - [ ] Test runs offline.
- **Dependencies**: T011.
- **Files touched**: `tests/agentic/test_equity_universe_cli.py` (new).
- **Risk**: Low.

### T013 — Capture legacy output for parity diff

- **Description**: Before deletion, run `python -m pipeline.gold.equity_yahoo --universe smi` and capture output (NDJSON or per-ISIN documents from OpenSearch). Stash under `data/cache/parity/legacy_smi.ndjson` (gitignored).
- **Acceptance Criteria**:
  - [ ] Legacy snapshot exists locally.
  - [ ] Reproducible: any reviewer can re-run on the prior commit.
- **Dependencies**: None (uses pre-existing legacy code).
- **Files touched**: `data/cache/parity/` (gitignored).
- **Risk**: Low.

### T014 — Live SMI run with new CLI; AC-1, AC-2

- **Description**: With docker-compose OpenSearch up, run the new CLI with `--universe smi` (no `--dry-run`). Verify counts in both indices via `curl localhost:9200/pms_golden_equity/_count` and `pms_golden_issuer/_count`. Re-run and confirm no duplicates.
- **Acceptance Criteria**:
  - [ ] AC-1 met.
  - [ ] AC-2 met (idempotent re-run).
- **Dependencies**: T011, T013 (snapshot first).
- **Files touched**: none (verification).
- **Risk**: Medium — touches live local services.

### T015 — Parity diff & PR body documentation

- **Description**: Diff per-ISIN documents from T013 (legacy) and T014 (new) on schema-overlapping fields. Document divergences in the PR body. Expected: new chain populates some fields legacy left blank (LEI, FIGI, CFI per CLAUDE.md note). Field-level non-regressions on the overlapping fields.
- **Acceptance Criteria**:
  - [ ] Divergence summary written to a scratchpad and pasted into the PR description at merge time.
  - [ ] No silent **regression** on a field legacy populated.
- **Dependencies**: T013, T014.
- **Files touched**: PR description at review time.
- **Risk**: Medium — surfaces unexpected schema drift.

### T016 — Delete legacy + update CLAUDE.md

- **Description**: Per clarification #4, delete `src/pipeline/gold/equity_yahoo.py` entirely. Grep for `pipeline.gold.equity_yahoo` and fix any stale imports. CLAUDE.md: remove the bullet under "Legacy bulk fetchers" for `equity_yahoo`; add a pointer to the new CLI under "Agentic data engineering".
- **Acceptance Criteria**:
  - [ ] File deleted.
  - [ ] Zero remaining imports of the deleted module.
  - [ ] CLAUDE.md current.
- **Dependencies**: T015 (verify parity before deleting).
- **Files touched**: `src/pipeline/gold/equity_yahoo.py` (deleted), `CLAUDE.md`, any callers.
- **Risk**: Medium — premature deletion before parity is the worst case; gated on T015.

### T017 — Final integration smoke & DoD tick

- **Description**: `pytest` clean. `docker compose up --build`. Hit `POST /instruments/assemble` for a known SMI ISIN — same behaviour as before. Hit `GET /instruments/search?identifier=NESN.SW` — record surfaces. Tick DoD checklist in `spec-002.md`.
- **Acceptance Criteria**:
  - [ ] `pytest` exits 0.
  - [ ] `instrument-api` smoke passes.
  - [ ] DoD ticked in spec-002.md.
- **Dependencies**: T016.
- **Files touched**: `spec-002.md` (DoD checkboxes).
- **Risk**: Low.

## Dependencies

### Task dependency graph

```
T001 ─┐
      ├──► T003 ──► T004
T002 ─┤
      └──► T008 ──► T009
                       │
              T005 ────┤
              │        │
              ├─► T006 │
              ├─► T007 │
              │        │
              T010 ────┤
                       ▼
                      T011 ──► T012
                              │
                       T013 ──┴──► T014 ──► T015 ──► T016 ──► T017
```

### External dependencies

- **OpenFIGI**: free tier (25 req/min) is fine for T014 (SMI=20 names). `OPENFIGI_API_KEY` required for S&P 500 / NASDAQ 100 smoke runs.
- **OpenSearch**: local `docker compose up` for T014, T017.
- **Yahoo Finance** via `yfinance`: rate-limit and reliability are best-effort.

## Parallel Execution Opportunities

### Can be done in parallel

- **T001 ∥ T002**: independent code reads.
- **T003 ∥ T005**: README writing can start as soon as T001 finishes; `universes.py` extraction is decoupled from the README.
- **T005 → (T006 ∥ T007)**: cache and tests are independent once the module exists.

### Must be sequential (critical path)

```
T002 → T008 → T011 → T012 → T014 → T015 → T016 → T017
```

T011 is the centre of gravity — most other tasks feed into or block on it.

## Risk Assessment

### Blocker risks

| Risk | Tasks affected | Probability | Impact | Mitigation |
|---|---|---|---|---|
| T001 finds planner is HTTP-only, not importable | T011 | Low | High | Refactor cost ≈ 1h; absorb into T011. Spec already calls it out (plan §Phase 0). |
| T002 finds OpenFIGI source needs extension | T008 | Medium | Low | T008 has both branches; extension is small. |
| Wikipedia table drift breaks T005/T007 | T005, T007 | Low | Medium | Pinned fixtures detect drift in CI; live fetch is independently cacheable per universe. |
| T014 OpenFIGI rate-limit slows SMI run | T014 | Low | Low | SMI = 20 names = 1 minute on free tier. Within budget. |
| T015 surfaces material schema regressions | T015, T016 | Medium | High | T016 is gated on T015; do not delete legacy if regressions exist. Open a follow-up sub-spec instead. |
| Hidden import of legacy module breaks pytest after T016 | T016, T017 | Low | Medium | Grep before delete (T016 task body). Pytest in T017 catches anything missed. |

### Resource constraints

| Resource | Bottleneck | Impact | Mitigation |
|---|---|---|---|
| Single developer, sequential critical path | T011 → T014 chain | ~5h serial | Acceptable for a 2-day feature. |
| OpenFIGI free quota during S&P 500 smoke | T014 if expanded | 20 min per universe | Out of scope for AC verification (SMI only). Document key requirement for users. |

## Completion Criteria

### Per-task DoD

- [ ] Code implemented and self-reviewed.
- [ ] Unit tests written (where the task involves logic) and passing.
- [ ] Acceptance criteria above met.
- [ ] No regressions in adjacent tests.

### Feature DoD (rolls up to spec-002.md DoD)

- [ ] All 17 tasks ticked.
- [ ] AC-1 through AC-5 in spec-002.md verified.
- [ ] Legacy `equity_yahoo.py` deleted.
- [ ] CLAUDE.md current.
- [ ] Branch ready for PyCharm review and merge.

## Notes & Decisions

- **2026-05-17**: tasks-001.md generated from plan-001.md. No service decomposition (single-service feature), so global numbering (T001..T017) is used per the framework's "no decomposition" branch.
- **2026-05-17**: Clarification #5 (`search_index_build` invocation) resolved at task level: T011 owns the `--rebuild-search` flag, default true. Removes the deferred question from spec-002.md.
- **Open**: per-ISIN concurrency stays strict-serial (clarification #3); revisit only if S&P 500 runtime turns out unworkable on paid OpenFIGI.

---

**Legend**

- [S] = Small (< 4 hours), [M] = Medium (4–8 hours), [L] = Large (> 8 hours)
- [P] = Priority, [D] = Deferred, [B] = Blocked
- **Status**: `[ ]` Pending, `[>]` In Progress, `[x]` Completed, `[!]` Blocked
