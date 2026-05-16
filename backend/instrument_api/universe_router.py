"""HTTP routes for the Investment Universe.

Built on top of the agentic assembler. `POST /universe/add` assembles a
golden record and stamps `universeStatus` on it; `GET /universe` lists
every persisted document that has a `universeStatus` field across the
three instrument scopes; `PATCH /universe/{scope}/{goldenId}/status`
flips membership without re-assembling.

Silver-tier components / time series for each universe member are a
future iteration — the goldenId returned here is the join key.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pipeline.agentic import assemble_and_persist
from pipeline.agentic.persist import (
    ALLOWED_UNIVERSE_STATUSES,
    update_universe_status,
)

log = logging.getLogger(__name__)

_INSTRUMENT_SCOPES = ("equity", "bond", "fund")


def _ensure_universe_status_mapping(client: Any) -> None:
    """Add `universeStatus` as a keyword field on the per-scope indices.

    The generated index mappings have `dynamic: false` so unknown fields
    are stored in _source but never indexed — meaning our `exists` /
    `term` queries on `universeStatus` would return zero hits. PUT
    _mapping is idempotent: a no-op when the field already exists with
    the same type, so this is safe to call on every router build.

    universeStatus is PMS-application metadata, not ontology truth, so
    we register the field at runtime rather than baking it into the
    ontology-generated `data/opensearch/golden/` mapping files.
    """
    body = {"properties": {"universeStatus": {"type": "keyword"}}}
    for scope in _INSTRUMENT_SCOPES:
        index = f"pms_golden_{scope}"
        try:
            client.indices.put_mapping(index=index, body=body)
        except Exception as exc:  # noqa: BLE001 — opensearchpy.NotFoundError + transport errors
            log.warning("universe_router: put_mapping on %s failed: %s", index, exc)


class _IdentifierIn(BaseModel):
    kind: str = Field(..., description="Identifier kind: 'isin', 'ticker'.")
    value: str = Field(..., description="Identifier value.")


class UniverseAddRequest(BaseModel):
    scope: str = Field(..., description="Instrument scope: 'equity', 'bond', 'fund'.")
    identifier: _IdentifierIn
    status: str = Field(
        default="in_universe",
        description="Initial universe status: 'watchlist' | 'in_universe' | 'excluded'.",
    )
    budget: Optional[int] = Field(default=None, ge=1, le=50)
    invoke_llm_skills: bool = Field(default=False)


class UniverseStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: 'watchlist' | 'in_universe' | 'excluded'.")


class UniverseAddResponse(BaseModel):
    scope: str
    goldenId: str
    universeStatus: str
    qualityScore: float
    remainingGaps: List[str]
    record: Dict[str, Any]
    chainedIssuers: List[Dict[str, Any]] = Field(default_factory=list)


class UniverseMember(BaseModel):
    scope: str
    goldenId: str
    universeStatus: str
    longName: Optional[str] = None
    isin: Optional[str] = None
    ticker: Optional[str] = None
    currency: Optional[str] = None
    qualityScore: Optional[float] = None
    goldenAsOf: Optional[str] = None


class UniverseListResponse(BaseModel):
    items: List[UniverseMember]
    total: int


def build_universe_router(opensearch_client: Optional[Any]) -> APIRouter:
    router = APIRouter(prefix="/universe", tags=["universe"])

    if opensearch_client is not None:
        _ensure_universe_status_mapping(opensearch_client)

    def _require_client():
        if opensearch_client is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Universe operations require OpenSearch. "
                    "Set OPENSEARCH_URL on instrument-api."
                ),
            )

    def _validate_scope(scope: str) -> None:
        if scope not in _INSTRUMENT_SCOPES:
            raise HTTPException(
                status_code=400,
                detail=f"scope must be one of {list(_INSTRUMENT_SCOPES)}, got {scope!r}",
            )

    def _validate_status(status: str) -> None:
        if status not in ALLOWED_UNIVERSE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"status must be one of {sorted(ALLOWED_UNIVERSE_STATUSES)}, "
                    f"got {status!r}"
                ),
            )

    @router.post("/add", response_model=UniverseAddResponse)
    def add_to_universe(body: UniverseAddRequest) -> UniverseAddResponse:
        _require_client()
        _validate_scope(body.scope)
        _validate_status(body.status)
        identifier = {"kind": body.identifier.kind, "value": body.identifier.value}
        max_cost_class = "llm_skill" if body.invoke_llm_skills else "web_fetch"
        try:
            outcome = assemble_and_persist(
                client=opensearch_client,
                scope=body.scope,
                identifier=identifier,
                budget=body.budget or 10,
                max_cost_class=max_cost_class,
                universe_status=body.status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        primary = outcome["primary"]
        return UniverseAddResponse(
            scope=primary.scope,
            goldenId=primary.record["goldenId"],
            universeStatus=body.status,
            qualityScore=primary.quality_score,
            remainingGaps=primary.remaining_gaps,
            record=primary.record,
            chainedIssuers=outcome["chained_issuers"],
        )

    @router.get("", response_model=UniverseListResponse)
    def list_universe(
        scope: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> UniverseListResponse:
        _require_client()
        if scope is not None:
            _validate_scope(scope)
            indices = [f"pms_golden_{scope}"]
        else:
            indices = [f"pms_golden_{s}" for s in _INSTRUMENT_SCOPES]
        if status is not None:
            _validate_status(status)
            query: Dict[str, Any] = {"term": {"universeStatus": status}}
        else:
            query = {"exists": {"field": "universeStatus"}}
        body = {
            "size": min(max(limit, 1), 1000),
            "query": query,
            "_source": [
                "goldenId",
                "universeStatus",
                "longName",
                "identifierList",
                "currencyOfDenomination",
                "recordMeta.qualityScore",
                "recordMeta.goldenAsOf",
            ],
            "sort": [{"recordMeta.goldenAsOf": {"order": "desc", "unmapped_type": "date"}}],
        }
        response = opensearch_client.search(
            index=",".join(indices),
            body=body,
            ignore_unavailable=True,
        )
        hits = response.get("hits", {}).get("hits", [])
        items: List[UniverseMember] = []
        for hit in hits:
            src = hit.get("_source", {}) or {}
            idx = hit.get("_index", "")
            hit_scope = idx.removeprefix("pms_golden_") if idx else ""
            isin, ticker = _split_identifiers(src.get("identifierList") or [])
            record_meta = src.get("recordMeta") or {}
            items.append(
                UniverseMember(
                    scope=hit_scope,
                    goldenId=src.get("goldenId") or hit.get("_id", ""),
                    universeStatus=src.get("universeStatus") or "",
                    longName=src.get("longName"),
                    isin=isin,
                    ticker=ticker,
                    currency=src.get("currencyOfDenomination"),
                    qualityScore=record_meta.get("qualityScore"),
                    goldenAsOf=record_meta.get("goldenAsOf"),
                )
            )
        return UniverseListResponse(items=items, total=len(items))

    @router.patch("/{scope}/{golden_id}/status")
    def update_status(scope: str, golden_id: str, body: UniverseStatusUpdate) -> Dict[str, Any]:
        _require_client()
        _validate_scope(scope)
        _validate_status(body.status)
        try:
            update_universe_status(opensearch_client, scope, golden_id, body.status)
        except Exception as exc:  # noqa: BLE001 — OpenSearch can raise opensearchpy.NotFoundError, etc.
            # NotFoundError is the common case — map cleanly to 404.
            if exc.__class__.__name__ == "NotFoundError":
                raise HTTPException(status_code=404, detail=f"{scope}/{golden_id} not found") from exc
            raise
        return {"scope": scope, "goldenId": golden_id, "universeStatus": body.status}

    return router


def _split_identifiers(identifier_list: List[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    """Pull the first ISIN and ticker from an identifierList projection."""
    isin: Optional[str] = None
    ticker: Optional[str] = None
    for entry in identifier_list:
        kind = (entry.get("type") or "").lower()
        if kind == "isin" and isin is None:
            isin = entry.get("identifier")
        elif kind == "tickersymbol" and ticker is None:
            ticker = entry.get("identifier")
    return isin, ticker
