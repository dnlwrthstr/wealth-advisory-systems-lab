"""Reference models for advisory client profiling."""

from dataclasses import dataclass, field
from typing import Literal

RiskLevel = Literal["low", "medium", "high"]
KnowledgeLevel = Literal["basic", "intermediate", "advanced"]
InstrumentExperienceLevel = Literal["none", "basic", "experienced", "advanced"]
InstrumentType = Literal[
    "equities",
    "bonds",
    "funds_etfs",
    "derivatives",
    "structured_products",
]


@dataclass(frozen=True)
class InstrumentKnowledge:
    """Knowledge and experience by instrument universe."""

    equities: InstrumentExperienceLevel = "none"
    bonds: InstrumentExperienceLevel = "none"
    funds_etfs: InstrumentExperienceLevel = "basic"
    derivatives: InstrumentExperienceLevel = "none"
    structured_products: InstrumentExperienceLevel = "none"

    def level_for(self, instrument_type: InstrumentType) -> InstrumentExperienceLevel:
        return getattr(self, instrument_type)


@dataclass(frozen=True)
class ClientProfile:
    """Client context needed for suitability and advisory monitoring."""

    client_id: str
    age: int
    annual_income: float
    liquid_net_worth: float
    investment_horizon_years: int
    liquidity_need_12m: float
    risk_tolerance: RiskLevel
    investment_knowledge: KnowledgeLevel
    instrument_knowledge: InstrumentKnowledge = field(default_factory=InstrumentKnowledge)
    has_dependents: bool = False
    restrictions: list[str] = field(default_factory=list)
