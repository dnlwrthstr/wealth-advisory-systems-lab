# Specification: Agentic fund universe — document existing chain + add batch CLI

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- SPEC_NUMBER: 002 -->
<!-- STATUS: clarified -->
<!-- SUPERSEDES: spec-001.md (placeholder skeleton) -->
<!-- CREATED: 2026-05-18T10:45:00Z -->

## Executive Summary

Third feature in the universe-loader series. Builds the fund slice via the agentic platform under `src/pipeline/agentic/`, scope=`fund`. The agentic chain for funds already has four sources (`fund_firds`, `fund_yahoo`, `fund_factsheet_patch`, `fund_factsheet_skill`); the universe HTTP route `POST /universe/fund` already works (covered by `test_universe_endpoint.py`). The missing piece is the **batch entry point** that loops over the curated [fund_umbrellas.yml](src/pipeline/gold/data/fund_umbrellas.yml) (10 entries: iShares / Vanguard / Xtrackers / Amundi / UBS), enumerates share-class ISINs per umbrella from FIRDS, and runs each through the agentic chain. The legacy `pipeline.gold.fund_firds --universe` CLI is then stripped back to a library.

Structurally a clone of feature 002 (per-LEI two-level loop), with three material differences:

| Dimension | Bond (feature 002) | Fund (this feature) |
|---|---|---|
| Universe key | Issuer LEI (issuer of debt) | Umbrella LEI (legal vehicle hosting sub-funds) |
| Corporate hierarchy | 1 level (issuer) | 5 levels (promoter → managementCompany → umbrella → subFund → shareClass) |
| Issuer chain per primary record | 1 (issuer LEI) | **3** (umbrella + managementCompany + promoter LEIs) |
| FIRDS CFI filter | `D*` (debt) | `C*` (collective investment vehicles) |
| Cost-class cap | `web_fetch` (no LLM) | **`llm_skill` by agent default** — `find-and-parse-factsheet` opt-in |
| CLI default cost posture | Cheap by construction | **Cap to `web_fetch` by default**; `--enable-factsheet-skill` opts in |

The cost-class decision is the load-bearing one: this is the first feature where the agentic chain can spend LLM tokens on the critical path. The CLI defaults to `web_fetch` so a full universe load is free; users opt into the factsheet skill explicitly when they want TER, SRRI/SRI, dealing terms, and service-provider enrichment.

Everything else inherits: `AGENTS["fund"].assemble_and_persist(...)` per ISIN, `index_search_hit` mirror, strict-serial, per-ISIN error isolation, per-umbrella error isolation, JSON report grouped per umbrella, lazy opensearch imports, `load_dotenv()` at module top.

## Description

### Part 1 — Document the existing agentic fund chain

Extend [src/pipeline/agentic/README.md](src/pipeline/agentic/README.md) (built up by features 001 + 002) with a new **Fund universe data flow** subsection under the existing "Universe batch CLIs" block. Cover:

- `fund_umbrellas.yml` shape (umbrellaLei, umbrellaName, managementCompanyLei + Name, promoter, country, legalStructure, legalFramework).
- Per-umbrella FIRDS enumeration via `pipeline.gold._firds.iter_issuer_records(lei, FIRDS_FL)` then `fund_firds.dedupe_by_isin` (CFI=C* filter).
- Per-share-class `AGENTS["fund"].assemble_and_persist(...)` invocation.
- The 4-source agentic chain order for `fund` scope: `fund_firds` (api_call) → `fund_yahoo` (api_call) → `fund_factsheet_patch` (file_read) → `fund_factsheet_skill` (llm_skill).
- The three-record issuer chain: persist's `extract_leis` walks `umbrella.lei`, `managementCompany.lei`, and `promoter.lei` (when present) and runs an issuer-scope assemble per distinct LEI.
- Cost-class semantics: `default_max_cost_class="llm_skill"` on `FundAgent`; the batch CLI overrides to `"web_fetch"` by default for cost safety.

### Part 2 — Add `fund-universe` batch CLI

