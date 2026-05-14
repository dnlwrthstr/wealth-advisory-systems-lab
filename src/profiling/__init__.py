"""Client profile models and enrichment logic."""

from .derivation import ProfileDerivation, derive_client_profile
from .models import (
    ClientProfile,
    InstrumentExperienceLevel,
    InstrumentKnowledge,
    InstrumentType,
    KnowledgeLevel,
    RiskLevel,
)
from .questionnaire import (
    AnswerOption,
    AnswerSet,
    EdgeCondition,
    GraphEdge,
    GraphNode,
    NavigationMetadata,
    Question,
    Questionnaire,
    RepeatConfig,
    SliderScale,
    ValidationResult,
    example_questionnaire,
    reachable_question_ids,
    validate_answers,
    validate_questionnaire_graph,
)
from .scoring import ProfileScores, ScoreContribution, score_answers
from .service import ProcessingResult, ProfilingService
from .signals import combined_risk_profile, liquidity_ratio, risk_capacity
from .store import PostgresQuestionnaireStore
from .strategy import (
    GateDecision,
    RiskProfileCategory,
    StrategyAssessment,
    StrategyLevel,
    StrategyProfile,
    assess_strategy_and_gates,
)

__all__ = [
    "AnswerOption",
    "AnswerSet",
    "ClientProfile",
    "EdgeCondition",
    "GraphEdge",
    "GraphNode",
    "GateDecision",
    "InstrumentExperienceLevel",
    "InstrumentKnowledge",
    "InstrumentType",
    "KnowledgeLevel",
    "NavigationMetadata",
    "PostgresQuestionnaireStore",
    "ProcessingResult",
    "ProfileDerivation",
    "ProfileScores",
    "ProfilingService",
    "Question",
    "Questionnaire",
    "RepeatConfig",
    "RiskProfileCategory",
    "RiskLevel",
    "ScoreContribution",
    "SliderScale",
    "StrategyAssessment",
    "StrategyLevel",
    "StrategyProfile",
    "ValidationResult",
    "assess_strategy_and_gates",
    "combined_risk_profile",
    "derive_client_profile",
    "example_questionnaire",
    "liquidity_ratio",
    "risk_capacity",
    "reachable_question_ids",
    "score_answers",
    "validate_answers",
    "validate_questionnaire_graph",
]
