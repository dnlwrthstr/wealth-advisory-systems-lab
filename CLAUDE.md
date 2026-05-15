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

Gold-tier ingestion is split across five fetchers + one aggregator under `src/pipeline/gold/`:

- `equity_yahoo` — two modes. Default (`--universe smi|sp500|…`) loads Wikipedia-sourced ticker universes and fetches yfinance per ticker. `--from-parquet` reads `data/universe/{seeds,equity}.parquet` (built by `scripts/extract_universe_seeds.py` + `scripts/ingest_universe.py`), translates FINFOX bare tickers to Yahoo's venue convention using the ISIN country prefix (`ISIN_COUNTRY_TO_YAHOO_SUFFIX` in `src/pipeline/silver.py`), and uses the parquet rows as the *baseline*: ISIN + valor come from parquet always; yfinance values overlay where present; seed-only fallback emits a record even when Yahoo returns nothing.
- `bond_firds` — bundled issuer-LEI YAML at `src/pipeline/gold/data/bond_issuers.yml`, queries ESMA FIRDS Solr, filters to CFI category D, builds `BondGolden`. Coupon rate from FIRDS is a percentage (1.5); the ontology expects a decimal fraction (0.015), so the fetcher divides by 100. The OpenSearchInstrumentStore then multiplies by 100 again when projecting onto the frontend's `coupon_pct` field.
- `bond_parquet` — reads `data/universe/bond.parquet` (real FINFOX `csv_terms` rows: coupon, maturity, seniority, S&P-style rating + agency, currency). Maps the rating into `IssuerSnapshot.creditProfile.issuerRatings[]` as full `Rating` objects (`agency`, `rating`, `ratingType="issuer_credit_rating"`, `scale="long_term"`, `status="active"`). Primary path for the lab; FIRDS is the secondary path for when the parquet master isn't available. Pass `--enrich-lei` to resolve each bond's issuer LEI via GLEIF's `filter[isin]=` endpoint (`src/pipeline/gold/_lei_lookup.py`, cached under `~/.cache/wealth-advisory-systems-lab/gleif-isin/`); typical coverage on a mixed universe is ~55–60% (Eurobonds with XS prefix often have no GLEIF ISIN mapping). When resolved, the issuer record uses `issuerId="ISS-<LEI>"` so the aggregator dedupes correctly and `issuer_gleif` can chain further enrichment.
- `bond_synthetic_market_data` — fills `BondGolden.marketData` with the analytically-derivable yield + duration fields for **active** bonds (skips matured / cancelled). Computes `yieldToMaturity` and `currentYield` as the coupon rate (par assumption), `macaulayDuration = (1/y)·(1 − (1+y)⁻ᵀ)`, `modifiedDuration = macaulayDuration / (1+y)`. **Does not fabricate** prices, accrued interest, or spreads — those need a real feed. Provenance label is `synthetic (coupon-as-YTM at par)`. Run this first, then `bond_boerse_frankfurt_enrich` overwrites with real numbers where they're available.
- `bond_boerse_frankfurt_enrich` — pulls real clean prices from `api.boerse-frankfurt.de/v1/data/quote_box` (Server-Sent-Events stream; the first `data:` line carries the quote, we close after that). Then recomputes `yieldToMaturity` via bisection on the standard price-yield equation `P(y) = c·annuity(y, n) + (1+y)⁻ⁿ`, the `currentYield` as `coupon / (price/100)`, and `macaulayDuration` / `modifiedDuration` from the calibrated YTM. Provenance: appends a separate `marketData → boerse-frankfurt.de` row to `sourceOfTruth` (the dedupe key is `(fieldGroup, source)` so the older synthetic row coexists as audit history). Cached per-ISIN under `~/.cache/wealth-advisory-systems-lab/boerse-frankfurt/`. Coverage on a mixed-jurisdiction universe is ~80 % of the active bonds — European listings (DE / CH / XS) hit almost universally, US Treasuries don't list there.
- `fund_firds` — bundled umbrella-LEI YAML at `src/pipeline/gold/data/fund_umbrellas.yml`, queries FIRDS, filters to CFI category C, builds `FundGolden`. CFI position 2 drives `fundSubType`, position 4 drives `dividendPolicy`, position 5 drives `primaryAssetClassExposure`. Populates the full UCITS five-level corporate hierarchy on each record: `promoter` (group sponsor) → `managementCompany` (regulated operator, own LEI) → `umbrella` (legal issuer per UCITS, own LEI) → `subFund` (strategy + inception) → `shareClass` (ISIN + currency + accumulating/distributing + inception). Each entity is its own pydantic object — the YAML carries `umbrellaLei`, `managementCompanyLei`, `managementCompanyId`, `managementCompanyName`, `promoterName` per umbrella. FundGolden marks `umbrella` as required (alongside `managementCompany`) since the UCITS umbrella is the legal issuer of the share class.
- `issuer_aggregate` — scans `pms_golden_{equity,bond,fund}` via the OpenSearch helpers scan API and writes one `IssuerGolden` document per distinct issuer to `pms_golden_issuer`, keyed by `issuerId`. For funds it emits THREE issuer records per instrument: `umbrella` (issuerType `fund_umbrella`), `managementCompany` (`fund_company`), and `promoter` (`promoter`) — they are separate legal entities in the UCITS hierarchy. Counts instruments per class on each issuer record. Re-run after re-loading any per-instrument index.
- `issuer_gleif` — enriches `pms_golden_issuer` documents from the GLEIF public API. For each issuer with a non-null `lei`, fetches the main record + ultimate-parent LEI. **GLEIF wins for legal-entity attributes** (`legalName`, `domicileCountry`, `headquartersCountry`, `ultimateParentLei`) — those overwrite upstream values, since GLEIF is the authoritative source and FINFOX names are abbreviated short-forms. `issuerType` is only refined when current is blank or the generic `corporate` default (so the upstream role-aware types `fund_umbrella`, `fund_company`, `promoter` survive). Results cached under `~/.cache/wealth-advisory-systems-lab/gleif/`.
- `search_index_build` — rebuilds the `pms_golden_instrumentsearch` helper index from the three per-security indices. One doc per `(scope, documentId)` denormalising every identifier (ISIN, ticker, valor, CUSIP, FIGI, RIC, …) into both a `keyword` keyword array and a `text` field, plus display names (long + short), issuer/umbrella/managementCompany legal names, and a few hoisted filter fields (currency, country, asset class, CFI, venue MIC, lifecycle status, quality score). The "Find an instrument" UI hits this one index instead of fanning out across the three per-security indices.
- `fund_yahoo_enrich` — reads a FundGolden NDJSON file, looks up each ISIN via `yfinance.Ticker(isin)`, and backfills `marketData` (NAV / marketPrice / AUM / OHLCV / trailing returns), `totalExpenseRatio` + `fees.ongoing.totalExpenseRatio` when Yahoo has it, `primaryListing.ticker`, and a `tickerSymbol` entry in `identifierList`. Cached under `~/.cache/wealth-advisory-systems-lab/yahoo-funds/`. Fill-missing-only — won't overwrite curated values. Run after `fund_firds` and before `search_index_build`.