New module at `src/pipeline/agentic/cli/fund_universe.py`. Flags:

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.fund_universe \
    [--umbrella-lei LEI]            # single-umbrella smoke test (mutually exclusive with --all)
    [--all]                         # process every umbrella in fund_umbrellas.yml (default)
    [--umbrellas PATH]              # override the curated YAML (legacy parity)
    [--limit-per-umbrella N]        # cap share-classes emitted per umbrella
    [--enable-factsheet-skill]      # opt into LLM cost class (default: web_fetch only)
    [--dry-run]
    [--universe-status STATUS]      # default in_universe
    [--report-out PATH]
    [--log-level LEVEL]
```

Behaviour per umbrella:

1. Resolve umbrella entry from `fund_umbrellas.yml`.
2. Call `iter_issuer_records(umbrella_lei, FIRDS_FL)` — same shared helper bond uses.
3. `dedupe_by_isin` (fund's own, filters to CFI=C*) → list of distinct share-class ISINs.
4. Apply `--limit-per-umbrella` if set.
5. For each ISIN, call `AGENTS["fund"].assemble_and_persist(client, identifier={"kind":"isin","value":isin}, status=universe_status, max_cost_class=...)` where `max_cost_class` is `"web_fetch"` by default or `"llm_skill"` when `--enable-factsheet-skill` is set.
6. Mirror onto `pms_golden_instrumentsearch` via `index_search_hit`.
7. Per-ISIN outcome captured: `(umbrella_lei, isin, status, golden_id, quality_score, remaining_gaps, chained_issuers, reason)`. `chained_issuers` is expected to be 1–3 per fund (umbrella + managementCompany when present + promoter when present).

Issuer-level error isolation matches bond: if a per-LEI FIRDS query returns nothing, log a warning and continue. The CLI inherits `iter_issuer_records`'s built-in retry-then-empty pattern.

### Part 3 — Strip legacy `pipeline.gold.fund_firds` to library

Same shape as features 001/002's T016 / T009. Delete:

- `main()` and the `argparse` setup.
- `write_ndjson` (only called by `main`).
- The `if __name__ == "__main__"` block.
- Unused imports after the above (`argparse`, possibly `Path` — check).

Keep (called by the agentic source or transitively):

- `fetch_by_isin` — called by `pipeline.agentic.sources.fund_firds`.
- `firds_to_golden`, `load_issuers`, `dedupe_by_isin`, `_resolve_issuer`, `_record_quality`, `_fingerprint`, `_to_float`, `_iso_date`, `_lifecycle_status`, `_asset_class_defaults`, `derive_*` helpers — supporting library.
- `FIRDS_FL` constant — fund-specific Solr field list.

Module docstring rewritten to "library only" — parity with `equity_yahoo` (feature 001) and `bond_firds` (feature 002).

## Functional Requirements

### FR-1 — Document the fund chain

- [ ] [src/pipeline/agentic/README.md](src/pipeline/agentic/README.md) gains a "Fund universe data flow" subsection covering the four-source order, the three-record issuer chain, and the cost-class default.
- [ ] CLAUDE.md pointer for the new CLI added under "Agentic data engineering"; "Legacy bulk fetchers" entry for `fund_firds` rewritten to reflect the library-only role (mirrors the feature 002 update for `bond_firds`).

### FR-2 — Universe resolution

- [ ] CLI accepts `--umbrella-lei LEI` (single) or `--all` (default, no flag needed). The two are mutually exclusive at argparse level.
- [ ] CLI accepts `--umbrellas PATH` for an override YAML.
- [ ] Unknown LEI (via `--umbrella-lei`) → exit non-zero with a helpful list of LEIs in the active YAML.
- [ ] If `fund_umbrellas.yml` is missing or malformed, exit non-zero with a clear error pointing at the expected location and shape.

### FR-3 — Per-umbrella FIRDS enumeration

- [ ] For each umbrella LEI, the CLI calls `iter_issuer_records(lei, FIRDS_FL)` and pipes the result through `dedupe_by_isin` (CFI=C* filter).
- [ ] Umbrella-level FIRDS failures (HTTP 5xx after the internal retry, timeout, empty response) appear as `isins_found=0` in the report and the batch continues.

### FR-4 — Per-ISIN assembly with cost-class control

- [ ] For each resolved ISIN, the CLI calls `AGENTS["fund"].assemble_and_persist(client, identifier, status, max_cost_class)` where:
  - `max_cost_class="web_fetch"` by default (skips `fund_factsheet_skill`).
  - `max_cost_class="llm_skill"` when `--enable-factsheet-skill` is set.
- [ ] After each successful persist, the record is mirrored onto `pms_golden_instrumentsearch` via `index_search_hit`.
- [ ] Per-ISIN errors are isolated. Per-umbrella errors are isolated. The batch never aborts on a single failure.

### FR-5 — Reporting

- [ ] Per-ISIN outcome captured with `umbrella_lei` field (parity with bond's `issuer_lei`).
- [ ] Report (stdout + optional `--report-out path.json`) carries per-umbrella totals AND overall totals. Same nested shape as bond's `_RunReport.issuers` — call it `_RunReport.umbrellas`.
- [ ] Exit code: `0` on no failures, `1` on per-ISIN failures, `2` on infrastructure failure (`OPENSEARCH_URL` unset when not `--dry-run`).

### FR-6 — Strip legacy bulk loader

- [ ] `pipeline.gold.fund_firds.main`, `write_ndjson`, the `argparse` setup, and the `if __name__` block are removed.
- [ ] `pipeline.gold.fund_firds.fetch_by_isin` and the supporting library functions remain importable.
- [ ] Existing tests under `tests/agentic/` that exercise `fetch_by_isin` continue to pass.

### Non-Functional Requirements

- **Performance**: full curated set (10 umbrellas; expected 50–500 share classes total) in under 15 minutes on strict serial with `--cap web_fetch`. With `--enable-factsheet-skill`, expect 2–5× slower per fund and real LLM cost.
- **Cost** (new for this feature): a full `--all` run with `--cap web_fetch` is free at the LLM layer. With `--enable-factsheet-skill`, budget ~$0.01–0.05 per fund without a pre-curated patch (Sonnet-class LLM, PDF parsing). The skill skips silently when a patch already exists under `data/opensearch/golden/fund/patches/`, so re-runs are cheap.
- **Reliability**: idempotent re-runs converge to the same OpenSearch state.
- **Observability**: structured logging per ISIN at INFO; per-umbrella summary at INFO; chained-issuer count surfaced in each outcome.

## User Stories

- **US-1** — As a data engineer seeding fund data into a fresh OpenSearch, I want one cost-safe CLI invocation to load every share class from the curated umbrella list so I don't have to think about LLM cost on the first pass.
- **US-2** — As a portfolio researcher who needs TER / SRRI / dealing terms for a specific umbrella, I want `--umbrella-lei <LEI> --enable-factsheet-skill` to scope an LLM-enriched load to one fund family.
- **US-3** — As a maintainer adding a new umbrella to the lab, I want to drop a YAML entry into `fund_umbrellas.yml` and re-run the CLI with no other coordination.

## Acceptance Criteria

- [ ] **AC-1** Given a clean local OpenSearch and the bundled `fund_umbrellas.yml`, when I run `python -m pipeline.agentic.cli.fund_universe`, then `pms_golden_fund` receives ≥1 document per umbrella LEI that has share-classes in FIRDS, and `pms_golden_issuer` receives between 1 and 3 records per umbrella (umbrella, managementCompany when present, promoter when present).
- [ ] **AC-2** Given the same OpenSearch state, when I re-run the same command, then document counts in `pms_golden_fund`, `pms_golden_issuer`, and `pms_golden_instrumentsearch` are unchanged (idempotent).
- [ ] **AC-3** Given an NDJSON snapshot from the legacy `pipeline.gold.fund_firds --universe` on the prior commit, when I diff schema-overlapping fields on the share-class records in `pms_golden_fund`, then no field that legacy populated is missing in the new chain, and divergences fall into one of: (a) fields newly populated by the agentic chain by design (e.g. `universeStatus`, factsheet-skill fields when `--enable-factsheet-skill` was set); (b) timestamp / run-id fields; (c) the `goldenId` format change documented in feature 002 (chain adds MIC venue suffix).
- [ ] **AC-4** Given `--dry-run`, when the CLI runs, then no writes hit `pms_golden_fund`, `pms_golden_issuer`, or `pms_golden_instrumentsearch`, and the report still shows per-umbrella resolution outcomes.
- [ ] **AC-5** Given `--umbrella-lei <unknown LEI>`, when the CLI runs, then exit code is non-zero and stderr lists the LEIs available in the active YAML.
- [ ] **AC-6** Given the default cost-class cap (`web_fetch`), when the CLI runs against an ISIN whose factsheet patch is **not** on disk, then `fund_factsheet_skill` is **not** invoked (no LLM call). Given `--enable-factsheet-skill`, the skill is eligible to fire and the record's `remaining_gaps` for skill-covered fields is reduced.

## Technical Constraints

### In scope

- Scope=fund only.
- Reuse the layered API from `src/pipeline/agentic/README.md` — no new abstractions.
- Reuse `pipeline.gold._firds.iter_issuer_records`, `fund_firds.fetch_by_isin`, `fund_firds.dedupe_by_isin`, `fund_firds.load_issuers` — all existing library functions stay.
- `from dotenv import load_dotenv; load_dotenv()` at module top per the convention established by PR #3 (post-feature-001 + post-feature-002 fix).

### Out of scope

- Adding new fund sources (separate feature if needed).
- Frontend changes — `Find an instrument` already reads from `pms_golden_instrumentsearch` and surfaces fund records via the existing `ow_type=fund` (single word, no casing mismatch).
- Ontology field additions in `universe.models.FundGolden`.
- Bulk re-running the LLM skill across all funds (the `find-and-parse-factsheet` skill is per-fund manual work; the CLI just lets it fire when patches are missing AND `--enable-factsheet-skill` is set).
- New fund universes (e.g. closed-end funds, hedge funds) — restrict to UCITS open-ended via FIRDS CFI=C*, same as legacy.

### Dependencies

- **External APIs**: ESMA FIRDS Solr (public), GLEIF (public; chained via `assemble_and_persist`'s issuer step).
- **External services** (gated by `--enable-factsheet-skill`): the `find-and-parse-factsheet` Claude Code skill (LLM call + PDF fetch).
- **Database**: existing `pms_golden_fund`, `pms_golden_issuer`, `pms_golden_instrumentsearch`. No mapping changes.
- **Libraries**: existing `requests`, `python-dotenv`. **No new requirements.txt additions**.

### Implementation Notes

- The CLI module mirrors `pipeline.agentic.cli.bond_universe.py` almost verbatim. The structural differences are: dataclass field is `umbrella_lei` (was `issuer_lei`), `_RunReport` field is `umbrellas` (was `issuers`), `_IssuerReport` renamed to `_UmbrellaReport`, plus the `--enable-factsheet-skill` flag and the per-call `max_cost_class` override.
- Opensearch-dependent imports stay lazy inside the functions that need them, matching the pattern set in features 001/002.
- The three-record issuer chain happens automatically inside `persist.assemble_and_persist` — the CLI does nothing special for it. The report's per-ISIN `chained_issuers` count surfaces it for verification (expected 1–3, vs ≤1 for bond).
- The `dotenv` import + `load_dotenv()` call goes immediately after `from __future__ import annotations` per the convention.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Accidentally invoking LLM skill in a default run | Low | Medium | CLI default is `--cap web_fetch`; `--enable-factsheet-skill` is opt-in only. AC-6 explicitly tests this. |
| FIRDS slow for one umbrella mid-batch | Medium | Low | `iter_issuer_records` retries internally; failed umbrella reports `isins_found=0`. |
| Three-record issuer chain creates duplicate writes for shared LEIs across umbrellas | Medium | Low | `pms_golden_issuer.goldenId` is LEI-derived, so re-writes overwrite the same doc — idempotent by construction. |
| AC-3 surfaces material regressions on share-class fields | Low | Medium | Same posture as features 001/002 — T009-equivalent gated on the parity diff. |
| Hidden caller of `fund_firds.main` survives the grep | Low | Medium | Phase 0 grep + pytest catch it (consistent with bond feature). |
| Volume of share-classes per umbrella materially larger than estimated | Low | Low | iShares + Vanguard together can have >500 share classes. `--limit-per-umbrella N` for smoke; document expected runtime. |

## Testing Strategy

- **Unit tests**:
  - `tests/agentic/test_fund_universe_cli.py` — mirror of `test_bond_universe_cli.py`. Mocked `AGENTS["fund"]`, mocked `iter_issuer_records`, mocked `index_search_hit` via `sys.modules` injection. Cover: AC-4 (dry-run), AC-5 (unknown LEI), AC-6 (cost-class default vs opt-in — assert `max_cost_class` passed through correctly), happy path (2 umbrellas × 3 share-classes), umbrella-level isolation (one FIRDS fail → others proceed), per-ISIN isolation, `--limit-per-umbrella` cap, JSON report shape.
- **Integration tests**:
  - Existing `tests/agentic/test_fund_firds_source.py` (if it exists) or equivalent covers `fetch_by_isin`; must still pass after the strip.
  - Existing `tests/agentic/test_universe_endpoint.py` exercises `POST /universe/fund`; must still pass.
- **End-to-end / live**:
  - Single-umbrella smoke (smallest in `fund_umbrellas.yml`) against docker-compose OpenSearch with `--cap web_fetch`.
  - `--all --limit-per-umbrella 3` for AC-1/AC-2 verification.
  - Optional: `--umbrella-lei <one> --enable-factsheet-skill --limit-per-umbrella 1` to verify the LLM-skill path lands a patch.

## Definition of Done

- [ ] All six functional requirements implemented.
- [ ] All six acceptance criteria met.
- [ ] Fund universe section landed in `src/pipeline/agentic/README.md`.
- [ ] `pipeline.gold.fund_firds --universe` CLI surface stripped; library functions retained.
- [ ] CLAUDE.md updated (legacy `fund_firds` bullet rewritten + new CLI pointer added).
- [ ] Tests pass: `pytest` clean.
- [ ] Branch `feat/agentic-fund-universe` merged into `main` via PyCharm review.
- [ ] Local smoke: `instrument-api` still serves `POST /instruments/assemble` for a fund ISIN; `GET /universe/fund` lists the loaded share-classes; `GET /instruments/search?type=fund` returns search-mirror hits (the bond `ow_type` casing bug from feature 002 doesn't apply here — fund is single-word).

## Clarifications (resolved 2026-05-18)

1. ✅ **CLARIFIED — Cost-class control on the CLI**: boolean opt-in `--enable-factsheet-skill`. Default is `max_cost_class="web_fetch"` (no LLM); the flag overrides to `"llm_skill"`. Symmetric with `--dry-run`; reads as an explicit cost decision.
2. ✅ **CLARIFIED — Patch pre-check**: omitted for now. Patches under `data/opensearch/golden/fund/patches/*.json` are honoured by the `fund_factsheet_patch` source automatically; listing them upfront is a separate concern.
3. ✅ **CLARIFIED — `--limit-per-umbrella` default**: no default cap. Matches bond's `--limit-per-issuer` semantics. Users opt into limits explicitly.
4. ✅ **CLARIFIED — Chained-issuer counts**: raw only. Per-ISIN `chained_issuers` reports the raw fan-out (1–3). Cross-umbrella distinct-LEI dedup is observable from the outcomes' goldenIds; not a top-level report field.

---

*Generated by /sp-spec on 2026-05-18. Supersedes spec-001.md (bootstrap skeleton). Mirrors feature 002 structure adapted to the umbrella-LEI universe model and the LLM-cost-class-default decision.*
