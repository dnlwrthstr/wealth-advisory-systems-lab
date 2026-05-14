"""Reference product profile models for suitability checks."""

from dataclasses import dataclass

from profiling import InstrumentExperienceLevel, InstrumentType, KnowledgeLevel, RiskLevel


@dataclass(frozen=True)
class ProductProfile:
    """Product attributes used by advisory suitability rules."""

    product_id: str
    name: str
    risk_level: RiskLevel
    required_knowledge: KnowledgeLevel
    daily_liquidity: bool
    instrument_type: InstrumentType = "funds_etfs"
    minimum_instrument_experience: InstrumentExperienceLevel = "basic"
