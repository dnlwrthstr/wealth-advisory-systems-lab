"""Agentic data engineering — assemble golden records from a registry of sources.

The platform reduces hand-coded enrichment pipelines to one loop: given
(identifier, scope), read the ontology to discover required fields, pick a
source from the registry that covers any unfilled fields, fetch it, merge
with provenance, repeat until the manifest is satisfied or the budget is
exhausted.

Public entrypoint: `assemble_golden(scope, identifier)` from
`pipeline.agentic.assemble`. The registry lives under `registry/`, the
ontology-derived field expectations under `annotations/`, source adapters
under `sources/`.
"""
from pipeline.agentic.assemble import assemble_golden, AssembleResult
from pipeline.agentic.persist import (
    assemble_and_persist,
    extract_leis,
    persist_record,
)

__all__ = [
    "assemble_golden",
    "AssembleResult",
    "assemble_and_persist",
    "extract_leis",
    "persist_record",
]
