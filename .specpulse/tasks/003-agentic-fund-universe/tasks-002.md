# Task Breakdown: Look-through reasoning for synthetic ETFs

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- TASK_LIST_ID: tasks-002 -->
<!-- STATUS: ready -->
<!-- CREATED: 2026-05-18T16:50:00Z -->
<!-- LAST_UPDATED: 2026-05-18T16:50:00Z -->
<!-- SPEC: spec-003.md -->
<!-- PLAN: plan-002.md -->
<!-- SUPERSEDES: tasks-001.md (which targeted the merged spec-002 scope, all 11 tasks done) -->

## Progress Overview

- **Total Tasks**: 13
- **Completed Tasks**: 0 (0%)
- **In Progress Tasks**: 0
- **Blocked Tasks**: 0
- **Status**: READY — awaiting `/sp-execute`.

## Task Categories

### Phase 0 — Discovery [Priority: HIGH]

- [ ] **T001**: [S] Verify Phase 0 contract assumptions — confirm `Holding` lives at `assetAllocation.holdings[]` path (not directly on `FundGolden`); confirm `replicationMethod` + `benchmarkIdentifier` casing actually written by existing patches (look at one curated patch under `data/opensearch/golden/fund/patches/`); audit `planner.run_planner` source-ordering rule (alphabetical within `cost_class` vs explicit `order` key); confirm `SourceFetchResult` / `Patch` shape from `pipeline.agentic.merger` for nested-array fields (`assetAllocation.holdings[].source`); confirm OpenSearch mapping has `benchmarkIdentifier.keyword`; sanity-check `pms_golden_fund` against the running docker stack for at least one physical MSCI World ETF with non-empty `assetAllocation.holdings` (preferred: IE00B4L5Y983). Append findings to plan-002.md as **Phase 0 findings** block before T002 starts. — 0.5h

### Phase 1 — Ontology + model additions [Priority: HIGH]

- [ ] **T002**: [M] Ontology + pydantic + OpenSearch mapping changes. In `ontology/securities/fund/Fund.yml`: extend `Holding` value object with optional `source` enum field (`[direct, physical_proxy, index_provider, fund_of_fund, aggregator]`, default `direct` consumer-side); add new `LookthroughProvenance` value object (`method`, `proxyIsin`, `proxyGoldenId`, `proxyName`, `benchmarkIdentifier`, `benchmarkName`, `asOfDate`, `confidence`). In `ontology/golden/fund/FundGolden.yml`: add top-level optional `lookthroughProvenance` field cross-referencing `LookthroughProvenance`. Regen pydantic (`PYTHONPATH=src python -m ontology_tools.ontology_2_pydantic`); regen OpenSearch mapping (`PYTHONPATH=src python -m ontology_tools.golden_record_2_opensearch.convert_to_opensearch -i ontology -o data/opensearch/golden`); add `lookthroughProvenance` entry to `src/pipeline/agentic/annotations/fund.yml` (row-level `source` lives inside the nested Holding object — no top-level annotation needed unless Phase 0 task 4 says otherwise). Smoke: `pytest tests/agentic/ -x` clean; manifest drift check passes. — 1.5h

### Phase 2 — Source module [Priority: HIGH]

