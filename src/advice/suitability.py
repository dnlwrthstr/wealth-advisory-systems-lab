"""Suitability checks for advisory recommendations."""

from profiling import ClientProfile, InstrumentExperienceLevel, RiskLevel, combined_risk_profile, liquidity_ratio

from .products import ProductProfile

RISK_ORDER: dict[RiskLevel, int] = {"low": 0, "medium": 1, "high": 2}
INSTRUMENT_EXPERIENCE_ORDER: dict[InstrumentExperienceLevel, int] = {
    "none": 0,
    "basic": 1,
    "experienced": 2,
    "advanced": 3,
}


def suitability_flags(profile: ClientProfile, product: ProductProfile) -> list[str]:
    """Return policy reasons that make a product unsuitable for a client."""

    flags = []

    if RISK_ORDER[product.risk_level] > RISK_ORDER[combined_risk_profile(profile)]:
        flags.append("product risk exceeds combined client risk profile")

    client_experience = profile.instrument_knowledge.level_for(product.instrument_type)
    if (
        INSTRUMENT_EXPERIENCE_ORDER[product.minimum_instrument_experience]
        > INSTRUMENT_EXPERIENCE_ORDER[client_experience]
    ):
        flags.append(
            f"client experience with {product.instrument_type} may be insufficient"
        )

    if liquidity_ratio(profile) > 0.10 and not product.daily_liquidity:
        flags.append("client has material near-term liquidity needs")

    return flags


def is_suitable(profile: ClientProfile, product: ProductProfile) -> bool:
    """Return whether the product passes the reference suitability checks."""

    return not suitability_flags(profile, product)
