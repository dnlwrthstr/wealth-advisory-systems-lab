"""Derived advisory signals from client profile data."""

from .models import ClientProfile, RiskLevel

RISK_ORDER: dict[RiskLevel, int] = {"low": 0, "medium": 1, "high": 2}
RISK_BY_SCORE: dict[int, RiskLevel] = {value: key for key, value in RISK_ORDER.items()}


def liquidity_ratio(profile: ClientProfile) -> float:
    """Return near-term liquidity need as a share of liquid net worth."""

    if profile.liquid_net_worth <= 0:
        raise ValueError("liquid_net_worth must be positive")
    return profile.liquidity_need_12m / profile.liquid_net_worth


def risk_capacity(profile: ClientProfile) -> RiskLevel:
    """Infer financial capacity to take risk from horizon and liquidity needs."""

    ratio = liquidity_ratio(profile)

    if profile.investment_horizon_years < 3 or ratio > 0.25:
        return "low"
    if profile.investment_horizon_years < 7 or ratio > 0.10 or profile.has_dependents:
        return "medium"
    return "high"


def combined_risk_profile(profile: ClientProfile) -> RiskLevel:
    """Combine willingness and capacity by taking the more conservative level."""

    tolerance = RISK_ORDER[profile.risk_tolerance]
    capacity = RISK_ORDER[risk_capacity(profile)]
    return RISK_BY_SCORE[min(tolerance, capacity)]

