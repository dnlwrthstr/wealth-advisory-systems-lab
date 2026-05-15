# Golden Record → OpenSearch

Generates OpenSearch index mappings for ontology entities tagged
`kind: golden_record` (the tier-3 read-models under `ontology/golden/`).

## Features

- Discovers every entity with `kind: golden_record` across the ontology tree.
- Emits one OpenSearch index-mapping JSON per record family.
- Generates an idempotent `create_indices.sh` bulk-creation script that
  works from any current working directory.

## Usage

```bash
# Default: ontology/ → output/opensearch/golden/
golden_record_2_opensearch

# Custom input and output
golden_record_2_opensearch -i ontology -o path/to/golden_indices
```

After running, create the indices against your cluster:

```bash
OPENSEARCH_URL=https://localhost:9200 bash output/opensearch/golden/create_indices.sh
```

## Index Naming

Index names are derived from the entity name with any `Golden` suffix
stripped: `EquityGolden` → `equity`, `BondGolden` → `bond`,
`FundGolden` → `fund`, `PositionGolden` → `position`.

## Field-Type Resolution

- Locally-defined `ref` / `$ref` value-objects → nested `object` mapping
  (recursively, with cycle guard).
- Cross-file `common_ontology` references → `{type: object, dynamic: true}`
  so unknown subfields are still searchable without a cross-file resolver.
- `string` with `format: date` → `date` (`yyyy-MM-dd`).
- `string` with `format: date-time` → `date`.
- Enum strings → `keyword`.
- Other strings → `text` + `keyword` sub-field.
- `integer` → `long`, `number` → `double`, `boolean` → `boolean`.
- `type: Country` and `type: CfiCode` → `keyword`.

## Output

For each golden entity:

- `<index>.index.json` — full OpenSearch settings + mappings document with a
  `_meta` block recording ontology name, version, source entity, source
  file and `tier: golden`.

Plus a top-level:

- `create_indices.sh` — bulk creation script that PUTs each mapping
  against `$OPENSEARCH_URL`.

This utility intentionally does **not** emit documents — golden documents
are produced by the enrichment pipeline (see `equity_golden_from_yahoo`,
`bond_golden_from_firds`, `fund_golden_from_firds`) and bulk-loaded with
`load_golden_to_opensearch`.
