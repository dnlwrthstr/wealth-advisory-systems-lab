"""Gold-tier pipeline: produces EquityGolden / BondGolden / FundGolden
documents from external sources and loads them into OpenSearch.

Silver-tier (parquet) checkpoints live next to the bronze stage in
`src/pipeline/bronze/`. The gold stage skips the silver checkpoint for
now — yfinance/FIRDS responses are already structured enough to map
straight to the ontology golden shape — and writes NDJSON under
`data/opensearch/golden/<entity>/` as the replayable artifact.
"""
