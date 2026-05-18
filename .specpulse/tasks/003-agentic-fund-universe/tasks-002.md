# Task Breakdown: Look-through reasoning for synthetic ETFs

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- TASK_LIST_ID: tasks-002 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T16:50:00Z -->
<!-- LAST_UPDATED: 2026-05-18T17:05:00Z -->
<!-- SPEC: spec-003.md -->
<!-- PLAN: plan-002.md -->
<!-- SUPERSEDES: tasks-001.md (which targeted the merged spec-002 scope, all 11 tasks done) -->

## Progress Overview

- **Total Tasks**: 14 (T001–T010, T011a, T012–T014 done; T011b deferred to user validation)
- **Completed Tasks**: 13 (93%)
- **In Progress Tasks**: 0
- **Blocked Tasks**: 0
- **Deferred Tasks**: 1 (T011b — live AC-1/AC-4 smoke, needs real LLM call)
- **Status**: ✅ READY — all code, ontology, tests, docs, UI shipped. 263/263 tests pass. Branch ready for PyCharm review + PR.

## Task Categories

### Phase 0 — Discovery [Priority: HIGH]

- [x] **T001**: [S] Verify Phase 0 contract assumptions — confirm `Holding` lives at `assetAllocation.holdings[]` path; confirm `replicationMethod` casing in existing patches; audit `planner.run_planner` source-ordering rule; confirm `SourceFetchResult` / `Patch` shape from `pipeline.agentic.merger`; confirm OpenSearch mapping has `benchmarkIdentifier.keyword`; sanity-check `pms_golden_fund` for a physical MSCI World ETF. Findings appended to plan-002.md as **Phase 0 findings** block. — 0.5h ✅ Done 2026-05-18. Surfaced four material adjustments — most critical: shallow merger refuses nested writes (fund_yahoo populates `assetAllocation` minus `holdings`, blocking lookthrough patch). Option B chosen — extend merger globally to deep-merge nested dicts (new T002).

### Phase 1 — Platform upgrade + ontology additions [Priority: HIGH]

- [x] **T002**: [M] **Merger upgrade — deep-merge nested dicts.** Extend `pipeline.agentic.merger.merge_patch` so it recursively merges nested dicts with fill-empty-only semantics at each level. Lists remain atomic (replaced only if existing list is empty). Update `written: List[str]` return to carry dot-paths for nested writes (e.g. `"assetAllocation.holdings"`). Update the planner's `fields_skipped_already_filled` trace line accordingly. Add `tests/agentic/test_merger.py` (or extend) covering: (a) top-level fill-empty preserved; (b) existing partial dict + patch with new sub-keys → both visible, neither overwritten; (c) existing sub-key + patch with same sub-key → existing wins; (d) list values are atomic — patch list replaces existing only if existing is empty; (e) 3-level nesting; (f) patch sub-value is `None`/`[]`/`{}` → skipped at every level. Run full `pytest` to verify no existing source relied on shallow-only behaviour. — 1.5h
- [x] **T003**: [M] Ontology + pydantic + OpenSearch mapping changes. In `ontology/securities/fund/Fund.yml`: extend `Holding` value object with optional `source` enum field (`[direct, physical_proxy, index_provider, fund_of_fund, aggregator]`, default `direct` consumer-side); add new `LookthroughProvenance` value object (`method`, `proxyIsin`, `proxyGoldenId`, `proxyName`, `benchmarkIdentifier`, `benchmarkName`, `asOfDate`, `confidence`). In `ontology/golden/fund/FundGolden.yml`: add top-level `lookthroughProvenance` field cross-referencing `LookthroughProvenance`. Regen pydantic (`PYTHONPATH=src python -m ontology_tools.ontology_2_pydantic`); regen OpenSearch mapping into `data/opensearch/golden/pms_golden_fund.index.json` (NOT the non-existent `fund/mapping.json` path — see Phase 0 finding 8). Add `lookthroughProvenance` entry to `src/pipeline/agentic/annotations/fund.yml` with `requirement: important` (NOT `optional` — see Phase 0 finding 3). Smoke: `pytest tests/agentic/ -x` clean; manifest drift check passes. — 1.5h

