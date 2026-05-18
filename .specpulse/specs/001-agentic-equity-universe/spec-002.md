# Specification: Agentic equity universe — document existing chain + add batch CLI

<!-- FEATURE_DIR: 001-agentic-equity-universe -->
<!-- FEATURE_ID: 001 -->
<!-- SPEC_NUMBER: 002 -->
<!-- STATUS: clarified -->
<!-- SUPERSEDES: spec-001.md (placeholder skeleton) -->
<!-- CREATED: 2026-05-17T11:00:00Z -->

## Executive Summary

The equity slice of the agentic instrument-data platform under `src/pipeline/agentic/` already assembles a single equity from an ISIN by chaining `openfigi → equity_yahoo` and persists the resulting `EquityGolden` to `pms_golden_equity` (with chained issuer assembly to `pms_golden_issuer`). What's missing is a **batch entry point**: a way to seed a whole named universe (SMI, S&P 500, …) through the same agentic chain instead of through the legacy bulk fetcher at `src/pipeline/gold/equity_yahoo.py --universe`.

This spec does two things:

1. **Documents the existing agentic equity chain** as a stable contract — sources, planner cost ordering, merge policy, persistence, issuer chaining — so future per-scope work (bond, fund) can mirror it.
2. **Adds an `equity-universe` batch CLI** under `src/pipeline/agentic/` that resolves a named universe to ISINs and calls the existing `assemble(scope="equity", persist=True)` per ISIN. The legacy `src/pipeline/gold/equity_yahoo.py --universe` path is removed once parity is verified.

No new abstractions: the CLI is a thin loop over the existing planner. The agentic platform's source registry, manifest loader, merge policy, and OpenSearch writes are reused as-is.

## Description

### Part 1 — Document the existing agentic equity chain (no code change)

Add a short architectural reference under `src/pipeline/agentic/README.md` (or extend `docs/`) capturing:

- **Sources in cost order**: `openfigi` (ISIN → FIGI / ticker / name; 25 req/min free, 250 req/min with `OPENFIGI_API_KEY`) → `equity_yahoo` (yfinance overlay; reads ticker from `identifierList.tickerSymbol` set by openfigi).
- **Entry point**: `POST /instruments/assemble` on `instrument-api` (port 8003), payload `{identifier, scope: "equity", persist: bool}`.
- **Persistence**: with `persist=true`, writes the composed `EquityGolden` to `pms_golden_equity`, then chains into issuer assembly for every embedded LEI (writes to `pms_golden_issuer` via the `issuer_gleif` source).
- **Merge policy**: fill-empty-only with per-field provenance recorded on the document.
- **Manifest contract**: source descriptors in `src/pipeline/agentic/registry/`, per-scope field annotations in `src/pipeline/agentic/annotations/`. Manifest loader raises at import if annotations and the pydantic model disagree on field names.

### Part 2 — Add `equity-universe` batch CLI

A new module under `src/pipeline/agentic/cli/equity_universe.py` (path subject to plan):

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.equity_universe \
    --universe smi|sp500|nasdaq100|dax40|ftse100 \
    [--limit N] [--dry-run] [--concurrency K]
