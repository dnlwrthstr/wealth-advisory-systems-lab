"""Hand-rolled in-memory / parquet schemas for the instrument universe.

Three layers:
  InstrumentSeed  — identifiers extracted once from source data (CSV)
  EquityMaster    — instrument master fetched from internet (slow-changing)
  BondMaster      — bond master fetched from internet (slow-changing)
  MarketSnapshot  — time-stamped market data, refreshed independently

These dataclasses are the working-memory shape used by the parquet store
(`ParquetUniverseStore`) and the ingestion scripts. The ontology-driven
pydantic models in `universe.models` (auto-generated from `ontology/`) are
the canonical wire/OpenSearch shape — the two coexist until the pipeline
adopts the gold layer end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class InstrumentSeed:
    """Identifiers-only record extracted from source data. Immutable once written."""
    isin: str
    valor_nr: str
    instrument_type: str        # OpenWealth FinancialInstrumentType
    name: str                   # raw name from source, cleaned
    ticker: str                 # exchange ticker from source (not Yahoo format)
    nominal_currency: str       # denomination currency from source


@dataclass
class EquityMaster:
    """Instrument master for equities — fetched from internet, slow-changing."""
    isin: str
    valor_nr: str
    instrument_type: str = "equity"

    # Identity
    name: str = ""
    ticker: str = ""
    exchange_mic: str = ""      # ISO 10383 MIC, e.g. XVTX, XNAS, XLON

    # Classification (GICS)
    sector: str = ""
    industry: str = ""

    # Geography
    country: str = ""           # ISO 3166-1 alpha-2 of issuer/domicile
    nominal_currency: str = ""

    # Issuer
    issuer_name: str = ""
    description: str = ""       # max 500 chars

    # ESG
    esg_label: str = ""         # e.g. "AAA", "BB" (MSCI ESG)

    # Provenance
    source: str = ""            # "yfinance" | "synthetic"
    fetched_at: str = ""        # ISO datetime


@dataclass
class BondMaster:
    """Instrument master for bonds (simpleBond, floater, convertibleBond, moneyMarket)."""
    isin: str
    valor_nr: str
    instrument_type: str = "simpleBond"

    # Identity
    name: str = ""

    # Issuer
    issuer_name: str = ""
    issuer_country: str = ""    # ISO 3166-1 alpha-2
    sector: str = ""

    # Terms
    nominal_currency: str = ""
    face_value: float = 1000.0
    coupon_rate: Optional[float] = None     # annual rate as fraction, e.g. 0.03 = 3%
    interest_type: str = "fixed"            # "fixed" | "floating"
    maturity_date: str = ""                 # ISO date
    is_callable: bool = False
    seniority: str = "senior_unsecured"     # "senior_secured" | "senior_unsecured" | "subordinated"

    # Credit
    rating: str = ""                        # S&P notation: AAA, AA+, … D
    rating_agency: str = "S&P"

    # Provenance
    source: str = ""
    fetched_at: str = ""


@dataclass
class MarketSnapshot:
    """Time-stamped market data snapshot — applies to any instrument type."""
    isin: str
    instrument_type: str
    as_of: str                              # ISO datetime of snapshot

    # Universal
    last_price: Optional[float] = None
    price_currency: str = ""

    # Equity / Fund
    market_cap: Optional[float] = None
    shares_outstanding: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None  # fraction, e.g. 0.025 = 2.5%
    beta: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None

    # Bond
    yield_to_maturity: Optional[float] = None
    duration: Optional[float] = None        # modified duration in years
    spread_bps: Optional[float] = None      # Z-spread over benchmark, basis points

    # Provenance
    source: str = ""                        # "yfinance" | "synthetic"
