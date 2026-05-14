from audit import AuditRecord
from profiling import AnswerOption, AnswerSet, GraphEdge, GraphNode, NavigationMetadata, Question, Questionnaire
from profiling.service import ProfilingService

from advice.products import ProductProfile


class FakeAuditStore:
    def __init__(self):
        self.records: list[AuditRecord] = []

    def save_profile_processing_run(self, record: AuditRecord) -> int:
        self.records.append(record)
        return 101


_PRODUCT = ProductProfile(
    product_id="P-204",
    name="Global Multi-Asset Fund",
    risk_level="medium",
    required_knowledge="basic",
    daily_liquidity=True,
)

_FINANCIAL_CTX = {"age": 42, "annual_income": 180_000, "liquid_net_worth": 750_000}


def _answers(**overrides) -> AnswerSet:
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


def test_service_exposes_default_questionnaire():
    service = ProfilingService()
    q = service.get_questionnaire("client_profile_v1")

    assert q is not None
    assert q.questionnaire_id == "client_profile_v1"
    assert q.version == "1.0"


def test_process_returns_profile_strategy_and_gates():
    service = ProfilingService()
    result = service.process("client_profile_v1", _answers(), product=_PRODUCT, **_FINANCIAL_CTX)

    assert result.valid
    assert result.derivation is not None
    assert result.derivation.profile.risk_tolerance == "medium"
    assert result.derivation.profile.investment_knowledge == "intermediate"
    assert result.assessment is not None
    assert result.assessment.strategy_profile.strategy == "balanced_growth"
    assert result.assessment.strategy_profile.risk_profile_category == "balanced"
    assert result.assessment.passed is True
    assert result.assessment.requires_review is False
    assert len(result.assessment.gates) == 3
    assert result.assessment.gates[1].gate_type == "appropriateness"
    assert result.assessment.gates[1].ontology_path == (
        "client_profile.knowledge_and_experience.appropriateness_gate"
    )


def test_process_returns_validation_errors():
    service = ProfilingService()
    result = service.process("client_profile_v1", _answers(horizon="not_real"), **_FINANCIAL_CTX)

    assert not result.valid
    assert result.errors == ["invalid answer for horizon: 'not_real'"]
    assert result.derivation is None
    assert result.assessment is None


def test_process_persists_audit_record_when_store_provided():
    audit_store = FakeAuditStore()
    service = ProfilingService(audit_store=audit_store)
    result = service.process(
        "client_profile_v1", _answers(), product=_PRODUCT, **_FINANCIAL_CTX
    )

    assert result.processing_run_id == 101
    assert len(audit_store.records) == 1
    record = audit_store.records[0]
    assert record.client_id == "C-1001"
    assert record.questionnaire_id == "client_profile_v1"
    assert record.ontology_version == "1.0"
    assert record.valid is True
    assert record.strategy_profile["risk_profile_category"] == "balanced"
    assert record.gates[0]["gate_type"] == "suitability"


def test_process_persists_invalid_audit_record():
    audit_store = FakeAuditStore()
    service = ProfilingService(audit_store=audit_store)
    result = service.process(
        "client_profile_v1", _answers(horizon="not_real"), **_FINANCIAL_CTX
    )

    assert result.processing_run_id == 101
    record = audit_store.records[0]
    assert record.valid is False
    assert record.errors == ["invalid answer for horizon: 'not_real'"]
    assert record.derived_profile is None


def test_service_can_register_questionnaire():
    q_node = Question(
        question_id="cares_about_esg",
        prompt="Do you care about ESG preferences?",
        answer_type="boolean",
        required=True,
        options=(
            AnswerOption(True, "Yes", 1),
            AnswerOption(False, "No", 0),
        ),
        ontology_path="client_profile.constraints_and_preferences.esg.enabled",
    )
    questionnaire = Questionnaire(
        questionnaire_id="graph_admin_v1",
        version="1.0",
        entry_node_id="start",
        nodes=(
            GraphNode(
                node_id="start",
                kind="question",
                question=q_node,
                navigation=NavigationMetadata(display_order=10),
            ),
        ),
        edges=(),
        applies_to_segments=("retail_advisory_natural_person",),
    )

    service = ProfilingService()
    service.register_questionnaire(questionnaire)

    saved = service.get_questionnaire("graph_admin_v1")
    assert saved is not None
    assert saved.questionnaire_id == "graph_admin_v1"
    assert saved.entry_node_id == "start"
    assert saved.applies_to_segments == ("retail_advisory_natural_person",)
    assert saved.nodes[0].question.question_id == "cares_about_esg"
