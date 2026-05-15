# Golden — Tier-3 Records

The `ontology/golden/` tree contains **tier-3 (golden) records**: denormalized,
search-optimised read-models composed from the canonical ontology entities and
designed to live as documents in OpenSearch.

These records are the primary documents the Portfolio Management System (PMS),
client portals and downstream analytics read from. They are derived; they are
never the source of truth.

## Tier Model

| Tier       | Where it lives                       | Source of truth? | Shape                                                      |
| :--------- | :----------------------------------- | :--------------- | :--------------------------------------------------------- |
| **Bronze** | Inbound feeds / vendor files         | Vendor / source  | Raw payloads (vendor-specific). Bronze → silver mapping is implemented *outside* this repo. |
| **Silver** | `ontology/` (everything except `golden/`) | **Yes**          | Canonical, normalized entities (Equity, Issuer, Listing, MarketDataSnapshot, …). |
| **Golden** | `ontology/golden/`                   | No (derived)     | Denormalized read-models. One document per business entity, ready for OpenSearch indexing. |

The silver tier is the contract between domains. The golden tier is a
performance / convenience layer over it.

## What lives here

One folder per golden record family:

- `golden/equity/EquityGolden.yml`
- `golden/bond/BondGolden.yml`
- `golden/fund/FundGolden.yml`
- `golden/position/PositionGolden.yml`

Each file defines a single tier-3 root entity tagged with `kind: golden_record`
plus the embedded value-objects (snapshots, flags, metadata) that document
references inline.

## Authoring rules

1. **Trace every field to silver.** Either reference the silver entity via
   `common_ontology` (preferred for the *type* of a copied field) or define an
   embedded snapshot value-object that mirrors the silver shape.
2. **Hoist high-cardinality filter fields to the top level.** Identifiers
   (`isin`, `figi`, `ticker`, `mic`), classification (`assetClass`, `sector`,
   `currency`, `country`) and time-series anchors (`asOf`) should be top-level
   to keep OpenSearch queries flat.
3. **Embed snapshots, don't `$ref` foreign entities.** A golden record must be
   readable in one fetch. Use `IssuerSnapshot`, `ListingSnapshot`, etc., not
   live references.
4. **Always include `recordMeta`.** Schema version, assembly timestamp, source
   attribution and content fingerprints power lineage, freshness and rebuild
   detection.
5. **No business logic.** Compliance flags, ratings buckets and derived labels
   are *computed by the enrichment pipeline and copied in*, not re-derived by
   readers.
6. **Backfill silver when a concept is genuinely missing.** If a golden record
   needs a fact that doesn't exist in silver yet, add it to the silver entity
   first, then mirror it in golden. Don't invent silver-tier concepts inside
   `golden/`.

## Converter behaviour

The `golden_record_2_opensearch` utility (see `src/golden_record_2_opensearch/`)
discovers entities tagged `kind: golden_record` and emits one OpenSearch index
mapping per record family, plus a bulk `create_indices.sh` script. Documents
themselves are produced at runtime by the enrichment pipeline and bulk-indexed
against these mappings — this repo defines the **shape**, not the data.

The other ontology converters (`ontology_2_pydantic`, `ontology_2_neo4j`,
`ontology_2_html`, `ontology_2_owl`) treat `golden_record` entities like any
other entity: Pydantic models are emitted, Neo4j classes are created, HTML
docs are generated. Only the OpenSearch utility is golden-aware.

---
*This page is hand-authored. The auto-generated HTML docs include it via the
standard CONTEXT.md pipeline.*
