# Wealth Advisory Systems Lab

Learning-oriented prototypes for wealth advisory workflows, regulatory controls, client profiling, monitoring, and AI governance.

This repository is intentionally separate from an investment research lab. Investment research asks, "What should we own, and why?" Wealth advisory systems ask, "Is this advice suitable, explainable, compliant, monitored, and governed for this client?"

## Focus Areas

- Client profiling and investor objectives
- Suitability, appropriateness, and advisory workflows
- Compliance monitoring and audit trails
- Portfolio oversight from an advisory perspective
- Regulatory reporting patterns
- Advisor productivity tools
- AI governance for financial advice

## Repository Layout

```text
wealth-advisory-lab/
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
├── notebooks/
│   ├── 01_client_profiling/
│   ├── 02_suitability_advice/
│   ├── 03_compliance_monitoring/
│   ├── 04_portfolio_oversight/
│   ├── 05_ai_governance/
│   └── 06_advisor_workflows/
├── src/
│   ├── data/
│   ├── profiling/
│   ├── advice/
│   ├── compliance/
│   ├── monitoring/
│   ├── governance/
│   └── analytics/
├── docs/
└── tests/
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For notebooks:

```bash
python -m ipykernel install --user --name wealth-advisory-lab --display-name "Python (Wealth Advisory Lab)"
jupyter notebook
```

## Docker Deployment

The lab includes a small containerized reference stack:

- `database`: PostgreSQL with the advisory schema initialized from `db/init`.
- `backend`: FastAPI service exposing health and suitability endpoints.
- `frontend`: React workbench built with Vite and served by nginx, proxying `/api/*` to the backend.

```bash
docker compose up --build
```

Then open:

- Frontend: <http://localhost:3000>
- Backend API docs: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5433`, database `wealth_advisory`, user `wealth_advisory`, password `wealth_advisory`
- OpenSearch (golden record store): <http://localhost:9200> — security disabled, no auth
- OpenSearch Dashboards: <http://localhost:5601>

The `opensearch-init` service runs once on first `up` to create the five
golden indices (`pms_golden_bond`, `pms_golden_equity`, `pms_golden_fund`,
`pms_golden_identifier`, `pms_golden_position`) from
`data/opensearch/golden/`. The script is idempotent — re-runs skip
existing indices. To regenerate mappings after changing the ontology:

```bash
PYTHONPATH=src python -m ontology_tools.golden_record_2_opensearch.convert_to_opensearch \
  -i ontology -o data/opensearch/golden
docker compose run --rm opensearch-init
```

### Populating the equity index

The gold-tier pipeline fetches real equities from Yahoo Finance and bulk-loads
them into `pms_golden_equity` (the same index the frontend instrument search
reads from when `OPENSEARCH_URL` is set on `instrument-api`):

```bash
# 1. Fetch (writes data/opensearch/golden/equity/equities.ndjson)
PYTHONPATH=src python -m pipeline.gold.equity_yahoo --universe smi

# 2. Load
PYTHONPATH=src python -m pipeline.gold.load \
  -i data/opensearch/golden/equity/equities.ndjson -x pms_golden_equity
```

Supported universes: `smi`, `sp500`, `nasdaq100`, `dax40`, `ftse100`. Add
`--limit N` for smoke testing.

If the browser still shows an older frontend after changes, rebuild and recreate the frontend container:

```bash
docker compose down
docker compose build --no-cache frontend
docker compose up --force-recreate
```

## Learning Objectives

By working through this lab, you should be able to:

- Model investor profiles, constraints, preferences, and knowledge/experience inputs.
- Translate advisory policies into testable suitability and compliance rules.
- Build monitoring workflows for drift, concentration, missing documentation, and policy exceptions.
- Design audit-friendly data flows for advisor recommendations.
- Evaluate AI-assisted advisory systems for explainability, human oversight, traceability, and governance risk.
