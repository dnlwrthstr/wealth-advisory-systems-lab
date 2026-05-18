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
| 2 | `fund_yahoo` | `api_call` | NAV / market price / OHLCV / AUM / TER / asset allocation buckets (sector / asset class / region — no holdings) |
| 3 | `fund_factsheet_patch` | `file_read` | pre-curated patches from `data/opensearch/golden/fund/patches/` |
| 4 | `fund_factsheet_skill` | `llm_skill` | live PDF KID parsing via the `find-and-parse-factsheet` skill |
| 5 | `fund_lookthrough_skill` | `llm_skill` | proxy-derived holdings for synthetic / swap-based ETFs — copies the constituent list of a physically-replicated peer ETF tracking the same benchmark, stamps each row `source: physical_proxy`, and writes a top-level `lookthroughProvenance` block (proxy ISIN, benchmark, asOfDate, confidence). Predicate-gated: fires only when `holdings` is empty AND `replicationMethod == synthetic_swap` AND a benchmark is set. Pre-curated patches under `data/opensearch/golden/fund/patches/lookthrough/` bypass the LLM. |

Both LLM-skill sources are gated by the same cost-class flag. Open the gate via `--enable-llm-skills` (CLI) or `max_cost_class="llm_skill"` (HTTP); restrict to a subset with `--llm-skills <id1,id2,...>` (CLI) or `allowed_llm_skills: [...]` (HTTP body).

### Issuer (`scope="issuer"`)

| Order | Source | Cost | Produces |
|---|---|---|---|
| 1 | `issuer_gleif` | `api_call` | authoritative legal-entity attributes by LEI |

## Merge policy

`merger.merge_patch` is **deep fill-empty-only**: at every level of a
nested dict the first writer wins, but sibling sub-keys not yet
populated still get written even when the parent dict is non-empty.
Lists remain atomic — a list value is replaced only when the existing
slot is empty.

This matters in practice: `fund_yahoo` populates `assetAllocation` with
sector and asset-class buckets (no holdings). `fund_lookthrough_skill`
later contributes `assetAllocation.holdings`. Under shallow fill-empty
the second patch would be silently dropped because the parent dict is
non-empty; under deep fill-empty the holdings land alongside the
buckets and downstream consumers see both.

The merger's return value carries dot-paths for nested writes
(e.g. `"assetAllocation.holdings"`); the planner's trace formatting
extracts the top-level prefix when computing
`fields_skipped_already_filled`. Each populated field gets a
`SourceAttribution` row appended to `recordMeta.sourceOfTruth` recording
the source name, timestamp, and (for proxy-derived rows) the proxy ISIN
and confidence.

### `replace_paths` — opt-in list replacement (spec 004)

A source can opt into **list replacement** instead of fill-empty-only by
declaring `replace_paths: List[str]` on its `SourceFetchResult`. Each
entry is a dot-path; when the patch carries a list value at that path,
the merger replaces the existing list verbatim (even when non-empty).

Why it exists: `fund_factsheet_skill` produces a top-N projection of
holdings (e.g. 10 of 1310 MSCI World constituents). `fund_lookthrough_skill`
later contributes the full constituent list from a physical-proxy peer
ETF. Without the marker, deep fill-empty-only would preserve the top-N
and silently drop the proxy's expanded list — exactly the wrong outcome
for portfolio-risk look-through.

Rules:
- Applies only when the patch's value at the marked path is a `list`.
  Marker is a no-op when the value is a dict (deep-merge applies) or a
  scalar (fill-empty-only applies).
- Empty patch lists (`[]`) are still skipped at every path — the marker
  doesn't override the never-write-nothing rule.
- Other paths in the same patch are unaffected — they follow standard
  deep fill-empty-only.

V1 has exactly one source using `replace_paths`: `fund_lookthrough_skill`
declares `["assetAllocation.holdings"]`. Adding a new source that uses
it requires review — the marker is a deliberate escape hatch from the
otherwise-safe fill-empty-only invariant.

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

**Universe batch CLIs (this package, `cli/`):**

