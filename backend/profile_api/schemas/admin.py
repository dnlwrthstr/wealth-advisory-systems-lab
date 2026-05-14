"""Admin API schemas for questionnaire and scoring configuration."""

from typing import Any

from pydantic import BaseModel, Field

from profiling import InstrumentExperienceLevel, InstrumentType, KnowledgeLevel, RiskLevel


class InstrumentKnowledgePayload(BaseModel):
    equities: InstrumentExperienceLevel = "none"
    bonds: InstrumentExperienceLevel = "none"
    funds_etfs: InstrumentExperienceLevel = "basic"
    derivatives: InstrumentExperienceLevel = "none"
    structured_products: InstrumentExperienceLevel = "none"


class AnswerOptionPayload(BaseModel):
    value: Any
    label: str
    score: int | None = None
    image_url: str | None = None


class SliderScalePayload(BaseModel):
    min: int | float
    max: int | float
    step: int | float = 1
    min_label: str | None = None
    max_label: str | None = None


class RepeatConfigPayload(BaseModel):
    enabled: bool = False
    context: str | None = None
    min_items: int = 0
    max_items: int | None = None


class NavigationMetadataPayload(BaseModel):
    display_order: int = 0
    section_id: str | None = None
    previous_label: str = "Back"
    next_label: str = "Continue"


class QuestionPayload(BaseModel):
    question_id: str
    prompt: str
    answer_type: str = Field(
        pattern="^(boolean|single_choice|multiple_choice|slider|text|image_choice|image_upload)$"
    )
    target_signal: str | None = Field(
        default=None,
        pattern="^(risk_willingness|knowledge|horizon|liquidity_pressure|obligation)$",
    )
    required: bool = True
    options: list[AnswerOptionPayload] = Field(default_factory=list)
    ontology_path: str | None = None
    scale: SliderScalePayload | None = None
    max_length: int | None = None


class EdgeConditionPayload(BaseModel):
    question_id: str
    operator: str = Field(pattern="^(equals|not_equals|in|not_in|exists)$")
    value: Any = None


class GraphNodePayload(BaseModel):
    node_id: str
    kind: str = Field(pattern="^(section|question|review|terminal)$")
    question: QuestionPayload | None = None
    label: str | None = None
    repeat: RepeatConfigPayload | None = None
    navigation: NavigationMetadataPayload = Field(default_factory=NavigationMetadataPayload)


class GraphEdgePayload(BaseModel):
    from_node_id: str
    to_node_id: str
    condition: EdgeConditionPayload | None = None


class QuestionnairePayload(BaseModel):
    questionnaire_id: str
    version: str
    questions: list[QuestionPayload] = Field(default_factory=list)
    entry_node_id: str | None = None
    nodes: list[GraphNodePayload] = Field(default_factory=list)
    edges: list[GraphEdgePayload] = Field(default_factory=list)
    applies_to_segments: list[str] = Field(default_factory=list)


class ClientSegmentPayload(BaseModel):
    segment_id: str
    label: str
    description: str = ""
    minimum_liquid_net_worth: float = Field(default=0, ge=0)
    default_questionnaire_id: str = "client_profile_v1"
    review_policy: str = Field(default="standard", pattern="^(standard|enhanced|specialist)$")
    enabled: bool = True


class AnswerSetPayload(BaseModel):
    client_id: str
    answers: dict[str, Any]
    repeat_context: str | None = None
    repeat_instance_id: str | None = None


class FinancialContextPayload(BaseModel):
    age: int = Field(default=42, ge=0)
    annual_income: float = Field(default=180_000, ge=0)
    liquid_net_worth: float = Field(default=750_000, gt=0)
    restrictions: list[str] = Field(default_factory=list)


class ProductGatePayload(BaseModel):
    product_id: str = "P-204"
    name: str = "Global Multi-Asset Fund"
    risk_level: RiskLevel = "medium"
    required_knowledge: KnowledgeLevel = "basic"
    daily_liquidity: bool = True
    instrument_type: InstrumentType = "funds_etfs"
    minimum_instrument_experience: InstrumentExperienceLevel = "basic"


class ProcessAnswersRequest(BaseModel):
    answer_set: AnswerSetPayload
    financial_context: FinancialContextPayload = Field(default_factory=FinancialContextPayload)
    product: ProductGatePayload | None = None


class ScoreContributionPayload(BaseModel):
    question_id: str
    signal: str
    answer: Any
    score: int
    ontology_path: str | None = None


class ProfileScoresPayload(BaseModel):
    risk_willingness_score: float
    knowledge_score: float
    horizon_score: int
    liquidity_pressure_score: int
    obligation_score: int
    contributions: list[ScoreContributionPayload]


class ClientProfileResultPayload(BaseModel):
    client_id: str
    age: int
    annual_income: float
    liquid_net_worth: float
    investment_horizon_years: int
    liquidity_need_12m: float
    risk_tolerance: RiskLevel
    investment_knowledge: KnowledgeLevel
    instrument_knowledge: InstrumentKnowledgePayload
    has_dependents: bool
    restrictions: list[str]


class StrategyProfilePayload(BaseModel):
    strategy: str
    risk_profile_category: str
    risk_capacity: RiskLevel
    combined_risk_profile: RiskLevel
    liquidity_ratio: float
    suitability_envelope: dict[str, object]


class GateDecisionPayload(BaseModel):
    gate_id: str
    gate_type: str
    severity: str
    passed: bool
    message: str
    ontology_path: str | None = None


class ProcessAnswersResponse(BaseModel):
    processing_run_id: int | None = None
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    questionnaire_id: str
    questionnaire_version: str
    scores: ProfileScoresPayload | None = None
    profile: ClientProfileResultPayload | None = None
    strategy_profile: StrategyProfilePayload | None = None
    gates: list[GateDecisionPayload] = Field(default_factory=list)
    passed: bool | None = None
    requires_review: bool | None = None


class LatestClientProfileResponse(BaseModel):
    """Latest stored profiling result for a client, sourced from the audit trail."""

    processing_run_id: int
    client_id: str
    questionnaire_id: str
    questionnaire_version: str
    profile: dict | None = None
    strategy_profile: dict | None = None
    gates: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    valid: bool
    processed_at: str
