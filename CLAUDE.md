# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branching workflow

Every coding task must be done on a feature branch:

```bash
git checkout -b <short-kebab-desc>   # create and switch
# ... make changes, run tests ...
git add <files>
git commit -m "..."
# leave branch checked out — user reviews in PyCharm and merges manually
```

Branch naming: `<topic>/<short-desc>` — e.g. `feat/duckdb-store`, `fix/snapshot-weight`, `refactor/profiling-service`.
Never commit directly to `main`.

After the user merges a branch, delete it locally and on the remote:

```bash
git branch -d <branch>
git push origin --delete <branch>
```

## Spec-first workflow (SpecPulse)

Non-trivial features go through a spec → plan → tasks loop **before any code is written**, using the SpecPulse slash commands in `.claude/commands/sp-*.md`:

```
/sp-pulse <feature-name>     # create .specpulse/specs/NNN-<name>/ scaffold + matching feat/<name> branch
/sp-spec "<one-liner>"        # write the spec — outcomes, scope, constraints, verification
/sp-plan                      # decompose spec into implementation plan
/sp-task                      # break plan into ordered tasks
/sp-execute                   # implement, one task at a time
/sp-validate                  # cross-check artefacts before merge
```

Artefacts under `.specpulse/specs/`, `.specpulse/plans/`, `.specpulse/tasks/` are committed alongside the code and reviewed in PyCharm as part of the PR.

**When to use it:**

- *Required* for net-new features, cross-package work, new ontology types, new agentic sources, new backend services, schema changes.
- *Skipped* for bugfixes, refactors, doc edits, dependency bumps, single-file changes — those stay ad-hoc on a `fix/…` or `refactor/…` branch.

**Memory boundary:**

- `.specpulse/memory/decisions.md` — per-feature decisions ("why we chose X for spec NNN"). Lives in git with the spec; rots with it.
- Claude Code auto-memory (`~/.claude/projects/.../memory/`) — cross-session facts about the user and the repo. Project-wide, not feature-specific.

Don't double-write the same fact into both.

## docker-compose.yml maintenance

`docker-compose.yml` must be kept in sync with architectural changes:

- Any new service dependency (e.g. a new backend service, a new data store) needs a corresponding service block, healthcheck, and `depends_on` wiring.
- Internal service hostnames use the Docker network port (e.g. `database:5432`), not the host-mapped port (e.g. `5433`).
- Data that must be generated at container start (not checked in) belongs in a named Docker volume; the service's entrypoint script is responsible for generating it if absent.
- When a service no longer depends on Postgres, remove its `depends_on: database` and `DATABASE_URL`.

## Commands

### Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Tests

```bash
pytest                          # all tests
pytest tests/test_suitability.py          # single file
pytest tests/test_profiling_signals.py::test_name  # single test
```

`pyproject.toml` adds `src/` to `pythonpath` automatically. The project root is on sys.path so `backend.*` imports resolve in tests.

### Backend services (local, no Docker)

```bash
# custodian-api on port 8001
PYTHONPATH=src uvicorn backend.custodian_api.main:app --reload --port 8001

# profile-api on port 8002
DATABASE_URL=postgresql://wealth_advisory:wealth_advisory@localhost:5433/wealth_advisory \
  PYTHONPATH=src uvicorn backend.profile_api.main:app --reload --port 8002
```

Omit `DATABASE_URL` to run `profile-api` without audit persistence.

### Frontend (local, no Docker)

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Docker stack

```bash
docker compose up --build
```

Services: frontend `localhost:3000`, custodian-api `localhost:8001`, profile-api `localhost:8002`, instrument-api `localhost:8003`, order-api `localhost:8004`, PostgreSQL `localhost:5433`, OpenSearch `localhost:9200`, OpenSearch Dashboards `localhost:5601`.

