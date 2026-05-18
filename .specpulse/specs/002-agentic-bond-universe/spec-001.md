# Specification: agentic-bond-universe

<!-- FEATURE_DIR: 002-agentic-bond-universe -->
<!-- FEATURE_ID: 002 -->
<!-- SPEC_NUMBER: 001 -->
<!-- STATUS: pending -->
<!-- CREATED: 2026-05-18T06:00:00Z -->

## Description

[NEEDS-CLARIFICATION: one-paragraph statement of the outcome — build the bond slice of the instrument universe via the agentic platform under `src/pipeline/agentic/`, scope=`bond`. Confirm whether this spec formalises the existing FIRDS chain, extends it, removes the legacy `pipeline.gold.bond_firds --universe` path, or all of the above.]

Mirror of feature 001 (`agentic-equity-universe`), but for bonds. The pattern needs adapting:

- **Bonds aren't grouped by named market index.** They're grouped by *issuer LEI*. The curated list lives in `src/pipeline/gold/data/bond_issuers.yml` (10 entries today: sovereigns + corporates).
- **The agentic `bond` scope already exists** with `bond_firds` as its single source (ESMA FIRDS Solr by ISIN; issuer metadata from `bond_issuers.yml` or GLEIF on chain).
- **The batch entry point** is what's missing: per-issuer-LEI → FIRDS lookup returns ISINs → per-ISIN `AGENTS["bond"].assemble_and_persist(..., status="in_universe")`.

## Requirements

### Functional Requirements

- [ ] [NEEDS-CLARIFICATION: per-LEI lookup of bond ISINs from ESMA FIRDS — does this exist in `pipeline.gold.bond_firds` and what's the public surface?]
- [ ] [NEEDS-CLARIFICATION: CLI flags — `--issuer-lei LEI` for single-issuer, `--all` for full curated set, or a different shape?]
- [ ] [NEEDS-CLARIFICATION: scope of legacy `pipeline.gold.bond_firds --universe` removal — strip CLI like equity, or full delete?]

### Non-Functional Requirements

- **Performance**: [NEEDS-CLARIFICATION: 10 curated issuers × N bonds each — typical FIRDS response sizes?]
- **Security**: ESMA FIRDS is public; no API key needed.
- **Scalability**: [NEEDS-CLARIFICATION: max bonds per issuer to cap at, if any?]

## Acceptance Criteria

- [ ] Given the curated `bond_issuers.yml` (10 issuers), when I run the batch CLI, then `pms_golden_bond` receives one document per bond ISIN returned by FIRDS, stamped with `universeStatus="in_universe"`.
- [ ] [NEEDS-CLARIFICATION: second criterion — issuer chaining, idempotency, search-index mirror]
- [ ] [NEEDS-CLARIFICATION: third criterion — parity vs legacy `bond_firds --universe`]

## Technical Considerations

### Dependencies

- **External APIs**: ESMA FIRDS Solr (public, no key).
- **Database**: existing `pms_golden_bond`, `pms_golden_issuer`, `pms_golden_instrumentsearch`. No mapping changes.
- **Libraries**: `requests` (existing).

### Implementation Notes

- Reuse the layered API documented in `src/pipeline/agentic/README.md`: `AGENTS["bond"].assemble_and_persist(client, identifier, status)`.
- Reuse `pipeline.gold.search_index_build.index_search_hit` to mirror each persisted record onto `pms_golden_instrumentsearch` (parity with the equity CLI and `POST /universe/bond`).
- Existing tests under `tests/agentic/test_assemble_bond.py`, `test_bond_firds_source.py`, `test_universe_endpoint.py` validate the assemble + HTTP paths — batch CLI tests are net new.

## Testing Strategy

- **Unit tests**: per-LEI → ISINs resolution against pinned FIRDS Solr fixtures.
- **Integration tests**: CLI smoke against mocked `AGENTS["bond"]` (covers AC-4-style dry-run + AC-5-style unknown LEI).
- **End-to-end**: live run against docker-compose OpenSearch for one issuer (smallest in `bond_issuers.yml`), verify counts.

## Definition of Done

- [ ] All functional requirements implemented.
- [ ] All acceptance criteria met.
- [ ] Legacy `pipeline.gold.bond_firds --universe` CLI surface stripped (scope to be confirmed in `/sp-clarify`).
- [ ] Tests pass: `pytest` clean.
- [ ] Branch `feat/agentic-bond-universe` merged into `main` via PyCharm review.
- [ ] Local smoke OK: `instrument-api` still serves `POST /instruments/assemble`, `GET /universe?scope=bond` returns the loaded set.

## Additional Notes

This is the second feature through the SpecPulse workflow. The shape will mirror 001-agentic-equity-universe closely; key difference is universe definition (issuer-LEI list vs Wikipedia-sourced ticker list). The agentic `bond_firds` source already does the per-ISIN heavy lifting — this feature is mostly the batch loop on top.

Cross-reference: `src/pipeline/agentic/README.md` (the architectural reference written in spec 001) documents the layered API. The bond CLI should mirror `pipeline.agentic.cli.equity_universe` in structure.
