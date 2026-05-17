# Specification: build instrument universe -> agentic pipeline for equities

<!-- FEATURE_DIR: 001-agentic-equity-universe -->
<!-- FEATURE_ID: 001 -->
<!-- SPEC_NUMBER: 001 -->
<!-- STATUS: pending -->
<!-- CREATED: 2026-05-17T10:52:00Z -->

## Description

[NEEDS-CLARIFICATION: one-paragraph statement of the outcome — build the equity slice of the instrument universe via the agentic platform under `src/pipeline/agentic/`, scope=`equity`. Confirm whether this spec formalises the existing `openfigi → equity_yahoo` chain, extends it (new sources, persistence, batch ingestion), or both.]

## Requirements

### Functional Requirements

- [ ] [NEEDS-CLARIFICATION: list the equity-scope sources to include — current registry has `openfigi` and `equity_yahoo`; are we adding more?]
- [ ] [NEEDS-CLARIFICATION: define the assembly entry point — `POST /instruments/assemble` only, or also a batch CLI for seeding a universe?]
- [ ] [NEEDS-CLARIFICATION: persistence behaviour — when `persist=true`, write to `pms_golden_equity` and chain issuer assembly per embedded LEI; confirm matches current behaviour or differs.]

### Non-Functional Requirements

- **Performance**: [NEEDS-CLARIFICATION: throughput target — e.g. N ISINs/min single-threaded, OpenFIGI rate limit handling (25 vs 250 req/min)]
- **Security**: [NEEDS-CLARIFICATION: handling of `OPENFIGI_API_KEY` and any other source credentials — already via project `.env`?]
- **Scalability**: [NEEDS-CLARIFICATION: max universe size targeted — SMI, S&P 500, both, or arbitrary]

## Acceptance Criteria

- [ ] Given an equity ISIN, when `POST /instruments/assemble` is called with `scope=equity, persist=true`, then a complete `EquityGolden` document is written to `pms_golden_equity` and the embedded issuer LEI triggers an issuer assembly into `pms_golden_issuer`.
- [ ] [NEEDS-CLARIFICATION: second criterion — batch seeding, search visibility, idempotency]
- [ ] [NEEDS-CLARIFICATION: third criterion — provenance / fill-empty-only merge behaviour]

## Technical Considerations

### Dependencies

- **External APIs**: OpenFIGI (Bloomberg mapping), Yahoo Finance via `yfinance`. [NEEDS-CLARIFICATION: any others?]
- **Database Changes**: none expected — `pms_golden_equity` and `pms_golden_instrumentsearch` indices already exist (see `data/opensearch/golden/`).
- **Third-party Libraries**: `yfinance` (already a project dep), HTTP client for OpenFIGI.

### Implementation Notes

- Source descriptors live in `src/pipeline/agentic/registry/`; per-scope field annotations in `src/pipeline/agentic/annotations/`. Manifest loader raises at import if annotations and the pydantic model disagree on field names.
- Planner runs sources in cost order: `file_read → api_call → web_fetch → llm_skill`.
- Merge policy: fill-empty-only with provenance per field.
- `instrument-api` exposes the entry point; depends on `OPENSEARCH_URL` for persistence (503 otherwise).

## Testing Strategy

- **Unit Tests**: per-source patch shape against pinned fixtures (OpenFIGI response, yfinance Ticker object).
- **Integration Tests**: `POST /instruments/assemble` against a live local OpenSearch from docker-compose; verify document shape and issuer chaining.
- **End-to-End Tests**: [NEEDS-CLARIFICATION: define — frontend "Find an instrument" surfaces the assembled record?]

## Definition of Done

- [ ] All requirements implemented
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved
- [ ] Tests written and passing
- [ ] `CLAUDE.md` updated if the per-scope source list or entry points change
- [ ] Deployed to production [NEEDS-CLARIFICATION: or is "merged to main" the DoD for this repo?]

## Additional Notes

This is the first feature in the project to go through the SpecPulse workflow. The agentic platform already exists under `src/pipeline/agentic/` with `equity` scope wired — the next step (`/sp-spec`) should clarify whether this spec retroactively documents that work, plans an extension, or both.
