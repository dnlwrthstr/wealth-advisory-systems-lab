# Implementation Plan: Look-through reasoning for synthetic ETFs

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- PLAN_NUMBER: 002 -->
<!-- STATUS: ready -->
<!-- SUPERSEDES: plan-001.md (which targeted the merged spec-002 scope) -->
<!-- CREATED: 2026-05-18T16:10:00Z -->

## Specification Reference

- **Spec**: `.specpulse/specs/003-agentic-fund-universe/spec-003.md` (status: clarified)
- **Plan Version**: 2.0 (extension of feature 003; spec-002 + plan-001 already implemented and merged via PR #4)

## Architecture Overview

### High-Level Design

```
   ┌───────────────────────────────────────────────────────────────┐
   │  AGENTS["fund"].assemble_and_persist(client, identifier,       │
   │                                       status, max_cost_class)  │
   │                                                                │
   │  ── sources/fund_firds           (api_call, order 1)           │
   │  ── sources/fund_yahoo           (api_call, order 2)           │
   │  ── sources/fund_factsheet_patch (file_read, order 3)          │
   │  ── sources/fund_factsheet_skill (llm_skill, order 4)          │
   │  ── sources/fund_lookthrough_skill (llm_skill, order 5) ★ NEW  │
   │                                                                │
   │      ★ Gating predicate (no LLM call unless ALL hold):         │
   │         current.assetAllocation.holdings is empty              │
   │         current.holdingsCount is None                          │
   │         current.replicationMethod ∈ {synthetic, swap}          │
   │         current.benchmarkIdentifier or benchmarkName present   │
   │                                                                │
   │      ★ Proxy lookup (single OpenSearch query):                 │
   │         pms_golden_fund where:                                 │
   │           benchmarkIdentifier == current.benchmarkIdentifier   │
   │           replicationMethod ∈ {physical, sampling}             │
   │           assetAllocation.holdings is non-empty                │
   │           goldenId != current.goldenId                         │
   │                                                                │
   │      ★ LLM ranks top-10 hits → single pick + confidence enum   │
   │                                                                │
   │      ★ Patch:                                                  │
   │         assetAllocation.holdings ← deep copy of proxy's,       │
   │            each row stamped source=physical_proxy              │
   │         holdingsCount, holdingsAsOf ← proxy's                  │
   │         lookthroughProvenance ← {proxyIsin, benchmark, …}      │
   │                                                                │
   │      ★ Patch cache (skips LLM entirely if present):            │
   │         data/opensearch/golden/fund/patches/lookthrough/       │
   │            FG-{ISIN}-001.json                                  │
   └───────────────────────────────────────────────────────────────┘
```

### Technical Stack

- **Language**: Python 3.x.
- **OpenSearch client**: `opensearch_client_from_env()` (existing).
- **Claude Agent SDK**: same path used by `fund_factsheet_skill` (`from claude_agent_sdk import ClaudeAgentOptions, query`). Lazy import; source skips gracefully when SDK absent or `ANTHROPIC_API_KEY` unset.
- **Pydantic models**: regenerated via existing `ontology_2_pydantic` after ontology edits.
- **OpenSearch mapping**: regenerated via existing `ontology_tools.golden_record_2_opensearch.convert_to_opensearch`.
- **Tests**: `pytest` (existing).

**No new requirements.txt additions.**

### Key Files

**New:**
- `src/pipeline/agentic/sources/fund_lookthrough_skill.py` — adapter (predicate + proxy lookup + LLM rank + cache).
- `src/pipeline/agentic/registry/fund_lookthrough_skill.yml` — registry descriptor.
- `tests/agentic/test_fund_lookthrough_skill.py` — unit tests.
- `tests/fixtures/lookthrough/FG-LU1681043599-001.json` — cache-hit fixture for AC-5.
- `data/opensearch/golden/fund/patches/lookthrough/.gitkeep` — patch cache dir (empty in repo).

**Modified:**
- `ontology/securities/fund/Fund.yml` — add `source` enum field to `Holding`.
- `ontology/golden/fund/FundGolden.yml` — add `lookthroughProvenance` top-level field; cross-ref to a new `LookthroughProvenance` value object in `Fund.yml`.
- `src/pipeline/agentic/annotations/fund.yml` — add `lookthroughProvenance` field (the row-level `source` is inside `holdings[]` so doesn't need a top-level annotation entry).
- `src/pipeline/agentic/README.md` — fund chain table: 4 → 5 sources; cost-class semantics paragraph names both LLM-skill sources.
- `src/pipeline/agentic/cli/fund_universe.py` — `--help` text on `--enable-factsheet-skill` updated to reflect "enables both factsheet + lookthrough LLM skills"; no flag-rename in this plan (deferred — see Open Questions).
- `CLAUDE.md` — "Agentic data engineering" fund-chain enumeration gains `fund_lookthrough_skill`; "Fact-sheet + full-holdings enrichment" block gains a proxy-fallback paragraph.
- `data/opensearch/golden/fund/mapping.json` — regenerated (additive only).
- `data/opensearch/golden/fund/golden.example.json` — regenerated to include the new optional fields (if the converter emits examples).

**Read-only references:**
- `src/pipeline/agentic/sources/fund_factsheet_skill.py` — structural template for the new adapter (predicate + SDK invocation + lazy import + cache pattern).
- `src/pipeline/agentic/sources/fund_factsheet_patch.py` — patch-file projection pattern.
- `src/pipeline/agentic/agents/fund_agent.py` — `FundAgent.default_max_cost_class="llm_skill"` (unchanged).
- `src/pipeline/agentic/planner.py` — confirms source ordering rule (cost_class then file order; may need explicit `order` key in the YAML — verified in Phase 0).
- `src/pipeline/agentic/merger.py` — `SourceFetchResult` shape + provenance row contract.

## Implementation Phases

### Phase 0: Discovery & contract verification — `[HIGH]`

**Timeline**: ~30 min
**Dependencies**: None

#### Tasks

1. [ ] Confirm `Holding` location — `ontology/securities/fund/Fund.yml` lines ~261–290. Verify the `holdings` array path is `assetAllocation.holdings[]`, NOT directly on `FundGolden` (spec-003 says `FundGolden.holdings[].source` colloquially; actual JSON path is `assetAllocation.holdings[].source`). Update spec language if material; the plan + code use the correct path.
2. [ ] Confirm `replicationMethod` and `benchmarkIdentifier` fields exist on `FundGolden` (already verified during spec drafting — lines 221, 233 of `FundGolden.yml`). Note actual values populated today by `fund_factsheet_patch` and `fund_factsheet_skill` (case sensitivity check: do existing patches use `synthetic`, `Synthetic`, `swap`, or `Swap-based`?).
3. [ ] Confirm source ordering in the planner. Read `src/pipeline/agentic/planner.py`. Question: when two sources share `cost_class=llm_skill`, what determines order? If alphabetical → `fund_factsheet_skill < fund_lookthrough_skill` works without an explicit `order` key. If load-order → may need `order: 5` in the YAML descriptor.
4. [ ] Confirm `SourceFetchResult` (or `Patch`) shape from `pipeline.agentic.merger`. Identify the canonical way to attach provenance to a nested-array field (`assetAllocation.holdings[].source`).
5. [ ] Identify the OpenSearch index analyzer for `benchmarkIdentifier`. The proxy lookup needs `.keyword` for exact-match. Confirm mapping has it.
6. [ ] Sanity-grep `pms_golden_fund` against the docker-compose stack: how many records have `replicationMethod ∈ {synthetic, swap}` today? How many have `replicationMethod == physical` + non-empty `assetAllocation.holdings`? If zero physical-with-holdings exist post-PR-#4 (factsheet skill defaults to skip), Phase 5 needs a seed step before AC-1 verification.

#### Deliverables

Phase 0 findings block appended to this plan before Phase 1 starts. If task 3 reveals load-order dependency, plan adjustment for the registry YAML.

### Phase 1: Ontology + model additions — `[HIGH]`

**Timeline**: ~1.5 h
**Dependencies**: Phase 0

#### Tasks

1. [ ] In `ontology/securities/fund/Fund.yml`, extend the `Holding` value object with a new optional field:

   ```yaml
   source:
     type: string
     enum: [direct, physical_proxy, index_provider, fund_of_fund, aggregator]
     description: >
       Provenance of this row. `direct` = from the issuer's own holdings page
       or factsheet. `physical_proxy` = copied from a physically-replicated
       ETF tracking the same benchmark (used for swap-based ETFs whose own
       holdings page returns the substitute basket, not economic exposure).
       The other values are reserved for future strategies.
     example: direct
   ```

   Mark as **optional** (not in `required`). Existing rows without `source` read as `direct` for back-compat (consumer-side default).

2. [ ] In `ontology/securities/fund/Fund.yml`, add a new value-object definition `LookthroughProvenance`:

   ```yaml
   LookthroughProvenance:
     description: >
       Provenance metadata for proxy-derived look-through holdings.
       Populated only when assetAllocation.holdings[] carries any row with
       source != direct. Null otherwise.
     kind: value_object
     type: object
     required: [method, proxyIsin, benchmarkName, asOfDate, confidence]
     properties:
       method:
         type: string
         enum: [physical_proxy, index_provider, fund_of_fund, aggregator]
       proxyIsin:
         type: string
         pattern: "^[A-Z]{2}[A-Z0-9]{9}[0-9]$"
       proxyGoldenId:
         type: string
       proxyName:
         type: string
       benchmarkIdentifier:
         type: string
       benchmarkName:
         type: string
       asOfDate:
         type: string
         format: date
       confidence:
         type: string
         enum: [high, medium, low]
   ```

3. [ ] In `ontology/golden/fund/FundGolden.yml`, add a top-level `lookthroughProvenance` field next to the existing holdings-related fields (~line 295, alongside `holdingsAsOf`):

   ```yaml
   lookthroughProvenance:
     description: Provenance metadata when assetAllocation.holdings is proxy-derived.
     ref: LookthroughProvenance
   ```

   Optional (not in any `required` block).

4. [ ] Regenerate pydantic models: `PYTHONPATH=src python -m ontology_tools.ontology_2_pydantic`. Confirm `LookthroughProvenance` class generated and `Holding.source: Optional[Literal[...]]` added.

5. [ ] Regenerate OpenSearch mapping: `PYTHONPATH=src python -m ontology_tools.golden_record_2_opensearch.convert_to_opensearch -i ontology -o data/opensearch/golden`. Confirm `mapping.json` adds the two field paths.

6. [ ] Add the new field to `src/pipeline/agentic/annotations/fund.yml`:

   ```yaml
   lookthroughProvenance:
     requirement: optional
     kind: source
     description: Proxy lineage when holdings are derived from a physical-equivalent ETF.
     notes: Populated only by fund_lookthrough_skill.
   ```

   (Row-level `source` is inside the nested `Holding` value object — the annotation manifest's import-time invariant only walks top-level `FundGolden` fields, so no entry needed for it. Confirm during Phase 0 task 4.)

7. [ ] Re-import the package and verify the manifest loader doesn't raise (drift check between annotation YAML and the regenerated pydantic model).

#### Deliverables

- [ ] Ontology + generated pydantic + OpenSearch mapping all carry the two new optional fields.
- [ ] Annotation manifest passes its drift check.
- [ ] No existing test in `tests/` breaks from the addition (run `pytest tests/agentic/ -x` as a smoke).

### Phase 2: Source module — `[HIGH]`

**Timeline**: ~2 h
**Dependencies**: Phase 1

#### Tasks

1. [ ] Create `src/pipeline/agentic/sources/fund_lookthrough_skill.py` mirroring `fund_factsheet_skill.py`'s top-level shape:
   - Module docstring explaining the predicate + proxy strategy.
   - Lazy import of `claude_agent_sdk` (same try/except + `_SDK_AVAILABLE` flag).
   - `fetch(identifier_kind, identifier_value, current) -> Optional[SourceFetchResult]` signature.

2. [ ] Implement the **trigger predicate**. Short-circuit + return `None` (skip) when any of the following:
   - `identifier_kind != "isin"`.
   - `current.get("assetAllocation", {}).get("holdings")` is non-empty.
   - `current.get("holdingsCount")` is not None.
   - `current.get("replicationMethod", "").lower()` not in `{"synthetic", "swap"}`.
   - Neither `current.get("benchmarkIdentifier")` nor `current.get("benchmarkName")` is set.

   Important: the predicate runs **before** any OpenSearch query and any SDK invocation. Cost-class budget should never be charged when the predicate short-circuits.

3. [ ] Implement the **patch cache check**. Compute `patch_path = Path("data/opensearch/golden/fund/patches/lookthrough") / f"FG-{identifier_value}-001.json"`. If exists, load + return as a `SourceFetchResult` (mirror `fund_factsheet_patch.fetch` projection logic). Log `cache_hit=True`. No SDK call.

4. [ ] Implement the **SDK gating**. After the predicate + cache check, gate the actual LLM call on `ANTHROPIC_API_KEY` env var + `_SDK_AVAILABLE`. If either is missing, log debug and return `None` — non-fatal, predicate-equivalent skip.

5. [ ] Implement the **proxy lookup** OpenSearch query. Helper function `_find_proxy_candidates(client, current) -> List[dict]`:

   ```python
   query = {
       "size": 10,
       "query": {
           "bool": {
               "must": [
                   # benchmark match: keyword preferred, name fallback
                   {"bool": {"should": [
                       {"term": {"benchmarkIdentifier.keyword": current["benchmarkIdentifier"]}}
                           if current.get("benchmarkIdentifier") else None,
                       {"match": {"benchmarkName": current["benchmarkName"]}}
                           if current.get("benchmarkName") else None,
                   ], "minimum_should_match": 1}},
               ],
               "filter": [
                   {"terms": {"replicationMethod.keyword": ["physical", "sampling"]}},
                   {"exists": {"field": "assetAllocation.holdings"}},
               ],
               "must_not": [
                   {"term": {"identifierList.isin.keyword": current["identifierList"]["isin"]}},
               ],
           }
       },
       "sort": [{"holdingsAsOf": {"order": "desc", "missing": "_last"}}],
   }
   ```

   Strip `None` clauses. Return `hits.hits[*]._source`. Empty result distinguishes two cases (resolution 6):
   - `reason="proxy_search_empty"` — when a separate "any physical fund?" probe (a cheaper, broader query without benchmark filters) also returns 0 hits → the index is cold, no physical funds seeded at all.
   - `reason="no_physical_proxy_in_universe"` — when the broader probe finds physical funds but none match this benchmark.

   The broader probe runs only on empty primary results, so cost is bounded.

6. [ ] Implement the **LLM ranking call**. `_pick_proxy_via_llm(current, candidates) -> dict | None`. Prompt:

   - System / preamble: "You are matching a synthetic (swap-based) ETF to a physically-replicated peer tracking the same benchmark. Pick the single best match."
   - Inputs (small JSON): synthetic ETF identity (longName, benchmarkIdentifier, benchmarkName, replicationMethod, currency, AUM) + candidate list (≤10 entries: longName, isin, goldenId, benchmarkIdentifier, benchmarkName, replicationMethod, AUM, holdingsAsOf, holdingsCount).
   - Output contract: JSON with `picked_isin` and `rationale` (one line, ≤140 chars). **No `confidence` field requested from the LLM** — confidence is derived post-hoc (resolution 7).
   - Token cap: ~400 output. Cost ceiling per call: ≤ $0.02 typical.

   If the LLM returns malformed JSON or `picked_isin` not in the candidate list → log warning, return `None` (no-op with `reason=llm_invalid_pick`).

6a. [ ] Implement `_derive_confidence(current, picked) -> Literal["high", "medium", "low"]` (resolution 7):
   - `high` if `picked.benchmarkIdentifier == current.benchmarkIdentifier` (both non-null, exact match).
   - `medium` if `picked.benchmarkName.lower() == current.benchmarkName.lower()` (case-insensitive name match) but identifiers differ or are null.
   - `low` if neither matches strictly — fuzzy / substring name match only.
   Deterministic given a fixed candidate set; LLM creativity can't drift the rating.

7. [ ] Build the **patch**. Helper `_build_patch(current, proxy, confidence) -> SourceFetchResult`:
   - `proxy_holdings = deepcopy(proxy["assetAllocation"]["holdings"])`. Stamp each row with `source: "physical_proxy"`.
   - Patch dict:
     ```python
     {
         "assetAllocation": {"holdings": proxy_holdings},
         "holdingsCount": proxy.get("holdingsCount"),
         "holdingsAsOf": proxy.get("holdingsAsOf"),
         "lookthroughProvenance": {
             "method": "physical_proxy",
             "proxyIsin": proxy["identifierList"]["isin"],
             "proxyGoldenId": proxy["goldenId"],
             "proxyName": proxy.get("longName"),
             "benchmarkIdentifier": proxy.get("benchmarkIdentifier"),
             "benchmarkName": proxy.get("benchmarkName"),
             "asOfDate": proxy.get("holdingsAsOf"),
             "confidence": confidence,
         },
     }
     ```
   - Return a `SourceFetchResult` carrying this patch + per-field provenance rows tagged `fund_lookthrough_skill`. Follow the same provenance shape `fund_factsheet_skill` uses.

8. [ ] Structured INFO log line per invocation: `{"source": "fund_lookthrough_skill", "isin": ..., "cache_hit": ..., "candidates": N, "picked_isin": ..., "confidence": ..., "cost_class_used": "llm_skill"}`. Errors at WARNING; predicate-skip at DEBUG only.

#### Deliverables

- [ ] Module imports cleanly without `claude-agent-sdk` installed.
- [ ] `from pipeline.agentic.sources import fund_lookthrough_skill; fund_lookthrough_skill.fetch("isin", "LU1681043599", current_dict)` short-circuits correctly for each truth-table case.

### Phase 3: Registry wiring + per-skill control plumbing — `[HIGH]`

**Timeline**: ~1.5 h
**Dependencies**: Phase 2

This phase wires the new source into the chain AND adds the per-skill control plumbing decided in resolution 5 (the `--enable-llm-skills` + `--llm-skills` flag pair, plus an `allowed_llm_skills` param threaded through the agent / assemble / planner layers).

#### Tasks — registry

1. [ ] Create `src/pipeline/agentic/registry/fund_lookthrough_skill.yml`:

   ```yaml
   id: fund_lookthrough_skill
   description: |
     Resolves look-through holdings for synthetic / swap-based fund ETFs
     by reasoning over physically-replicated peers in pms_golden_fund.
     Fires only when current holdings are empty AND replicationMethod is
     synthetic/swap AND a benchmark identifier or name is set. Costs an
     LLM call to rank candidates; pre-curated patches under
     data/opensearch/golden/fund/patches/lookthrough/ bypass the call.
   module: pipeline.agentic.sources.fund_lookthrough_skill
   entrypoint: fetch
   covers: [fund]
   requires_identifier:
     any_of: [isin]
   produces_fields:
     - assetAllocation
     - holdingsCount
     - holdingsAsOf
     - lookthroughProvenance
   confidence: medium
   cost_class: llm_skill
   ```

2. [ ] If Phase 0 task 3 reveals ordering requires an explicit `order` key, add `order: 5` (after factsheet_skill which would then be `order: 4`).

3. [ ] Verify the registry loader picks it up: `python -c "from pipeline.agentic.agents import AGENTS; print([s.id for s in AGENTS['fund'].sources])"` shows 5 sources in the expected order.

#### Tasks — agent / assemble / planner layers (per-skill control)

4. [ ] Extend `pipeline.agentic.planner.run_planner` with an optional `allowed_llm_skills: Optional[set[str]] = None` param. In the source-eligibility check, add: `source eligible iff source.cost_class <= max_cost_class AND (source.cost_class != "llm_skill" OR allowed_llm_skills is None OR source.id in allowed_llm_skills)`.
5. [ ] Thread the param up through `assemble.assemble_golden`, `persist.assemble_and_persist`, and `agents.base.BaseAgent.assemble_and_persist`. All default to `None` to preserve existing behaviour. The agent-layer signature change touches `EquityAgent` / `BondAgent` / `FundAgent` by inheritance only — no per-agent edits.
6. [ ] Update the `/instruments/assemble` HTTP endpoint Pydantic request body to accept an optional `allowed_llm_skills: List[str]` field. Pass it through to the agent call.

#### Tasks — fund_universe CLI argparse

7. [ ] In `src/pipeline/agentic/cli/fund_universe.py`:
   - Replace `--enable-factsheet-skill` argparse entry with `--enable-llm-skills` (boolean).
   - Add `--llm-skills` (string, comma-list; argparse `type=lambda s: set(s.split(","))`).
   - Add `--enable-factsheet-skill` as a **deprecated alias** for `--enable-llm-skills`: argparse `action="store_true"` with `dest="enable_llm_skills"`. After parsing, if the user passed the alias, emit a single `log.warning("--enable-factsheet-skill is deprecated; use --enable-llm-skills")` line.
   - Translation in the CLI body:
     - `max_cost_class = "llm_skill" if args.enable_llm_skills else "web_fetch"`
     - `allowed_llm_skills = args.llm_skills if args.enable_llm_skills and args.llm_skills else None`
   - Pass both into `AGENTS["fund"].assemble_and_persist(..., max_cost_class=..., allowed_llm_skills=...)`.

8. [ ] Run `pytest tests/agentic/` — confirm no schema drift detection failures and existing tests still pass (the new param is opt-in, default `None` is current behaviour).

#### Deliverables

- [ ] Fund agent chain has 5 sources, `fund_lookthrough_skill` last.
- [ ] `allowed_llm_skills` plumbed through agent → assemble → planner with `None` default.
- [ ] `fund_universe` CLI exposes `--enable-llm-skills` + `--llm-skills`; `--enable-factsheet-skill` works as deprecated alias.
- [ ] `/instruments/assemble` HTTP endpoint accepts `allowed_llm_skills` in the request body.
- [ ] Annotation drift check + registry schema check both pass; existing tests unchanged.

### Phase 4: Unit tests — `[HIGH]`

**Timeline**: ~2 h
**Dependencies**: Phase 3

#### Tasks

1. [ ] Create `tests/agentic/test_fund_lookthrough_skill.py`. Fixtures: in-memory `current_record` builder; mock OpenSearch client returning a programmable hit list; mock LLM `_pick_proxy_via_llm` (monkeypatch).

2. [ ] **Predicate truth table** (covers AC-2):
   - synthetic + no holdings + benchmark → predicate passes (continues to lookup).
   - physical → predicate skips (returns `None`, no OpenSearch call recorded).
   - Empty `replicationMethod` → skip.
   - Holdings already non-empty → skip.
   - `holdingsCount` set, holdings empty → skip (defensive: count without rows means upstream populated metadata; don't trample).
   - No benchmark anywhere → skip.

3. [ ] **Proxy resolution** (covers AC-1 happy path under stubbed search + LLM):
   - 3 candidates returned, LLM stub picks one → patch built; `holdings` rows all stamped `source=physical_proxy`; `lookthroughProvenance.proxyIsin` matches the pick.
   - 0 candidates → no-op with reason `no_physical_proxy_in_universe` (AC-3).
   - LLM picks an ISIN not in the candidate list → no-op with reason `llm_invalid_pick`.

4. [ ] **Cache hit** (covers AC-5):
   - Drop `tests/fixtures/lookthrough/FG-LU1681043599-001.json` into a tmp dir; monkeypatch the cache base path. Call `fetch`. Assert patch returned without invoking the LLM mock (assert mock call count == 0).

5. [ ] **SDK / API key gating**:
   - `ANTHROPIC_API_KEY` unset → skip cleanly.
   - SDK import-failed (`_SDK_AVAILABLE=False`) → skip cleanly.

6. [ ] **Cold start vs no-peer distinction** (covers AC-7 + resolution 6):
   - Primary query returns 0 hits AND broader "any physical fund?" probe returns 0 hits → reason `proxy_search_empty`.
   - Primary query returns 0 hits AND broader probe returns ≥1 hit → reason `no_physical_proxy_in_universe`.
   - Assert both cases via separate test functions.

7. [ ] **LLM error path**:
   - LLM stub raises → `fetch` catches, logs WARNING, returns `None`. Batch never aborts.

8. [ ] **Confidence-derivation truth table** (covers resolution 7):
   - Picked candidate's `benchmarkIdentifier == current.benchmarkIdentifier` → `high`.
   - Identifiers differ but `benchmarkName` matches case-insensitively → `medium`.
   - Only fuzzy / substring name match → `low`.

9. [ ] **Per-skill restriction** (covers AC-6b + resolution 5):
   - Mock the planner / agent call with `allowed_llm_skills={"fund_factsheet_skill"}` → lookthrough source's `fetch` is not invoked.
   - With `allowed_llm_skills=None` and `max_cost_class="llm_skill"` → lookthrough source eligible.
   - With `--enable-factsheet-skill` (alias) → deprecation log emitted exactly once, behaviour identical to `--enable-llm-skills`.

#### Deliverables

- [ ] `pytest tests/agentic/test_fund_lookthrough_skill.py -v` green.
- [ ] All 7 cases above mapped 1:1 to test functions named per case.

### Phase 5: Integration + live smoke — `[MEDIUM]`

**Timeline**: ~1.5 h
**Dependencies**: Phase 4

#### Tasks

1. [ ] **Chain order integration test** in `tests/agentic/test_assemble_fund.py` (extend, don't duplicate): assert the assembled record's `recordMeta.sourceOfTruth` rows show `fund_lookthrough_skill` only after `fund_factsheet_skill`. Verifies Phase 3 ordering work.

2. [ ] **Fill-empty-only integration test**: build a `current_record` where `fund_factsheet_skill` has already populated `assetAllocation.holdings` (mocked) — assert `fund_lookthrough_skill.fetch` predicate short-circuits. Locks FR-6.

3. [ ] **Live seed**: bring up `docker compose up`. Ensure `pms_golden_fund` contains IE00B4L5Y983 (iShares Core MSCI World) with non-empty `assetAllocation.holdings` and `replicationMethod=physical`. If not: assemble it via `POST /instruments/assemble {identifier:..., persist:true, max_cost_class:llm_skill}` (factsheet skill will hit + populate holdings via the existing patch under `patches/FG-IE00B4L5Y983-001.json` if present, OR the iShares holdings flow described in CLAUDE.md). Phase 0 task 6 informs whether this seed step is needed.

4. [ ] **AC-1 live**: `POST /instruments/assemble` for LU1681043599 with `persist=true, max_cost_class=llm_skill`. Inspect returned record:
   - `assetAllocation.holdings.length > 1000`.
   - Every row's `source == "physical_proxy"`.
   - `lookthroughProvenance.proxyIsin == "IE00B4L5Y983"`.
   - `recordMeta.sourceOfTruth` carries a `fund_lookthrough_skill` row.

5. [ ] **AC-4 live (idempotency)**: re-run the same `POST /instruments/assemble`. Verify `holdings.length`, `lookthroughProvenance.proxyIsin` byte-identical to step 4 (timestamps may differ). Also verify the index doc count for `pms_golden_fund` did not change.

6. [ ] **AC-6 live (default-cap safety)**: run `python -m pipeline.agentic.cli.fund_universe --umbrella-lei <Amundi-LEI> --limit-per-umbrella 1` (no `--enable-llm-skills`). Confirm neither factsheet nor lookthrough skill log lines appear. Locks the cost-safe default.
6a. [ ] **AC-6b live (per-skill restriction)**: re-run with `--enable-llm-skills --llm-skills fund_factsheet_skill` against the same synthetic ETF. Confirm only `fund_factsheet_skill` invocation logs appear; no `fund_lookthrough_skill` log lines.
6b. [ ] **Deprecated alias smoke**: run `--enable-factsheet-skill` (no other flag changes). Confirm the deprecation warning logs exactly once and behaviour matches `--enable-llm-skills` alone.

7. [ ] **Find-an-instrument UI smoke**: browse to the local frontend, search for "MSCI World Swap", open LU1681043599's detail panel, confirm holdings count > 1000 and (if UI updated) the proxy provenance is visible. If the UI doesn't yet surface `lookthroughProvenance`, log the gap for follow-up — out of scope for this plan.

#### Deliverables

- [ ] AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 all green (live for AC-1/4/6, unit for AC-2/3/5/7).
- [ ] `pytest` green across the repo.

### Phase 6: Documentation — `[LOW]`

**Timeline**: ~30 min
**Dependencies**: Phase 5

#### Tasks

1. [ ] `src/pipeline/agentic/README.md` — update the "Fund (`scope="fund"`)" table to show 5 sources; new row for `fund_lookthrough_skill` with cost `llm_skill` and a one-liner on the predicate. Update the "Universe batch CLIs" / cost-class paragraph to name both LLM-skill sources.
2. [ ] `CLAUDE.md` — under "Agentic data engineering" → fund chain enumeration, append `fund_lookthrough_skill` with a brief description. Under "Fact-sheet + full-holdings enrichment", add a one-paragraph note that synthetic ETFs fall back to physical-peer proxies via this skill, and proxy lineage is filterable via `assetAllocation.holdings[].source == physical_proxy` and `lookthroughProvenance.*`.
3. [ ] Update `--help` text on `pipeline.agentic.cli.fund_universe`:
   - `--enable-llm-skills`: "Open the cost-class gate to llm_skill, making LLM-backed sources eligible (currently: fund_factsheet_skill, fund_lookthrough_skill). Default off; batch loads stay free of LLM cost."
   - `--llm-skills`: "Comma-separated list of llm_skill source IDs to allow. Only effective when --enable-llm-skills is set. Defaults to all eligible sources. Example: --llm-skills fund_factsheet_skill,fund_lookthrough_skill."
   - `--enable-factsheet-skill`: "DEPRECATED alias for --enable-llm-skills. Will be removed in a future release."

#### Deliverables

- [ ] README + CLAUDE.md reflect the 5-source chain.
- [ ] CLI `--help` text reflects both LLM-skill sources.

### Phase 7: UI surfacing of lookthroughProvenance — `[LOW]`

**Timeline**: ~1 h
**Dependencies**: Phase 6 (data layer must be live before frontend reads it)

The "Find an instrument" fund detail panel already renders a **Fund Profile** subpanel (benchmark, replication) at [frontend/src/instruments.jsx:789](frontend/src/instruments.jsx:789) and a **Holdings** table at [frontend/src/instruments.jsx:1018](frontend/src/instruments.jsx:1018). Minimal surface: a "Look-through" badge in the Fund Profile subpanel when proxy-derived, plus a column-level visual cue in the holdings table.

#### Tasks

1. [ ] **API passthrough check** — confirm `instrument-api`'s fund response (the `/instruments/search` and `/instruments/assemble` paths) already serialise `lookthroughProvenance` and `assetAllocation.holdings[].source`. Since the backend uses pydantic native serialisation and the new fields are additive on `FundGolden`, this should be free. Smoke-test with `curl localhost:8003/instruments/assemble -d '{"identifier":...,"persist":false}'`.

2. [ ] **Fund Profile subpanel** — at `frontend/src/instruments.jsx` around line 789, add a conditional row beneath "Replication":

   ```jsx
   {source.lookthroughProvenance && (
     <>
       <Row
         label="Look-through"
         value={
           <span className="lookthrough-badge" title={`Proxy: ${source.lookthroughProvenance.proxyName ?? source.lookthroughProvenance.proxyIsin}\nBenchmark: ${source.lookthroughProvenance.benchmarkName}\nAs of: ${source.lookthroughProvenance.asOfDate}\nConfidence: ${source.lookthroughProvenance.confidence}`}>
             via {source.lookthroughProvenance.proxyIsin} ({source.lookthroughProvenance.confidence})
           </span>
         }
       />
     </>
   )}
   ```

   Style: small inline badge, neutral colour, hover-tooltip surfaces the full provenance. No new CSS class strictly required — reuse existing badge styles in `styles.css` if any (grep for `.badge` first), otherwise add a minimal `.lookthrough-badge` rule.

3. [ ] **Holdings table cue** — at `frontend/src/instruments.jsx` around line 1042 (the `holdings.map(...)` row render), add a subtle visual marker when a row's `source === 'physical_proxy'`. Options ranked by minimal-touch:
   - **(a) Subtitle change**: when **any** holding is proxy-derived, append `" (via physical proxy)"` to the table subtitle (already computed at line 1020). One-line change.
   - **(b) Per-row asterisk + footer note**: append a `*` to rows where `h.source === 'physical_proxy'`, render a footer line under the table explaining it. Slightly heavier.

   Default to **(a)** for the minimal-badge brief. If review feedback prefers per-row, swap to (b).

4. [ ] **Local UI smoke** — `cd frontend && npm run dev`. With docker-compose stack running and LU1681043599 already enriched (from Phase 5 task 4), navigate to Find an instrument → search "MSCI World Swap" → open LU1681043599's detail panel. Verify:
   - Fund Profile subpanel shows the new "Look-through" row with `via IE00B4L5Y983 (high)`.
   - Hover-tooltip shows full provenance (proxy name, benchmark, asOfDate, confidence).
   - Holdings table subtitle reads `~1400 (via physical proxy)` or equivalent.

5. [ ] **Regression smoke** — open a physical ETF (e.g. IE00B4L5Y983 itself) in the panel. Verify the "Look-through" row is absent and the holdings table subtitle has no proxy annotation. Locks the conditional-render guard.

6. [ ] **Docker rebuild** — per CLAUDE.md's frontend-only-changes recipe:
   ```bash
   docker compose down && docker compose build --no-cache frontend && docker compose up --force-recreate
   ```
   Verify the badge surfaces in the containerised build too.

#### Deliverables

- [ ] Fund detail panel renders a "Look-through" row when `lookthroughProvenance` is set.
- [ ] Holdings table subtitle indicates proxy-derived data.
- [ ] No render regression on physical-ETF or non-fund instruments.
- [ ] Tick spec-003 DoD checkboxes for items completed.
- [ ] `git log --oneline -10` review; commit hygiene check.
- [ ] Branch ready for `git push -u origin feat/fund-lookthrough-skill` + PyCharm review.

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `assetAllocation.holdings` path discovery in spec wrong (spec colloquially said `FundGolden.holdings`) | Confirmed | Low | Plan task 0.1 + code use the actual path. Spec wording is informational. |
| Ontology change breaks pydantic regen or OpenSearch mapping load | Low | Medium | Both fields strictly optional; back-compat reads default to `direct` / null. Phase 1 task 7 manifest invariant + Phase 1 deliverable smoke catch drift. |
| Source ordering wrong → lookthrough fires before factsheet_skill populates replicationMethod | Medium | Medium | Phase 0 task 3 audits the planner; Phase 3 task 2 adds explicit `order` if alphabetical doesn't suffice. Integration test in Phase 5 task 1 locks it. |
| LLM picks a wrong proxy (MSCI World vs MSCI World NR / ESG) | Medium | Medium | Confidence enum + rationale surfaced. Patch cache under `patches/lookthrough/` lets curators override. Expected: a small number of corrections in first month of use. |
| Proxy lookup returns 0 hits because no physical ETFs are loaded (cold start) | Medium | Low | AC-7 covers this. Graceful no-op with reason. Phase 5 task 3 ensures the seed exists before AC-1 verification. |
| LLM cost regression vs spec-002 baseline | Low | Low | Same `--enable-factsheet-skill` gate. AC-6 unit-tested. Phase 5 task 6 verifies live. |
| Per-skill control plumbing introduces a regression in spec-002's factsheet skill flow | Medium | Medium | `allowed_llm_skills=None` default preserves existing behaviour. `--enable-factsheet-skill` works as a deprecated alias for one release. Phase 4 task 9 unit-tests both the alias and the new flag pair; Phase 5 task 6b smoke-tests the alias live. |
| Provenance row format for nested-array fields (holdings[].source) isn't a clean fit for the existing per-field SourceOfTruth shape | Low | Low | Phase 0 task 4 confirms. If needed, attribute provenance to the parent `assetAllocation.holdings` path; the per-row `source` enum is the discoverability mechanism. |
| Idempotency edge case: a curator manually populates `holdings` directly between two runs | Low | Low | Fill-empty-only merge → second run no-ops. Curator wins. Document in CLAUDE.md if it comes up. |

### External Dependencies

| Dependency | Risk | Contingency |
|---|---|---|
| OpenSearch (proxy lookup) | Low | Same client used elsewhere; query is read-only. Failure returns `None` → graceful skip. |
| Claude API (LLM ranking) | Medium | Wrapped in try/except. Timeout / API error → empty patch with `llm_unavailable` reason. Chain proceeds. |
| `claude-agent-sdk` installation | Low | Lazy import; `_SDK_AVAILABLE` flag. Mirrors `fund_factsheet_skill`. |
| `ANTHROPIC_API_KEY` in `.env` | Low | Predicate-equivalent skip when unset. CLI default cap means production CI doesn't depend on it. |

## Resource Requirements

### Development

- **Backend Developer**: 1 person. Estimated ~9 hours total (~1 working day with smoke, docs, and UI). Phase 7 adds ~1 h of frontend touch — no React state or routing changes, only JSX conditional rendering in an existing component.

### Infrastructure

- **Local Docker stack** for Phase 5.
- **`ANTHROPIC_API_KEY`** in `.env` for Phase 5 task 4 (AC-1 live verification). Budget: ≤ $0.05 for one LLM call.
- **`pms_golden_fund` seeded with at least one physical MSCI World ETF** (IE00B4L5Y983 recommended). Phase 5 task 3 ensures this.

## Success Metrics

- AC-1 through AC-7 all pass.
- `pytest` clean.
- New skill never fires on a default `fund_universe` batch run (AC-6 lock).
- OpenSearch mapping change is additive: no document re-index required for existing docs.
- LLM cost per Phase 5 live verification ≤ $0.05.
- Net lines added: ~400 (source module ~200, tests ~150, ontology ~30, registry/annotation ~20). No deletions expected (legacy strip already done in spec-002 scope).

## Rollout Plan

Standard repo flow:

1. Phase 1–6 on branch `feat/fund-lookthrough-skill`.
2. PR opened against `main`, body summarises the new chain step + the AC-1 evidence (Amundi MSCI World Swap → iShares Core MSCI World proxy demo).
3. Review in PyCharm. Merge. Delete branch (local + remote).
4. Optional: pre-curate `patches/lookthrough/FG-{ISIN}-001.json` for high-AUM synthetic ETFs in the universe to avoid first-run LLM cost.

## Definition of Done

- [ ] All eight phases complete (0 through 7).
- [ ] All seven spec acceptance criteria met.
- [ ] Ontology + pydantic + OpenSearch mapping carry the two new optional fields.
- [ ] `src/pipeline/agentic/README.md` and `CLAUDE.md` updated.
- [ ] `fund_universe` CLI `--help` text updated.
- [ ] Fund detail panel surfaces `lookthroughProvenance` (badge + tooltip) and the holdings table indicates proxy-derived data.
- [ ] `pytest` clean.
- [ ] Spec-003 DoD section ticked.
- [ ] Branch merged + remote deleted.

## Open Questions

All resolved 2026-05-18:

1. ✅ **Flag design** — replace `--enable-factsheet-skill` with `--enable-llm-skills` (umbrella) + optional `--llm-skills <comma-list>` (per-skill restriction). Agent layer gains `allowed_llm_skills` param. Deprecated alias kept for one release. See spec-003 Clarification #5, plan Phase 3 tasks 4–7, Phase 4 task 9, Phase 5 tasks 6a/6b.
2. ✅ **Reason-string vocabulary** — distinguish `proxy_search_empty` (cold start, no physical funds in index) from `no_physical_proxy_in_universe` (physical funds exist but none match this benchmark). Implemented via a broader probe on empty primary results. See plan Phase 2 task 5 and Phase 4 task 6.
3. ✅ **Confidence-enum derivation** — post-hoc classification on the LLM's `picked_isin` (high = identifier match, medium = name match, low = fuzzy). The LLM no longer emits confidence directly. See plan Phase 2 task 6a and Phase 4 task 8.
4. ✅ **UI surfacing** — resolved by adding Phase 7. "Find an instrument" fund detail panel surfaces the badge + tooltip + holdings-table cue.

## Additional Notes

- **Inheritance from spec-002 implementation**: same lazy-SDK import pattern, same cache-file convention shape, same registry descriptor shape, same `--enable-factsheet-skill` cost-gate semantics. Net delta is tightly scoped: 1 new source + 2 optional ontology fields + 1 new test file + 4 doc touch-ups.
- **Single-service feature** — no decomposition directory needed.
- **Phase 0 findings** to be appended in-place before Phase 1 starts, per the convention from plan-001.

---

*Generated by /sp-plan on 2026-05-18. Plans the implementation of spec-003.md (synthetic-ETF look-through via physical-equivalent proxy). Inherits structure and conventions from plan-001.md (merged via PR #4).*
