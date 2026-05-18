# `pipeline.agentic` — agentic instrument-data assembly

This package assembles a per-instrument golden record from an identifier
(ISIN, ticker, LEI) by running a planner loop over a per-scope source
registry. Each source contributes a partial patch; the merger combines
them with fill-empty-only semantics and per-field provenance. Persistence
writes the result to `pms_golden_{scope}` and, where the record embeds
issuer LEIs, chains into a separate `pms_golden_issuer` assembly.

The agentic platform is **identifier-in, golden-record-out**. It does not
own bulk loading — that's the universe-loader CLI (one per scope) that
calls into the per-scope agent in a loop. The platform also does not own
the user-facing search API — `pms_golden_instrumentsearch` is mirrored
from the per-scope writes via `pipeline.gold.search_index_build.index_search_hit`.

## Layered API

Four layers, narrowest to widest. Most callers want one of the top two.

| Layer | Function | Used by |
|---|---|---|
| **Agent** (narrowest, recommended) | `agents.AGENTS["equity"].assemble_and_persist(client=..., identifier=..., status="in_universe")` | HTTP endpoints, batch CLIs |
| **Persist** | `persist.assemble_and_persist(client=..., scope=..., identifier=..., universe_status=...)` | Agent layer; rarely called directly |
| **Assemble** (pure) | `assemble.assemble_golden(scope=..., identifier=...)` → `AssembleResult` | Anyone wanting a record without writes (skills, notebooks) |
| **Planner** (engine) | `planner.run_planner(...)` | Implementation detail of `assemble_golden` |

The agent layer is preferred because it binds the scope (so callers can't
mix `EquityAgent` with `scope="bond"`) and carries per-type defaults
(funds default `max_cost_class="llm_skill"` to enable the factsheet skill;
equity/bond stay at `web_fetch`).

## Sources by scope

Sources live in `sources/` (Python adapters) with matching descriptors in
`registry/*.yml`. The planner orders them by `cost_class` —
`file_read → api_call → web_fetch → llm_skill` — and skips any whose
`requires_identifier.any_of` doesn't include the input kind.

### Equity (`scope="equity"`)

| Order | Source | Cost | Direction | Produces |
|---|---|---|---|---|
| 1 | `six_ticker_isin` | `file_read` | ticker → ISIN | `identifierList` (SIX-listed only) |
| 2 | `openfigi` | `api_call` | ISIN → FIGI/ticker/name | `identifierList`, `longName`, `equitySubType` |
| 3 | `equity_firds` | `api_call` | ISIN → ESMA reg data | `longName`, `cfiCode`, `issuer`, `secondaryListings`, `lifecycleStatus`, `firstTradingDate` |
| 4 | `equity_yahoo` | `api_call` | ISIN or ticker → market data | `assetClass`, `industrySector`, `currencyOfDenomination`, `primaryListing`, `marketData`, `keyFigures`, … |
| 5 | `finnhub` | `api_call` (skipped without `FINNHUB_API_KEY`) | ISIN or ticker → second-opinion overlay | `marketData`, `keyFigures`, `incorporationCountry`, `industrySector` |

### Bond (`scope="bond"`)

| Order | Source | Cost | Produces |
|---|---|---|---|
| 1 | `bond_firds` | `api_call` | full bond record from ESMA FIRDS by ISIN; issuer LEI either from curated `bond_issuers.yml` or GLEIF on the chain |

### Fund (`scope="fund"`)

| Order | Source | Cost | Produces |
|---|---|---|---|
| 1 | `fund_firds` | `api_call` | UCITS hierarchy from ESMA FIRDS + umbrella LEI map |
| 2 | `fund_yahoo` | `api_call` | NAV / market price / OHLCV / AUM / TER / asset allocation |
| 3 | `fund_factsheet_patch` | `file_read` | pre-curated patches from `data/opensearch/golden/fund/patches/` |
| 4 | `fund_factsheet_skill` | `llm_skill` | live PDF KID parsing via the `find-and-parse-factsheet` skill |

### Issuer (`scope="issuer"`)

| Order | Source | Cost | Produces |
|---|---|---|---|
| 1 | `issuer_gleif` | `api_call` | authoritative legal-entity attributes by LEI |

