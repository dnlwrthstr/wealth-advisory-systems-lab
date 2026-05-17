# Implementation Plan: Agentic equity universe

<!-- FEATURE_DIR: 001-agentic-equity-universe -->
<!-- FEATURE_ID: 001 -->
<!-- PLAN_NUMBER: 001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-17T11:15:00Z -->

## Specification Reference

- **Spec**: `.specpulse/specs/001-agentic-equity-universe/spec-002.md` (status: clarified)
- **Plan Version**: 1.0

## Architecture Overview

### High-Level Design

Two parallel deliverables share one common pipeline:

```
                ┌─────────────────────────────┐
                │  src/pipeline/agentic/      │
                │  (existing planner stack)   │
                │                             │
                │  assemble(identifier,       │
                │           scope="equity",   │
                │           persist=True)     │
                │                             │
                │  ── sources/openfigi ──     │
                │  ── sources/equity_yahoo ── │
                │  ── merger ──> persist ──>  │
                │     pms_golden_equity       │
                │     pms_golden_issuer       │
                └──────────────▲──────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
      ┌───────┴────────┐               ┌────────┴───────┐
      │ existing       │               │ NEW            │
      │ POST           │               │ CLI loop       │
      │ /instruments/  │               │ over an ISIN   │
      │ assemble       │               │ list resolved  │
      │ (instrument-   │               │ from a named   │
      │  api)          │               │ universe       │
      └────────────────┘               └────────────────┘
                                              │
                                              ▼
                                   ┌───────────────────────┐
                                   │ pipeline.agentic      │
                                   │   .universes (NEW)    │
                                   │  Wikipedia → tickers  │
                                   │  → OpenFIGI → ISINs   │
                                   └───────────────────────┘
```

Plus a documentation-only deliverable: `src/pipeline/agentic/README.md` capturing the chain contract.

### Technical Stack

- **Language**: Python 3.x (existing venv).
- **HTTP**: `requests` (already a dep) for Wikipedia + OpenFIGI; `yfinance` for Yahoo.
- **HTML parsing**: `beautifulsoup4` (already used by legacy `equity_yahoo.py`).
- **OpenSearch**: existing `OpenSearchInstrumentStore`, no schema changes.
- **CLI framework**: `argparse` (consistent with the rest of `src/pipeline/`).
- **Tests**: `pytest` (existing), with `requests-mock` or pinned HTML fixtures.

### Key Files

**Touched / new:**
- `src/pipeline/agentic/README.md` — NEW. Architectural contract for the equity chain.
- `src/pipeline/agentic/universes.py` — NEW. Wikipedia table → ticker list. Extracted from legacy.
- `src/pipeline/agentic/cli/__init__.py` — NEW. CLI sub-package.
- `src/pipeline/agentic/cli/equity_universe.py` — NEW. Batch entry point.
- `src/pipeline/agentic/sources/openfigi.py` — maybe extended for ticker → ISIN if not already supported.
- `tests/agentic/test_universes.py` — NEW. Unit tests with pinned HTML fixtures.
- `tests/agentic/test_equity_universe_cli.py` — NEW. CLI smoke test (mocked planner).
- `src/pipeline/gold/equity_yahoo.py` — DELETED in Phase 5.
- `CLAUDE.md` — updated to remove the deleted CLI from "Legacy bulk fetchers".

**Read-only references:**
- `src/pipeline/agentic/assemble.py`, `planner.py`, `manifest.py`, `merger.py`, `persist.py` — entry surface for the loop.
- `src/pipeline/agentic/sources/openfigi.py`, `equity_yahoo.py` — confirm the ticker direction.

## Implementation Phases

### Phase 0: Discovery & contract verification — `[HIGH]`

**Timeline**: ~1 hour
**Dependencies**: None

#### Tasks