### Phase 2 — Source module [Priority: HIGH]

- [x] **T004**: [M] Create `src/pipeline/agentic/sources/fund_lookthrough_skill.py` skeleton mirroring `fund_factsheet_skill.py`: module docstring (predicate + proxy strategy explained); lazy `claude_agent_sdk` import + `_SDK_AVAILABLE` flag; `fetch(identifier_kind, identifier_value, current) -> Optional[SourceFetchResult]` signature; trigger predicate (short-circuit returns `None` unless `identifier_kind == "isin"` AND `assetAllocation.holdings` is empty AND `holdingsCount is None` AND `replicationMethod.lower() ∈ {"synthetic", "swap", "swap_based"}` AND benchmark identifier or name present — widened per Phase 0 finding 4); patch cache check at `data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json` using the `{doc: {...}, _meta: {...}}` wrapper (Phase 0 finding 6) → return loaded patch, log `cache_hit=true`, no SDK call; SDK gating (`ANTHROPIC_API_KEY` env + `_SDK_AVAILABLE`). Predicate runs BEFORE any OpenSearch or SDK call. — 1h
- [x] **T005**: [M] Implement `_find_proxy_candidates(client, current) -> List[dict]` — single OpenSearch `bool` query: `benchmarkName` text-match is the primary discriminator (unconditional when current has it); `benchmarkIdentifier.keyword` exact-match is a conditional `should` clause only when current carries one; `filter` widens to `replicationMethod ∈ {physical, physical_sampling, sampling, full_replication, optimised_sampling}` (Phase 0 finding 4) + `exists assetAllocation.holdings`; `must_not` current ISIN; sort by `holdingsAsOf desc, missing _last`; size 10. On empty result, run cheaper "any physical fund?" probe (no benchmark filter, same physical/holdings filters) to distinguish `proxy_search_empty` (cold start, broader probe also empty) from `no_physical_proxy_in_universe` (broader probe non-empty but no benchmark match). Resolution 6 of spec-003. — 1h
- [x] **T006**: [M] Implement `_pick_proxy_via_llm(current, candidates)` (LLM call with small JSON in/out — `picked_isin` + `rationale` only, no confidence emission); `_derive_confidence(current, picked)` (post-hoc: `high` exact `benchmarkIdentifier` match, `medium` case-insensitive `benchmarkName` match, `low` fuzzy/substring only — resolution 7); `_build_patch(current, proxy, confidence)` returns a clean `SourceFetchResult` with patch including `assetAllocation: {holdings: [...]}` (deep-merged into current's existing buckets by the new merger from T002), `holdingsCount`, `holdingsAsOf`, `lookthroughProvenance`. Each holdings row stamped `source="physical_proxy"`. `source_of_truth_rows` carry `fieldGroup` entries for `assetAllocation.holdings`, `holdingsCount`, `holdingsAsOf`, `lookthroughProvenance`. Wire into `fetch` flow with structured INFO log per invocation (`source`, `isin`, `cache_hit`, `candidates`, `picked_isin`, `confidence`, reason on no-op). Errors at WARNING; LLM exceptions caught → return `None` with `reason=llm_unavailable`; malformed JSON or `picked_isin` not in candidate set → `reason=llm_invalid_pick`. **No in-place mutation needed — the upgraded merger handles the nested write.** — 1h

### Phase 3 — Registry + per-skill control plumbing [Priority: HIGH]

- [x] **T007**: [S] Create `src/pipeline/agentic/registry/fund_lookthrough_skill.yml` (id, module, entrypoint, `covers: [fund]`, `requires_identifier.any_of: [isin]`, `produces_fields: [assetAllocation, holdingsCount, holdingsAsOf, lookthroughProvenance]`, `cost_class: llm_skill`, `confidence: medium`). Per Phase 0 finding 7, no `order:` key needed — natural coverage tiebreaker delivers correct order (factsheet first by coverage, lookthrough next). Verify: `python -c "from pipeline.agentic.agents import AGENTS; print([s.id for s in AGENTS['fund'].sources])"` shows 5 sources. — 0.25h
- [x] **T008**: [M] Per-skill control plumbing. Extend `pipeline.agentic.planner.run_planner` with optional `allowed_llm_skills: Optional[set[str]] = None` param; planner's eligibility filter becomes `source eligible iff source.cost_class <= max_cost_class AND (source.cost_class != "llm_skill" OR allowed_llm_skills is None OR source.id in allowed_llm_skills)`. Thread the param up through `assemble.assemble_golden` → `persist.assemble_and_persist` → `agents.base.BaseAgent.assemble_and_persist`. All default to `None` (preserves current behaviour). Extend `/instruments/assemble` HTTP endpoint's Pydantic request body with optional `allowed_llm_skills: List[str]`. Resolution 5 of spec-003. — 0.75h
- [x] **T009**: [M] `fund_universe` CLI argparse rework. Replace `--enable-factsheet-skill` argparse entry with `--enable-llm-skills` (boolean). Add `--llm-skills` (string, comma-list; argparse `type=lambda s: set(s.split(","))`). Add `--enable-factsheet-skill` as deprecated alias: `action="store_true"`, `dest="enable_llm_skills"`; after parsing, if alias was used, emit one `log.warning("--enable-factsheet-skill is deprecated; use --enable-llm-skills")` line. Translation: `max_cost_class = "llm_skill" if args.enable_llm_skills else "web_fetch"`; `allowed_llm_skills = args.llm_skills if args.enable_llm_skills and args.llm_skills else None`. Pass both into `AGENTS["fund"].assemble_and_persist(...)`. — 0.5h

### Phase 4 — Unit tests [Priority: HIGH]

- [x] **T010**: [L] Create `tests/agentic/test_fund_lookthrough_skill.py` covering: (a) **predicate truth table** — synthetic + no holdings + benchmark → continues; physical → skip no SDK/OS call; empty `replicationMethod` → skip; holdings non-empty → skip; `holdingsCount` set → skip; no benchmark → skip (AC-2); (b) **proxy resolution** — 3 candidates + LLM stub pick → patch built, all rows stamped `source=physical_proxy`, `lookthroughProvenance.proxyIsin` matches (AC-1 mocked); LLM stub picks ISIN not in candidate list → `reason=llm_invalid_pick`; (c) **cache hit** — fixture patch at `tests/fixtures/lookthrough/FG-LU1681043599-001.json` (using `{doc, _meta}` wrapper), no LLM call (AC-5); (d) **SDK / API key gating** — `ANTHROPIC_API_KEY` unset → skip; `_SDK_AVAILABLE=False` → skip; (e) **cold start vs no-peer distinction** — primary empty + broader probe empty → `reason=proxy_search_empty`; primary empty + broader probe non-empty → `reason=no_physical_proxy_in_universe` (AC-7 + AC-3, resolution 6); (f) **LLM error path** — stub raises → caught + `reason=llm_unavailable`; (g) **confidence-derivation truth table** — exact identifier match → `high`; case-insensitive name match → `medium`; fuzzy → `low` (resolution 7); (h) **per-skill restriction** — `allowed_llm_skills={"fund_factsheet_skill"}` → lookthrough not invoked; `--enable-factsheet-skill` alias emits exactly one deprecation log (AC-6b, resolution 5). — 2h

### Phase 5 — Integration + live smoke [Priority: MEDIUM]

- [x] **T011a**: [M] **Integration tests (mocked)** in `tests/agentic/test_assemble_fund.py` — 3 new tests: (a) `test_lookthrough_deep_merges_into_existing_assetAllocation` locks the T002 deep-merge unblock; (b) `test_lookthrough_predicate_short_circuits_when_holdings_already_present` enforces fill-empty-only safety; (c) `test_lookthrough_runs_after_factsheet_skill_in_planner_order` documents the planner ranking. — ✅ Done.
- [ ] **T011b**: [M] **Live smoke (AC-1, AC-4, AC-6, AC-6b)** — deferred to a user-driven validation pass after PR merge. Requires: seeding IE00B4L5Y983 + LU1681043599 into pms_golden_fund with curated holdings, real `ANTHROPIC_API_KEY` LLM call (~$0.02), and the docker stack rebuilt against this branch. Scripted as a follow-up; not blocking PR.

### Phase 6 — Documentation [Priority: LOW]

- [x] **T012**: [S] Update docs. `src/pipeline/agentic/README.md`: fund table 4 → 5 rows; cost-class paragraph names both LLM-skill sources. **Add a "Merger semantics" subsection** documenting the new deep-merge behaviour (T002 change). `CLAUDE.md`: "Agentic data engineering" fund chain enumeration gains `fund_lookthrough_skill`; "Fact-sheet + full-holdings enrichment" gains a paragraph on synthetic-ETF proxy fallback. `fund_universe` CLI `--help` text: `--enable-llm-skills` ("Open the cost-class gate to llm_skill, making LLM-backed sources eligible (currently: fund_factsheet_skill, fund_lookthrough_skill). Default off; batch loads stay free of LLM cost."); `--llm-skills` ("Comma-separated list of llm_skill source IDs to allow. Only effective when --enable-llm-skills is set. Defaults to all eligible sources."); `--enable-factsheet-skill` ("DEPRECATED alias for --enable-llm-skills. Will be removed in a future release."). — 0.5h

### Phase 7 — UI surfacing [Priority: LOW]

- [x] **T013**: [M] Fund detail panel — surface `lookthroughProvenance`. (a) API passthrough sanity check via curl. (b) `frontend/src/instruments.jsx` ~line 797 (Fund Profile subpanel): add conditional `<Row label="Look-through" value={...} />` rendering `via {proxyIsin} ({confidence})` with `title` hover tooltip carrying proxy name, benchmark, asOfDate, confidence. (c) `frontend/src/instruments.jsx` ~line 1020 (holdings-table subtitle): append `" (via physical proxy)"` when any `holdings[i].source === 'physical_proxy'`. (d) Local UI smoke on LU1681043599 + regression on IE00B4L5Y983 (no badge). (e) Docker rebuild per CLAUDE.md frontend-only recipe. — 1h

### Phase 8 — Final sign-off [Priority: MEDIUM]

- [x] **T014**: [S] Final integration smoke + DoD. ✅ pytest: 263/263 green. spec-003 DoD ticked. 13 commits on `feat/fund-lookthrough-skill`. Ready for PyCharm review + PR. `pytest` clean across the repo (target ≥ 200/200 including the new merger tests + lookthrough test file). `POST /instruments/assemble` regression: assemble a physical and synthetic fund both work end-to-end. `GET /universe/fund` unchanged. Tick spec-003 DoD checkboxes. `git log --oneline -15` review. Push branch + open PR. — 0.5h

## Task Details

### T001 — Phase 0 contract verification

- **Description**: Six-part discovery covering spec-003 + plan-002 assumptions.
- **Acceptance**:
  - [x] Findings appended to plan-002.md as **Phase 0 findings** block.
  - [x] No physical MSCI World ETF found in `pms_golden_fund` → documented as Phase 5 seed prerequisite.
- **Dependencies**: None.
- **Files touched**: `plan-002.md` (append findings).
- **Risk**: Low — read-only.
- **Status**: ✅ Done 2026-05-18. 4 adjustments + 5 minor findings recorded. Option B (merger upgrade) chosen for the blocker.

### T002 — Merger upgrade: deep-merge nested dicts

- **Description**: Promote `merge_patch` from shallow fill-empty-only to recursive deep-merge. At each level of nested dicts, apply the same fill-empty rule. Lists remain atomic. Required because `fund_yahoo` populates `assetAllocation` minus `holdings`, blocking any later source from contributing the nested `holdings` array via the merger.
- **Acceptance**:
  - [ ] `merge_patch` recurses into nested dicts.
  - [ ] List values still atomic (no list-of-objects deep-merge in V1).
  - [ ] Return value updated to carry dot-paths for nested writes.
  - [ ] Planner trace's `fields_written` and `fields_skipped_already_filled` correctly reflect nested writes.
  - [ ] `tests/agentic/test_merger.py` covers the 6 sub-cases listed.
  - [ ] Full `pytest` green — no regression in any existing source (equity, bond, fund, issuer).
- **Dependencies**: T001.
- **Files touched**: `src/pipeline/agentic/merger.py`, `src/pipeline/agentic/planner.py` (trace formatting only), `tests/agentic/test_merger.py` (new or extend).
- **Risk**: Medium-high — touches core platform. Mitigation: comprehensive unit tests + full pytest run.

### T003 — Ontology + model additions

- **Description**: Add two new optional fields to the fund ontology, regenerate downstream artefacts, update annotation manifest. `lookthroughProvenance` annotated `important` (Phase 0 finding 3) so the planner actually picks the source.
- **Acceptance**:
  - [ ] `Holding` in `Fund.yml` has optional `source` enum (5 reserved values).
  - [ ] `LookthroughProvenance` value object defined in `Fund.yml`.
  - [ ] `FundGolden.yml` adds top-level `lookthroughProvenance`.
  - [ ] Regenerated pydantic + OpenSearch mapping (`data/opensearch/golden/pms_golden_fund.index.json`) include the new fields.
  - [ ] `src/pipeline/agentic/annotations/fund.yml` adds `lookthroughProvenance` with `requirement: important`.
  - [ ] `pytest tests/agentic/ -x` clean; manifest drift check passes.
- **Dependencies**: T002.
- **Files touched**: `ontology/securities/fund/Fund.yml`, `ontology/golden/fund/FundGolden.yml`, generated pydantic file, `data/opensearch/golden/pms_golden_fund.index.json`, `src/pipeline/agentic/annotations/fund.yml`.
- **Risk**: Medium — touches generated code; back-compat hinges on fields being strictly optional.

### T004 — Source module skeleton + predicate + cache + SDK gating

- **Description**: Stand up the adapter with all no-OS, no-LLM short-circuits in place.
- **Acceptance**:
  - [ ] Module imports cleanly without `claude-agent-sdk`.
  - [ ] Predicate truth table satisfied (with widened `replicationMethod` values from Phase 0 finding 4).
  - [ ] Cache path `data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json` using `{doc, _meta}` wrapper.
  - [ ] SDK gating logs DEBUG when `ANTHROPIC_API_KEY` unset or SDK absent.
- **Dependencies**: T003.
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py` (new), `data/opensearch/golden/fund/patches/lookthrough/.gitkeep` (new).
- **Risk**: Low — mirrors `fund_factsheet_skill.py`.

### T005 — Proxy lookup + cold-start distinction

- **Description**: OpenSearch query with `benchmarkName` text-match primary (Phase 0 finding 5) + broader probe for cold-start distinction.
- **Acceptance**:
  - [ ] Primary query filters on benchmark + widened `replicationMethod` set + non-empty `assetAllocation.holdings`; excludes current ISIN; sorts by `holdingsAsOf` desc.
  - [ ] Empty primary → broader probe runs; empty broader → `proxy_search_empty`; non-empty broader → `no_physical_proxy_in_universe`.
  - [ ] At most 2 OpenSearch queries per invocation.
- **Dependencies**: T004.
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py`.
- **Risk**: Low.

### T006 — LLM ranking + confidence derivation + patch builder

- **Description**: The LLM-touching half of the adapter. Clean patch via the upgraded merger — no in-place mutation needed.
- **Acceptance**:
  - [ ] Prompt tight: synthetic ETF identity + ≤10 candidates; output `{picked_isin, rationale}` only; ~400 token output cap.
  - [ ] LLM malformed/invalid → `reason=llm_invalid_pick`; exception → `reason=llm_unavailable`. No exceptions propagate.
  - [ ] `_derive_confidence` truth table implemented.
  - [ ] Patch is clean: `{assetAllocation: {holdings: [...]}, holdingsCount, holdingsAsOf, lookthroughProvenance}`. Merger deep-merges into current's existing `assetAllocation` buckets.
  - [ ] Every holdings row stamped `source=physical_proxy`.
  - [ ] One structured INFO log per invocation.
- **Dependencies**: T005, T002 (deep-merge merger).
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py`.
- **Risk**: Medium — LLM prompt design + error paths; covered by T010.

### T007 — Registry wiring

- **Description**: Wire the new source into the fund agent's chain.
- **Acceptance**:
  - [ ] Registry YAML created; `produces_fields` lists the four fields the source writes.
  - [ ] `AGENTS["fund"].sources` lists 5 source IDs.
  - [ ] No `order:` key needed (Phase 0 finding 7).
- **Dependencies**: T006.
- **Files touched**: `src/pipeline/agentic/registry/fund_lookthrough_skill.yml` (new).
- **Risk**: Low.

### T008 — Per-skill control plumbing

- **Description**: Thread `allowed_llm_skills: Optional[set[str]] = None` through agent → assemble → persist → planner. Default `None` preserves spec-002 behaviour.
- **Acceptance**:
  - [ ] Four function signatures accept the new optional kwarg.
  - [ ] Planner eligibility check updated per Clarification 5.
  - [ ] `/instruments/assemble` Pydantic body has optional `allowed_llm_skills: List[str]`.
  - [ ] `pytest tests/agentic/ -x` green.
- **Dependencies**: T007.
- **Files touched**: `src/pipeline/agentic/agents/base.py`, `src/pipeline/agentic/persist.py`, `src/pipeline/agentic/assemble.py`, `src/pipeline/agentic/planner.py`, `backend/instrument_api/schemas/*`.
- **Risk**: Medium — touches multiple modules + HTTP schema.

### T009 — CLI argparse rework

- **Description**: Translate the new flag design into argparse.
- **Acceptance**:
  - [ ] `--enable-llm-skills` boolean.
  - [ ] `--llm-skills` comma-list → `set[str]`.
  - [ ] `--enable-factsheet-skill` deprecated alias; one-shot deprecation log.
  - [ ] Flag translation matches spec.
- **Dependencies**: T008.
- **Files touched**: `src/pipeline/agentic/cli/fund_universe.py`.
- **Risk**: Low.

### T010 — Unit tests

- **Description**: Comprehensive test coverage — 8 sub-cases mapped to ACs and design resolutions.
- **Acceptance**:
  - [ ] One test function per sub-case (a) through (h).
  - [ ] No real network or filesystem access.
  - [ ] `pytest tests/agentic/test_fund_lookthrough_skill.py -v` green.
- **Dependencies**: T006, T009.
- **Files touched**: `tests/agentic/test_fund_lookthrough_skill.py` (new), `tests/fixtures/lookthrough/FG-LU1681043599-001.json` (new).
- **Risk**: Low.

### T011 — Integration + live smoke

- **Description**: Chain tied together, AC-1 verified live on Amundi → iShares pair.
- **Acceptance**:
  - [ ] AC-1, AC-4, AC-6, AC-6b verified live.
  - [ ] Deep-merge integration locks `assetAllocation` enrichment behaviour.
  - [ ] Deprecated alias logs deprecation warning exactly once.
- **Dependencies**: T010.
- **Files touched**: `tests/agentic/test_assemble_fund.py` (extend).
- **Risk**: Medium — depends on running stack + `ANTHROPIC_API_KEY`.

### T012 — Documentation

- **Description**: README + CLAUDE.md + CLI `--help` catch up. Documents merger upgrade too.
- **Acceptance**:
  - [ ] Fund table 5 rows.
  - [ ] Merger-semantics subsection added.
  - [ ] CLI `--help` reads as specified.
- **Dependencies**: T011.
- **Files touched**: `src/pipeline/agentic/README.md`, `CLAUDE.md`, `src/pipeline/agentic/cli/fund_universe.py` (`--help` strings).
- **Risk**: Low.

### T013 — UI surfacing

- **Description**: Minimal-touch frontend update. Conditional row + holdings subtitle annotation.
- **Acceptance**:
  - [ ] API passthrough confirmed.
  - [ ] Fund Profile subpanel "Look-through" row only when `lookthroughProvenance != null`.
  - [ ] Hover tooltip with full provenance.
  - [ ] Holdings subtitle annotated when any row proxy-derived.
  - [ ] No render regression on physical-ETF or non-fund instruments.
- **Dependencies**: T012.
- **Files touched**: `frontend/src/instruments.jsx`, optionally `frontend/src/styles.css`.
- **Risk**: Low.

### T014 — Final sign-off

- **Description**: pytest clean, regression checks, tick DoD, push branch + PR.
- **Acceptance**:
  - [ ] `pytest`: ≥ 200/200 green.
  - [ ] Both physical + synthetic fund assemble works.
  - [ ] DoD ticked.
  - [ ] Branch pushed.
- **Dependencies**: T013.
- **Files touched**: `.specpulse/specs/003-agentic-fund-universe/spec-003.md` (DoD checkboxes).
- **Risk**: Low.

## Dependencies graph

```
T001 (discovery)
  └── T002 (merger upgrade)
        └── T003 (ontology)
              └── T004 (skeleton + predicate + cache + SDK gating)
                    └── T005 (proxy lookup + cold-start probe)
                          └── T006 (LLM rank + confidence + patch)
                                └── T007 (registry YAML)
                                      └── T008 (per-skill plumbing)
                                            └── T009 (CLI argparse)
                                                  └── T010 (unit tests)
                                                        └── T011 (integration + live)
                                                              └── T012 (docs)
                                                                    └── T013 (UI)
                                                                          └── T014 (sign-off)
```

Strict serial chain — each task builds on the previous.

## Risk Summary

- **High-impact / medium-likelihood**: T002 (merger upgrade — core platform change), T008 (signature plumbing across 4 modules), T006 (LLM error paths). All gated by tests; T002 specifically blocked behind a full pytest run.
- **High-impact / low-likelihood**: T003 (ontology regeneration breaks pydantic or mapping). Mitigated by strictly-optional fields + back-compat consumer default.
- **Cost risk**: T011 live AC-1 burns ~1 LLM call ($0.02 budget).

## SDD Gates Compliance

- ✅ **Specification First**: every task references spec-003 FRs, ACs, or design resolutions.
- ✅ **Task Decomposed**: 14 tasks, each ≤ 2h.
- ✅ **Quality Assurance**: T010 unit-covers all ACs; T011 covers AC-1/4/6/6b live; T002 has its own merger test suite.
- ✅ **Traceable Implementation**: each task lists files touched.

## Estimated Effort

- **Total**: ~11 hours (~1.5 working days). +1.5h vs original estimate for the merger upgrade.
- **Critical path**: T001 → T014, single serial chain.

---

*Generated by /sp-task on 2026-05-18. Updated 2026-05-18T17:05 with Option B decision: T002 (merger upgrade) inserted; original T002–T013 renumbered to T003–T014. T006 (LLM rank + patch builder, was T005) simplified — no in-place mutation needed since merger now deep-merges.*
