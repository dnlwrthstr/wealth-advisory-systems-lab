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

Services: frontend `localhost:3000`, custodian-api `localhost:8001`, profile-api `localhost:8002`, PostgreSQL `localhost:5433`.

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
