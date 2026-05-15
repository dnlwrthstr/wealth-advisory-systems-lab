"""HTTP routes for the instrument API."""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from instruments.search_store import OpenSearchInstrumentSearch
from instruments.service import InstrumentService


def build_router(
    service: InstrumentService,
    search_store: Optional[OpenSearchInstrumentSearch] = None,
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
