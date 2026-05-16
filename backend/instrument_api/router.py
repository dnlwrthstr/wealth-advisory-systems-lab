"""HTTP routes for the instrument API."""

from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from instruments.search_store import OpenSearchInstrumentSearch
from instruments.service import InstrumentService
from pipeline.agentic import assemble_and_persist, assemble_golden


class _IdentifierIn(BaseModel):
    kind: str = Field(..., description="Identifier kind, e.g. 'isin', 'ticker', 'lei'.")
    value: str = Field(..., description="Identifier value (not normalised).")


class AssembleRequest(BaseModel):
    scope: str = Field(..., description="Golden-record scope: 'equity', 'bond', 'fund', 'issuer'.")
    identifier: _IdentifierIn
    budget: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Max planner iterations (default 10).",
    )
    persist: bool = Field(
        default=False,
        description=(
            "When true, write the assembled record to pms_golden_{scope} and, "
            "for instrument scopes, also assemble + persist any IssuerGolden "
            "records derivable from LEIs embedded in the result."
        ),
    )
    invoke_llm_skills: bool = Field(
        default=False,
        description=(
            "When true, raise the planner's cost cap to include llm_skill "
            "sources (e.g. fund_factsheet_skill via the Claude Agent SDK). "
            "Slow and costs money — opt in per request."
        ),
    )


class _ChainedIssuer(BaseModel):
    lei: str
    golden_id: Optional[str]
    quality_score: float
    remaining_gaps: list[str]


class AssembleResponse(BaseModel):
    scope: str
    identifier: Dict[str, str]
    record: Dict[str, Any]
    quality_score: float
    remaining_gaps: list[str]
    provenance: list[Dict[str, Any]]
    trace: Dict[str, Any]
    run_id: str
    persisted: bool = False
    chained_issuers: list[_ChainedIssuer] = Field(default_factory=list)


def build_router(
    service: InstrumentService,
    search_store: Optional[OpenSearchInstrumentSearch] = None,
    opensearch_client: Optional[Any] = None,
) -> APIRouter:
    router = APIRouter(prefix="/instruments", tags=["instruments"])

    @router.get("")
    def search_instruments(
        q: str = Query(default="", description="Free-text search: name, ISIN, ticker"),
        type: str | None = Query(default=None, description="OpenWealth instrument type filter"),
        currency: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict:
        result = service.search(
            query=q,
            type_filter=type,
            currency=currency,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [_to_dict(i) for i in result.items],
            "total": result.total,
            "query": result.query,
            "type_filter": result.type_filter,
        }

    @router.get("/types")
    def list_types() -> list[str]:
        return service.list_types()

    @router.get("/search")
    def search_helper_index(
        identifier: str = Query(default="", description="ISIN / ticker / valor / CUSIP fragment"),
        name: str = Query(default="", description="Short or long name fragment"),
        issuer: str = Query(default="", description="Issuer / umbrella / promoter legal name fragment"),
        type: str | None = Query(default=None, description="OpenWealth instrument type (or 'all')"),
        currency: str | None = Query(default=None),
        country: str | None = Query(default=None),
        limit: int = Query(default=25, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict:
        if search_store is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Search helper not configured. Set OPENSEARCH_URL and ensure "
                    "the pms_golden_instrumentsearch index exists "
                    "(pipeline.gold.search_index_build)."
                ),
            )
        filters = {"currency": currency or "", "country": country or ""}
        result = search_store.search(
            identifier=identifier,
            name=name,
            issuer=issuer,
            ow_type=type,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [asdict(hit) for hit in result["items"]],
            "total": result["total"],
            "query": {
                "identifier": identifier,
                "name": name,
                "issuer": issuer,
                "type": type,
                "currency": currency,
                "country": country,
            },
        }

    @router.get("/document/{scope}/{document_id}")
    def get_document(scope: str, document_id: str) -> dict:
        if search_store is None:
            raise HTTPException(
                status_code=503,
                detail="Search store not configured; OPENSEARCH_URL is required.",
            )
        source = search_store.fetch_document(scope, document_id)
        if source is None:
            raise HTTPException(status_code=404, detail="document not found")
        return {"scope": scope, "documentId": document_id, "source": source}

    @router.post("/assemble", response_model=AssembleResponse)
    def assemble(body: AssembleRequest) -> AssembleResponse:
        """Agentic assembly — build a golden record from an identifier.

        Reads the per-scope source registry, picks sources to call by
        gap coverage, merges results with provenance, and returns the
        composed record. When `persist=true`, also writes the record to
        OpenSearch and chains into issuer assembly for every embedded LEI.
        """
        identifier = {"kind": body.identifier.kind, "value": body.identifier.value}
        budget = body.budget or 10
        max_cost_class = "llm_skill" if body.invoke_llm_skills else "web_fetch"

        if body.persist:
            if opensearch_client is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Persist requested but OpenSearch is not configured. "
                        "Set OPENSEARCH_URL on instrument-api."
                    ),
                )
            try:
                outcome = assemble_and_persist(
                    client=opensearch_client,
                    scope=body.scope,
                    identifier=identifier,
                    budget=budget,
                    max_cost_class=max_cost_class,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            result = outcome["primary"]
            chained = outcome["chained_issuers"]
            persisted = True
        else:
            try:
                result = assemble_golden(
                    scope=body.scope,
                    identifier=identifier,
                    budget=budget,
                    max_cost_class=max_cost_class,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            chained = []
            persisted = False

        return AssembleResponse(
            scope=result.scope,
            identifier=result.identifier,
            record=result.record,
            quality_score=result.quality_score,
            remaining_gaps=result.remaining_gaps,
            provenance=result.provenance,
            trace={
                "iterations": result.trace.iterations,
                "invocations": result.trace.invocations,
                "stopped_reason": result.trace.stopped_reason,
            },
            run_id=result.run_id,
            persisted=persisted,
            chained_issuers=chained,
        )

    @router.get("/{instrument_id}")
    def get_instrument(instrument_id: str) -> dict:
        # Accept both internal ID and ISIN
        instr = service.get(instrument_id) or service.get_by_isin(instrument_id)
        if instr is None:
            raise HTTPException(status_code=404, detail="instrument not found")
        return _to_dict(instr)

    return router


def _to_dict(i) -> dict:
    return {
        "id": i.id,
        "isin": i.isin,
        "name": i.name,
        "shortName": i.short_name,
        "type": i.type,
        "currency": i.currency,
        "price": i.price,
        "exchange": i.exchange,
        "country": i.country,
        "sector": i.sector,
        "couponPct": i.coupon_pct,
        "maturityDate": i.maturity_date,
        "yieldPct": i.yield_pct,
        "description": i.description,
    }
