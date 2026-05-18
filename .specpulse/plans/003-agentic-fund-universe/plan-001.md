# Implementation Plan: Agentic fund universe

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- PLAN_NUMBER: 001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T11:00:00Z -->

## Specification Reference

- **Spec**: `.specpulse/specs/003-agentic-fund-universe/spec-002.md` (status: clarified)
- **Plan Version**: 1.0

## Architecture Overview

### High-Level Design

```
                ┌──────────────────────────────────┐
                │  src/pipeline/agentic/           │
                │  AGENTS["fund"].assemble_and_    │
                │      persist(client, identifier, │
                │              status,             │
                │              max_cost_class)     │
                │                                  │
                │  ── sources/fund_firds ──        │
                │  ── sources/fund_yahoo ──        │
                │  ── sources/fund_factsheet_patch │
                │  ── sources/fund_factsheet_skill │
                │     (gated by max_cost_class)    │
                │                                  │
                │  ── persist →                    │
                │     pms_golden_fund              │
                │  ── chain → 3 LEIs →             │
                │     pms_golden_issuer            │
                └────────────▲─────────────────────┘
                             │
                ┌────────────┴─────────────┐
                │                          │
        ┌───────┴────────┐         ┌───────┴────────┐
        │ existing       │         │ NEW            │
        │ POST           │         │ CLI loop:      │
        │ /universe/fund │         │ per umbrella → │
        │                │         │ per share-     │
        │                │         │ class ISIN     │
        └────────────────┘         └────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  per-umbrella-LEI       │
                              │  FIRDS enumeration via  │
                              │  iter_issuer_records    │
                              │  + fund_firds.          │
                              │    dedupe_by_isin       │
                              │  (CFI=C* filter)        │
                              └────────────┬────────────┘
                                           ▼
                              ┌─────────────────────────┐
                              │  fund_umbrellas.yml     │
                              │  (curated, 10 LEIs)     │
                              └─────────────────────────┘
```

Plus a documentation-only deliverable: extend `src/pipeline/agentic/README.md` with a "Fund universe data flow" subsection alongside the existing "Equity" and "Bond" ones.

### Technical Stack

