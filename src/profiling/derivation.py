"""Derive client profile fields from questionnaire scores."""

from dataclasses import dataclass, field

from .models import ClientProfile, InstrumentKnowledge, KnowledgeLevel, RiskLevel
from .scoring import ProfileScores


@dataclass(frozen=True)
class ProfileDerivation:
    profile: ClientProfile
    questionnaire_id: str
    questionnaire_version: str
    warnings: list[str] = field(default_factory=list)


def derive_client_profile(
    scores: ProfileScores,
    *,
    age: int = 42,
    annual_income: float = 180_000,
    liquid_net_worth: float = 750_000,
    restrictions: list[str] | None = None,
) -> ProfileDerivation:
    investment_knowledge = _knowledge_from_score(scores.knowledge_score)
    profile = ClientProfile(
        client_id=scores.client_id,
        age=age,
        annual_income=annual_income,
        liquid_net_worth=liquid_net_worth,
        investment_horizon_years=scores.horizon_score,
        liquidity_need_12m=scores.liquidity_pressure_score,
        risk_tolerance=_risk_tolerance_from_score(scores.risk_willingness_score),
        investment_knowledge=investment_knowledge,
        instrument_knowledge=_instrument_knowledge_from_level(investment_knowledge),
        has_dependents=scores.obligation_score > 0,
        restrictions=restrictions or [],
    )

    return ProfileDerivation(
        profile=profile,
        questionnaire_id=scores.questionnaire_id,
        questionnaire_version=scores.questionnaire_version,
        warnings=scores.warnings,
    )


def _risk_tolerance_from_score(score: float) -> RiskLevel:
    if score < 0.75:
        return "low"
    if score < 1.5:
        return "medium"
    return "high"


def _knowledge_from_score(score: float) -> KnowledgeLevel:
    if score < 0.75:
        return "basic"
    if score < 1.5:
        return "intermediate"
    return "advanced"


def _instrument_knowledge_from_level(level: KnowledgeLevel) -> InstrumentKnowledge:
    if level == "basic":
        return InstrumentKnowledge(funds_etfs="basic")
    if level == "intermediate":
        return InstrumentKnowledge(
            equities="basic",
            bonds="basic",
            funds_etfs="experienced",
        )
    return InstrumentKnowledge(
        equities="experienced",
        bonds="experienced",
        funds_etfs="experienced",
        derivatives="basic",
        structured_products="basic",
    )