## Merge policy

`merger.merge_into` is **fill-empty-only**: a source patch sets a field
only when the target slot is empty (`None`, `""`, `[]`, `{}`). Already-
populated fields are never overwritten — so source order matters and
high-confidence sources should run first. Each populated field gets a
`SourceAttribution` row appended to `recordMeta.sourceOfTruth` recording
the source name and timestamp.

## Persistence and chaining

`persist.assemble_and_persist`:

1. Runs `assemble_golden`.
2. Writes the primary record to `pms_golden_{scope}` with
   `refresh="wait_for"` so subsequent reads see it.
3. If `chain_issuers=True` (default) and the scope is not already
   `issuer`, walks the record for every distinct embedded `lei` value
   and runs `assemble_golden(scope="issuer", identifier={"kind": "lei", "value": lei})`
   for each one, persisting the result to `pms_golden_issuer`. Failures
   in the chain are logged at WARNING, not raised.

The `universe_status` parameter (one of `watchlist`, `in_universe`,
`excluded`) is stamped as a top-level field on the primary record only —
chained issuer records don't carry membership.

## Manifest invariant

`manifest.manifest_for(scope)` loads the per-scope field annotations
from `annotations/{scope}.yml`. At import time it cross-checks the
annotation field names against the pydantic model under `universe.models`
and raises if they disagree. Adding a field to the model without an
annotation entry (or vice versa) fails fast on next import — drift is
not silent.

## Entry points

**Python (in-process):**

```python
from pipeline.agentic.agents import AGENTS
from pipeline.opensearch_client import opensearch_client_from_env

client = opensearch_client_from_env()
outcome = AGENTS["equity"].assemble_and_persist(
    client=client,
    identifier={"kind": "isin", "value": "CH0038863350"},
    status="in_universe",
)
# outcome = {"primary": AssembleResult, "chained_issuers": [...]}
```

**HTTP (instrument-api on port 8003):**

- `POST /instruments/assemble` — single-instrument assemble; `persist=true` writes to OpenSearch.
- `POST /universe/{equity|bond|fund}` — universe-membership add; same chain plus `index_search_hit` mirror for immediate Find-an-instrument visibility.
- `GET /universe` — cross-scope universe listing.
- `PATCH /universe/{scope}/{golden_id}/status` — partial update of `universeStatus`.

**Universe batch CLI (this package, `cli/equity_universe.py`):**

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.equity_universe \
    --universe smi   # one of: smi, sp500, nasdaq100, dax40, ftse100
```

Resolves a named ticker universe (Wikipedia-sourced), maps tickers to
ISINs (via `six_ticker_isin` for SIX-listed, via OpenFIGI's
ticker-direction lookup for foreign exchanges), and calls
`AGENTS["equity"].assemble_and_persist(..., status="in_universe")` per
ISIN in strict serial order. Mirrors each persisted record onto
`pms_golden_instrumentsearch` via `index_search_hit`.

## Adding a new source

1. Add `sources/<name>.py` implementing `fetch(identifier_kind, identifier_value, current) -> Optional[SourceFetchResult]`.
2. Add `registry/<name>.yml` with `module`, `entrypoint`, `covers`, `requires_identifier`, `produces_fields`, `confidence`, `cost_class`.
3. The planner picks it up automatically — no agent-side wiring needed.
4. Add a test under `tests/agentic/test_<name>_source.py`.

## Where things live

```
pipeline/agentic/
  ├── README.md            ← you are here
  ├── agents/              ← per-scope facades (EquityAgent, BondAgent, FundAgent)
  ├── annotations/         ← per-scope field manifests (YAML)
  ├── registry/            ← per-source descriptors (YAML)
  ├── sources/             ← per-source Python adapters
  ├── cli/                 ← batch loaders (one per scope, as needed)
  ├── assemble.py          ← pure assemble entry
  ├── persist.py           ← assemble + write + LEI chain
  ├── planner.py           ← cost-ordered execution loop
  ├── manifest.py          ← per-scope field manifest loader
  ├── merger.py            ← fill-empty-only merge + provenance
  └── universes.py         ← named-universe → ticker list resolver
```
