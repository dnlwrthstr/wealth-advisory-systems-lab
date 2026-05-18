# Specification: Agentic bond universe — document existing chain + add batch CLI

<!-- FEATURE_DIR: 002-agentic-bond-universe -->
<!-- FEATURE_ID: 002 -->
<!-- SPEC_NUMBER: 002 -->
<!-- STATUS: clarified -->
<!-- SUPERSEDES: spec-001.md (placeholder skeleton) -->
<!-- CREATED: 2026-05-18T06:15:00Z -->

## Executive Summary

Mirror feature 001 (`agentic-equity-universe`), but adapted to the **per-issuer-LEI** shape that bonds actually have. The agentic `bond` scope already exists with `bond_firds` as its single source; the universe HTTP route `POST /universe/bond` already works (covered by `test_universe_endpoint.py`). The missing piece is a **batch entry point** that loops over the curated [bond_issuers.yml](src/pipeline/gold/data/bond_issuers.yml) (10 entries: sovereigns + corporates), queries ESMA FIRDS to enumerate bond ISINs per issuer, and runs each ISIN through the agentic chain. The legacy `pipeline.gold.bond_firds --universe` CLI is then stripped back to a library.

Bond shape is materially different from equity:

| Dimension | Equity (feature 001) | Bond (this feature) |
|---|---|---|
| Universe definition | 5 named market indexes (SMI, S&P 500, …) | Curated issuer-LEI list (`bond_issuers.yml`) |
| Universe resolution | Wikipedia table → tickers → OpenFIGI/six_ticker_isin → ISIN | Per-LEI FIRDS Solr query → bond ISINs (1-to-many) |
| Per-ticker fallback | Yes (OpenFIGI miss → ticker direct to planner) | Not applicable — ISINs come directly from FIRDS |
| Wikipedia / pandas / lxml | Yes | **No** — FIRDS Solr only |
| Per-input cap | `--limit N` (caps total ISINs) | `--limit-per-issuer N` (legacy semantics; caps bonds per LEI) |
| Selector flag | `--universe smi|sp500|…` (required) | `--issuer-lei LEI` (single) or default-all over curated set |
| Legacy strip | equity_yahoo.py: 99 lines removed | bond_firds.py: similar magnitude expected |

Everything else is the same: `AGENTS["bond"].assemble_and_persist(client, identifier, status="in_universe")` per ISIN, `index_search_hit` mirror, strict-serial, per-ISIN error isolation, JSON report.

## Description

### Part 1 — Document the existing agentic bond chain (no code change)

The architectural reference at [src/pipeline/agentic/README.md](src/pipeline/agentic/README.md) was written in feature 001 and already covers the bond scope at a high level. Updates needed:

