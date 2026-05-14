from advice import ProductProfile
from profiling import ClientProfile, assess_strategy_and_gates


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


def test_strategy_maps_combined_risk_to_balanced_for_reference_client():
    assessment = assess_strategy_and_gates(profile())

    assert assessment.strategy_profile.strategy == "balanced_growth"
    assert assessment.strategy_profile.risk_profile_category == "balanced"
    assert assessment.strategy_profile.risk_capacity == "medium"
    assert assessment.strategy_profile.combined_risk_profile == "medium"
    assert assessment.strategy_profile.liquidity_ratio == 0.08
    assert assessment.strategy_profile.suitability_envelope["allowed_asset_classes"] == [
        "cash",
        "bonds",
        "equities",
        "funds",
    ]
    assert assessment.passed
    assert not assessment.requires_review


def test_product_risk_gate_blocks_product_above_combined_profile():
    assessment = assess_strategy_and_gates(profile(), product=product(risk_level="high"))
    risk_gate = next(gate for gate in assessment.gates if gate.gate_id == "product_risk_within_profile")

    assert not risk_gate.passed
    assert risk_gate.gate_type == "suitability"
    assert risk_gate.severity == "block"
    assert risk_gate.ontology_path == "client_profile.scoring_summary.final_risk_score"
    assert not assessment.passed


def test_instrument_experience_gate_blocks_unexperienced_instrument():
    assessment = assess_strategy_and_gates(
        profile(),
        product=product(
            instrument_type="derivatives",
            minimum_instrument_experience="basic",
        ),
    )
    gate = next(
        gate for gate in assessment.gates if gate.gate_id == "instrument_experience_sufficient"
    )

    assert not gate.passed
    assert gate.gate_type == "appropriateness"
    assert gate.ontology_path == "client_profile.knowledge_and_experience.appropriateness_gate"
    assert not assessment.passed


def test_questionnaire_warning_requires_review_without_blocking():
    assessment = assess_strategy_and_gates(profile(), warnings=["answers require review"])
    review_gate = assessment.gates[0]

    assert review_gate.gate_id == "questionnaire_warning_review"
    assert review_gate.gate_type == "review"
    assert review_gate.severity == "review"
    assert review_gate.ontology_path == "client_profile.audit_trail"
    assert not review_gate.passed
    assert assessment.passed
    assert assessment.requires_review