### Fact-sheet + full-holdings enrichment (per-fund, LLM-assisted)

For the field groups Yahoo doesn't carry — TER beyond what yfinance reports, the rest of the fees (management / entry / exit / performance), SRRI/SRI, PRIIPS transaction costs, dealing terms (settlement, cutoff, minimum investment), service providers (depositary / administrator / transfer agent / auditor), benchmark, replication method, rebalance frequency, **and the full constituent list / `holdingsCount`** — there's a Claude Code skill at `.claude/skills/find-and-parse-factsheet/SKILL.md`. Per-fund, on-demand, review-then-apply: the skill locates the KID/KIID/fact-sheet PDF and/or the issuer's holdings page for a given ISIN, parses the relevant fields, writes a JSON patch to `data/opensearch/golden/fund/patches/<goldenId>.json`, and only PATCHes the OpenSearch doc after the user confirms.

The skill applies patches through `pipeline.gold.apply_fund_patch`, which validates the top-level fields against a FundGolden allow-list, runs `POST /pms_golden_fund/_update/<goldenId>`, refreshes the index, and rebuilds `pms_golden_instrumentsearch` so any newly hoisted fields surface in the "Find an instrument" UI. The skill's full-holdings procedure routes per `managementCompany.legalName` to the right issuer page (iShares / Vanguard / Xtrackers / Amundi / UBS) and includes holdings-specific quality gates: total weight must be within `[0.95, 1.05]`, snapshot date no older than 30 days, at most 1 % of rows missing an identifier. Full programmatic scraping of iShares holdings is intentionally NOT a pipeline module — their site is JS-rendered and the ajax endpoints are obfuscated; LLM-driven WebFetch + parsing is the right surface for that variability.

`instrument-api` exposes two search surfaces. Legacy: `GET /instruments?q=...&type=...&currency=...` returns the flat `Instrument` dataclass (used by the old order-flow UI). New: `GET /instruments/search?identifier=&name=&issuer=&type=&currency=&country=` hits `pms_golden_instrumentsearch` directly and returns the richer `SearchHit` shape (scope, ow_type, identifiers list, asset_class, issuer_legal_name, lei, management_company_name, promoter_name, lifecycle_status, quality_score). Both endpoints share the same OpenSearch client; the search endpoint is null when `OPENSEARCH_URL` is unset and returns 503.

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
