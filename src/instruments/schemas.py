"""Instrument universe schemas — OpenWealth-aligned but extended for a tradeable universe."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instrument:
    id: str                          # e.g. "EQ-001"
    isin: str
    name: str
    short_name: str
    type: str                        # OpenWealth FinancialInstrumentType value
    currency: str
    price: float
    exchange: str | None = None
    country: str | None = None
    sector: str | None = None
    coupon_pct: float | None = None  # bonds
    maturity_date: str | None = None # bonds
    yield_pct: float | None = None   # bonds / income
    description: str = ""


@dataclass
class InstrumentSearchResult:
    items: list[Instrument]
    total: int
    query: str
    type_filter: str | None