```

Behaviour:

- Resolves the universe name to a list of ISINs. Universe lists are sourced from Wikipedia (same as legacy `equity_yahoo --universe`), but the ticker → ISIN mapping goes through OpenFIGI (the existing source already handles ticker → ISIN; we just invoke it in the unusual direction, or extend it minimally).
- For each ISIN, calls the agentic assemble loop with `scope="equity", persist=True` — same code path as the API endpoint.
- Reports per-ISIN outcome (success / partial / failed) and a summary.
- Honours OpenFIGI rate limits via a shared client or a simple token bucket.
- `--dry-run` skips persistence; useful for verifying universe resolution and source availability.
- The legacy `src/pipeline/gold/equity_yahoo.py --universe` is removed in the same commit as the parity verification (see Acceptance Criteria).

## Functional Requirements

### FR-1 — Document existing chain

- [ ] Architectural reference exists for `src/pipeline/agentic/` scope=equity, covering source list, cost ordering, merge policy, persistence, issuer chaining, and the manifest-loader invariant.
- [ ] Reference lives where a new contributor will find it (project README, or `src/pipeline/agentic/README.md`, or extends CLAUDE.md — exact location decided in `/sp-plan`).

### FR-2 — Universe resolution

- [ ] CLI accepts `--universe` from the set `{smi, sp500, nasdaq100, dax40, ftse100}` (parity with legacy `equity_yahoo.py`).
- [ ] Resolution produces a list of ISINs. Source: Wikipedia ticker list → OpenFIGI ticker → ISIN lookup. Wikipedia fetch is cached on disk under `data/cache/universe/<name>.json` with a 7-day TTL.
- [ ] Unknown universe name exits non-zero with a clear error listing the supported set.

### FR-3 — Per-ISIN assembly

- [ ] For each resolved ISIN, the CLI invokes the same in-process assemble entry point used by `POST /instruments/assemble` (i.e. the planner under `src/pipeline/agentic/`), with `scope="equity", persist=True`.
- [ ] Per-ISIN failures are isolated: one bad ISIN does not abort the batch.
- [ ] On success, the `EquityGolden` lands in `pms_golden_equity` and the embedded LEI triggers an `IssuerGolden` write to `pms_golden_issuer`.

### FR-4 — Rate limiting

- [ ] CLI respects OpenFIGI's per-minute quota (25 req/min free tier, 250 with key). On 429, back off and retry.
- [ ] yfinance is treated as best-effort — transient failures are logged, not retried indefinitely.

### FR-5 — Reporting

- [ ] CLI writes a run report (stdout + optional `--report-out path.json`) with: total ISINs, successes, partial successes (assembled but some sources empty), failures with reason, elapsed time, OpenFIGI requests used.

### FR-6 — Replace legacy path

- [ ] `src/pipeline/gold/equity_yahoo.py --universe` is removed.
- [ ] Any documentation referencing the legacy path (CLAUDE.md "Legacy bulk fetchers" section) is updated.

### Non-Functional Requirements

- **Performance**: SMI (20 names) in under 2 minutes on free OpenFIGI tier; S&P 500 (500 names) in under 30 minutes on a 250 req/min key. Single-machine, single-process is acceptable; concurrency is opportunistic.
- **Reliability**: idempotent re-runs — re-running the same universe should converge to the same state in OpenSearch, not duplicate.
- **Security**: `OPENFIGI_API_KEY` loaded from the existing project `.env` (already wired into docker-compose for `instrument-api`); CLI reads the same env var.
- **Observability**: structured logging per ISIN (level INFO for outcomes, DEBUG for source-by-source detail).

## User Stories

- **US-1** — As a data engineer seeding a fresh OpenSearch instance, I want to run one CLI invocation to load the SMI equities through the agentic chain so that I get the same golden record shape as the per-ISIN API path.
- **US-2** — As a backend developer adding a new equity source (e.g. SEC EDGAR), I want a single chain that both the API and the batch loader use so that I implement the source once and it shows up in both.
- **US-3** — As a maintainer reading the codebase for the first time, I want a single architectural document describing the agentic equity chain so that I can answer "what runs, in what order, and where do the outputs land" without grepping.

## Acceptance Criteria

- [ ] **AC-1** Given a clean local OpenSearch, when I run `python -m pipeline.agentic.cli.equity_universe --universe smi`, then `pms_golden_equity` contains ≥18 of the 20 SMI constituents (allowing 2 transient OpenFIGI / yfinance failures) and `pms_golden_issuer` contains the corresponding distinct LEIs.
- [ ] **AC-2** Given the same OpenSearch state, when I re-run the same command, then no duplicate documents are created and field-level provenance is preserved.
- [ ] **AC-3** Given an explicit ISIN list passed through the legacy `equity_yahoo.py --universe smi` path on the prior commit, when I diff the resulting `pms_golden_equity` documents against the new CLI's output, then the schema-overlapping fields match (modulo timestamps and any fields newly populated by the agentic chain).
- [ ] **AC-4** Given `--dry-run`, when the CLI runs, then no writes hit OpenSearch and the report still shows per-ISIN resolution outcomes.
- [ ] **AC-5** Given an unsupported `--universe foo`, when the CLI runs, then exit code is non-zero and stderr lists the supported set.

## Technical Constraints

### In scope

- Scope=equity only. Bond and fund scopes are out of scope (separate features).
- Wikipedia + OpenFIGI for universe resolution. No paid identifier services.
- Reuse `src/pipeline/agentic/` planner, registry, annotations, merge — no parallel framework.

### Out of scope

- Adding new equity sources (separate feature).
- A scheduled / cron loader (one-shot CLI only).
- Frontend changes — "Find an instrument" already reads from `pms_golden_instrumentsearch` via the existing rebuild path.
- Bond / fund universe loaders.

### Dependencies

- **External APIs**: OpenFIGI, Yahoo Finance (yfinance), Wikipedia (HTML scrape of constituent tables).
- **Database**: existing `pms_golden_equity`, `pms_golden_issuer`, `pms_golden_instrumentsearch` indices. No mapping changes.
- **Libraries**: `yfinance`, `requests` / `httpx`, `beautifulsoup4` (already used by the legacy Wikipedia fetcher).

### Implementation Notes

- The legacy `src/pipeline/gold/equity_yahoo.py` contains the Wikipedia-table-parsing logic already. Either extract that into a shared helper (`pipeline.agentic.universes`) before deleting the legacy CLI, or copy + adapt it inline. Decision deferred to `/sp-plan`.
- The agentic planner needs to be reachable as a Python callable, not just via HTTP. Confirm during `/sp-plan` that the planner is importable directly from `src/pipeline/agentic/` (it should be — `instrument-api` imports it).
- OpenFIGI ticker → ISIN lookup direction: the current `openfigi` source goes ISIN → ticker. Confirm during `/sp-plan` whether the same source handles the reverse direction; if not, a small extension is in scope.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenFIGI rate limit slows S&P 500 ingest | High | Medium | Require `OPENFIGI_API_KEY` for universes >50 names; document in CLI help. |
| Wikipedia constituent tables change format | Medium | Medium | Cache + a smoke test per universe; fail loudly with a structural error. |
| Schema drift between legacy and agentic output blocks AC-3 | Medium | Medium | AC-3 explicitly allows divergence on newly-populated fields; document the diff in the plan. |
| yfinance returns empty for delisted/illiquid names | Low | Low | Treat as partial success, not failure; report counts. |
| Removing legacy path before parity is verified | Low | High | Removal and verification land in the same commit; PR review gates this. |

## Testing Strategy

- **Unit tests**:
  - `pipeline.agentic.universes` (or chosen helper) — Wikipedia HTML → ticker list, against pinned fixtures.
  - Ticker → ISIN lookup against a fixture OpenFIGI response.
  - Per-ISIN assemble already covered by existing tests under `src/pipeline/agentic/` — no new coverage required there.
- **Integration tests**:
  - CLI end-to-end against a docker-compose OpenSearch with `--universe smi --limit 3`. Verify document counts in `pms_golden_equity` and `pms_golden_issuer`.
- **End-to-end / manual**:
  - After `--universe smi`, hit `GET /instruments/search?identifier=NESN.SW` on instrument-api and confirm the assembled record surfaces (depends on the existing `search_index_build` rebuild — invoke it from the CLI or document the follow-up).

## Definition of Done

- [x] All functional requirements implemented.
- [x] All acceptance criteria met (AC-1 through AC-5).
- [x] `src/pipeline/gold/equity_yahoo.py --universe` removed (revised T016: strip universe loader, keep `fetch_by_identifier` library); CLAUDE.md updated.
- [x] Architectural reference for the agentic equity chain landed (`src/pipeline/agentic/README.md`).
- [x] Tests pass: `pytest` 162/162.
- [ ] Branch `feat/agentic-equity-universe` merged into `main` via PyCharm review (pending user action).
- [x] Local `docker compose up --build` smoke-checked: `instrument-api` still serves `POST /instruments/assemble` unchanged; `GET /instruments/search?identifier=NESN.SW` returns the agentic record; `GET /universe` lists 23 in_universe equities.

## Clarifications (resolved 2026-05-17)

1. ✅ **CLARIFIED — Architectural reference location**: `src/pipeline/agentic/README.md`. Package-level README, co-located with the code it documents.
2. ✅ **CLARIFIED — Universe helper location**: extract a shared `pipeline.agentic.universes` module before deleting the legacy CLI. Reusable when bond/fund universes ever need similar resolution.
3. ✅ **CLARIFIED — Concurrency model**: strict serial. Simplest, naturally respects OpenFIGI's quota. S&P 500 on a paid key still finishes well inside the 30 min budget.
4. ✅ **CLARIFIED — Legacy removal scope**: delete the entire `src/pipeline/gold/equity_yahoo.py` fetcher once AC-3 parity is verified. The "Legacy bulk fetchers" section of CLAUDE.md shrinks accordingly.
5. **DEFERRED to plan-time** — `search_index_build` invocation. Decided in `/sp-plan` (likely: call it once at the end of a batch run via a `--rebuild-search` flag, default true).

---

*Generated by /sp-spec on 2026-05-17. Supersedes spec-001.md (bootstrap skeleton). Clarifications resolved interactively on the same day.*
