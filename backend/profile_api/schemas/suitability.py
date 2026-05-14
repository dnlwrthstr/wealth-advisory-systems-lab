"""Request and response schemas for suitability checks."""

from pydantic import BaseModel, Field

from profiling import InstrumentExperienceLevel, InstrumentType, KnowledgeLevel, RiskLevel


class InstrumentKnowledgePayload(BaseModel):
    equities: InstrumentExperienceLevel = "none"
    bonds: InstrumentExperienceLevel = "none"
    funds_etfs: InstrumentExperienceLevel = "basic"
    derivatives: InstrumentExperienceLevel = "none"
    structured_products: InstrumentExperienceLevel = "none"


class ClientProfilePayload(BaseModel):
    client_id: str = "C-1001"
    age: int = Field(default=42, ge=0)
    annual_income: float = Field(default=180_000, ge=0)
    liquid_net_worth: float = Field(default=750_000, gt=0)
    investment_horizon_years: int = Field(default=12, ge=0)
    liquidity_need_12m: float = Field(default=60_000, ge=0)
    risk_tolerance: RiskLevel = "medium"
    investment_knowledge: KnowledgeLevel = "intermediate"
    instrument_knowledge: InstrumentKnowledgePayload = Field(default_factory=InstrumentKnowledgePayload)
    has_dependents: bool = True
    restrictions: list[str] = Field(default_factory=lambda: ["no single-stock positions above 10%"])


class ProductProfilePayload(BaseModel):
    product_id: str = "P-204"
    name: str = "Global Multi-Asset Fund"
    risk_level: RiskLevel = "medium"
    required_knowledge: KnowledgeLevel = "basic"
    daily_liquidity: bool = True
    instrument_type: InstrumentType = "funds_etfs"
    minimum_instrument_experience: InstrumentExperienceLevel = "basic"


class SuitabilityRequest(BaseModel):
    client: ClientProfilePayload = Field(default_factory=ClientProfilePayload)
    product: ProductProfilePayload = Field(default_factory=ProductProfilePayload)


class SuitabilityResponse(BaseModel):
    client_id: str
    product_id: str
    liquidity_ratio: float
    risk_capacity: RiskLevel
    combined_risk_profile: RiskLevel
    suitable: bool
    flags: list[str]
