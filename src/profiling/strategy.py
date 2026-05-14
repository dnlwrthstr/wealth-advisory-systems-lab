"""Strategy and gate derivation from a client profile."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from .models import ClientProfile, InstrumentExperienceLevel, InstrumentType, KnowledgeLevel, RiskLevel
from .signals import combined_risk_profile, liquidity_ratio, risk_capacity

StrategyLevel = Literal["capital_preservation", "income", "balanced_growth", "capital_growth"]
RiskProfileCategory = Literal["defensive", "conservative", "balanced", "growth"]
GateSeverity = Literal["block", "review"]

RISK_ORDER: dict[RiskLevel, int] = {"low": 0, "medium": 1, "high": 2}
KNOWLEDGE_ORDER: dict[KnowledgeLevel, int] = {
    "basic": 0,
    "intermediate": 1,
    "advanced": 2,
}
INSTRUMENT_EXPERIENCE_ORDER: dict[InstrumentExperienceLevel, int] = {
    "none": 0,
    "basic": 1,
    "experienced": 2,
    "advanced": 3,
}


class GateProduct(Protocol):
    risk_level: RiskLevel
    required_knowledge: KnowledgeLevel
    daily_liquidity: bool
    instrument_type: InstrumentType
    minimum_instrument_experience: InstrumentExperienceLevel


@dataclass(frozen=True)
class GateDecision:
    gate_id: str
    gate_type: str
    severity: GateSeverity
    passed: bool
    message: str
    ontology_path: str | None = None


@dataclass(frozen=True)
class StrategyProfile:
    strategy: StrategyLevel
    risk_profile_category: RiskProfileCategory
    risk_capacity: RiskLevel
    combined_risk_profile: RiskLevel
    liquidity_ratio: float
    suitability_envelope: dict[str, object]


@dataclass(frozen=True)
class StrategyAssessment:
    strategy_profile: StrategyProfile
    gates: list[GateDecision] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(gate.passed or gate.severity == "review" for gate in self.gates)

    @property
    def requires_review(self) -> bool:
        return any(not gate.passed and gate.severity == "review" for gate in self.gates)


def assess_strategy_and_gates(
    profile: ClientProfile,
    *,
    product: GateProduct | None = None,
    warnings: list[str] | None = None,
) -> StrategyAssessment:
    combined = combined_risk_profile(profile)
    strategy_profile = StrategyProfile(
        strategy=_strategy_from_combined_risk(combined),
        risk_profile_category=_risk_profile_category(combined, profile),
        risk_capacity=risk_capacity(profile),
        combined_risk_profile=combined,
        liquidity_ratio=round(liquidity_ratio(profile), 3),
        suitability_envelope=_suitability_envelope(combined),
    )
    gates: list[GateDecision] = []

    if product is not None:
        gates.extend(_product_gates(profile, product, combined))

    for warning in warnings or []:
        gates.append(
            GateDecision(
                gate_id="questionnaire_warning_review",
                gate_type="review",
                severity="review",
                passed=False,
                message=warning,
                ontology_path="client_profile.audit_trail",
            )
        )

    return StrategyAssessment(strategy_profile=strategy_profile, gates=gates)


def _strategy_from_combined_risk(risk_level: RiskLevel) -> StrategyLevel:
    return {
        "low": "capital_preservation",
        "medium": "balanced_growth",
        "high": "capital_growth",
    }[risk_level]


def _risk_profile_category(
    risk_level: RiskLevel,
    profile: ClientProfile,
) -> RiskProfileCategory:
    if risk_level == "low":
        if profile.investment_horizon_years < 3 or liquidity_ratio(profile) > 0.25:
            return "defensive"
        return "conservative"
    if risk_level == "medium":
        return "balanced"
    return "growth"


def _suitability_envelope(risk_level: RiskLevel) -> dict[str, object]:
    envelopes: dict[RiskLevel, dict[str, object]] = {
        "low": {
            "allowed_asset_classes": ["cash", "bonds", "funds"],
            "excluded_instruments": ["alternatives", "derivatives", "leverage"],
            "max_leverage": 1.0,
            "equity_exposure_range": {"min_percent": 0, "max_percent": 30},
        },
        "medium": {
            "allowed_asset_classes": ["cash", "bonds", "equities", "funds"],
            "excluded_instruments": ["uncovered_derivatives", "leverage"],
            "max_leverage": 1.0,
            "equity_exposure_range": {"min_percent": 30, "max_percent": 65},
        },
        "high": {
            "allowed_asset_classes": ["cash", "bonds", "equities", "funds", "alternatives"],
            "excluded_instruments": ["uncovered_derivatives"],
            "max_leverage": 1.0,
            "equity_exposure_range": {"min_percent": 60, "max_percent": 100},
        },
    }
    return envelopes[risk_level]


def _product_gates(
    profile: ClientProfile,
    product: GateProduct,
    combined: RiskLevel,
) -> list[GateDecision]:
    gates: list[GateDecision] = []

    gates.append(
        GateDecision(
            gate_id="product_risk_within_profile",
            gate_type="suitability",
            severity="block",
            passed=RISK_ORDER[product.risk_level] <= RISK_ORDER[combined],
            message="product risk must not exceed combined client risk profile",
            ontology_path="client_profile.scoring_summary.final_risk_score",
        )
    )
    gates.append(
        GateDecision(
            gate_id="instrument_experience_sufficient",
            gate_type="appropriateness",
            severity="block",
            passed=_instrument_experience_sufficient(profile, product),
            message=(
                f"client experience with {product.instrument_type} must meet "
                f"{product.minimum_instrument_experience} requirement"
            ),
            ontology_path="client_profile.knowledge_and_experience.appropriateness_gate",
        )
    )
    gates.append(
        GateDecision(
            gate_id="liquidity_requirement_met",
            gate_type="risk_capacity",
            severity="block",
            passed=liquidity_ratio(profile) <= 0.10 or product.daily_liquidity,
            message="material near-term liquidity need requires daily liquidity",
            ontology_path="client_profile.financial_situation.liquidity_needs",
        )
    )

    return gates


def _instrument_experience_sufficient(
    profile: ClientProfile,
    product: GateProduct,
) -> bool:
    client_level = profile.instrument_knowledge.level_for(product.instrument_type)
    return (
        INSTRUMENT_EXPERIENCE_ORDER[client_level]
        >= INSTRUMENT_EXPERIENCE_ORDER[product.minimum_instrument_experience]
    )