- **Language**: Python 3.x.
- **HTTP**: existing `requests`/`httpx` via `pipeline.gold._firds.solr_get` + `assemble_and_persist`'s downstream Yahoo/factsheet calls.
- **OpenSearch**: existing `OpenSearchInstrumentStore` (no schema changes).
- **CLI framework**: `argparse`.
- **Tests**: `pytest` (existing).
- **Env loading**: `python-dotenv` (already in `requirements.txt` per PR #3).

### Key Files

**New:**
- `src/pipeline/agentic/cli/fund_universe.py` — batch entry point.
- `tests/agentic/test_fund_universe_cli.py` — smoke tests.

**Modified:**
- `src/pipeline/agentic/README.md` — Fund universe data-flow subsection.
- `src/pipeline/gold/fund_firds.py` — strip CLI surface (`main`, `argparse`, `write_ndjson`, `__main__`). Keep library functions.
- `CLAUDE.md` — rewrite `fund_firds` bullet under "Legacy bulk fetchers"; add CLI pointer under "Agentic data engineering".

**Read-only references:**
- `src/pipeline/gold/_firds.py` — `iter_issuer_records`, `solr_get`. Shared with bond.
- `src/pipeline/agentic/agents/fund_agent.py` — `FundAgent.default_max_cost_class="llm_skill"`.
- `src/pipeline/agentic/cli/bond_universe.py` — structural template.

**No new helper module, no new requirements.txt deps.**

## Implementation Phases

### Phase 0: Discovery & contract verification — `[HIGH]`

**Timeline**: ~30 min
**Dependencies**: None

#### Tasks

1. [ ] Confirm `pipeline.gold.fund_firds.dedupe_by_isin` filters on CFI=`C*` (spec assumed) — already verified during /sp-spec, recheck briefly.
2. [ ] Grep for external callers of `fund_firds.main` / `fund_firds.write_ndjson` — expect zero matches (same posture as features 001/002).
3. [ ] Spot-check `tests/agentic/test_fund_firds_source.py` (or whatever covers `fund_firds.fetch_by_isin`) — confirm only library APIs are used.
4. [ ] Confirm `BaseAgent.assemble_and_persist` (and `FundAgent.assemble_and_persist`) accept `max_cost_class` and pass it through to `persist.assemble_and_persist` and into the planner. Pop into the source files to verify.
5. [ ] Confirm `persist.assemble_and_persist`'s `extract_leis` walks `umbrella.lei`, `managementCompany.lei`, `promoter.lei` (or equivalent paths) for the fund record. Confirms the 3-record chain claim.

#### Deliverables

Notes appended to this plan under a **Phase 0 findings** block before Phase 1 starts.

### Phase 1: Documentation — `[HIGH]`

**Timeline**: ~30 min
**Dependencies**: Phase 0

#### Tasks

1. [ ] Add a "Fund universe data flow" subsection to `src/pipeline/agentic/README.md`, alongside the existing equity + bond subsections. Cover the four-source order, the three-record issuer chain, and the cost-class default behaviour.
2. [ ] CLAUDE.md: add a one-line pointer to `python -m pipeline.agentic.cli.fund_universe` under "Agentic data engineering" next to the equity + bond pointers.

#### Deliverables

- [ ] README updated.
- [ ] CLAUDE.md updated (new CLI pointer; legacy `fund_firds` rewrite happens in T010 after the strip).

### Phase 2: Batch CLI — `[HIGH]`

**Timeline**: ~2 h
**Dependencies**: Phase 0

#### Tasks

1. [ ] Create `src/pipeline/agentic/cli/fund_universe.py`. Argparse:
   - `--umbrella-lei LEI` (single; mutually exclusive with `--all`).
   - `--all` (default).
   - `--umbrellas PATH` (override YAML).
   - `--limit-per-umbrella N` (no default cap; matches bond).
   - `--enable-factsheet-skill` (boolean opt-in for LLM cost class).
   - `--dry-run`.
   - `--universe-status STATUS` (default `in_universe`).
   - `--report-out PATH`.
   - `--log-level LEVEL`.
2. [ ] `_Outcome` dataclass — same shape as bond's but with `umbrella_lei` field.
3. [ ] `_UmbrellaReport` dataclass (parity with bond's `_IssuerReport`).
4. [ ] `_RunReport` dataclass with `umbrellas: List[_UmbrellaReport]` and totals.
5. [ ] Main loop:
   1. `load_issuers(args.umbrellas)` from legacy `fund_firds` lib.
   2. Filter to single umbrella LEI if requested; exit non-zero with helpful list if unknown.
   3. Determine `max_cost_class = "llm_skill" if args.enable_factsheet_skill else "web_fetch"`.
   4. For each umbrella:
      - `iter_issuer_records(umbrella_lei, FIRDS_FL)` → records.
      - `dedupe_by_isin(records)` → list of share-class entries.
      - Apply `--limit-per-umbrella`.
      - For each ISIN: `AGENTS["fund"].assemble_and_persist(client, identifier, status, max_cost_class=max_cost_class)` then `index_search_hit`. Per-ISIN errors isolated.
   5. Emit per-umbrella summary log line at INFO.
6. [ ] `load_dotenv()` at module top, immediately after `from __future__ import annotations`. Matches the PR #3 convention now used by equity + bond CLIs.
7. [ ] Lazy-import `opensearch_client_from_env` and `index_search_hit` (mirror bond CLI).
8. [ ] Module entrypoint: `if __name__ == "__main__": sys.exit(run())`.

#### Deliverables

- [ ] `fund_universe.py` runnable: `python -m pipeline.agentic.cli.fund_universe --dry-run --umbrella-lei <known-LEI>` exits 0 with a report.
- [ ] `--help` shows all documented flags, including `--enable-factsheet-skill` with a cost-warning hint.

### Phase 3: Smoke tests — `[HIGH]`

**Timeline**: ~1.5 h
**Dependencies**: Phase 2

#### Tasks

1. [ ] `tests/agentic/test_fund_universe_cli.py` — mirror `test_bond_universe_cli.py`.
2. [ ] Fixtures: stub `AGENTS["fund"]` (recording, captures `max_cost_class`), stub `iter_issuer_records`, stub `index_search_hit` via `sys.modules` injection. Test fixtures need `gnr_cfi_code: "CIVSXX"` (CFI starts with 'C') instead of bond's `"DBFTFR"` so they survive `fund_firds.dedupe_by_isin`'s filter.
3. [ ] Tests:
   - [ ] AC-5: `--umbrella-lei <unknown>` non-zero exit + stderr lists known LEIs.
   - [ ] AC-4: `--dry-run` produces report, no agent calls.
   - [ ] Happy path: 2 umbrellas × 3 share-classes → 6 agent calls with `status="in_universe"` AND `max_cost_class="web_fetch"` by default.
   - [ ] **AC-6 (cost-class default)**: default run passes `max_cost_class="web_fetch"` to every `assemble_and_persist` call.
   - [ ] **AC-6 (cost-class opt-in)**: `--enable-factsheet-skill` passes `max_cost_class="llm_skill"` to every call.
   - [ ] Umbrella-level FIRDS failure isolated.
   - [ ] Per-ISIN error isolated → exit code 1, others proceed.
   - [ ] `--limit-per-umbrella 2` caps per-umbrella count.
   - [ ] `--report-out` writes JSON with per-umbrella grouping.
   - [ ] Chained issuer count of 3 reported when stub returns 3 chained.

#### Deliverables

- [ ] Test file passes locally. Runs offline.

### Phase 4: Parity verification + legacy strip — `[HIGH]`

**Timeline**: ~2 h
**Dependencies**: Phases 2 + 3

#### Tasks (Phase 4a — Verification)

1. [ ] Capture legacy snapshot: `python -m pipeline.gold.fund_firds --output data/cache/parity/legacy_funds.ndjson`. Pre-strip.
2. [ ] Rebuild instrument-api container so the new CLI module is in the image.
3. [ ] Single-umbrella smoke: pick the smallest in `fund_umbrellas.yml` (likely a single Vanguard or Xtrackers umbrella) and run `--umbrella-lei <LEI>` with `--limit-per-umbrella 3`. Default `--cap web_fetch`.
4. [ ] Verify counts: `curl localhost:9200/pms_golden_fund/_count` increases by 3; `pms_golden_issuer/_count` increases by up to 3 (umbrella + managementCompany + promoter).
5. [ ] Full curated set smoke: drop `--umbrella-lei`; use `--limit-per-umbrella 3` to keep total ISINs in the 20–30 range. Verify AC-1 (≥1 doc per umbrella with FIRDS share-classes) and AC-2 (idempotent re-run).
6. [ ] AC-3 parity diff via `data/cache/parity/diff_funds.py` (mirror of `diff_bonds.py`). Document divergences for PR body.
7. [ ] **AC-6 LLM-skill verification**: pick one ISIN that does NOT have a pre-curated patch under `data/opensearch/golden/fund/patches/`, run `--umbrella-lei <LEI> --enable-factsheet-skill --limit-per-umbrella 1`, confirm the `find-and-parse-factsheet` skill ran (check logs / patch file created). Budget: ~$0.05 LLM cost for this verification step.

#### Tasks (Phase 4b — Strip)

8. [ ] Strip `pipeline.gold.fund_firds`:
   - Delete `main()`, the `argparse` setup, `write_ndjson`, the `if __name__` block.
   - Remove imports unused after the strip (`argparse`; `Path` only if no remaining usage — likely still used by `load_issuers`).
   - Rewrite module docstring to "library only" per `equity_yahoo` (feature 001) and `bond_firds` (feature 002).
9. [ ] Verify `pipeline.gold.fund_firds.fetch_by_isin` still imports and runs.
10. [ ] Run pytest — expect green.
11. [ ] CLAUDE.md: rewrite the `fund_firds` bullet under "Legacy bulk fetchers" to reflect the slimmed library role.

#### Deliverables

- [ ] AC-1, AC-2, AC-3, AC-6 all met live.
- [ ] Legacy CLI gone; `fetch_by_isin` still importable; existing tests pass.
- [ ] PR-ready divergence summary captured.

### Phase 5: Integration smoke & sign-off — `[MEDIUM]`

**Timeline**: ~30 min
**Dependencies**: Phase 4

#### Tasks

1. [ ] `pytest` clean across the repo.
2. [ ] `POST /instruments/assemble` for one known fund ISIN works (regression check on strip).
3. [ ] `GET /universe/fund` lists the loaded share-classes.
4. [ ] `GET /instruments/search?type=fund` returns search-mirror hits — confirms no equivalent of the bond `ow_type` casing bug here (fund is single-word, already verified during /sp-spec).
5. [ ] Tick DoD in spec-002.md.

#### Deliverables

- [ ] All ACs met.
- [ ] DoD ticked.
- [ ] Branch `feat/agentic-fund-universe` ready for PyCharm review and PR.

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `iter_issuer_records` raises on one umbrella | Low | Low | Built-in retry-then-empty pattern (verified for bond). Defensive per-umbrella try/except already in design. |
| `max_cost_class` not threaded through agent → planner correctly | Low | High | Phase 0 task 4 verifies the wire-up. If broken, fix the agent layer first. |
| Three-record issuer chain doesn't fire (e.g. only umbrella populated, no managementCompany / promoter LEIs in the record) | Medium | Low | `extract_leis` already returns just the distinct LEIs it finds. Curated YAML has 8 of 10 umbrellas with managementCompanyLei; promoter LEIs are intentionally absent (per the YAML comment). Real-world chain count varies 1–3. |
| LLM skill cost overrun during AC-6 verification | Low | Low | Verification uses a single ISIN. Budget capped. Skip if patches already exist. |
| AC-3 surfaces material regressions on share-class fields | Low | Medium | T009 gated on T008. Document divergences in PR body. |
| Fund volume per umbrella very large (>500 share classes for iShares) | Medium | Low | `--limit-per-umbrella N` for smokes; production-scale runs documented as "expect hours". |
| Legacy `fund_firds.main` has hidden importer | Low | Medium | Phase 0 task 2 grep + Phase 4b pytest catch. |

### External Dependencies

| Dependency | Risk | Contingency |
|---|---|---|
| ESMA FIRDS Solr | Medium | Per-umbrella isolation; retry inside the helper. |
| GLEIF (issuer chain) | Low | Already non-fatal via `assemble_and_persist`'s `try/except` on the issuer chain. |
| LLM API (factsheet skill) | Medium | Only fires under `--enable-factsheet-skill`. Failure surfaces as `remaining_gaps` on the outcome; not a batch-aborter. |

## Resource Requirements

### Development

- **Backend Developer**: 1 person. Estimated 1 working day (~7 hours).

### Infrastructure

- **Local Docker stack** for Phase 4 + Phase 5.
- **Optional**: `ANTHROPIC_API_KEY` in `.env` for AC-6's LLM-skill verification step (already wired via docker-compose for instrument-api per CLAUDE.md).

## Success Metrics

- AC-1 through AC-6 all pass live.
- `pytest` clean.
- Net change in lines of code is **negative** (legacy `fund_firds.py --universe` strip exceeds the new CLI's size).
- CLAUDE.md drift: "Legacy bulk fetchers" entry for `fund_firds` shrinks; "Agentic data engineering" gets one new bullet.
- Cost-class control verified end-to-end: default run is free of LLM spend; opt-in run produces a real factsheet patch.

## Rollout Plan

Single-machine internal-tool feature. Standard repo flow: feature branch → PyCharm review → PR → merge to `main` → delete branch (per CLAUDE.md "Branching workflow").

## Definition of Done

- [ ] All five phases complete.
- [ ] All six spec acceptance criteria met.
- [ ] `src/pipeline/agentic/README.md` has a fund-universe section.
- [ ] `pipeline.gold.fund_firds` CLI surface stripped; library retained.
- [ ] `pytest` clean.
- [ ] Branch merged + remote deleted.

## Additional Notes

- **Inheritance from features 001/002**: layered API, search-mirror per record, lazy opensearch imports, JSON report shape (extended to nested per-parent-LEI grouping in bond's `_IssuerReport` pattern), strict-serial concurrency, per-record error isolation, `dotenv` at module top. The fund CLI extends — not redesigns — feature 002's pattern.
- **Decomposition directory not used** — single-service feature.
- Phase 0 findings should be appended in-place before Phase 1 starts.
