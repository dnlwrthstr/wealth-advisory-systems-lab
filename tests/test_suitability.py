from advice import ProductProfile, is_suitable, suitability_flags
from profiling import ClientProfile


def client(**overrides):
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


def product(**overrides):
    values = {
        "product_id": "P-204",
        "name": "Global Multi-Asset Fund",
        "risk_level": "medium",
        "required_knowledge": "basic",
        "daily_liquidity": True,
    }
    values.update(overrides)
    return ProductProfile(**values)


def test_medium_daily_liquid_product_is_suitable_for_reference_client():
    assert suitability_flags(client(), product()) == []
    assert is_suitable(client(), product())


def test_high_risk_product_is_flagged_for_medium_combined_profile():
    assert suitability_flags(client(), product(risk_level="high")) == [
        "product risk exceeds combined client risk profile"
    ]


def test_product_requiring_advanced_instrument_experience_is_flagged():
    assert suitability_flags(client(), product(minimum_instrument_experience="advanced")) == [
        "client experience with funds_etfs may be insufficient"
    ]


def test_illiquid_product_is_flagged_when_near_term_liquidity_need_is_material():
    flags = suitability_flags(
        client(liquidity_need_12m=100_000),
        product(daily_liquidity=False),
    )

    assert "client has material near-term liquidity needs" in flags
    assert not is_suitable(client(liquidity_need_12m=100_000), product(daily_liquidity=False))