OpenSearch runs with the security plugin disabled (dev mode, no auth, plain HTTP). The `opensearch-init` one-shot service creates the five `pms_golden_*` indices from `data/opensearch/golden/` on first `up`; it is idempotent — `docker compose run --rm opensearch-init` re-applies safely (existing indices are skipped). Regenerate mappings after ontology edits with `PYTHONPATH=src python -m ontology_tools.golden_record_2_opensearch.convert_to_opensearch -i ontology -o data/opensearch/golden`.

`instrument-api` reads from OpenSearch (across `pms_golden_equity`, `pms_golden_bond`, and `pms_golden_fund`) when `OPENSEARCH_URL` is set; without it the service falls back to the static `INSTRUMENTS` fixture in `src/instruments/data.py` so unit tests still work.

### Agentic data engineering (primary path)

The universe is built one instrument at a time via the agentic platform under `src/pipeline/agentic/`. Given an identifier (ISIN, ticker, LEI), the planner reads the ontology-derived field manifest, picks sources from a per-scope registry, runs them in cost order (file_read → api_call → web_fetch → llm_skill), merges their patches with provenance (fill-empty-only), and returns a composed golden record. The instrument-api exposes `POST /instruments/assemble`; with `persist=true` it writes to `pms_golden_{scope}` and chains into issuer assembly for every embedded LEI. For a full architectural reference (layered API, source tables per scope, merge policy, manifest invariant), see [`src/pipeline/agentic/README.md`](src/pipeline/agentic/README.md). Batch seeding from a named universe (SMI, S&P 500, …) is handled by `python -m pipeline.agentic.cli.equity_universe --universe …`. Batch seeding of bonds (curated issuer-LEI list at `src/pipeline/gold/data/bond_issuers.yml`) is handled by `python -m pipeline.agentic.cli.bond_universe [--issuer-lei LEI | --all]`. Batch seeding of funds (curated umbrella-LEI list at `src/pipeline/gold/data/fund_umbrellas.yml`) is handled by `python -m pipeline.agentic.cli.fund_universe [--umbrella-lei LEI | --all] [--enable-factsheet-skill]` — defaults `max_cost_class=web_fetch` so no LLM tokens spend unless the flag is set explicitly.

Per scope:

