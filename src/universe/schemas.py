"""Golden record schemas for the instrument universe."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EquityRecord:
    """Golden record for a single equity instrument."""
    isin: str
    valor_nr: str
    instrument_type: str = "equity"

    # Identifiers & names
    name: str = ""
    short_name: str = ""
    ticker: str = ""
    exchange_mic: str = ""          # ISO 10383 MIC, e.g. XVTX, XNAS, XLON

    # Classification
    sector: str = ""                # GICS sector
    industry: str = ""              # GICS industry group
    country: str = ""               # ISO 3166-1 alpha-2 issuer country
    nominal_currency: str = ""      # trading currency

    # Issuer
    issuer_name: str = ""
    description: str = ""

    # Market data (snapshot at ingestion time)
    last_price: Optional[float] = None
    price_currency: str = ""
    market_cap: Optional[float] = None          # in price_currency
    shares_outstanding: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None      # as fraction, e.g. 0.025 = 2.5%
    beta: Optional[float] = None

    # ESG
    esg_score: Optional[float] = None          # 0–100 scale
    esg_label: str = ""                        # e.g. "AAA", "BB"

    # Metadata
    fetched_at: str = ""                       # ISO datetime of last data pull
    source: str = "yfinance"


@dataclass
class BondRecord:
    """Golden record for a simple (fixed/floating) bond."""
    isin: str
    valor_nr: str
    instrument_type: str = "simpleBond"

    # Names
    name: str = ""
    short_name: str = ""

    # Issuer
    issuer_name: str = ""
    issuer_country: str = ""        # ISO 3166-1 alpha-2
    sector: str = ""

    # Terms
    nominal_currency: str = ""
    face_value: float = 1000.0
    coupon_rate: Optional[float] = None         # annual, as fraction, e.g. 0.03 = 3%
    interest_type: str = "fixed"               # "fixed" | "floating"
    maturity_date: str = ""                    # ISO date
    is_callable: bool = False
    seniority: str = "senior_unsecured"        # "senior_secured" | "senior_unsecured" | "subordinated"

    # Analytics (at ingestion time)
    duration: Optional[float] = None           # modified duration in years
    yield_to_maturity: Optional[float] = None  # as fraction
    last_price: Optional[float] = None         # % of face value, e.g. 99.5

    # Rating
    rating: str = ""                           # S&P notation: AAA, AA+, ... D
    rating_agency: str = "S&P"

    # Metadata
    fetched_at: str = ""
    source: str = "csv_seed"
