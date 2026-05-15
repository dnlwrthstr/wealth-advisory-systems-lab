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

### Populating the golden indices

The gold-tier pipeline fetches from public sources and bulk-loads into
the `pms_golden_*` indices. When `OPENSEARCH_URL` is set on
`instrument-api`, the frontend instrument search queries all three
families (`pms_golden_equity`, `pms_golden_bond`, `pms_golden_fund`).

```bash
# Equities (Yahoo Finance) — two modes:
# 1. Wikipedia-sourced universes: smi, sp500, nasdaq100, dax40, ftse100
PYTHONPATH=src python -m pipeline.gold.equity_yahoo --universe smi
# 2. Parquet-seeded (ISIN/valor from FINFOX, Yahoo overlay; seed-only fallback)
PYTHONPATH=src python -m pipeline.gold.equity_yahoo --from-parquet --limit 50
PYTHONPATH=src python -m pipeline.gold.load \
  -i data/opensearch/golden/equity/equities.ndjson -x pms_golden_equity

# Bonds (parquet-direct) — real FINFOX terms + S&P ratings
PYTHONPATH=src python -m pipeline.gold.bond_parquet --limit 500
PYTHONPATH=src python -m pipeline.gold.load \
  -i data/opensearch/golden/bond/bonds.ndjson -x pms_golden_bond

# Bonds alternative (ESMA FIRDS) — when no parquet master is available
PYTHONPATH=src python -m pipeline.gold.bond_firds --limit-per-issuer 10
PYTHONPATH=src python -m pipeline.gold.load \
  -i data/opensearch/golden/bond/bonds.ndjson -x pms_golden_bond

# UCITS funds (ESMA FIRDS) — bundled curated umbrella LEIs
PYTHONPATH=src python -m pipeline.gold.fund_firds --limit-per-issuer 10
PYTHONPATH=src python -m pipeline.gold.load \
  -i data/opensearch/golden/fund/funds.ndjson -x pms_golden_fund
```

Add `--limit-per-issuer N` to bond/fund fetchers for smoke testing. FIRDS
hosts the data on best-effort infra; transient 5xx errors are retried with
exponential backoff in the bundled Solr client.

After loading any per-security index, regenerate the canonical issuer
index from the embedded snapshots:

```bash
PYTHONPATH=src python -m pipeline.gold.issuer_aggregate
```

This scans `pms_golden_{equity,bond,fund}` and writes one `IssuerGolden`
document per distinct issuer into `pms_golden_issuer`, with
`instrumentsByClass` counters.

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