One batch loader per scope. All share the same shape: enumerate ISINs,
call `AGENTS[scope].assemble_and_persist(..., status="in_universe")`
per ISIN in strict serial order, mirror each persisted record onto
`pms_golden_instrumentsearch` via `index_search_hit`. Per-ISIN errors
are isolated. The scopes differ only in how the universe is enumerated.

### Equity — `cli/equity_universe.py`

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.equity_universe \
    --universe smi   # one of: smi, sp500, nasdaq100, dax40, ftse100
```

Universe model: named market index. Resolves a Wikipedia ticker table
to a list of tickers, then maps each to an ISIN (via `six_ticker_isin`
for SIX-listed, OpenFIGI's ticker-direction lookup for foreign
exchanges; falls back to passing the ticker directly to the planner
when OpenFIGI misses).

### Bond — `cli/bond_universe.py`

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.bond_universe \
    [--issuer-lei LEI]       # single-issuer smoke test
    [--all]                  # full curated set (default)
    [--limit-per-issuer N]   # cap bonds emitted per issuer
```

Universe model: per-issuer-LEI. Reads the curated
[bond_issuers.yml](../gold/data/bond_issuers.yml) (sovereigns +
corporates), then for each LEI runs `pipeline.gold._firds.iter_issuer_records(lei, FIRDS_FL)`
to enumerate all bond ISINs that issuer has reported to ESMA FIRDS,
deduplicates by ISIN, and calls `AGENTS["bond"].assemble_and_persist`
per ISIN. Issuer chaining via GLEIF fires automatically inside the
persist call; the curated `bond_issuers.yml` metadata acts as a
fallback when GLEIF lacks a record.

The loop is two-level (issuer → ISIN); the report groups outcomes
per-issuer. Issuer-level FIRDS failures are silently swallowed by
`iter_issuer_records` (its built-in retry-then-empty pattern), so a
failed issuer shows up as "0 bonds" in the report rather than as an
exception.

### Fund — `cli/fund_universe.py`

```bash
PYTHONPATH=src python -m pipeline.agentic.cli.fund_universe \
    [--umbrella-lei LEI]          # single-umbrella smoke test
    [--all]                       # full curated set (default)
    [--limit-per-umbrella N]      # cap share-classes emitted per umbrella
    [--enable-factsheet-skill]    # opt into LLM cost (default: web_fetch cap)
```

Universe model: per-umbrella-LEI, with a five-level corporate
hierarchy (promoter → managementCompany → umbrella → subFund →
shareClass). Reads the curated
[fund_umbrellas.yml](../gold/data/fund_umbrellas.yml) (iShares /
Vanguard / Xtrackers / Amundi / UBS), then for each umbrella LEI runs
the same `iter_issuer_records(lei, FIRDS_FL)` helper bond uses but
with fund-specific `FIRDS_FL` and a CFI=C* filter in
`fund_firds.dedupe_by_isin`. Calls `AGENTS["fund"].assemble_and_persist`
per share-class ISIN.

**Cost-class control (unique to fund)**: `FundAgent.default_max_cost_class="llm_skill"`,
because the `find-and-parse-factsheet` skill carries TER, SRRI/SRI,
dealing terms, and service-provider data that nothing else surfaces.
The batch CLI overrides this default to `"web_fetch"` so a full
universe load is free at the LLM layer; `--enable-factsheet-skill`
opts in. Pre-curated patches under
`data/opensearch/golden/fund/patches/*.json` are honoured by the
`fund_factsheet_patch` source regardless (cheap, `file_read`) — the
skill only fires when a patch is missing AND the cap allows
`llm_skill`.

**Three-record issuer chain**: `persist.extract_leis` walks every
`lei` key in the assembled record. For a fund, this typically picks
up `umbrella.lei` and `managementCompany.lei` (and `promoter.lei`
when the curated YAML has it), so each fund-scope `assemble_and_persist`
triggers 1–3 chained issuer writes to `pms_golden_issuer` — vs ~1 for
bond/equity.

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
