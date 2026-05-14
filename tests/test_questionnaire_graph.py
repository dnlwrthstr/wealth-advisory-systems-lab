from profiling import (
    AnswerOption,
    AnswerSet,
    EdgeCondition,
    GraphEdge,
    GraphNode,
    Question,
    Questionnaire,
    RepeatConfig,
    SliderScale,
    reachable_question_ids,
    score_answers,
    validate_answers,
    validate_questionnaire_graph,
)


def graph_questionnaire():
    esg = Question(
        question_id="cares_about_esg",
        prompt="Do you care about ESG preferences?",
        answer_type="boolean",
        required=True,
        options=(
            AnswerOption(True, "Yes", 1),
            AnswerOption(False, "No", 0),
        ),
    )
    sectors = Question(
        question_id="excluded_sectors",
        prompt="Which sectors should be excluded?",
        answer_type="multiple_choice",
        required=False,
        ontology_path="client_profile.constraints_and_preferences.esg.exclusions.sectors",
        options=(
            AnswerOption("weapons", "Weapons", 1),
            AnswerOption("tobacco", "Tobacco", 1),
            AnswerOption("thermal_coal", "Thermal coal", 1),
        ),
    )
    loss_comfort = Question(
        question_id="loss_comfort",
        prompt="How comfortable are you with temporary losses?",
        answer_type="slider",
        required=True,
        target_signal="risk_willingness",
        scale=SliderScale(min=1, max=5, step=1),
    )
    note = Question(
        question_id="advisor_note",
        prompt="Advisor review note",
        answer_type="text",
        required=False,
        max_length=200,
    )

    return Questionnaire(
        questionnaire_id="graph_profile_v1",
        version="1.0",
        entry_node_id="cares_about_esg",
        nodes=(
            GraphNode(node_id="cares_about_esg", kind="question", question=esg),
            GraphNode(
                node_id="excluded_sectors",
                kind="question",
                question=sectors,
                repeat=RepeatConfig(enabled=True, context="portfolio", min_items=0, max_items=5),
            ),
            GraphNode(node_id="loss_comfort", kind="question", question=loss_comfort),
            GraphNode(node_id="advisor_note", kind="question", question=note),
        ),
        edges=(
            GraphEdge(
                from_node_id="cares_about_esg",
                to_node_id="excluded_sectors",
                condition=EdgeCondition(
                    question_id="cares_about_esg",
                    operator="equals",
                    value=True,
                ),
            ),
            GraphEdge(
                from_node_id="cares_about_esg",
                to_node_id="loss_comfort",
                condition=EdgeCondition(
                    question_id="cares_about_esg",
                    operator="equals",
                    value=False,
                ),
            ),
            GraphEdge(from_node_id="excluded_sectors", to_node_id="loss_comfort"),
            GraphEdge(from_node_id="loss_comfort", to_node_id="advisor_note"),
        ),
    )


def test_graph_validation_accepts_acyclic_questionnaire():
    result = validate_questionnaire_graph(graph_questionnaire())

    assert result.valid
    assert result.errors == []


def test_graph_validation_rejects_cycles():
    questionnaire = graph_questionnaire()
    cyclic = Questionnaire(
        questionnaire_id=questionnaire.questionnaire_id,
        version=questionnaire.version,
        entry_node_id=questionnaire.entry_node_id,
        nodes=questionnaire.nodes,
        edges=(
            *questionnaire.edges,
            GraphEdge(from_node_id="advisor_note", to_node_id="cares_about_esg"),
        ),
    )

    result = validate_questionnaire_graph(cyclic)

    assert not result.valid
    assert result.errors == ["graph cycles are not allowed"]


def test_reachable_questions_follow_answer_conditions():
    questionnaire = graph_questionnaire()

    yes_path = reachable_question_ids(
        questionnaire,
        AnswerSet(
            client_id="C-1001",
            answers={"cares_about_esg": True},
        ),
    )
    no_path = reachable_question_ids(
        questionnaire,
        AnswerSet(
            client_id="C-1001",
            answers={"cares_about_esg": False},
        ),
    )

    assert "excluded_sectors" in yes_path
    assert "excluded_sectors" not in no_path
    assert "loss_comfort" in no_path


def test_validate_answers_accepts_flexible_answer_types():
    questionnaire = graph_questionnaire()
    result = validate_answers(
        questionnaire,
        AnswerSet(
            client_id="C-1001",
            repeat_context="portfolio",
            repeat_instance_id="portfolio_core",
            answers={
                "cares_about_esg": True,
                "excluded_sectors": ["weapons", "thermal_coal"],
                "loss_comfort": 3,
                "advisor_note": "Client wants constraints reviewed annually.",
            },
        ),
    )

    assert result.valid
    assert result.errors == []


def test_score_answers_ignores_unscored_text_and_scores_slider():
    scores = score_answers(
        graph_questionnaire(),
        AnswerSet(
            client_id="C-1001",
            answers={
                "cares_about_esg": True,
                "excluded_sectors": ["weapons"],
                "loss_comfort": 3,
                "advisor_note": "Review note",
            },
        ),
    )

    assert scores.risk_willingness_score == 3
    assert [contribution.question_id for contribution in scores.contributions] == [
        "loss_comfort"
    ]

