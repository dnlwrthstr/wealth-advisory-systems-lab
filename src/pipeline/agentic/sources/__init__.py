"""Agentic source adapters.

Each adapter wraps a single upstream fetcher / enricher with the agentic
contract: `fetch(identifier_kind, identifier_value, current) ->
Optional[SourceFetchResult]`.

The adapter is intentionally thin — the heavy lifting stays in the
existing `pipeline.gold.*` modules. The adapter only translates between
"return me an EquityGolden / BondGolden / FundGolden" and "give me a
{patch, source_of_truth_rows} envelope" the planner can compose.
"""
