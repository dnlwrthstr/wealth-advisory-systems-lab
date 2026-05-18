# Specification: Agentic fund chain — look-through reasoning for synthetic ETFs

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- SPEC_NUMBER: 003 -->
<!-- STATUS: clarified -->
<!-- SUPERSEDES: spec-002.md (which is itself the implemented + merged scope) -->
<!-- CREATED: 2026-05-18T15:50:00Z -->

## Executive Summary

Extension of feature 003. The current fund agentic chain (`fund_firds` → `fund_yahoo` → `fund_factsheet_patch` → `fund_factsheet_skill`) extracts holdings from the issuer's own factsheet / holdings page. For physically-replicated ETFs this is the right answer. For **swap-based (synthetic) ETFs** — e.g. Amundi MSCI World Swap UCITS ETF (LU1681043599) — the issuer's holdings page returns the *substitute basket* (counterparty collateral), not the economic exposure (the ~1,400 MSCI World constituents the fund tracks via swap). For portfolio-risk look-through, the substitute basket is the wrong number.

Add a 5th source — `fund_lookthrough_skill` — that fires only when the chain's earlier sources failed to populate holdings AND the fund is flagged as synthetic / swap-replication. The skill reasons over an **indirect path**: locate a physically-replicated ETF tracking the same benchmark in our own `pms_golden_fund` index, copy its constituent weights, and tag the result with explicit proxy provenance so risk consumers can filter.

Key invariants carried over from spec-002:

- Cost-safe by default. The CLI flag `--enable-factsheet-skill` already lifts `max_cost_class` to `llm_skill`; this spec reuses that same gate (semantic is "open the LLM gate," not "fire one specific skill"). No new flag.
- Fill-empty-only merge. The skill never overwrites holdings populated by an earlier source — by construction it can't fire unless they're empty.
- Per-field provenance via `recordMeta.sourceOfTruth`.
- Universe CLI keeps `web_fetch` cap by default → free batch loads stay free.

What's new and scope-defining:

| Dimension | spec-002 (implemented) | spec-003 (this) |
|---|---|---|
| Fund chain length | 4 sources | **5 sources** (adds `fund_lookthrough_skill`) |
| Holdings source field | implicit (single `holdings` array) | **explicit `source` enum** per holdings row: `direct \| physical_proxy` (V1) |
| Top-level provenance | `recordMeta.sourceOfTruth` rows | adds **`lookthroughProvenance`** block (proxy ISIN, benchmark code, asOfDate, confidence) |
| LLM-skill catalogue | 1 (`fund_factsheet_skill`) | 2 — both gated by the same cost-class lift |
| Proxy strategies | n/a | **physical-equivalent ETF only** (V1); index-provider / FoF / aggregator fallbacks out of scope |

## Description

### Part 1 — New source `fund_lookthrough_skill`

New module at `src/pipeline/agentic/sources/fund_lookthrough_skill.py`. Registry descriptor at `src/pipeline/agentic/registry/fund_lookthrough_skill.yml`.

Source descriptor shape (mirrors `fund_factsheet_skill.yml`):

```yaml
id: fund_lookthrough_skill
module: pipeline.agentic.sources.fund_lookthrough_skill
entrypoint: fetch
covers: [fund]
requires_identifier:
  any_of: [isin]
produces_fields:
  - holdings
  - holdingsCount
  - holdingsAsOf
  - lookthroughProvenance
confidence: medium
cost_class: llm_skill
```

Adapter contract (`fetch(client, identifier, current_record) -> SourcePatch`):

1. **Trigger predicate**. Return an empty patch (no-op) unless **all** hold:
   - `current_record.holdings` is empty/null AND `current_record.holdingsCount` is null.
   - `current_record.replicationMethod` is one of `synthetic` / `swap` (case-insensitive). If null → no-op (the skill does not infer replication mode in V1; that's the factsheet skill's job).
   - `current_record.benchmarkIdentifier` or `current_record.benchmarkName` is populated. Without a benchmark there's nothing to match a proxy against.
2. **Locate physical proxy**. Query `pms_golden_fund` for documents where:
   - `benchmarkIdentifier == current.benchmarkIdentifier` (preferred) or fuzzy match on `benchmarkName`.
   - `replicationMethod == physical` (or `sampling` accepted as second-tier).
   - `holdings` non-empty.
   - ISIN ≠ current ISIN.
   The LLM ranks candidates by holdings recency (`holdingsAsOf`) and AUM, picks one. If none found → no-op with reason `no_physical_proxy_in_universe`.
