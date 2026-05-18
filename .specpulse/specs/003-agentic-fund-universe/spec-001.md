# Specification: agentic-fund-universe

<!-- FEATURE_DIR: 003-agentic-fund-universe -->
<!-- FEATURE_ID: 003 -->
<!-- SPEC_NUMBER: 001 -->
<!-- STATUS: pending -->
<!-- CREATED: 2026-05-18T10:30:00Z -->

## Description

[NEEDS-CLARIFICATION: one-paragraph statement of the outcome — build the fund slice of the instrument universe via the agentic platform under `src/pipeline/agentic/`, scope=`fund`. Confirm whether this spec formalises the existing FIRDS-driven chain, extends it, removes the legacy `pipeline.gold.fund_firds --universe` path, or all of the above.]

Third feature in the universe-loader series. Mirrors feature 002 (`agentic-bond-universe`) structurally — per-LEI lookup, two-level loop — but funds have three material differences that shape the spec:

1. **Universe definition**: per-umbrella-LEI, via the curated [fund_umbrellas.yml](src/pipeline/gold/data/fund_umbrellas.yml) (10 entries today). FIRDS returns the umbrella's sub-funds and share classes.
2. **Five-level corporate hierarchy** (promoter → managementCompany → umbrella → subFund → shareClass). Issuer chaining emits **three** records per fund (umbrella + managementCompany + promoter) instead of one.
3. **LLM-skill cost class default**: `AGENTS["fund"].default_max_cost_class = "llm_skill"` — every fund assemble may trigger the `find-and-parse-factsheet` skill if no patch is already on disk. Real LLM cost per fund. This needs explicit scope handling in the CLI (default cap? opt-in flag?).

## Requirements

### Functional Requirements

- [ ] [NEEDS-CLARIFICATION: per-umbrella-LEI FIRDS lookup — same `iter_issuer_records` helper as bond, returning share-class records keyed by ISIN?]
- [ ] [NEEDS-CLARIFICATION: CLI flag shape — `--umbrella-lei LEI` (single), `--all` (default), `--limit-per-umbrella N`? Mirror bond exactly?]
- [ ] [NEEDS-CLARIFICATION: cost-class control — should `--cap web_fetch` be the CLI default (cheap, no LLM) and `--cap llm_skill` opt-in? Or trust the agent's `llm_skill` default and add `--no-llm` as the escape?]
- [ ] [NEEDS-CLARIFICATION: scope of legacy `pipeline.gold.fund_firds --universe` removal — strip CLI like bond/equity, or full delete?]

### Non-Functional Requirements

- **Performance**: [NEEDS-CLARIFICATION: typical share-classes per umbrella + LLM cost per fund + total budget for a full-universe smoke?]
- **Security**: ESMA FIRDS is public; GLEIF is public; the factsheet skill needs network (PDF fetch + LLM call).
- **Cost**: explicit — first feature where the agentic chain spends LLM tokens on the critical path.

## Acceptance Criteria

- [ ] Given the curated `fund_umbrellas.yml`, when I run the batch CLI, then `pms_golden_fund` receives one document per share-class ISIN.
- [ ] [NEEDS-CLARIFICATION: per-umbrella issuer chain — three `pms_golden_issuer` records per fund (promoter, managementCompany, umbrella)?]
- [ ] [NEEDS-CLARIFICATION: factsheet skill interaction — verify patches under `data/opensearch/golden/fund/patches/*.json` are honoured before the LLM fires?]
- [ ] [NEEDS-CLARIFICATION: parity vs legacy `fund_firds --universe`?]

## Technical Considerations

### Dependencies

- **External APIs**: ESMA FIRDS Solr (public), GLEIF (public), the `find-and-parse-factsheet` skill (LLM, opt-in via cost-class cap).
- **Database**: existing `pms_golden_fund`, `pms_golden_issuer`, `pms_golden_instrumentsearch`. No mapping changes.
- **Libraries**: existing `requests`. No new requirements.txt entries expected.

### Implementation Notes

- Reuse the layered API documented in `src/pipeline/agentic/README.md`: `AGENTS["fund"].assemble_and_persist(client, identifier, status)`.
- Reuse `pipeline.gold.search_index_build.index_search_hit` for per-ISIN search mirror — same as bond/equity. The `simpleBond`-style ow_type casing fix from feature 002 already accounts for fund (`ow_type=fund`, single word, no mismatch).
- Existing tests under `tests/agentic/test_assemble_fund.py`, `test_fund_yahoo_source.py`, `test_fund_factsheet_patch.py`, `test_factsheet_skill.py`, `test_universe_endpoint.py` already exercise the agentic fund path. Batch CLI tests are net new.
- Pre-curated factsheet patches under `data/opensearch/golden/fund/patches/` are auto-loaded by `fund_factsheet_patch` source (cost: `file_read`) — the LLM is only invoked when a fund has no patch yet.

## Testing Strategy

- **Unit tests**: per-umbrella-LEI → ISINs resolution against pinned FIRDS Solr fixtures; CLI smoke with mocked `AGENTS["fund"]`.
- **Integration tests**: live run against docker-compose OpenSearch for one umbrella (smallest in `fund_umbrellas.yml`), verify counts and issuer-chain triplet.
- **End-to-end**: confirm `GET /instruments/search?type=fund` surfaces the loaded share classes.

## Definition of Done

- [ ] All functional requirements implemented.
- [ ] All acceptance criteria met.
- [ ] Legacy `pipeline.gold.fund_firds --universe` CLI surface stripped (scope confirmed in `/sp-clarify`).
- [ ] Tests pass: `pytest` clean.
- [ ] Branch `feat/agentic-fund-universe` merged into `main` via PyCharm review.
- [ ] Local smoke: `instrument-api` still serves `POST /instruments/assemble` for a fund ISIN; `GET /universe/fund` lists the loaded funds.

## Additional Notes

Third feature through the SpecPulse workflow. The architectural rails are set by features 001/002:
- Layered API (planner/persist/agent/cli).
- Two-level batch loop (LEI → ISIN).
- Lazy opensearch imports for test compatibility.
- JSON report grouped per parent entity.
- `dotenv` auto-load at module top (added to feature 001/002 CLIs post-merge — apply here too).

The interesting work in this feature is the LLM-cost-class decision, the three-record issuer chaining behaviour, and confirming that the existing factsheet-patch flow already covers the highest-coverage funds. Cross-reference: [src/pipeline/agentic/README.md](src/pipeline/agentic/README.md) "Bond" subsection should get a sibling "Fund" subsection.