- Expand the bond row in the per-scope source table to call out the issuer chaining behaviour (`bond_issuers.yml` provides issuer metadata as a fallback when LEI isn't in GLEIF; otherwise GLEIF wins).
- Add a section "Where bond universe data comes from" describing the `bond_issuers.yml` → FIRDS Solr → per-issuer ISIN list flow.
- Cross-link the new CLI: `python -m pipeline.agentic.cli.bond_universe`.

### Part 2 — Add `bond-universe` batch CLI

New module at `src/pipeline/agentic/cli/bond_universe.py`. Flags:

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.bond_universe \
    [--issuer-lei LEI]        # single-issuer smoke test (mutually exclusive with --all)
    [--all]                   # process every issuer in bond_issuers.yml (default behaviour)
    [--issuers PATH]          # override the curated YAML (legacy parity)
    [--limit-per-issuer N]    # cap bonds emitted per issuer (legacy semantics)
    [--dry-run]
    [--universe-status STATUS]  # default in_universe
    [--report-out PATH]
    [--log-level LEVEL]
```

Behaviour per issuer:

1. Resolve issuer entry from `bond_issuers.yml`.
2. Call `pipeline.gold._firds.iter_issuer_records(lei, FIRDS_FL)` to enumerate matching FIRDS records.
3. `dedupe_by_isin` (existing legacy helper) → list of distinct ISINs.
4. Apply `--limit-per-issuer` if set.
5. For each ISIN, call `AGENTS["bond"].assemble_and_persist(client, identifier={"kind":"isin","value":isin}, status=universe_status)`.
6. Mirror onto `pms_golden_instrumentsearch` via `index_search_hit`.
7. Collect per-ISIN outcome (success / partial / failed) plus the issuer LEI it came from.

Issuer-level error isolation: if a per-LEI FIRDS query fails (HTTP error, no records), log a warning and continue with the next issuer. Per-ISIN errors are isolated within the issuer.

### Part 3 — Strip legacy `pipeline.gold.bond_firds` to library

Same shape as feature 001's T016. Delete:

- `main()` and the `argparse` setup (~45 lines).
- `write_ndjson` (only called by `main`).
- The `if __name__ == "__main__"` block.
- Unused imports after the above (`argparse`, `Path` if it's only in `main`).

Keep (all called by the agentic source or transitively):

- `fetch_by_isin` — called by `pipeline.agentic.sources.bond_firds`.
- `firds_to_golden`, `load_issuers`, `dedupe_by_isin`, `_resolve_issuer`, `_gleif_to_issuer`, `_record_quality`, `_fingerprint`, `_to_float`, `_iso_date`, `_lifecycle_status`, `_asset_class_defaults`, `derive_bond_sub_type`, `derive_coupon_type` — supporting library.
- `FIRDS_FL` constant — the field list used by Solr.

Module docstring rewritten to reflect the new "library only" role, same convention as `pipeline.gold.equity_yahoo` after feature 001.

## Functional Requirements

### FR-1 — Document the bond chain

- [ ] [src/pipeline/agentic/README.md](src/pipeline/agentic/README.md) expanded with a "Bond universe data flow" subsection covering `bond_issuers.yml` + `iter_issuer_records` + chained GLEIF issuer assembly.
- [ ] CLAUDE.md pointer for the new CLI added under "Agentic data engineering". The "Legacy bulk fetchers" entry for `bond_firds` is rewritten to reflect its library-only role (parity with the `equity_yahoo` rewrite from feature 001).

### FR-2 — Universe resolution

- [ ] CLI accepts `--issuer-lei LEI` (single) or `--all` (default, no flag needed).
- [ ] CLI accepts `--issuers PATH` for an override YAML, matching legacy `--issuers` semantics.
- [ ] Unknown LEI (passed via `--issuer-lei`) → exit non-zero with a helpful error listing the LEIs from the active YAML.
- [ ] If `bond_issuers.yml` is missing or malformed, exit non-zero with a clear pointer to its expected location and shape.

### FR-3 — Per-issuer FIRDS enumeration

- [ ] For each issuer LEI, the CLI calls `iter_issuer_records(lei, FIRDS_FL)` (existing helper) to enumerate raw FIRDS records.
- [ ] Records are deduplicated by ISIN via the existing `dedupe_by_isin` helper.
- [ ] Issuer-level FIRDS errors (HTTP 5xx, timeout, empty response) are logged at WARNING and the batch continues with the next issuer.

### FR-4 — Per-ISIN assembly

- [ ] For each resolved ISIN, the CLI calls `AGENTS["bond"].assemble_and_persist(client, identifier={"kind":"isin","value":isin}, status=universe_status)`.
- [ ] After each successful persist, the record is mirrored onto `pms_golden_instrumentsearch` via `pipeline.gold.search_index_build.index_search_hit` — same posture as `POST /universe/bond`.
- [ ] Per-ISIN errors are isolated; one bad ISIN does not abort the issuer's loop, and one bad issuer does not abort the batch.

### FR-5 — Reporting

- [ ] Per-ISIN outcome captured: `(issuer_lei, isin, status, golden_id, quality_score, remaining_gaps, chained_issuers, reason)`.
- [ ] Report (stdout + optional `--report-out path.json`) carries: per-issuer totals (success / partial / failed per LEI) AND overall totals. Bond shape: grouped by issuer, not flat like equity.
- [ ] Exit code: `0` on no failures, `1` on any per-ISIN failure, `2` on infrastructure failure (e.g. `OPENSEARCH_URL` unset when not in `--dry-run`).

### FR-6 — Strip legacy bulk loader

- [ ] `pipeline.gold.bond_firds.main`, `write_ndjson`, `argparse` setup, and `if __name__` block are removed.
- [ ] `pipeline.gold.bond_firds.fetch_by_isin` and the supporting `firds_to_golden` / `derive_*` / `_*` helpers remain importable.
- [ ] All existing tests under `tests/agentic/` that exercise `fetch_by_isin` continue to pass.

### Non-Functional Requirements

- **Performance**: full curated set (~10 issuers, expected ~50–200 bonds total) in under 10 minutes on strict serial. FIRDS Solr is fast (~100ms/query); per-bond assemble dominates (one FIRDS call + the merger). For a single corporate issuer, under 60 seconds.
- **Reliability**: idempotent re-runs converge to the same OpenSearch state.
- **Observability**: structured logging per ISIN at INFO; per-issuer summary at INFO; source-by-source detail at DEBUG.
- **No new external dependencies**: no Wikipedia, no pandas, no lxml. The container's existing deps (`opensearch-py`, `requests`/`httpx`) cover everything.

## User Stories

- **US-1** — As a data engineer seeding bond data into a fresh OpenSearch, I want one CLI invocation to load every bond from the curated issuer list so I don't have to chain three separate legacy scripts.
- **US-2** — As a developer debugging one specific issuer's bonds, I want `--issuer-lei <LEI>` to scope the run to that issuer alone, so I get fast iteration without re-loading the full set.
- **US-3** — As a maintainer adding a new bond issuer, I want to drop a YAML entry into `bond_issuers.yml` and re-run the CLI, and have everything else (LEI resolution, FIRDS enumeration, persist, search mirror) happen automatically.

## Acceptance Criteria

- [ ] **AC-1** Given a clean local OpenSearch and the bundled `bond_issuers.yml`, when I run `python -m pipeline.agentic.cli.bond_universe`, then `pms_golden_bond` contains ≥1 document per issuer LEI in the YAML and `pms_golden_issuer` contains ≥1 record per distinct issuer LEI.
- [ ] **AC-2** Given the same OpenSearch state, when I re-run the same command, then document counts in `pms_golden_bond`, `pms_golden_issuer`, and `pms_golden_instrumentsearch` are unchanged (idempotent).
- [ ] **AC-3** Given an NDJSON snapshot from the legacy `pipeline.gold.bond_firds --universe` on the prior commit, when I diff schema-overlapping fields in `pms_golden_bond`, then no field that legacy populated is missing in the new chain, and divergences fall into one of: (a) fields newly populated by the agentic chain by design (e.g. `lei`, GLEIF-derived issuer metadata); (b) timestamp / run-id fields.
- [ ] **AC-4** Given `--dry-run`, when the CLI runs, then no writes hit `pms_golden_bond`, `pms_golden_issuer`, or `pms_golden_instrumentsearch`, and the report still shows the per-issuer resolution outcomes (counts of ISINs found per LEI).
- [ ] **AC-5** Given `--issuer-lei <unknown LEI>`, when the CLI runs, then exit code is non-zero and stderr lists the LEIs available in the active YAML.
- [ ] **AC-6** Given a FIRDS query failure for one issuer (simulated via 5xx in tests), when the CLI runs the full curated set, then the other issuers still complete and the failed issuer appears in the report with `status=failed`, `reason="firds: …"`.

## Technical Constraints

### In scope

- Scope=bond only. Equity and fund universes already covered (feature 001) or out of scope here.
- Reuse the layered API (planner / persist / agent / cli) documented in `src/pipeline/agentic/README.md`. No new abstractions.
- Reuse `pipeline.gold._firds.iter_issuer_records`, `bond_firds.fetch_by_isin`, `bond_firds.dedupe_by_isin`, `bond_firds.load_issuers` — all existing library functions stay.

### Out of scope

- `pipeline.gold.bond_synthetic_market_data` — separate enrichment CLI that fills `marketData → yieldToMaturity` etc. from coupon. Stays as-is. Possible follow-up: fold into the agentic chain as a `bond` scope source. **Not this feature.**
- `pipeline.gold.bond_boerse_frankfurt_enrich` — separate enrichment CLI that pulls real Frankfurt clean prices and recomputes YTM. Same disposition. **Not this feature.**
- Fund universe loader. Spec 003 territory if needed.
- Frontend changes — `Find an instrument` already reads from `pms_golden_instrumentsearch` and surfaces the mirrored records automatically.
- New bond fields in the ontology. The current `BondGolden` model is what the chain populates.

### Dependencies

- **External APIs**: ESMA FIRDS Solr (public, no key). GLEIF (already wired via the issuer chain).
- **Database**: existing `pms_golden_bond`, `pms_golden_issuer`, `pms_golden_instrumentsearch`. No mapping changes.
- **Libraries**: `requests` (existing). **No new requirements.txt additions** — unlike feature 001, no lxml.

### Implementation Notes

- The CLI module mirrors the file shape of `pipeline.agentic.cli.equity_universe` but the loop is two-level (issuer → ISIN) instead of flat. The `_Outcome` dataclass gains an `issuer_lei` field.
- The opensearch-dependent imports (`opensearch_client_from_env`, `index_search_hit`) stay lazy inside the functions, matching the pattern set in feature 001's T011 (keeps the module importable for unit tests without `opensearch-py`).
- No new helper module needed — `load_issuers` and `iter_issuer_records` live where they already do. The bond universe doesn't need a `pipeline.agentic.universes`-style helper because there's no Wikipedia scraping or ticker→ISIN bridging.
- The legacy `--issuers PATH` flag is preserved verbatim in the new CLI for tooling parity (anyone who scripted the legacy invocation keeps working).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| FIRDS Solr returns 5xx mid-batch | Medium | Medium | Issuer-level error isolation (FR-3, AC-6). Failed issuer reported, batch continues. |
| `bond_issuers.yml` drifts (LEI typo, missing fields) | Low | Low | `load_issuers` already validates entries; CLI surfaces parse errors loudly. |
| AC-3 surfaces material schema drift | Medium | Medium | Same posture as feature 001 AC-3 — documented in PR body, no merge block unless a legacy-populated field disappears. |
| Bond volume grows materially as new issuers are added | Low | Low | Strict-serial OK up to ~1000 bonds. Beyond that, revisit. Document the threshold in CLI `--help`. |
| Existing test using legacy `bond_firds.main` breaks | Low | Medium | Grep for `bond_firds.main` and `from pipeline.gold.bond_firds import main` before deleting; update any test (probably zero matches). |
| `iter_issuer_records` is internal (`_firds`) and not stable | Low | Medium | The `_` prefix is module-local convention; the helper is heavily used and stable. Document the agentic CLI's dependency on it. |

## Testing Strategy

- **Unit tests**:
  - `tests/agentic/test_bond_universe_cli.py` — mocked `AGENTS["bond"]` + mocked `iter_issuer_records` + mocked `index_search_hit`. Cover: AC-4 (dry-run), AC-5 (unknown LEI), AC-6 (one issuer fails, others proceed), happy path with `--limit-per-issuer`, report shape per-issuer grouping.
  - No new helper module → no separate "universes" tests to write (unlike feature 001).
- **Integration tests**:
  - Existing `tests/agentic/test_bond_firds_source.py` already covers `fetch_by_isin`; after the strip-down, it must still pass.
  - Existing `tests/agentic/test_universe_endpoint.py` exercises `POST /universe/bond`; must still pass.
- **End-to-end / live**:
  - Run the new CLI against docker-compose OpenSearch for one issuer first (smoke), then the full curated set.
  - Hit `GET /instruments/search?type=simpleBond&issuer=<some-name>` to verify the search mirror surfaces the new records.

## Definition of Done

- [x] All six functional requirements implemented.
- [x] All six acceptance criteria met (AC-1 + AC-2 verified live on `--all --limit-per-issuer 3`; AC-3 parity diff at `data/cache/parity/diff_bonds_report.md`; AC-4/AC-5/AC-6 covered by smoke tests).
- [x] Architectural reference for the bond chain landed in `src/pipeline/agentic/README.md`.
- [x] `pipeline.gold.bond_firds --universe` CLI surface stripped; library functions retained.
- [x] CLAUDE.md "Legacy bulk fetchers" entry for `bond_firds` rewritten; "Agentic data engineering" gets the new CLI pointer.
- [x] Tests pass: `pytest` 174/174.
- [ ] Branch `feat/agentic-bond-universe` merged into `main` via PyCharm review (pending user action).
- [x] Local smoke: `instrument-api` still serves `POST /instruments/assemble` for a bond ISIN unchanged (SAP `DE000A13SL34` → quality 0.857); `GET /universe/bond` lists 25 bonds.
- [x] **Bug fix landed inline (T012)**: bond search-mirror `ow_type` casing mismatch (`simple_bond` → `simpleBond`) in `pipeline.gold.search_index_build`. Surfaced during T011 smoke when `GET /instruments/search?type=simpleBond` returned 1 hit instead of 25. Fix changes one map entry + 5 regression tests in `tests/agentic/test_search_index_build.py`. After the fix: 25/25 in-universe bonds surface via the public search filter.

## Clarifications (resolved 2026-05-18)

1. ✅ **CLARIFIED — `--issuer-lei` ergonomics**: single LEI only. `--issuer-lei LEI` accepts exactly one LEI; multi-issuer subsets use `--all` or extend `bond_issuers.yml`. Keeps the smoke-test path simple.
2. ✅ **CLARIFIED — Default behaviour**: `--all` is the default. Running with no args processes every issuer in `bond_issuers.yml`. `--issuer-lei` overrides. Matches the most common operational use (full reload after issuer additions).
3. ✅ **CLARIFIED — Named groups by issuer type**: omitted for now. Partial loads use `--issuer-lei`. Revisit only if the curated list grows beyond ~30 issuers.
4. ✅ **CLARIFIED — Global cap**: just `--limit-per-issuer` (legacy semantics). No separate `--limit-total`. Small per-issuer caps already give a usable smoke across all issuers.
5. ✅ **CLARIFIED — Architectural doc location**: extend `src/pipeline/agentic/README.md` per feature 001 precedent. No per-scope sub-README.

---

*Generated by /sp-spec on 2026-05-18. Supersedes spec-001.md (bootstrap skeleton). Bond-specific scope captured; mirrors feature 001 structure but adapted to the issuer-LEI universe model.*
