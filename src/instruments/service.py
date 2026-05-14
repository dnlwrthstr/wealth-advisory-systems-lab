"""Instrument service — search and retrieve instruments from the universe."""

from __future__ import annotations
from .schemas import Instrument, InstrumentSearchResult
from .store import InstrumentStore


class InstrumentService:
    def __init__(self, store: InstrumentStore):
        self._store = store

    def search(
        self,
        query: str = "",
        type_filter: str | None = None,
        currency: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InstrumentSearchResult:
        items, total = self._store.search(
            query=query,
            type_filter=type_filter,
            currency=currency,
            limit=limit,
            offset=offset,
        )
        return InstrumentSearchResult(
            items=items,
            total=total,
            query=query,
            type_filter=type_filter,
        )

    def get(self, instrument_id: str) -> Instrument | None:
        return self._store.get_by_id(instrument_id)

    def get_by_isin(self, isin: str) -> Instrument | None:
        return self._store.get_by_isin(isin)

    def list_types(self) -> list[str]:
        return self._store.list_types()
