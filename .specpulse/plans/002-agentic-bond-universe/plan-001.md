# Implementation Plan: Agentic bond universe

<!-- FEATURE_DIR: 002-agentic-bond-universe -->
<!-- FEATURE_ID: 002 -->
<!-- PLAN_NUMBER: 001 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T06:30:00Z -->

## Specification Reference

- **Spec**: `.specpulse/specs/002-agentic-bond-universe/spec-002.md` (status: clarified)
- **Plan Version**: 1.0

## Architecture Overview

### High-Level Design

```
                ┌──────────────────────────────────┐
                │  src/pipeline/agentic/           │
                │  (existing planner / agents)     │
                │                                  │
                │  AGENTS["bond"].assemble_and_    │
                │      persist(client, identifier, │
                │              status=...)         │
                │                                  │
                │  ── sources/bond_firds ──        │
                │  ── persist → pms_golden_bond ── │
                │  ── chain → pms_golden_issuer ── │
                └────────────▲─────────────────────┘
                             │
                ┌────────────┴─────────────┐
                │                          │
        ┌───────┴────────┐         ┌───────┴────────┐
        │ existing       │         │ NEW            │
        │ POST           │         │ CLI loop:      │
        │ /universe/bond │         │ per issuer →   │
        │                │         │ per bond ISIN  │
        └────────────────┘         └────────────────┘
                                           │
                                           ▼
                                 ┌──────────────────────┐
                                 │  per-issuer-LEI      │
                                 │  FIRDS enumeration   │
                                 │  via                 │
                                 │  pipeline.gold       │
                                 │  ._firds             │
                                 │  .iter_issuer_       │
                                 │   records(lei)       │
                                 └──────────┬───────────┘
                                            │
                                            ▼
                                 ┌──────────────────────┐
                                 │  bond_issuers.yml    │
                                 │  (curated, 10 LEIs)  │
                                 └──────────────────────┘
```

Plus a documentation-only deliverable: extend `src/pipeline/agentic/README.md` with a bond-universe data-flow section.

### Technical Stack

- **Language**: Python 3.x.
- **HTTP**: existing `requests`/`httpx` via `pipeline.gold._firds.solr_get`.
- **OpenSearch**: existing `OpenSearchInstrumentStore` (no schema changes).
- **CLI framework**: `argparse`.
- **Tests**: `pytest` (existing).

### Key Files

**New:**
- `src/pipeline/agentic/cli/bond_universe.py` — batch entry point.
- `tests/agentic/test_bond_universe_cli.py` — smoke tests.

**Modified:**
- `src/pipeline/agentic/README.md` — bond universe data-flow section.
- `src/pipeline/gold/bond_firds.py` — strip CLI surface (`main`, `argparse`, `write_ndjson`, `if __name__`). Keep library functions.
- `CLAUDE.md` — rewrite `bond_firds` bullet under "Legacy bulk fetchers"; add CLI pointer under "Agentic data engineering".

**Read-only references:**
- `src/pipeline/gold/_firds.py` — `iter_issuer_records`, `solr_get`.
- `src/pipeline/agentic/agents/__init__.py` — `AGENTS["bond"]`.
- `src/pipeline/agentic/cli/equity_universe.py` — shape reference.

**No new helper module.** Unlike feature 001 (which created `pipeline.agentic.universes`), bond universe resolution uses existing legacy helpers (`load_issuers`, `iter_issuer_records`) — no Wikipedia, no ticker bridging.

**No new requirements.txt deps.** Unlike feature 001 (which added `lxml`), bonds need only `requests` + `opensearch-py` (already there).

## Implementation Phases

### Phase 0: Discovery & contract verification — `[HIGH]`

**Timeline**: ~45 min
**Dependencies**: None

#### Tasks

1. [ ] Read `pipeline.gold._firds.iter_issuer_records` — confirm signature, return type, exception behaviour.
2. [ ] Read `pipeline.gold.bond_firds.load_issuers` / `dedupe_by_isin` / `FIRDS_FL` — confirm public surface stays stable after the strip.
3. [ ] Grep for `bond_firds.main` / `bond_firds.write_ndjson` callers in `src/`, `tests/`, `backend/`. Expect zero matches (legacy CLI is process-only).
4. [ ] Spot-check `tests/agentic/test_bond_firds_source.py` and `test_assemble_bond.py` to confirm they exercise the library API that survives the strip.