- **equity** — `openfigi` (ISIN → FIGI / ticker / name via Bloomberg's free mapping API; pass `OPENFIGI_API_KEY` for 250 req/min instead of 25) then `equity_yahoo` (yfinance overlay; reads ticker from `identifierList.tickerSymbol` when openfigi set one).
- **bond** — `bond_firds` (ESMA FIRDS Solr by ISIN; issuer metadata comes from the curated LEI map at `src/pipeline/gold/data/bond_issuers.yml` when it has the LEI, otherwise from GLEIF — so any FIRDS-listed bond assembles without manual curation, and the chained issuer assembly downstream still resolves the full IssuerGolden from GLEIF).
- **fund** — `fund_firds` (FIRDS by ISIN + umbrella LEI map at `src/pipeline/gold/data/fund_umbrellas.yml`) → `fund_yahoo` (NAV / market price / OHLCV / AUM / TER / asset allocation) → `fund_factsheet_patch` (reads pre-curated output of the `find-and-parse-factsheet` Claude Code skill from `data/opensearch/golden/fund/patches/FG-{ISIN}-001.json`).
- **issuer** — `issuer_gleif` (GLEIF public API by LEI; authoritative for legal-entity attributes).

Source descriptors are YAML under `src/pipeline/agentic/registry/`; per-scope field annotations under `src/pipeline/agentic/annotations/`. The manifest loader raises if the annotation YAML and the pydantic model disagree on field names — drift is detected at import time.

### Legacy bulk fetchers (still under `src/pipeline/gold/`)

For batch-loading the initial OpenSearch indices from named universes (SMI, S&P 500, FIRDS issuer lists), the legacy CLIs are still useful:

- `equity_yahoo` — **library only** since spec 001-agentic-equity-universe. Exposes `fetch_by_identifier(kind, value)` for the agentic `equity_yahoo` source to call. The former `--universe` bulk CLI moved to `pipeline.agentic.cli.equity_universe`, which routes every ISIN through the full agentic chain (openfigi → equity_firds → equity_yahoo) and persists via `assemble_and_persist` with `universe_status="in_universe"`.
- `bond_firds` — **library only** since spec 002-agentic-bond-universe. Exposes `fetch_by_isin(isin)`, `firds_to_golden`, `load_issuers`, `dedupe_by_isin`, and the `derive_*` helpers for the agentic `bond_firds` source to call. The former curated-issuer bulk CLI moved to `pipeline.agentic.cli.bond_universe`. Coupon-rate scaling caveat still applies: FIRDS returns a percentage (1.5) and `firds_to_golden` divides by 100 to the ontology's decimal (0.015); the OpenSearchInstrumentStore multiplies back by 100 when projecting onto the frontend's `coupon_pct` field.
- `bond_synthetic_market_data` — fills `BondGolden.marketData` with the analytically-derivable yield + duration fields for active bonds. Computes `yieldToMaturity` and `currentYield` as the coupon rate (par assumption), `macaulayDuration = (1/y)·(1 − (1+y)⁻ᵀ)`, `modifiedDuration = macaulayDuration / (1+y)`. Provenance label is `synthetic (coupon-as-YTM at par)`. Run before `bond_boerse_frankfurt_enrich`.
- `bond_boerse_frankfurt_enrich` — pulls real clean prices from `api.boerse-frankfurt.de/v1/data/quote_box`, recomputes YTM via bisection on `P(y) = c·annuity(y, n) + (1+y)⁻ⁿ`. Appends a separate `marketData → boerse-frankfurt.de` row to `sourceOfTruth`. Cached per-ISIN.
- `fund_firds` — **library only** since spec 003-agentic-fund-universe. Exposes `fetch_by_isin(isin)`, `firds_to_golden`, `load_issuers`, `dedupe_by_isin`, and `derive_*` helpers for the agentic `fund_firds` source to call. The former umbrella-driven bulk CLI moved to `pipeline.agentic.cli.fund_universe`, which routes every share-class ISIN through the full agentic chain (fund_firds → fund_yahoo → fund_factsheet_patch → fund_factsheet_skill) and persists via `assemble_and_persist` with `universe_status="in_universe"`. Cost-class control: CLI defaults `max_cost_class="web_fetch"` (no LLM); `--enable-factsheet-skill` lifts the cap to `llm_skill`.
- `issuer_aggregate` — scans `pms_golden_{equity,bond,fund}` and writes one `IssuerGolden` per distinct issuer to `pms_golden_issuer`. For funds emits three records per instrument: umbrella + managementCompany + promoter. Re-run after re-loading any per-instrument index.
- `issuer_gleif` — enriches `pms_golden_issuer` documents from GLEIF. GLEIF wins for legal-entity attributes; `issuerType` is only refined when the current value is blank or the generic `corporate` default (so role-aware types `fund_umbrella`, `fund_company`, `promoter` survive).
- `search_index_build` — rebuilds `pms_golden_instrumentsearch` from the three per-security indices.
- `fund_yahoo_enrich` — reads a FundGolden NDJSON and backfills market data + TER per ISIN.

### Fact-sheet + full-holdings enrichment (per-fund, LLM-assisted)

For the long tail of fund fields Yahoo doesn't carry — fees beyond TER, SRRI/SRI, PRIIPS transaction costs, dealing terms, service providers, benchmark, replication method, rebalance frequency, **and the full constituent list / `holdingsCount`** — there's a Claude Code skill at `.claude/skills/find-and-parse-factsheet/SKILL.md`. Per-fund, on-demand, review-then-apply: the skill locates the KID/KIID/fact-sheet PDF and/or the issuer's holdings page for a given ISIN, parses the relevant fields, writes a JSON patch to `data/opensearch/golden/fund/patches/<goldenId>.json`, and only PATCHes the OpenSearch doc after the user confirms. The agentic platform's `fund_factsheet_patch` source then surfaces that file as a regular source during assembly.

The skill applies patches through `pipeline.gold.apply_fund_patch`, which validates the top-level fields against a FundGolden allow-list, runs `POST /pms_golden_fund/_update/<goldenId>`, refreshes the index, and rebuilds `pms_golden_instrumentsearch` so any newly hoisted fields surface in the "Find an instrument" UI. The skill's full-holdings procedure routes per `managementCompany.legalName` to the right issuer page (iShares / Vanguard / Xtrackers / Amundi / UBS) and includes holdings-specific quality gates: total weight must be within `[0.95, 1.05]`, snapshot date no older than 30 days, at most 1 % of rows missing an identifier.

`instrument-api` exposes three surfaces. Legacy: `GET /instruments?q=...&type=...&currency=...` returns the flat `Instrument` dataclass (used by the old order-flow UI). Search: `GET /instruments/search?identifier=&name=&issuer=&type=&currency=&country=` hits `pms_golden_instrumentsearch` and returns the richer `SearchHit` shape. Assemble: `POST /instruments/assemble` runs the agentic loop and (with `persist=true`) writes to `pms_golden_{scope}` + chains into issuer assembly for every embedded LEI. All three share the OpenSearch client; search and assemble-persist return 503 when `OPENSEARCH_URL` is unset.

The OpenFIGI API key lives in a project `.env` (gitignored) — docker-compose substitutes it into `instrument-api`'s environment as `OPENFIGI_API_KEY`. Without a key the source still works at the 25 req/min free tier.

All three rely on pydantic's native serialisation. `Currency` was redefined in `ontology/reference_data/currency/Currency.yml` from a 7-field value object to a scalar value object (`kind: value_object, type: string, pattern: "^[A-Z]{3}$"`), matching how `LegalEntityIdentifier` and `CfiCode` are modelled. The descriptive metadata that ISO 4217 attaches per code (numeric code, name, minor units, symbol, issuing country, monetary authority) lives in `CurrencyReferenceEntry` inside `CurrencyReferenceData.yml` — golden records hold the code, lookups go through the reference dataset. After regeneration (`ontology_2_pydantic` + `golden_record_2_opensearch`), `Currency`, `Country` and `CfiCode` are all `RootModel[str]` and serialise as bare strings; no post-processing flatten helper is needed.

`OpenSearchInstrumentStore.search` accepts `type=equity|simpleBond|fund` and translates each to an `assetClass.keyword` prefix filter (`Equity` / `Fixed Income` / `Fund`). The frontend's existing `Instrument` dataclass is the API contract; bond-specific fields (`coupon_pct`, `maturity_date`) populate from BondGolden, others stay null.

API docs: `http://localhost:8001/docs` and `http://localhost:8002/docs`.

```bash
# After frontend-only changes:
docker compose down && docker compose build --no-cache frontend && docker compose up --force-recreate
```

### Notebooks

```bash
python -m ipykernel install --user --name wealth-advisory-lab --display-name "Python (Wealth Advisory Lab)"
jupyter notebook
```

## Architecture

### Two-layer structure

`src/` holds standalone Python packages used by both the backend services and notebooks. `backend/` contains two independent FastAPI applications that delegate entirely to `src/` — no domain logic lives in `backend/`.

#### `src/` packages

| Package | Key classes | Role |
|---|---|---|
| `src/profiling/` | `ProfilingService`, `PostgresQuestionnaireStore` | Questionnaire registry, full processing pipeline, strategy/gate assessment |
| `src/advice/` | `SuitabilityService` | Product suitability and appropriateness evaluation |
| `src/custodian/` | `CustodianService`, `InMemoryCustodianStore`, `PostgresCustodianStore` | OpenWealth-style custody data access |
| `src/audit/` | `PostgresAuditStore` | Persists processing audit trails to Postgres |
| `src/instruments/` | `InstrumentService`, `InstrumentStore` | 175-instrument universe across all 15 OpenWealth FinancialInstrumentType values; `data.py` holds the fixtures |
| `src/orders/` | `OrderService`, `OrderStore` | In-memory order book; daemon thread simulates random fills every 3 s |

Each service class takes a store in its constructor — use the in-memory store for notebooks and tests, the Postgres store when a `DATABASE_URL` is available:

```python
from profiling.service import ProfilingService
from profiling.store import PostgresQuestionnaireStore
from advice.service import SuitabilityService
from custodian.service import CustodianService
from custodian.store import InMemoryCustodianStore, PostgresCustodianStore
from custodian.data import CUSTOMERS, ACCOUNTS, POSITIONS, TRANSACTIONS

# notebook / offline
profiling = ProfilingService()
custody = CustodianService(InMemoryCustodianStore(CUSTOMERS, ACCOUNTS, POSITIONS, TRANSACTIONS))

# with database
profiling = ProfilingService(
    audit_store=PostgresAuditStore(db_url),
    questionnaire_store=PostgresQuestionnaireStore(db_url),
)
custody = CustodianService(PostgresCustodianStore(db_url))
```

#### `backend/` services

| Service | Port | Dockerfile |
|---|---|---|
| `backend/custodian_api/` | 8001 | `backend/custodian_api/Dockerfile` |
| `backend/profile_api/` | 8002 | `backend/profile_api/Dockerfile` |
| `backend/instrument_api/` | 8003 | `backend/instrument_api/Dockerfile` |
| `backend/order_api/` | 8004 | `backend/order_api/Dockerfile` |

Each service has a `main.py` (FastAPI app + service instantiation), a `router.py` (routes + Pydantic↔domain serialization), and a `schemas/` sub-package. The router is the only place that converts between Pydantic payloads and domain dataclasses.

### Questionnaire processing pipeline

`ProfilingService.process()` runs the full pipeline through four stages, each in its own module:

1. **`questionnaire.py`** — validates answers against a `Questionnaire` DAG (graph traversal respects conditional branching; detects cycles, unreachable nodes, contradictory answers).
2. **`scoring.py`** — maps answers to five named signals: `risk_willingness`, `knowledge`, `horizon`, `liquidity_pressure`, `obligation`.
3. **`derivation.py`** — converts `ProfileScores` + financial context (age, income, net worth) into a `ClientProfile` dataclass.
4. **`strategy.py`** — derives `StrategyProfile` (strategy level, suitability envelope) and `GateDecision` list. Gates are `block` (hard fail) or `review` (requires sign-off). Returns `StrategyAssessment` with `.passed` and `.requires_review` convenience properties.

`ProcessingResult` carries all intermediate outputs (scores, derivation, assessment) and is what the `profile_api` router serializes into `ProcessAnswersResponse`.

### Frontend routing

nginx proxies `/api/custody/*` → `custodian-api:8001/custody/` and `/api/*` → `profile-api:8002/`. When running the frontend outside Docker, point API calls directly at the respective service ports.

### Database schemas

One PostgreSQL instance, four schemas — each service owns its schemas:

| Schema | Owner service | Key tables |
|---|---|---|
| `custodian` | custodian-api | `custody_customer`, `custody_portfolio`, `custody_account`, `custody_position`, `custody_transaction` |
| `advisory` | profile-api | `client_profile`, `product_profile`, `suitability_evaluation` |
| `admin` | profile-api | `questionnaire_definition` (versioned JSONB, `(questionnaire_id, version)` PK) |
| `audit` | profile-api | `profile_processing_run` (full processing trace, FK to `admin.questionnaire_definition`) |

Both services connect to the same Postgres instance via `DATABASE_URL`. `profile-api` loads active questionnaires from `admin.questionnaire_definition` on startup; `custodian-api` reads custody data from the `custodian` schema. Without `DATABASE_URL`, both fall back to in-memory fixture data.

### Ontology paths

Questions and gate decisions carry `ontology_path` strings (e.g. `client_profile.risk_tolerance.questionnaire.loss_scenarios.loss_10_percent`). These are traceability tags linking data points back to `docs/client_profiling_ontology.yml` — not functional code paths.