- [ ] **T003**: [M] Create `src/pipeline/agentic/sources/fund_lookthrough_skill.py` skeleton mirroring `fund_factsheet_skill.py`: module docstring (predicate + proxy strategy explained); lazy `claude_agent_sdk` import + `_SDK_AVAILABLE` flag; `fetch(identifier_kind, identifier_value, current) -> Optional[SourceFetchResult]` signature; trigger predicate (short-circuit returns `None` unless `identifier_kind == "isin"` AND `assetAllocation.holdings` is empty AND `holdingsCount is None` AND `replicationMethod.lower() ∈ {"synthetic", "swap"}` AND benchmark identifier or name present); patch cache check (`data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json` → return loaded patch, log `cache_hit=true`, no SDK call); SDK gating (`ANTHROPIC_API_KEY` env + `_SDK_AVAILABLE`). Predicate runs BEFORE any OpenSearch or SDK call. — 1h
- [ ] **T004**: [M] Implement `_find_proxy_candidates(client, current) -> List[dict]` — single OpenSearch `bool` query (`benchmarkIdentifier.keyword` exact-match preferred, `benchmarkName` text fallback; `filter` on `replicationMethod ∈ {physical, sampling}` + `exists assetAllocation.holdings`; `must_not` current ISIN; sort by `holdingsAsOf desc, missing _last`; size 10). On empty result, run cheaper "any physical fund?" probe (no benchmark filter) to distinguish `proxy_search_empty` (cold start, broader probe also empty) from `no_physical_proxy_in_universe` (broader probe non-empty but no benchmark match). Resolution 6 of spec-003. — 1h
- [ ] **T005**: [M] Implement `_pick_proxy_via_llm(current, candidates)` (LLM call with small JSON in/out — `picked_isin` + `rationale` only, no confidence emission); `_derive_confidence(current, picked)` (post-hoc: `high` exact `benchmarkIdentifier` match, `medium` case-insensitive `benchmarkName` match, `low` fuzzy/substring only — resolution 7); `_build_patch(current, proxy, confidence)` (deep copy proxy's `assetAllocation.holdings`, stamp each row `source="physical_proxy"`, set `holdingsCount` + `holdingsAsOf`, populate `lookthroughProvenance` block); wire into `fetch` flow with structured INFO log per invocation (`source`, `isin`, `cache_hit`, `candidates`, `picked_isin`, `confidence`, reason on no-op). Errors at WARNING; LLM exceptions caught → return `None` with `reason=llm_unavailable`; malformed JSON or `picked_isin` not in candidate set → `reason=llm_invalid_pick`. — 1h

### Phase 3 — Registry + per-skill control plumbing [Priority: HIGH]

- [ ] **T006**: [S] Create `src/pipeline/agentic/registry/fund_lookthrough_skill.yml` (id, module, entrypoint, `covers: [fund]`, `requires_identifier.any_of: [isin]`, `produces_fields: [assetAllocation, holdingsCount, holdingsAsOf, lookthroughProvenance]`, `cost_class: llm_skill`, `confidence: medium`). If Phase 0 task 3 says alphabetical ordering doesn't put `fund_lookthrough_skill` after `fund_factsheet_skill`, add explicit `order: 5` (factsheet_skill becomes `order: 4`). Verify: `python -c "from pipeline.agentic.agents import AGENTS; print([s.id for s in AGENTS['fund'].sources])"` shows 5 sources in expected order. — 0.5h
- [ ] **T007**: [M] Per-skill control plumbing. Extend `pipeline.agentic.planner.run_planner` with optional `allowed_llm_skills: Optional[set[str]] = None` param; planner's eligibility filter becomes `source eligible iff source.cost_class <= max_cost_class AND (source.cost_class != "llm_skill" OR allowed_llm_skills is None OR source.id in allowed_llm_skills)`. Thread the param up through `assemble.assemble_golden` → `persist.assemble_and_persist` → `agents.base.BaseAgent.assemble_and_persist`. All default to `None` (preserves current behaviour — no regression for spec-002 flows). Extend `/instruments/assemble` HTTP endpoint's Pydantic request body with optional `allowed_llm_skills: List[str]`. Resolution 5 of spec-003. — 0.75h
- [ ] **T008**: [M] `fund_universe` CLI argparse rework. Replace `--enable-factsheet-skill` argparse entry with `--enable-llm-skills` (boolean). Add `--llm-skills` (string, comma-list; argparse `type=lambda s: set(s.split(","))`). Add `--enable-factsheet-skill` as deprecated alias: `action="store_true"`, `dest="enable_llm_skills"`; after parsing, if alias was used, emit one `log.warning("--enable-factsheet-skill is deprecated; use --enable-llm-skills")` line. Translation in CLI body: `max_cost_class = "llm_skill" if args.enable_llm_skills else "web_fetch"`; `allowed_llm_skills = args.llm_skills if args.enable_llm_skills and args.llm_skills else None`. Pass both into `AGENTS["fund"].assemble_and_persist(...)`. — 0.5h

### Phase 4 — Unit tests [Priority: HIGH]

- [ ] **T009**: [L] Create `tests/agentic/test_fund_lookthrough_skill.py` covering: (a) **predicate truth table** — synthetic + no holdings + benchmark → continues; physical → skips no SDK/OS call; empty `replicationMethod` → skip; holdings non-empty → skip; `holdingsCount` set → skip; no benchmark → skip (AC-2); (b) **proxy resolution** — 3 candidates + LLM stub pick → patch built, all rows stamped `source=physical_proxy`, `lookthroughProvenance.proxyIsin` matches (AC-1 mocked); LLM stub picks ISIN not in candidate list → `reason=llm_invalid_pick`; (c) **cache hit** — fixture patch at `tests/fixtures/lookthrough/FG-LU1681043599-001.json`, no LLM call (AC-5); (d) **SDK / API key gating** — `ANTHROPIC_API_KEY` unset → skip; `_SDK_AVAILABLE=False` → skip; (e) **cold start vs no-peer distinction** — primary empty + broader probe empty → `reason=proxy_search_empty`; primary empty + broader probe non-empty → `reason=no_physical_proxy_in_universe` (AC-7 + AC-3, resolution 6); (f) **LLM error path** — stub raises → caught + `reason=llm_unavailable`, no exception propagated; (g) **confidence-derivation truth table** — exact identifier match → `high`; case-insensitive name match → `medium`; fuzzy → `low` (resolution 7); (h) **per-skill restriction** — `allowed_llm_skills={"fund_factsheet_skill"}` → lookthrough source's `fetch` not invoked; `allowed_llm_skills=None` → eligible; `--enable-factsheet-skill` alias emits exactly one deprecation log (AC-6b, resolution 5). — 2h

### Phase 5 — Integration + live smoke [Priority: MEDIUM]

- [ ] **T010**: [L] **Integration tests** in `tests/agentic/test_assemble_fund.py` (extend, don't duplicate): chain order verification — `recordMeta.sourceOfTruth` shows `fund_lookthrough_skill` strictly after `fund_factsheet_skill`; fill-empty-only safety — when factsheet_skill upstream populates `holdings`, lookthrough_skill predicate short-circuits. **Live smoke** on docker-compose stack: ensure IE00B4L5Y983 (iShares Core MSCI World physical) is in `pms_golden_fund` with non-empty holdings (seed via `POST /instruments/assemble` if not); AC-1 — `POST /instruments/assemble {identifier:LU1681043599, max_cost_class:llm_skill, persist:true}` → persisted record has `assetAllocation.holdings.length > 1000`, every row `source==physical_proxy`, `lookthroughProvenance.proxyIsin=="IE00B4L5Y983"`; AC-4 — re-run, verify byte-identical (modulo timestamps); AC-6 — `fund_universe --umbrella-lei <Amundi> --limit-per-umbrella 1` without `--enable-llm-skills`, confirm no factsheet/lookthrough log lines; AC-6b — `--enable-llm-skills --llm-skills fund_factsheet_skill`, confirm only factsheet runs; deprecated alias smoke — `--enable-factsheet-skill` alone, deprecation warning logs exactly once. — 1.5h

### Phase 6 — Documentation [Priority: LOW]

- [ ] **T011**: [S] Update docs to reflect 5-source chain + new flag design. `src/pipeline/agentic/README.md`: fund-source table 4 → 5 rows, new row for `fund_lookthrough_skill` with cost `llm_skill` + one-liner on predicate; cost-class paragraph names both LLM-skill sources. `CLAUDE.md`: "Agentic data engineering" fund chain enumeration gains `fund_lookthrough_skill`; "Fact-sheet + full-holdings enrichment" gains a paragraph on synthetic-ETF proxy fallback + how to filter proxy-derived data (`assetAllocation.holdings[].source == physical_proxy`, `lookthroughProvenance.*`). `fund_universe` CLI `--help` text: `--enable-llm-skills` ("Open the cost-class gate to llm_skill, making LLM-backed sources eligible (currently: fund_factsheet_skill, fund_lookthrough_skill). Default off; batch loads stay free of LLM cost."); `--llm-skills` ("Comma-separated list of llm_skill source IDs to allow. Only effective when --enable-llm-skills is set. Defaults to all eligible sources."); `--enable-factsheet-skill` ("DEPRECATED alias for --enable-llm-skills. Will be removed in a future release."). — 0.5h

### Phase 7 — UI surfacing [Priority: LOW]

- [ ] **T012**: [M] Fund detail panel — surface `lookthroughProvenance`. (a) API passthrough sanity check: `curl localhost:8003/instruments/assemble -d '...' | jq .lookthroughProvenance` confirms the field rides pydantic native serialisation through the API. (b) `frontend/src/instruments.jsx` ~line 797 (Fund Profile subpanel): add a conditional `<Row label="Look-through" value={...} />` rendering `via {proxyIsin} ({confidence})` with a `title` attribute for the hover tooltip carrying proxy name, benchmark, asOfDate, confidence. (c) `frontend/src/instruments.jsx` ~line 1020 (holdings-table subtitle): append `" (via physical proxy)"` to the existing subtitle when any `holdings[i].source === 'physical_proxy'`. (d) Local UI smoke: `cd frontend && npm run dev`, navigate to Find an instrument → search "MSCI World Swap" → open LU1681043599 detail panel; verify "Look-through" row + holdings subtitle annotation; open IE00B4L5Y983 for regression (no badge, no annotation). (e) Docker rebuild per CLAUDE.md's frontend-only recipe (`docker compose down && docker compose build --no-cache frontend && docker compose up --force-recreate`); verify the badge surfaces in the containerised build. — 1h

### Phase 8 — Final sign-off [Priority: MEDIUM]

- [ ] **T013**: [S] Final integration smoke + DoD. `pytest` clean across the repo (target ≥ 195/195 including the new test file). `POST /instruments/assemble` regression: assemble a non-synthetic fund (e.g. IE00B4L5Y983) and a synthetic fund (LU1681043599) both work end-to-end. `GET /universe/fund` lists loaded funds unchanged. Tick spec-003 DoD checkboxes for completed items. `git log --oneline -10` review — commits are coherent and well-named. Push branch + open PR. — 0.5h

## Task Details

### T001 — Phase 0 contract verification

- **Description**: Six-part discovery check covering spec-003 + plan-002 assumptions: holdings JSON path (`assetAllocation.holdings`); replicationMethod casing in existing patches; planner source-ordering rule; merger contract for nested-array provenance; OpenSearch keyword analyzer on `benchmarkIdentifier`; presence of a physical MSCI World ETF in the running stack.
- **Acceptance**:
  - [ ] Findings appended to plan-002.md as **Phase 0 findings** block.
  - [ ] If ordering relies on alphabetical and `fund_lookthrough_skill` lands AFTER `fund_factsheet_skill` (which it does — `fund_factsheet_skill < fund_lookthrough_skill`), note "no `order:` key needed" and proceed; otherwise document the required explicit `order` in the registry YAML.
  - [ ] If no physical MSCI World ETF is in the index, document this as a Phase 5 prerequisite (seed step needed before AC-1 live verification).
- **Dependencies**: None.
- **Files touched**: `plan-002.md` (append findings only).
- **Risk**: Low — read-only discovery.

### T002 — Ontology + model additions

- **Description**: Add the two new optional fields to the fund ontology, regenerate downstream artefacts (pydantic + OpenSearch mapping), update annotation manifest.
- **Acceptance**:
  - [ ] `Holding` value object in `Fund.yml` has optional `source` enum with 5 reserved values.
  - [ ] `LookthroughProvenance` value object defined in `Fund.yml`.
  - [ ] `FundGolden.yml` adds top-level `lookthroughProvenance` cross-referencing the new value object.
  - [ ] Regenerated `src/wealth_advisory/models/fund/Fund.py` (or wherever pydantic lands) carries the new types.
  - [ ] `data/opensearch/golden/fund/mapping.json` includes the two new field paths.
  - [ ] `src/pipeline/agentic/annotations/fund.yml` gains a `lookthroughProvenance` entry.
  - [ ] `pytest tests/agentic/ -x` passes (no regressions from the additive schema change).
  - [ ] Manifest drift check (import-time invariant in `pipeline.agentic.manifest`) does not raise.
- **Dependencies**: T001.
- **Files touched**: `ontology/securities/fund/Fund.yml`, `ontology/golden/fund/FundGolden.yml`, generated pydantic file, `data/opensearch/golden/fund/mapping.json`, `src/pipeline/agentic/annotations/fund.yml`.
- **Risk**: Medium — touches generated code; back-compat hinges on fields being strictly optional.

### T003 — Source module skeleton + predicate + cache + SDK gating

- **Description**: Stand up the `fund_lookthrough_skill` adapter with all the no-OS, no-LLM short-circuits in place. Costs nothing to call when preconditions fail.
- **Acceptance**:
  - [ ] Module imports cleanly without `claude-agent-sdk`.
  - [ ] Predicate truth table from spec FR-2 satisfied.
  - [ ] Cache file path computed as `data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json`; existing cache → load + return without SDK call.
  - [ ] SDK gating logs DEBUG (not WARNING) when `ANTHROPIC_API_KEY` unset or SDK absent.
- **Dependencies**: T002.
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py` (new), `data/opensearch/golden/fund/patches/lookthrough/.gitkeep` (new).
- **Risk**: Low — mirrors `fund_factsheet_skill.py` pattern.

### T004 — Proxy lookup + cold-start distinction

- **Description**: OpenSearch query for physical-replication peers tracking the same benchmark, plus a cheaper "any physical fund?" probe to distinguish cold start from no-peer-for-benchmark (resolution 6).
- **Acceptance**:
  - [ ] Primary query filters on benchmark + `replicationMethod ∈ {physical, sampling}` + non-empty `assetAllocation.holdings`; excludes current ISIN; sorts by `holdingsAsOf` desc.
  - [ ] Empty primary → broader probe runs (no benchmark filter, same physical / holdings filters); empty broader → `proxy_search_empty`; non-empty broader → `no_physical_proxy_in_universe`.
  - [ ] No more than 11 OpenSearch queries per invocation (1 primary + at most 1 broader probe).
- **Dependencies**: T003.
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py`.
- **Risk**: Low.

### T005 — LLM ranking + confidence derivation + patch builder

- **Description**: The LLM-touching half of the adapter. Small prompt, deterministic post-hoc confidence, fully-stamped patch.
- **Acceptance**:
  - [ ] Prompt is tight: synthetic ETF identity + ≤10 candidates; output contract `{picked_isin, rationale}` only; ~400 token output cap.
  - [ ] LLM returns malformed JSON or invalid `picked_isin` → `reason=llm_invalid_pick`; exception → `reason=llm_unavailable`. No exceptions propagate.
  - [ ] `_derive_confidence` truth table from resolution 7 implemented.
  - [ ] Patch builds: deep-copy holdings stamped `source=physical_proxy`; `holdingsCount`, `holdingsAsOf` from proxy; full `lookthroughProvenance` block.
  - [ ] One structured INFO log line per invocation with all required fields.
- **Dependencies**: T004.
- **Files touched**: `src/pipeline/agentic/sources/fund_lookthrough_skill.py`.
- **Risk**: Medium — LLM prompt design + error paths; covered comprehensively by T009.

### T006 — Registry wiring + chain-order verification

- **Description**: Wire the new source into the fund agent's chain at position 5.
- **Acceptance**:
  - [ ] Registry YAML created; `produces_fields` lists the four fields the source writes.
  - [ ] `AGENTS["fund"].sources` lists 5 source IDs in the expected order, lookthrough last.
  - [ ] If alphabetical ordering doesn't suffice (per Phase 0 finding), `order: 5` added explicitly.
- **Dependencies**: T005.
- **Files touched**: `src/pipeline/agentic/registry/fund_lookthrough_skill.yml` (new).
- **Risk**: Low.

### T007 — Per-skill control plumbing

- **Description**: Thread `allowed_llm_skills: Optional[set[str]] = None` through the agent → assemble → persist → planner layers so per-skill restriction is enforceable below the CLI. Surface it in the HTTP endpoint schema. Default `None` preserves spec-002 behaviour.
- **Acceptance**:
  - [ ] All four function signatures (`BaseAgent.assemble_and_persist`, `persist.assemble_and_persist`, `assemble.assemble_golden`, `planner.run_planner`) accept the new optional kwarg.
  - [ ] Planner eligibility check updated per spec-003 Clarification 5.
  - [ ] `/instruments/assemble` Pydantic request body has optional `allowed_llm_skills: List[str]`.
  - [ ] `pytest tests/agentic/ -x` green (existing tests unchanged — they pass `None` implicitly).
- **Dependencies**: T002 (so the source can be exercised via the agent), T006.
- **Files touched**: `src/pipeline/agentic/agents/base.py`, `src/pipeline/agentic/persist.py`, `src/pipeline/agentic/assemble.py`, `src/pipeline/agentic/planner.py`, `backend/instrument_api/schemas/*` (or wherever the assemble request body lives).
- **Risk**: Medium — touches multiple modules + an HTTP schema. Default-None preserves back-compat.

### T008 — CLI argparse rework

- **Description**: Translate the new flag design into argparse on `fund_universe.py`.
- **Acceptance**:
  - [ ] `--enable-llm-skills` boolean flag added.
  - [ ] `--llm-skills` accepts a comma-list, parsed into a `set[str]`.
  - [ ] `--enable-factsheet-skill` works as a deprecated alias (`dest="enable_llm_skills"`); using it emits exactly one deprecation log line.
  - [ ] CLI translates flags → `max_cost_class` + `allowed_llm_skills` correctly per Phase 3 task 7 spec.
  - [ ] `--help` text reads as specified in T011.
- **Dependencies**: T007.
- **Files touched**: `src/pipeline/agentic/cli/fund_universe.py`.
- **Risk**: Low.

### T009 — Unit tests for `fund_lookthrough_skill`

- **Description**: Comprehensive test coverage. 8 sub-cases mapped to spec ACs and design resolutions.
- **Acceptance**:
  - [ ] One test function per sub-case (a) through (h) in the breakdown.
  - [ ] Tests use `monkeypatch` for the cache base path, the OpenSearch client, the LLM call, the SDK availability flag, and the `ANTHROPIC_API_KEY` env var.
  - [ ] No real network or filesystem access (the cache fixture lives under `tests/fixtures/lookthrough/`).
  - [ ] `pytest tests/agentic/test_fund_lookthrough_skill.py -v` green.
- **Dependencies**: T005, T008.
- **Files touched**: `tests/agentic/test_fund_lookthrough_skill.py` (new), `tests/fixtures/lookthrough/FG-LU1681043599-001.json` (new).
- **Risk**: Low.

### T010 — Integration + live smoke

- **Description**: Tie the chain together and validate the canonical Amundi → iShares case end-to-end against the docker-compose stack.
- **Acceptance**:
  - [ ] AC-1 verified live on LU1681043599 → IE00B4L5Y983.
  - [ ] AC-4 idempotency verified.
  - [ ] AC-6 default-cap safety verified (default batch invocation, neither LLM skill fires).
  - [ ] AC-6b per-skill restriction verified (`--llm-skills fund_factsheet_skill` → lookthrough skipped).
  - [ ] Deprecated `--enable-factsheet-skill` alias logs deprecation warning exactly once.
  - [ ] Chain-order + fill-empty-only locked by integration tests.
- **Dependencies**: T009.
- **Files touched**: `tests/agentic/test_assemble_fund.py` (extend), no source edits.
- **Risk**: Medium — depends on the running stack + `ANTHROPIC_API_KEY` for the live AC-1 step.

### T011 — Documentation updates

- **Description**: README, CLAUDE.md, and CLI `--help` text catch up to the 5-source chain + the new flag design.
- **Acceptance**:
  - [ ] Fund table in `src/pipeline/agentic/README.md` shows 5 rows.
  - [ ] CLAUDE.md updates discoverable: fund chain enumeration + factsheet/lookthrough block.
  - [ ] CLI `--help` reads exactly as drafted in plan-002 Phase 6 task 3.
- **Dependencies**: T010 (so docs reflect actual behaviour).
- **Files touched**: `src/pipeline/agentic/README.md`, `CLAUDE.md`, `src/pipeline/agentic/cli/fund_universe.py` (`--help` strings only).
- **Risk**: Low.

### T012 — UI surfacing in fund detail panel

- **Description**: Minimal-touch frontend update. Conditional "Look-through" row in Fund Profile subpanel + holdings-subtitle annotation. No new components, no state changes.
- **Acceptance**:
  - [ ] API passthrough confirmed: `lookthroughProvenance` and `assetAllocation.holdings[].source` ride through `instrument-api`'s response.
  - [ ] Fund Profile subpanel renders "Look-through" row only when `lookthroughProvenance != null`.
  - [ ] Hover tooltip exposes proxy name, benchmark, asOfDate, confidence.
  - [ ] Holdings table subtitle appends `" (via physical proxy)"` only when any row is proxy-derived.
  - [ ] No render regression on physical-ETF or non-fund instruments.
  - [ ] Containerised build (after docker rebuild) shows the badge.
- **Dependencies**: T011.
- **Files touched**: `frontend/src/instruments.jsx`, optionally `frontend/src/styles.css` for a `.lookthrough-badge` rule.
- **Risk**: Low — additive UI change, conditional on existing data.

### T013 — Final integration smoke + DoD

- **Description**: Repo-wide pytest, regression checks on the API surfaces, tick DoD, ready PR.
- **Acceptance**:
  - [ ] `pytest`: ≥ 195/195 green (190 baseline from spec-002 + the new test file).
  - [ ] `POST /instruments/assemble` for both physical (IE00B4L5Y983) and synthetic (LU1681043599) fund works.
  - [ ] `GET /universe/fund` unchanged behaviour.
  - [ ] spec-003 DoD checkboxes ticked.
  - [ ] Branch ready for `git push -u origin feat/fund-lookthrough-skill` + PR.
- **Dependencies**: T012.
- **Files touched**: `.specpulse/specs/003-agentic-fund-universe/spec-003.md` (DoD checkboxes).
- **Risk**: Low.

## Dependencies graph

```
T001 (discovery)
  └── T002 (ontology)
        └── T003 (skeleton + predicate + cache + SDK gating)
              └── T004 (proxy lookup + cold-start probe)
                    └── T005 (LLM rank + confidence + patch)
                          └── T006 (registry YAML)
                                └── T007 (per-skill plumbing)
                                      └── T008 (CLI argparse)
                                            └── T009 (unit tests)
                                                  └── T010 (integration + live)
                                                        └── T011 (docs)
                                                              └── T012 (UI)
                                                                    └── T013 (sign-off)
```

Strict serial chain — each task builds on the previous. No parallel paths beyond running `pytest tests/agentic/` smokes interleaved with development.

## Risk Summary

- **High-impact / medium-likelihood**: T007 (signature plumbing) and T005 (LLM error paths). Both covered by T009 unit tests; T007 also gated by the existing `tests/agentic/` smoke after every signature change.
- **High-impact / low-likelihood**: T002 (ontology regeneration breaks pydantic or mapping). Mitigated by strictly-optional fields and back-compat consumer-side default of `direct`.
- **Cost risk**: T010 step (live AC-1 run) burns 1 LLM call (~$0.02). Budget capped.

## SDD Gates Compliance

- ✅ **Specification First**: every task references spec-003 FRs, ACs, or design resolutions.
- ✅ **Task Decomposed**: 13 tasks, each ≤ 2h, with concrete acceptance.
- ✅ **Quality Assurance**: T009 covers all spec FRs/ACs at unit level; T010 covers AC-1/4/6/6b live.
- ✅ **Traceable Implementation**: each task lists files touched.

## Estimated Effort

- **Total**: ~9.5 hours (1 working day).
- **Critical path**: T001 → T013, single serial chain.
- **Velocity assumption**: 1 task/hour average; the L-sized tasks (T009, T010) cap at 2h.

---

*Generated by /sp-task on 2026-05-18. Implements spec-003.md per plan-002.md. Supersedes tasks-001.md (which targeted spec-002 scope, merged via PR #4).*