#### Deliverables

Notes appended to this plan under a **Phase 0 findings** block before Phase 1 starts.

### Phase 1: Documentation — `[HIGH]`

**Timeline**: ~45 min
**Dependencies**: Phase 0

#### Tasks

1. [ ] Add a "Bond universe data flow" subsection to `src/pipeline/agentic/README.md`. Cover: `bond_issuers.yml` shape, `iter_issuer_records` lookup, per-ISIN agent invocation, GLEIF issuer chaining.
2. [ ] CLAUDE.md: rewrite the `bond_firds` bullet under "Legacy bulk fetchers" → library-only. Add a one-line pointer to `pipeline.agentic.cli.bond_universe` under "Agentic data engineering" (next to the equity CLI pointer added by feature 001).

#### Deliverables

- [ ] README updated.
- [ ] CLAUDE.md updated.

### Phase 2: Batch CLI — `[HIGH]`

**Timeline**: ~2.5 h
**Dependencies**: Phase 0

#### Tasks

1. [ ] Create `src/pipeline/agentic/cli/bond_universe.py`. Argparse:
   - `--issuer-lei LEI` (single; mutually exclusive with `--all`).
   - `--all` (default if no flags set).
   - `--issuers PATH` (override YAML).
   - `--limit-per-issuer N`.
   - `--dry-run`.
   - `--universe-status STATUS` (default `in_universe`).
   - `--report-out PATH`.
   - `--log-level LEVEL`.
2. [ ] `_Outcome` dataclass — same shape as feature 001's CLI but adds `issuer_lei: str`.
3. [ ] `_RunReport` dataclass — totals + per-issuer grouping. JSON shape: `{issuers: [{lei, name, success, partial, failed, outcomes: [...]}, ...], totals: {...}}`.
4. [ ] Main loop:
   1. `load_issuers(args.issuers)` from legacy lib.
   2. Filter to single LEI if `--issuer-lei` set; exit non-zero with helpful list if LEI unknown.
   3. For each issuer:
      - Try `iter_issuer_records(lei, FIRDS_FL)` → catch exceptions, mark issuer-level failure, continue.
      - `dedupe_by_isin` → list of ISINs.
      - Apply `--limit-per-issuer`.
      - For each ISIN: `AGENTS["bond"].assemble_and_persist(client, identifier, status)` then `index_search_hit`. Per-ISIN errors isolated.
   4. Emit per-issuer summary log line at INFO.
5. [ ] Lazy-import `opensearch_client_from_env` and `index_search_hit` inside their callers (mirror the equity CLI for test compatibility).
6. [ ] Module entrypoint: `if __name__ == "__main__": sys.exit(run())`.

#### Deliverables

- [ ] `bond_universe.py` runnable: `python -m pipeline.agentic.cli.bond_universe --dry-run --issuer-lei <known-LEI>` exits 0 with a report.
- [ ] All flags surface in `--help`.

### Phase 3: Smoke tests — `[HIGH]`

**Timeline**: ~1.5 h
**Dependencies**: Phase 2

#### Tasks

1. [ ] `tests/agentic/test_bond_universe_cli.py` — module-level structure mirrors `test_equity_universe_cli.py`.
2. [ ] Fixtures: stub `AGENTS["bond"]` (recording), stub `pipeline.gold._firds.iter_issuer_records` (returns per-LEI canned records), stub `index_search_hit` via `sys.modules` injection (no opensearchpy needed).
3. [ ] Tests:
   - [ ] AC-5: `--issuer-lei <unknown>` exits non-zero with stderr listing known LEIs.
   - [ ] AC-4: `--dry-run` produces report, calls no agent, no opensearch lookups.
   - [ ] Happy path: 2 issuers × 3 bonds each → 6 agent calls with `status="in_universe"` by default.
   - [ ] AC-6: simulate `iter_issuer_records` raising for one LEI → other issuer's bonds still process; failed issuer in report with `reason` populated.
   - [ ] Per-ISIN error isolation: simulate agent raising on one ISIN → other ISINs proceed; exit code 1.
   - [ ] `--limit-per-issuer 2` caps per-issuer count.
   - [ ] `--report-out` writes JSON with per-issuer grouping.