1. [ ] Read `src/pipeline/agentic/assemble.py` and `planner.py`; confirm `assemble(identifier, scope, persist)` (or equivalent) is importable as a Python function — not just an HTTP handler.
2. [ ] Read `src/pipeline/agentic/sources/openfigi.py`; confirm whether it accepts a ticker as input or only ISIN. Document the direction.
3. [ ] Read `src/pipeline/gold/equity_yahoo.py`; catalog the Wikipedia-fetch helpers (which functions, which CSS selectors, which universe → table mapping).
4. [ ] Confirm `pipeline.gold.search_index_build` is importable as a function (for the `--rebuild-search` flag).
5. [ ] Spot-check `pms_golden_equity` mapping against `EquityGolden` — note any fields legacy populates that the agentic chain doesn't (these surface in AC-3 diff).

#### Deliverables

- A short notes block (committed in this plan, appended below as **Phase 0 findings**, or inline in the next phase's tasks) — no production code.

### Phase 1: Architectural reference (Part 1 of spec) — `[HIGH]`

**Timeline**: ~2 hours
**Dependencies**: Phase 0

#### Tasks

1. [ ] Create `src/pipeline/agentic/README.md`.
2. [ ] Sections: **What it does**, **Cost-ordered sources per scope** (equity covered; bond/fund stub), **Merge policy**, **Persistence + issuer chaining**, **Manifest invariant**, **Entry points** (HTTP + Python).
3. [ ] Use the existing `equity` scope as the worked example (concrete source list, what each populates).
4. [ ] Cross-link from CLAUDE.md's "Agentic data engineering" block to this README.

#### Deliverables

- [ ] `src/pipeline/agentic/README.md` lands.
- [ ] CLAUDE.md has a one-line pointer to it.

### Phase 2: Extract universe helper — `[HIGH]`

**Timeline**: ~3 hours
**Dependencies**: Phase 0

#### Tasks

1. [ ] Create `src/pipeline/agentic/universes.py`. Public surface: `resolve(universe: str) -> list[str]` returning **tickers** (ISIN resolution is the next phase).
2. [ ] Move the Wikipedia table-parsing helpers verbatim from `src/pipeline/gold/equity_yahoo.py`. Keep the public function names recognisable.
3. [ ] Add on-disk caching under `data/cache/universe/<name>.json` with a 7-day TTL (per spec FR-2). Provide a `--no-cache` escape hatch on the future CLI.
4. [ ] Universes supported: `smi`, `sp500`, `nasdaq100`, `dax40`, `ftse100` (parity with legacy).
5. [ ] Unit tests: pin HTML snapshots of each Wikipedia table under `tests/agentic/fixtures/universe/<name>.html`; assert ticker counts (SMI=20, S&P 500≈500, etc.) and a sample of known tickers.

#### Deliverables

- [ ] `src/pipeline/agentic/universes.py` with `resolve()` covering all 5 universes.
- [ ] `tests/agentic/test_universes.py` green.
- [ ] `data/cache/universe/` writable; sample file committed only if small.

### Phase 3: Ticker → ISIN bridge — `[HIGH]`

**Timeline**: ~2–4 hours (range depends on Phase 0 finding 2)
**Dependencies**: Phase 0, Phase 2

#### Tasks (branch on Phase 0 finding)

**If `openfigi` source already accepts tickers:**

1. [ ] Add a thin function `pipeline.agentic.universes.tickers_to_isins(tickers: list[str]) -> list[Resolution]` that calls the existing source. `Resolution` is a tiny dataclass `(ticker, isin | None, reason | None)`.

**If `openfigi` source only goes ISIN → ticker:**

1. [ ] Extend `src/pipeline/agentic/sources/openfigi.py` with a `lookup_by_ticker(ticker, exchange_code: str | None = None) -> str | None` helper. Keep it in the same module — no new abstractions.
2. [ ] Honour the same `OPENFIGI_API_KEY` env handling and rate-limit posture.
3. [ ] Unit test against a pinned OpenFIGI JSON fixture.

**Both branches:**

4. [ ] Document the resolution path in `src/pipeline/agentic/README.md` (add a section under universe-loader contract).

#### Deliverables

- [ ] `tickers_to_isins()` callable from the upcoming CLI.
- [ ] Test coverage for the new lookup direction (or wrapper).

### Phase 4: Batch CLI — `[HIGH]`

**Timeline**: ~4 hours
**Dependencies**: Phases 2 + 3

#### Tasks

1. [ ] Create `src/pipeline/agentic/cli/__init__.py` (empty marker).
2. [ ] Create `src/pipeline/agentic/cli/equity_universe.py`. Argparse flags:
   - `--universe {smi,sp500,nasdaq100,dax40,ftse100}` (required).
   - `--limit N` (cap ISINs processed; for smoke tests).
   - `--dry-run` (skip persistence).
   - `--no-cache` (force Wikipedia re-fetch).
   - `--rebuild-search` / `--no-rebuild-search` (default: rebuild; resolves deferred clarification #5).
   - `--report-out PATH` (write JSON report).
3. [ ] Pipeline:
   1. Resolve universe → tickers (cached).
   2. Tickers → ISINs (OpenFIGI).
   3. For each ISIN, call the agentic `assemble(identifier=isin, scope="equity", persist=not dry_run)`. **Strict serial** per clarification #3.
   4. Collect per-ISIN outcome: `success | partial | failed (reason)`.
   5. Unless `--no-rebuild-search` or `--dry-run`, call `pipeline.gold.search_index_build.main()` (or equivalent) once at the end.
   6. Emit report (stdout always; JSON if `--report-out`).
4. [ ] Logging: structured per-ISIN at INFO; source-by-source at DEBUG.
5. [ ] Rate-limit handling: catch 429 from OpenFIGI / yfinance, back off (e.g. simple exponential to 60s), retry once, then mark partial. No fancy bookkeeping (strict serial — see clarification #3).
6. [ ] Smoke test `tests/agentic/test_equity_universe_cli.py` with the planner mocked (don't hit live APIs in CI). Verify report shape and exit codes for the unknown-universe case (AC-5).

#### Deliverables

- [ ] CLI runnable: `PYTHONPATH=src python -m pipeline.agentic.cli.equity_universe --universe smi --limit 3 --dry-run`.
- [ ] Unit tests green.

### Phase 5: Parity verification & legacy removal — `[HIGH]`

**Timeline**: ~3 hours
**Dependencies**: Phase 4

#### Tasks

1. [ ] **Before deletion**: run the legacy `python -m pipeline.gold.equity_yahoo --universe smi` once into a side NDJSON; bulk-load into a throwaway OpenSearch namespace or capture per-ISIN JSON.
2. [ ] Run the new CLI against the same OpenSearch (`--universe smi`). Confirm AC-1: ≥18/20 SMI in `pms_golden_equity`, distinct LEIs in `pms_golden_issuer`.
3. [ ] AC-2: re-run the new CLI; confirm no duplicates and provenance preserved.
4. [ ] AC-3: diff legacy vs new output on schema-overlapping fields. Document divergences in the PR description.
5. [ ] AC-4: `--dry-run` writes no documents; report is still populated.
6. [ ] AC-5: `--universe foo` exits non-zero with a helpful message.
7. [ ] Delete `src/pipeline/gold/equity_yahoo.py`.
8. [ ] Grep for stale imports across the tree (`grep -r "pipeline.gold.equity_yahoo"`). Fix any.
9. [ ] Update CLAUDE.md: remove the `equity_yahoo` bullet under "Legacy bulk fetchers"; add a pointer under "Agentic data engineering" pointing at the new CLI.

#### Deliverables

- [ ] AC-1 through AC-5 pass.
- [ ] Legacy file gone; tree builds.
- [ ] CLAUDE.md current.

### Phase 6: Integration & sign-off — `[MEDIUM]`

**Timeline**: ~1 hour
**Dependencies**: Phase 5

#### Tasks

1. [ ] `pytest` clean on the whole repo.
2. [ ] `docker compose up --build` smoke: `instrument-api` still serves `POST /instruments/assemble` for an SMI ISIN unchanged.
3. [ ] Hit `GET /instruments/search?identifier=NESN.SW` and confirm the agentic-assembled record surfaces (validates the `--rebuild-search` step).
4. [ ] Branch `feat/agentic-equity-universe` ready for PyCharm review and merge to `main` (per CLAUDE.md branching workflow).

#### Deliverables

- [ ] Green pytest.
- [ ] Manual smoke checks pass.
- [ ] DoD checklist in spec-002.md ticked.

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Planner not importable as a Python function — only as an HTTP route | Low | High | Phase 0 verifies first. If true, the fix is a small refactor in `assemble.py`/`router.py` — pull the core into a function the router thin-wraps. Adds ~1h. |
| OpenFIGI ticker → ISIN direction not supported by current source | Medium | Medium | Phase 3 has both branches planned. Worst case: ~2h extra. |
| Wikipedia table format drifts between fixture and live | Medium | Medium | Cache + structural assertion in `resolve()`. Fail loudly with a clear error. |
| AC-3 schema diff is large (agentic fills more fields) | Medium | Low | AC-3 explicitly allows divergence on newly-populated fields; document the diff in the PR description, do not block. |
| S&P 500 runtime exceeds 30 min budget | Low | Low | Strict serial is the chosen mode (clarification #3). On free OpenFIGI tier, S&P 500 will be ≈20 min for OpenFIGI alone. With paid key it's fine. Document the requirement in CLI help text. |
| Existing tests assume legacy `equity_yahoo` is importable | Low | Medium | Grep before delete (Phase 5 task 8). Update any that break. |

### External Dependencies

| Dependency | Risk | Contingency |
|---|---|---|
| OpenFIGI free tier (25 req/min) | High for large universes | Document `OPENFIGI_API_KEY` requirement for `sp500` in CLI help. |
| Wikipedia constituent tables | Medium | Pinned-fixture tests + 7-day cache. Manual smoke per universe at PR time. |
| Yahoo Finance via yfinance | Medium | Treat per-ISIN failures as partial success, not batch failure. |

## Resource Requirements

### Development

- **Backend Developer**: 1 person. Estimated 2 working days.

### Infrastructure

- **Local Docker stack** (existing `docker-compose.yml`) for OpenSearch + instrument-api integration testing.
- **OPENFIGI_API_KEY** in `.env` for any S&P 500 / NASDAQ 100 testing.

## Success Metrics

- All five acceptance criteria pass (AC-1 through AC-5 in spec-002.md).
- `pytest` clean.
- Net change in lines of code is **negative** (legacy `equity_yahoo.py` is larger than the new helper + CLI + README combined).
- CLAUDE.md drift: the "Legacy bulk fetchers" section gets one bullet shorter; "Agentic data engineering" gets a new pointer.

## Rollout Plan

Single-machine, internal-tool feature — no staged rollout, no monitoring setup, no team training. Standard repo flow: feature branch → PyCharm review → merge to `main` → delete branch locally and on remote (per CLAUDE.md "Branching workflow").

## Definition of Done

- [ ] All six phases complete.
- [ ] All five spec acceptance criteria met.
- [ ] `src/pipeline/agentic/README.md` exists and is cross-linked from CLAUDE.md.
- [ ] `src/pipeline/gold/equity_yahoo.py` deleted; no stale imports.
- [ ] `pytest` clean; docker-compose smoke OK.
- [ ] Branch merged to `main` and deleted on origin (manual, post-review).

## Additional Notes

- The decomposition directory does not exist for this feature, so no service-specific sub-plans are generated.
- The plan resolves the spec's deferred clarification #5 (`search_index_build` invocation): the CLI exposes `--rebuild-search` / `--no-rebuild-search`, defaulting to rebuild. This avoids a documented "remember to run X next" step for fresh seedings.
- Phase 0's findings should be appended to this plan (in-place) before Phase 1 starts, so the dependency assumptions are recorded.

## Phase 0 findings (T001 + T002, 2026-05-17)

**T001 — Planner / persist entry points**

- `pipeline.agentic.assemble.assemble_golden(scope, identifier, *, budget=10, max_cost_class="web_fetch", run_id=None, now=None) -> AssembleResult` is the pure assemble function. It does **not** write to OpenSearch by design (docstring: "the caller decides whether to PUT").
- `pipeline.agentic.persist.assemble_and_persist(*, client, scope, identifier, budget=10, chain_issuers=True, max_cost_class=None, universe_status=None) -> dict` is the high-level entry that:
  - Runs `assemble_golden`,
  - Writes the primary record to `pms_golden_{scope}` with `refresh="wait_for"`,
  - Walks the record for every embedded LEI and assembles + writes an `IssuerGolden` per LEI to `pms_golden_issuer`.
- **Bonus discovery**: `persist.assemble_and_persist` already accepts a `universe_status` parameter constrained to `{"watchlist", "in_universe", "excluded"}` and stamps it on the primary record. **The universe loader CLI should pass `universe_status="in_universe"`** to mark these records as part of the investable PMS universe — this resolves an unwritten gap in the spec.
- Identifier shape: `{"kind": "isin"|"ticker"|..., "value": "..."}`. The planner accepts a `ticker` kind, but the existing `openfigi` source only fires on `kind == "isin"` (returns `None` otherwise). See T002.
- **No refactor needed for T011.** The CLI calls `assemble_and_persist(client=..., scope="equity", identifier={"kind": "isin", "value": isin}, universe_status="in_universe")` per ISIN.

**T002 — OpenFIGI ticker → ISIN direction: NOT YET SUPPORTED**

- `pipeline.gold.openfigi.fetch_openfigi_by_isin(isin)` is the only direction implemented. OpenFIGI's `/v3/mapping` endpoint itself supports `idType=TICKER`, so the extension is a sibling function — no new dependency.
- `pipeline.agentic.sources.openfigi.fetch` is hard-gated on `identifier_kind == "isin"`.
- **Decision (per plan §Phase 3 branch B)**: add `fetch_openfigi_by_ticker(ticker, exchange_code=None, *, use_cache=True) -> Optional[Dict[str, Any]]` to `src/pipeline/gold/openfigi.py`. Same User-Agent, same cache layout (cache key includes exchange_code to disambiguate), same `OPENFIGI_API_KEY` env-var posture. Surface it via `pipeline.agentic.universes.tickers_to_isins(tickers)` — **do not** wire it into the agentic planner's source for the `ticker` direction, because the existing `equity` source list is documented as ISIN-first and adding a second direction would expand the agentic chain's contract beyond this feature's spec.

**Net impact on T008 estimate**: low end of the 1-3h range — closer to 1.5h. The extension is mechanical.

**No other plan adjustments required.** T011's CLI body is straightforward against `assemble_and_persist`.

**Addendum — agent + universe HTTP layer already exist (T003/T011 refinement, 2026-05-17)**

A deeper read surfaced two layers above raw `persist.assemble_and_persist`:

- `pipeline.agentic.agents.AGENTS = {"equity": EquityAgent, "bond": BondAgent, "fund": FundAgent}` — scope-bound facade. `EquityAgent.assemble_and_persist(*, client, identifier, status, budget=None, max_cost_class=None)` is the per-scope entry point with sensible defaults.
- `backend.instrument_api.universe_router` already exposes `POST /universe/{equity|bond|fund}` driving the same agent. After each persist, it calls `pipeline.gold.search_index_build.index_search_hit(client, scope, record, universe_status=status)` to mirror onto `pms_golden_instrumentsearch` so the record is searchable immediately.
- Existing tests: `tests/agentic/test_universe.py`, `tests/agentic/test_universe_endpoint.py`, `tests/agentic/test_assemble_equity.py`. The HTTP path is exercised; the batch path is not.

**Refinements:**

1. **T011 CLI binds to `AGENTS["equity"].assemble_and_persist`**, not raw `persist.assemble_and_persist`. Matches the HTTP route.
2. **T011 also calls `index_search_hit` per ISIN** so each loaded record surfaces in Find-an-instrument right away — same posture as the HTTP route. This reduces the importance of `--rebuild-search`; keep the flag for full-rebuild scenarios but default it to **off** now (one fewer batch step). Resolves deferred clarification #5 differently than the original plan said — per-ISIN mirroring beats a single end-of-run rebuild.
3. **T003 README** documents three entry layers: planner (`assemble_golden`), persist (`assemble_and_persist`), agent (`EquityAgent.assemble_and_persist`). The batch CLI is the fourth (universe-batch) layer.
4. **No HTTP coupling for the CLI** — call the agent in-process. The CLI does not require `instrument-api` to be running.

**T011 estimate unchanged at ~3h.** The agent layer slightly simplifies the body; the search-index mirror is a 3-line addition.
