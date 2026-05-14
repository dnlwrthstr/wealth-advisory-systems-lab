"""In-memory instrument store — single source of truth for the instrument universe."""

from __future__ import annotations
from .schemas import Instrument


class InstrumentStore:
    def __init__(self, instruments: list):
        normalized = [_coerce(i) for i in instruments]
        self._by_id: dict[str, Instrument] = {i.id: i for i in normalized}
        self._by_isin: dict[str, Instrument] = {i.isin: i for i in normalized}
        self._all = normalized

    def get_by_id(self, instrument_id: str) -> Instrument | None:
        return self._by_id.get(instrument_id)

    def get_by_isin(self, isin: str) -> Instrument | None:
        return self._by_isin.get(isin)

    def search(
        self,
        query: str = "",
        type_filter: str | None = None,
        currency: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Instrument], int]:
        q = query.strip().lower()
        results = self._all

        if q:
            results = [
                i for i in results
                if q in i.name.lower()
                or q in i.isin.lower()
                or q in i.short_name.lower()
                or (i.sector and q in i.sector.lower())
                or (i.country and q in i.country.lower())
            ]

        if type_filter:
            results = [i for i in results if i.type == type_filter]

        if currency:
            results = [i for i in results if i.currency == currency]

        total = len(results)
        return results[offset: offset + limit], total

    def list_types(self) -> list[str]:
        return sorted({i.type for i in self._all})


def _coerce(item) -> Instrument:
    if isinstance(item, Instrument):
        return item
    return Instrument(
        id=item["id"],
        isin=item["isin"],
        name=item["name"],
        short_name=item["short_name"],
        type=item["type"],
        currency=item["currency"],
        price=item["price"],
        exchange=item.get("exchange"),
        country=item.get("country"),
        sector=item.get("sector"),
        coupon_pct=item.get("coupon_pct"),
        maturity_date=item.get("maturity_date"),
        yield_pct=item.get("yield_pct"),
        description=item.get("description", ""),
    )
