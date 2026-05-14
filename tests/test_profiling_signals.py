import pytest

from profiling import ClientProfile, combined_risk_profile, liquidity_ratio, risk_capacity


def profile(**overrides):
    values = {
        "client_id": "C-1001",
        "age": 42,
        "annual_income": 180_000,
        "liquid_net_worth": 750_000,
        "investment_horizon_years": 12,
        "liquidity_need_12m": 60_000,
        "risk_tolerance": "medium",
        "investment_knowledge": "intermediate",
        "has_dependents": True,
    }
    values.update(overrides)
    return ClientProfile(**values)


def test_liquidity_ratio_uses_liquid_net_worth():
    assert liquidity_ratio(profile()) == pytest.approx(0.08)


def test_liquidity_ratio_requires_positive_liquid_net_worth():
    with pytest.raises(ValueError, match="liquid_net_worth must be positive"):
        liquidity_ratio(profile(liquid_net_worth=0))


def test_risk_capacity_is_low_for_short_horizon():
    assert risk_capacity(profile(investment_horizon_years=2)) == "low"


def test_risk_capacity_is_medium_when_dependents_reduce_capacity():
    assert risk_capacity(profile(has_dependents=True, investment_horizon_years=12)) == "medium"


def test_combined_risk_profile_uses_more_conservative_level():
    assert combined_risk_profile(profile(risk_tolerance="high", has_dependents=True)) == "medium"

