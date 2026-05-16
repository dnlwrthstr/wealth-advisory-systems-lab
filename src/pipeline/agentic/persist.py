"""Persistence + side-effect chaining for assembled golden records.

`persist_record` writes a single document to `pms_golden_{scope}`.
`assemble_and_persist` runs the full loop: assemble the primary record,
write it, then for every LEI it finds embedded in that record, assemble
and write an IssuerGolden too. The chain only fires when `chain_issuers`
is truthy (default) and the primary scope is not already `issuer`.

The OpenSearch client is taken as a parameter — this module makes no
assumptions about how it was constructed. The instrument-api wires it
from `opensearch_client_from_env()`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from pipeline.agentic.assemble import AssembleResult, assemble_golden

log = logging.getLogger(__name__)


def persist_record(client: Any, scope: str, record: Dict[str, Any]) -> None:
    """Index `record` under `pms_golden_{scope}` with refresh=wait_for.

    `refresh=wait_for` makes the write visible to subsequent searches —
    crucial when the frontend's next call is a "did the assembled record
    show up?" lookup.
    """
    index = f"pms_golden_{scope}"
    client.index(index=index, id=record["goldenId"], body=record, refresh="wait_for")


def extract_leis(record: Dict[str, Any]) -> List[str]:
    """Walk `record` and return every distinct LEI string found.

    The same LEI can appear in multiple places — `issuer.lei`,
    `umbrella.lei`, `managementCompany.lei` — but each is materially the
    same legal entity, so the de-duped list is what the chain iterates.
    """
    found: List[str] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "lei" and isinstance(value, str) and value and value not in seen:
                    seen.add(value)
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(record)
    return found


def assemble_and_persist(
    *,
    client: Any,
    scope: str,
    identifier: Dict[str, str],
    budget: int = 10,
    chain_issuers: bool = True,
) -> Dict[str, Any]:
    """Assemble + persist the primary record; chain into issuer assembly.

    Returns:
      {
        "primary": AssembleResult,
        "chained_issuers": [{lei, golden_id, quality_score, remaining_gaps}, ...]
      }
    """
    primary: AssembleResult = assemble_golden(
        scope=scope, identifier=identifier, budget=budget
    )
    persist_record(client, scope, primary.record)

    chained: List[Dict[str, Any]] = []
    if chain_issuers and scope != "issuer":
        for lei in extract_leis(primary.record):
            try:
                issuer = assemble_golden(
                    scope="issuer",
                    identifier={"kind": "lei", "value": lei},
                    budget=budget,
                )
                persist_record(client, "issuer", issuer.record)
                chained.append({
                    "lei": lei,
                    "golden_id": issuer.record.get("goldenId"),
                    "quality_score": issuer.quality_score,
                    "remaining_gaps": issuer.remaining_gaps,
                })
            except Exception as exc:  # noqa: BLE001 — broad: GLEIF can fail any number of ways
                log.warning("issuer chain failed for lei=%s: %s", lei, exc)

    return {"primary": primary, "chained_issuers": chained}
