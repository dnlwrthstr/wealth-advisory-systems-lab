import pytest

from profiling import (
    AnswerSet,
    derive_client_profile,
    example_questionnaire,
    score_answers,
    validate_answers,
)


def complete_answers(**overrides):
    answers = {
        "loss_reaction": "hold",
        "portfolio_decline_comfort": "somewhat_comfortable",
        "investment_experience": "funds_and_etfs",
        "product_knowledge": "general",
        "horizon": "7_to_15_years",
        "liquidity_need": "moderate",
        "has_dependents": True,
    }
    answers.update(overrides)
    return AnswerSet(client_id="C-1001", answers=answers)


def test_example_questionnaire_contains_stable_required_question_ids():
    questionnaire = example_questionnaire()

    assert set(questionnaire.question_by_id()) == {
        "loss_reaction",
        "portfolio_decline_comfort",
        "investment_experience",
        "product_knowledge",
        "horizon",
        "liquidity_need",
        "has_dependents",
    }


def test_validate_answers_accepts_complete_answer_set():
    result = validate_answers(example_questionnaire(), complete_answers())

    assert result.valid
    assert result.errors == []
    assert result.warnings == []


def test_validate_answers_reports_missing_required_answer():
    answer_set = complete_answers()
    answer_set.answers.pop("horizon")

    result = validate_answers(example_questionnaire(), answer_set)

    assert not result.valid
    assert result.errors == ["missing required answer: horizon"]


def test_validate_answers_reports_unknown_question_id():
    result = validate_answers(
        example_questionnaire(),
        complete_answers(untracked_question="anything"),
    )

    assert not result.valid
    assert result.errors == ["unknown question id: untracked_question"]


def test_validate_answers_reports_invalid_choice():
    result = validate_answers(
        example_questionnaire(),
        complete_answers(loss_reaction="panic"),
    )

    assert not result.valid
    assert result.errors == ["invalid answer for loss_reaction: 'panic'"]


def test_score_answers_creates_intermediate_profile_scores():
    scores = score_answers(example_questionnaire(), complete_answers())

    assert scores.client_id == "C-1001"
    assert scores.questionnaire_id == "client_profile_v1"
    assert scores.questionnaire_version == "1.0"
    assert scores.risk_willingness_score == pytest.approx(1.0)
    assert scores.knowledge_score == pytest.approx(1.0)
    assert scores.horizon_score == 12
    assert scores.liquidity_pressure_score == 60_000
    assert scores.obligation_score == 1
    assert len(scores.contributions) == 7
    assert scores.contributions[0].ontology_path == (
        "client_profile.risk_tolerance.questionnaire.loss_scenarios.loss_10_percent"
    )


def test_derive_client_profile_maps_scores_to_reference_profile():
    scores = score_answers(example_questionnaire(), complete_answers())
    derivation = derive_client_profile(
        scores,
        age=42,
        annual_income=180_000,
        liquid_net_worth=750_000,
        restrictions=["no single-stock positions above 10%"],
    )

    assert derivation.questionnaire_id == "client_profile_v1"
    assert derivation.questionnaire_version == "1.0"
    assert derivation.profile.client_id == "C-1001"
    assert derivation.profile.risk_tolerance == "medium"
    assert derivation.profile.investment_knowledge == "intermediate"
    assert derivation.profile.investment_horizon_years == 12
    assert derivation.profile.liquidity_need_12m == 60_000
    assert derivation.profile.has_dependents is True
    assert derivation.profile.restrictions == ["no single-stock positions above 10%"]


def test_aggressive_but_loss_uncomfortable_answers_keep_warning_evidence():
    scores = score_answers(
        example_questionnaire(),
        complete_answers(
            loss_reaction="buy_more",
            portfolio_decline_comfort="very_uncomfortable",
        ),
    )
    derivation = derive_client_profile(scores)

    assert scores.warnings == [
        "contradictory answers: aggressive loss reaction with low decline comfort"
    ]
    assert derivation.warnings == scores.warnings