3. **Copy holdings**. Patch contributes:
   - `holdings`: deep copy of proxy's holdings, each row stamped with `source: physical_proxy`.
   - `holdingsCount`: proxy's count.
   - `holdingsAsOf`: proxy's `holdingsAsOf`.
   - `lookthroughProvenance`: `{ method: "physical_proxy", proxyIsin, proxyGoldenId, proxyName, benchmarkIdentifier, benchmarkName, asOfDate, confidence }`.
4. **Optional patch cache**. Before LLM invocation, check `data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json` for a pre-curated lookthrough patch (parity with how `fund_factsheet_patch` shadows `fund_factsheet_skill`). If present, return it and skip the LLM entirely.

### Part 2 — Ontology / model changes

- `FundGolden.holdings[].source`: new optional enum field. Values: `direct` (default; populated by issuer's own page or factsheet), `physical_proxy` (this spec). Future values left for forward-compat: `index_provider`, `fund_of_fund`, `aggregator`. Existing rows have no `source` → treated as `direct` for back-compat.
- `FundGolden.lookthroughProvenance`: new optional value object. Fields: `method` (enum mirroring the row-level `source`), `proxyIsin` (string, ISIN regex), `proxyGoldenId` (string), `proxyName` (string), `benchmarkIdentifier` (string), `benchmarkName` (string), `asOfDate` (ISO date), `confidence` (enum: `high|medium|low`). Null when all holdings are `direct`.
- Annotation YAML update at `src/pipeline/agentic/annotations/fund.yml` — add the two field entries. Manifest loader's import-time invariant check forces the pydantic model and annotation YAML to stay in sync.
- OpenSearch mapping at `data/opensearch/golden/fund/mapping.json` regenerated by `ontology_tools.golden_record_2_opensearch.convert_to_opensearch`. Backwards-compatible — only adds fields.

### Part 3 — CLI surface

Replace `--enable-factsheet-skill` (introduced in spec-002) with a two-flag design that scales as more LLM skills land:

```bash
--enable-llm-skills              # umbrella: opens max_cost_class gate to llm_skill;
                                 # when set alone, ALL llm_skill sources are eligible.
--llm-skills <comma-list>        # optional restriction: only these llm_skill source IDs run.
                                 # e.g. --llm-skills fund_factsheet_skill,fund_lookthrough_skill
                                 # Omitted → all eligible. Ignored when --enable-llm-skills absent.
```

`--enable-factsheet-skill` remains as a **deprecated alias** for `--enable-llm-skills` (no-op renamed; emits a deprecation log line). One release of overlap, then removal — out of scope to remove here.

Agent-layer change: `assemble_and_persist` (and the layers below it — `assemble.assemble_golden`, `planner.run_planner`) gain an optional `allowed_llm_skills: Optional[set[str]] = None` param. Default `None` preserves current behaviour (all llm_skill sources eligible when cost gate is open). The planner filters: a source is eligible iff `source.cost_class <= max_cost_class` AND (`source.cost_class != llm_skill` OR `allowed_llm_skills is None` OR `source.id in allowed_llm_skills`).

For per-fund work, `POST /instruments/assemble` already accepts `max_cost_class` in the request body; the schema gains an optional `allowed_llm_skills` array. The lookthrough skill fires when callers set `max_cost_class="llm_skill"` and either omit `allowed_llm_skills` or include `"fund_lookthrough_skill"` in it.

## Functional Requirements

### FR-1 — Source registration

- [ ] `pipeline.agentic.sources.fund_lookthrough_skill.fetch` exists with the adapter signature used by `fund_factsheet_skill`.
- [ ] `src/pipeline/agentic/registry/fund_lookthrough_skill.yml` is loaded by the registry loader; `AGENTS["fund"]` chain length becomes 5.
- [ ] Source order: `fund_lookthrough_skill` runs **after** `fund_factsheet_skill` (alphabetical resolution within `cost_class=llm_skill` works; lock with explicit `order` key in the YAML if needed).

### FR-2 — Trigger predicate

- [ ] Skill returns an empty patch when any precondition fails: `holdings` already populated, `replicationMethod` not in `{synthetic, swap}`, or no benchmark identifier/name.
- [ ] No LLM call is made when the predicate short-circuits — the function must check preconditions before any network or `claude-agent-sdk` invocation.

### FR-3 — Proxy resolution

- [ ] Skill queries `pms_golden_fund` filtered by `benchmarkIdentifier` (exact) then `benchmarkName` (text-match) and selects a physical-replication candidate.
- [ ] When multiple candidates exist, the LLM ranks them by `holdingsAsOf` recency and AUM; the picked candidate's ISIN, goldenId, and name land in `lookthroughProvenance`.
- [ ] When zero candidates exist, the skill returns an empty patch with a structured reason (`no_physical_proxy_in_universe`) surfaced in the assemble result's `remaining_gaps` / source log.

### FR-4 — Patch shape

- [ ] Each row in the patched `holdings` array carries `source: physical_proxy`.
- [ ] `lookthroughProvenance` is populated with `method=physical_proxy`, the proxy's ISIN, goldenId, name, benchmark, asOfDate, and a confidence enum value.
- [ ] `recordMeta.sourceOfTruth` gains a `fund_lookthrough_skill` row stamping each affected field.

### FR-5 — Patch cache

- [ ] If `data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json` exists, the skill loads + returns it verbatim, **without** an LLM call.
- [ ] The cache file shape mirrors the live patch — it must include `source: physical_proxy` on every row and a full `lookthroughProvenance` block.

### FR-6 — Idempotency and merge safety

- [ ] Re-running the chain over a fund whose holdings are already proxy-populated is a no-op (predicate short-circuits on non-empty `holdings`).
- [ ] If a future direct-holdings source later populates `holdings`, the proxy data is **not** overwritten on subsequent runs — the merger is fill-empty-only. Replacing proxy data with direct data is a separate concern (out of scope; needs an explicit "refresh" path).

### Non-Functional Requirements

- **Performance**: per-fund latency budget ≤ 30 s when the skill fires (one OpenSearch query, one LLM call). Skill is gated to a tiny subset of funds (synthetic + no holdings) so universe-wide impact is low.
- **Cost**: ~$0.005–0.02 per fund when the skill actually fires (LLM ranks ≤ 10 candidates from a short OpenSearch hit list). Pre-curated patches under `patches/lookthrough/` cost $0.
- **Reliability**: an LLM timeout / API error → empty patch with reason `llm_unavailable`. The chain continues; the fund record persists without lookthrough. No fund is ever blocked by this skill.
- **Observability**: structured log per invocation with proxy ISIN (or `no_proxy`), `cost_class_used`, `cache_hit` boolean. `lookthroughProvenance.confidence` surfaces in the assemble outcome.

## User Stories

- **US-1** — As a portfolio risk analyst pulling look-through exposures for a client portfolio that holds Amundi MSCI World Swap UCITS ETF (LU1681043599), I want the assembled fund record to carry the ~1,400 MSCI World constituents (via the iShares Core MSCI World physical proxy) tagged with `source: physical_proxy`, so my factor models see the right economic exposure and the proxy lineage is auditable.
- **US-2** — As a data engineer, I want the skill to short-circuit cheaply on funds where it can't help (physical ETFs, funds with holdings already populated, funds missing a benchmark) so cost stays bounded as the fund universe grows.
- **US-3** — As a compliance reviewer, I want every proxy-derived holding to be filterable by `holdings[].source = physical_proxy` and traceable back to its proxy ISIN via `lookthroughProvenance.proxyIsin`, so I can produce regulatory reports distinguishing direct vs. derived exposures.

## Acceptance Criteria

- [ ] **AC-1** Given LU1681043599 (Amundi MSCI World Swap) is in `pms_golden_fund` with `replicationMethod=synthetic`, `benchmarkName="MSCI World"`, no `holdings`, and IE00B4L5Y983 (iShares Core MSCI World physical) is also in the index with non-empty `holdings`, when I `POST /instruments/assemble` with `identifier={kind:isin,value:LU1681043599}, max_cost_class=llm_skill, persist=true`, then the persisted record has `holdings.length > 1000`, every row has `source: "physical_proxy"`, and `lookthroughProvenance.proxyIsin == "IE00B4L5Y983"`.
- [ ] **AC-2** Given IE00B4L5Y983 (a physical ETF), when I assemble it with `max_cost_class=llm_skill`, then `fund_lookthrough_skill` does not contribute a patch (predicate short-circuit on `replicationMethod != synthetic`), and no LLM call is recorded.
- [ ] **AC-3** Given a synthetic fund whose benchmark has no physical-replication peer in `pms_golden_fund`, when I assemble it with `max_cost_class=llm_skill`, then the skill returns an empty patch with reason `no_physical_proxy_in_universe`, the assemble succeeds, and the persisted record has empty `holdings` (unchanged).
- [ ] **AC-4** Given the same synthetic fund as AC-1, when I re-run the assemble immediately (idempotency), then `holdings` and `lookthroughProvenance` are unchanged byte-for-byte (modulo `recordMeta` timestamps).
- [ ] **AC-5** Given `data/opensearch/golden/fund/patches/lookthrough/FG-LU1681043599-001.json` exists with a hand-curated proxy mapping to a different ISIN, when I assemble LU1681043599 with `max_cost_class=llm_skill`, then the cached patch wins (no LLM call, `lookthroughProvenance.proxyIsin` matches the cache file), and the cache_hit log line is emitted.
- [ ] **AC-6** Given the default CLI invocation `python -m pipeline.agentic.cli.fund_universe --all` (no `--enable-llm-skills`), when the batch runs, then neither `fund_factsheet_skill` nor `fund_lookthrough_skill` is invoked, regardless of how many synthetic ETFs are in the universe (cost-safe default preserved from spec-002).
- [ ] **AC-6b** Given `--enable-llm-skills --llm-skills fund_factsheet_skill` (umbrella + exclusion), when the batch runs against a synthetic ETF, then `fund_factsheet_skill` is invoked but `fund_lookthrough_skill` is **not** — per-skill restriction takes effect.
- [ ] **AC-7** Given the OpenSearch query for a proxy returns 0 hits because `pms_golden_fund` is empty, when the skill runs, then it gracefully returns an empty patch with reason `proxy_search_empty` (handles the cold-start case where no physical ETFs have been loaded yet).

## Technical Constraints

### In scope

- Scope=fund only.
- Single proxy strategy: **physical-equivalent ETF** sourced from our own `pms_golden_fund` index.
- Ontology additions: `holdings[].source` enum and `lookthroughProvenance` value object on `FundGolden`.
- Reuse the existing layered API. Replace the spec-002 `--enable-factsheet-skill` flag with `--enable-llm-skills` + optional `--llm-skills <comma-list>` for per-skill restriction. Keep `--enable-factsheet-skill` as a deprecated alias for one release.
- Reuse `pipeline.gold.fund_yahoo_enrich` workflow for the proxy fund — assumes physical-equivalent ETFs are already seeded via the universe CLI before the synthetic ETF is assembled, OR that they get seeded in the same batch.

### Out of scope

- Index-provider constituent files (MSCI / FTSE / S&P direct ingestion).
- Fund-of-fund recursive decomposition.
- Aggregator scrapers (justETF, Trackinsight).
- Refreshing proxy-derived holdings when the proxy itself updates (subsequent runs are no-ops by design — proxy refresh is a separate "stale-data sweep" concern).
- Substitute-basket / counterparty-collateral analysis (the *other* swap-ETF use case; orthogonal to portfolio-risk look-through).
- Replication-method inference (V1 trusts `replicationMethod` as populated by `fund_factsheet_patch` / `fund_factsheet_skill`).

### Dependencies

- **External APIs**: none new. The skill reads from local OpenSearch + invokes the existing `claude-agent-sdk` path already used by `fund_factsheet_skill`.
- **Database**: existing `pms_golden_fund` index — both as input (proxy lookup) and as output (persisted enrichment). OpenSearch mapping change is **additive only** (two new optional fields). The `opensearch-init` regeneration step picks them up via the standard `golden_record_2_opensearch` build.
- **Libraries**: no new requirements.txt additions.
- **Ordering**: this source must run after `fund_factsheet_skill` in the per-fund chain so `replicationMethod` and `benchmarkIdentifier` have a chance to be populated first.

### Implementation Notes

- The proxy lookup is a single OpenSearch `bool` query: `must` on `benchmarkIdentifier.keyword`, `should` on `benchmarkName` (text), `filter` on `replicationMethod ∈ {physical, sampling}`. Top 10 hits to the LLM for ranking.
- The LLM prompt should be small: scope=fund, present the synthetic fund's identity (name, benchmark, AUM) and a JSON list of candidate physical proxies (name, ISIN, benchmark, AUM, holdingsAsOf, holdingsCount). Ask for the single best match with a confidence enum and a one-line rationale. Cap tokens.
- The `lookthroughProvenance.confidence` enum maps from the LLM's rating: high (exact benchmark match), medium (variant match — e.g. "MSCI World" vs "MSCI World NR"), low (loose match, name only).
- Cache file path `data/opensearch/golden/fund/patches/lookthrough/FG-{ISIN}-001.json` keeps lookthrough patches separate from regular factsheet patches so a curator can manage them independently.
- The chained-issuer assembly downstream is unaffected — `extract_leis` operates on umbrella / managementCompany / promoter; holdings rows don't carry LEIs that trigger chaining.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM picks a wrong proxy (different index variant, e.g. World NR vs World) | Medium | Medium | `lookthroughProvenance.confidence` surfaced for downstream filtering; AC-1 verifies the canonical case (MSCI World swap → iShares Core MSCI World). Curators can override via the patch cache file. |
| Proxy holdings are stale (proxy `holdingsAsOf` lags by months) | Medium | Low | `lookthroughProvenance.asOfDate` carries the proxy's snapshot date verbatim; downstream consumers decide stale thresholds. No silent freshness rewrite. |
| Synthetic ETF has no physical peer in universe (e.g. niche bespoke index) | Medium | Low | AC-3 — graceful no-op with structured reason. User can seed a peer or accept the gap. |
| `replicationMethod` is null because factsheet skill wasn't run | High (default CLI) | Low | By design — lookthrough skill is also LLM-skill class, gated by same flag. If factsheet skill didn't run, lookthrough won't either, so the precondition gap is moot. |
| Cost runaway from a recursive / self-referential proxy chain (proxy fund A → references B → references A) | Low | Low | Single hop only — proxy fund's own `holdings` is what we copy. We never re-resolve through the proxy's chain. V1 doesn't support FoF decomposition. |
| Ontology change breaks existing `pms_golden_fund` reads | Low | Medium | Both fields optional + back-compat: missing `holdings[].source` reads as `direct`; missing `lookthroughProvenance` is null. Search index mirror is regenerated by existing `search_index_build`. |
| LLM cost regression vs spec-002 baseline | Medium | Low | New skill is strictly opt-in via the new `--enable-llm-skills` flag; default-cap batch loads stay free. AC-6 locks the global default; AC-6b locks per-skill restriction. |
| Per-skill control plumbing introduces a regression in the existing factsheet skill flow | Medium | Medium | `allowed_llm_skills=None` default preserves current behaviour; deprecated `--enable-factsheet-skill` alias keeps spec-002's invocation working. Phase 4 unit tests cover both the legacy alias and the new flag pair. |

## Testing Strategy

- **Unit tests** (`tests/agentic/test_fund_lookthrough_skill.py`):
  - Trigger predicate truth table: synthetic + no holdings + benchmark → fires; physical → no-op; missing benchmark → no-op; holdings already populated → no-op.
  - Proxy selection: given a mocked OpenSearch returning 3 candidates, assert the LLM picks the right one based on stub responses; assert empty-result handling (AC-3, AC-7).
  - Patch shape: `holdings[].source = physical_proxy` on every row; `lookthroughProvenance` block fully populated.
  - Cache hit: stub the cache file, assert no LLM call (AC-5).
  - LLM timeout / API error → empty patch with `reason=llm_unavailable`; no exception propagated.
- **Integration tests** (`tests/agentic/test_fund_chain_e2e.py` — extend the existing one):
  - Chain order: `fund_lookthrough_skill` runs after `fund_factsheet_skill`.
  - Fill-empty-only: direct holdings populated upstream → lookthrough skill no-ops.
  - End-to-end with stubbed OpenSearch + stubbed LLM: AC-1 happy path on LU1681043599 → IE00B4L5Y983.
- **End-to-end / live**:
  - Manual smoke on docker-compose stack: load IE00B4L5Y983 via `fund_universe --umbrella-lei <iShares-LEI>`; then assemble LU1681043599 with `max_cost_class=llm_skill, persist=true`; verify proxy holdings in the persisted doc + the `Find an instrument` UI surfaces holdings count.
- **Idempotency**: re-run the same `--all --enable-factsheet-skill` batch; assert `pms_golden_fund` doc counts and `lookthroughProvenance.proxyIsin` are unchanged (AC-4).

## Definition of Done

- [ ] All six functional requirements implemented.
- [ ] All seven acceptance criteria met (AC-1 + AC-4 verified live on the Amundi MSCI World swap → iShares physical proxy pair; AC-2 / AC-3 / AC-6 / AC-7 covered by unit tests; AC-5 covered by a fixture patch under `tests/fixtures/`).
- [ ] `FundGolden.holdings[].source` and `FundGolden.lookthroughProvenance` added to the ontology with annotation entries + regenerated OpenSearch mapping.
- [ ] `src/pipeline/agentic/README.md` "Fund (`scope="fund"`)" table updated to show 5 sources; cost-class semantics paragraph updated to name both LLM-skill sources.
- [ ] `CLAUDE.md` "Agentic data engineering" block notes `fund_lookthrough_skill` in the fund chain enumeration; "Fact-sheet + full-holdings enrichment" block gets a paragraph on the proxy-fallback path.
- [ ] `pytest` green (target ≥ 195/195 including the new tests).
- [ ] Branch `feat/fund-lookthrough-skill` merged into `main` via PyCharm review.
- [ ] Manual smoke: synthetic ETF assemble surfaces `lookthroughProvenance` in the `Find an instrument` fund detail panel (UI may need a small render update; track separately if non-trivial).

## Clarifications (resolved 2026-05-18)

1. ✅ **CLARIFIED — Chain placement**: new source `fund_lookthrough_skill` (5th in fund chain), runs after `fund_factsheet_skill`. Clean separation between document-parsing (factsheet) and cross-fund reasoning (lookthrough); independent gateability via per-skill restriction (resolution 5).
2. ✅ **CLARIFIED — Trigger**: fires only when `holdings` is empty AND `replicationMethod ∈ {synthetic, swap}`. Cost-bounded by construction; aligns with the cost-conscious default established in spec-002.
3. ✅ **CLARIFIED — Indirect strategy (V1)**: physical-equivalent ETF proxy only. Sourced from our own `pms_golden_fund` — no external scraping, no index-provider integration, no fund-of-fund recursion. Future strategies remain open via the `source` enum's reserved values.
4. ✅ **CLARIFIED — Provenance shape**: new `holdings[].source` enum + new top-level `lookthroughProvenance` block on `FundGolden`. Risk teams can filter holdings by source; auditors can trace each proxy-derived dataset back to its source ISIN, benchmark, asOfDate, and confidence rating.
5. ✅ **CLARIFIED — CLI flag design**: replace `--enable-factsheet-skill` with `--enable-llm-skills` (umbrella) + optional `--llm-skills <comma-list>` (per-skill restriction). Cost-gate semantic is decoupled from skill identity, so future LLM skills slot in without another flag rename. Agent layer gains `allowed_llm_skills: Optional[set[str]]` to make this enforceable below the CLI. `--enable-factsheet-skill` remains as a deprecated alias for one release.
6. ✅ **CLARIFIED — Reason-string vocabulary**: distinguish two empty-result cases. `proxy_search_empty` = the OpenSearch query returned zero hits total (cold start, index has no physical funds yet). `no_physical_proxy_in_universe` = hits exist but none match the benchmark. Downstream consumers can tell "we need to seed the universe" from "this benchmark has no peer."
7. ✅ **CLARIFIED — Confidence-enum derivation**: post-hoc classification on the LLM's `picked_isin`, NOT a value the LLM emits directly. Logic: `high` = picked candidate's `benchmarkIdentifier` exactly matches current; `medium` = `benchmarkName` matches but identifier differs (variant index, e.g. World NR vs World); `low` = name-only fuzzy match. More robust against LLM creativity and keeps the rating deterministic given a fixed candidate set.

### Open for the next iteration (not blocking V1)

- Refreshing proxy-derived holdings when the proxy itself updates (separate "stale-data sweep" or a `--refresh-lookthrough` CLI flag).
- Inferring `replicationMethod` when the factsheet skill couldn't (e.g. LLM reads the prospectus title / structure from public sources).
- Index-provider direct ingestion (MSCI / FTSE / S&P constituent files) as a higher-confidence alternative to physical proxies.
- Fund-of-fund recursive decomposition (`source: fund_of_fund`).

---

*Generated by /sp-spec on 2026-05-18. Supersedes spec-002.md (implemented + merged via PR #4). Extends the agentic fund chain with a 5th source for synthetic-ETF look-through via physical-equivalent proxies.*
