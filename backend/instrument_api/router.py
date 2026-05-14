"""HTTP routes for the instrument API."""

from fastapi import APIRouter, HTTPException, Query
from instruments.service import InstrumentService


def build_router(service: InstrumentService) -> APIRouter:
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