#### Deliverables

- [ ] Test file passes locally. Runs offline (no docker, no opensearchpy).

### Phase 4: Parity verification + legacy strip — `[HIGH]`

**Timeline**: ~2 h
**Dependencies**: Phases 2 + 3

#### Tasks (Phase 4a — Verification)

1. [ ] Capture legacy snapshot: `python -m pipeline.gold.bond_firds --output data/cache/parity/legacy_bonds.ndjson`. Pre-strip.
2. [ ] Rebuild instrument-api container (no new deps, but the new CLI module needs to be in the image).
3. [ ] Single-issuer smoke first: `docker compose exec instrument-api python -m pipeline.agentic.cli.bond_universe --issuer-lei <small-corporate-LEI> --report-out /tmp/run1.json`.
4. [ ] Verify counts: `curl localhost:9200/pms_golden_bond/_count` and `pms_golden_issuer/_count` increase as expected.
5. [ ] Full run: drop `--issuer-lei`; expect ~50–200 bonds processed depending on FIRDS coverage.
6. [ ] Re-run for AC-2 (idempotency): counts unchanged.
7. [ ] Run the parity diff script (`data/cache/parity/diff_bonds.py` — pattern from feature 001's `diff_smi.py`). Document divergences for PR body.

#### Tasks (Phase 4b — Strip)

8. [ ] Strip `pipeline.gold.bond_firds`:
   - Delete `main()` (~45 lines).
   - Delete the `argparse` setup inside `main`.
   - Delete `write_ndjson`.
   - Delete `if __name__ == "__main__":` block.
   - Remove unused imports (`argparse`; `Path` if no other use — check).
   - Rewrite module docstring to "library only" per `equity_yahoo`'s post-strip pattern.
9. [ ] Verify `pipeline.gold.bond_firds.fetch_by_isin` still imports and runs.
10. [ ] Run pytest — expect green.
11. [ ] CLAUDE.md: rewrite the `bond_firds` bullet under "Legacy bulk fetchers" to reflect the slimmed library role.

#### Deliverables

- [ ] AC-1, AC-2, AC-3 met (live).
- [ ] Legacy CLI gone; `fetch_by_isin` still importable; existing tests pass.
- [ ] PR-ready divergence summary captured.

### Phase 5: Integration smoke & sign-off — `[MEDIUM]`

**Timeline**: ~30 min
**Dependencies**: Phase 4

#### Tasks

1. [ ] `pytest` clean across the repo.
2. [ ] `POST /instruments/assemble` for a known bond ISIN still works (regression-checking after Phase 4b strip).
3. [ ] `GET /universe?scope=bond` lists the loaded bonds.
4. [ ] `GET /instruments/search?type=simpleBond` returns search-mirror hits for the new records.
5. [ ] Tick DoD in spec-002.md.

#### Deliverables

- [ ] All ACs met.
- [ ] DoD ticked.
- [ ] Branch `feat/agentic-bond-universe` ready for PyCharm review.

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `iter_issuer_records` raises on one LEI mid-batch | Medium | Low | Issuer-level error isolation (Phase 2 task 4). Failure reported, batch continues. |
| FIRDS Solr returns very different shape vs current expectation | Low | Medium | Phase 0 spot-check first. Existing `tests/agentic/test_bond_firds_source.py` already exercises this. |
| AC-3 surfaces material schema drift | Medium | Low | Same posture as feature 001 — document in PR body, do not block unless legacy-populated field disappears. |
| Hidden caller of `bond_firds.main` breaks after strip | Low | Medium | Phase 0 grep + Phase 4b pytest catches it. Grep was zero matches in equity equivalent. |
| Bond volume too large for strict serial | Low | Low | 10 issuers × ~10-30 bonds typical = ~150 bonds; ~10 min budget. Document threshold in CLI `--help` if it grows. |

### External Dependencies

| Dependency | Risk | Contingency |
|---|---|---|
| ESMA FIRDS Solr availability | Medium | Per-issuer retry logic existing in `_firds`; CLI surfaces issuer-level failures, continues batch. |
| GLEIF (downstream issuer chain) | Low | Already part of `assemble_and_persist`; failures logged at WARNING, don't block primary write. |

## Resource Requirements

### Development

- **Backend Developer**: 1 person. Estimated 1 working day (~7 hours). Smaller than feature 001 (~2 days) because no helper module + no new deps + no parity-direction extension.

### Infrastructure

- **Local Docker stack** for Phase 4a integration smoke.
- **No new env vars or API keys.** FIRDS is public; GLEIF is public.

## Success Metrics

- AC-1 through AC-6 all pass live.
- `pytest` clean.
- Net change in lines of code is negative (legacy `bond_firds.py --universe` strip is larger than the new CLI + tests).
- CLAUDE.md drift: "Legacy bulk fetchers" entry for `bond_firds` shrinks; "Agentic data engineering" gets one new bullet for the bond CLI.

## Rollout Plan

Single-machine, internal-tool feature. No staged rollout. Standard repo flow: feature branch → PyCharm review → merge to `main` (via PR) → delete branch locally and on remote (per CLAUDE.md "Branching workflow").

## Definition of Done

- [ ] All five phases complete.
- [ ] All six spec acceptance criteria met.
- [ ] `src/pipeline/agentic/README.md` has a bond-universe section.
- [ ] `pipeline.gold.bond_firds` CLI surface stripped; library functions retained.
- [ ] `pytest` clean.
- [ ] Branch merged to `main` and remote deleted (post-review).

## Additional Notes

- The decomposition directory does not exist for this feature, so no service-specific sub-plans are generated.
- **Architectural inheritance from feature 001**: layered API (planner/persist/agent/cli), search-mirror per record, lazy opensearch imports, JSON report shape, strict-serial concurrency, per-record error isolation. The bond CLI extends — not redesigns — the equity CLI's pattern.
- Phase 0 findings should be appended to this plan (in-place) before Phase 1 starts, so the dependency assumptions are recorded.

## Phase 0 findings (T001, 2026-05-18)

**`pipeline.gold._firds.iter_issuer_records(lei, fl)` contract:**

- Signature: `iter_issuer_records(lei: str, fl: List[str]) -> Iterator[Dict[str, Any]]`.
- Internally paginated (`FIRDS_PAGE_SIZE=200`, `FIRDS_MAX_PAGES=200` → caps at 40k records per LEI).
- `solr_get` has its own retry layer (5 attempts, exponential backoff on 5xx + URLError).
- **Important**: persistent FIRDS errors are swallowed inside `iter_issuer_records` — the iterator just returns empty rather than raising. This means a transient/persistent FIRDS failure for one LEI surfaces as "0 bonds" to the caller, indistinguishable from a genuine empty result.
- **Implication for the CLI**: AC-6 ("issuer-level FIRDS failure → other issuers proceed") is automatic — `iter_issuer_records` never raises. The CLI's defensive `try/except` around the call costs nothing but is functionally redundant. Per-issuer outcome distinguishes "0 bonds" from "1+ bonds" in the report; cannot distinguish "no bonds" from "FIRDS failed silently" without surfacing the internal warning logs.

**External callers of `bond_firds.main` / `write_ndjson`**: **zero**. Grep returned nothing across `src/`, `tests/`, `backend/`. T009 strip is safe.

**Test surface compatibility**: `tests/agentic/test_bond_firds_source.py` imports `from pipeline.gold import bond_firds as gold` and uses `gold.fetch_by_isin`, `gold.firds_to_golden`, etc. — only library APIs that survive the strip. `tests/agentic/test_assemble_bond.py` doesn't import `pipeline.gold.bond_firds` directly. Both safe.

**`load_issuers` contract**: `load_issuers(path: Optional[Path]) -> List[Dict[str, Any]]`. `path=None` → loads bundled `bond_issuers.yml` via `importlib.resources`. Override path supported. Stable.

**No plan adjustments needed.** Proceed to Phase 1.
