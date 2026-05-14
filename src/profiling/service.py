"""ProfilingService wraps the questionnaire processing pipeline."""

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from audit import AuditRecord, AuditStore

from .derivation import ProfileDerivation, derive_client_profile
from .models import ClientProfile
from .questionnaire import AnswerSet, Questionnaire, example_questionnaire, validate_answers
from .scoring import ProfileScores, score_answers
from .strategy import GateDecision, StrategyAssessment, assess_strategy_and_gates

if TYPE_CHECKING:
    from .store import QuestionnaireStore

ONTOLOGY_VERSION = "1.0"


@dataclass
class ProcessingResult:
    valid: bool
    questionnaire_id: str
    questionnaire_version: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scores: ProfileScores | None = None
    derivation: ProfileDerivation | None = None
    assessment: StrategyAssessment | None = None
    processing_run_id: int | None = None


class ProfilingService:
    def __init__(
        self,
        audit_store: AuditStore | None = None,
        questionnaire_store: "QuestionnaireStore | None" = None,
    ) -> None:
        self._audit_store = audit_store
        self._questionnaire_store = questionnaire_store

        if questionnaire_store is not None:
            self._questionnaires: dict[str, Questionnaire] = {
                q.questionnaire_id: q for q in questionnaire_store.load_active()
            }
        else:
            self._questionnaires = {
                example_questionnaire().questionnaire_id: example_questionnaire()
            }

    def register_questionnaire(self, questionnaire: Questionnaire) -> None:
        self._questionnaires[questionnaire.questionnaire_id] = questionnaire
        if self._questionnaire_store is not None:
            self._questionnaire_store.save(questionnaire)

    def get_questionnaire(self, questionnaire_id: str) -> Questionnaire | None:
        return self._questionnaires.get(questionnaire_id)

    def list_questionnaires(self) -> list[Questionnaire]:
        return list(self._questionnaires.values())

    def process(
        self,
        questionnaire_id: str,
        answer_set: AnswerSet,
        *,
        age: int,
        annual_income: float,
        liquid_net_worth: float,
        restrictions: list[str] | None = None,
        product=None,
    ) -> ProcessingResult:
        """Run the full pipeline: validate → score → derive profile → assess strategy → audit."""
        questionnaire = self._questionnaires.get(questionnaire_id)
        if questionnaire is None:
            raise KeyError(f"questionnaire not found: {questionnaire_id!r}")

        validation = validate_answers(questionnaire, answer_set)
        if not validation.valid:
            result = ProcessingResult(
                valid=False,
                questionnaire_id=questionnaire.questionnaire_id,
                questionnaire_version=questionnaire.version,
                errors=validation.errors,
                warnings=validation.warnings,
            )
            self._persist_audit(answer_set, result)
            return result

        scores = score_answers(questionnaire, answer_set)
        derivation = derive_client_profile(
            scores,
            age=age,
            annual_income=annual_income,
            liquid_net_worth=liquid_net_worth,
            restrictions=restrictions,
        )
        assessment = assess_strategy_and_gates(
            derivation.profile,
            product=product,
            warnings=derivation.warnings,
        )

        result = ProcessingResult(
            valid=True,
            questionnaire_id=questionnaire.questionnaire_id,
            questionnaire_version=questionnaire.version,
            warnings=derivation.warnings,
            scores=scores,
            derivation=derivation,
            assessment=assessment,
        )
        self._persist_audit(answer_set, result)
        return result

    def _persist_audit(self, answer_set: AnswerSet, result: ProcessingResult) -> None:
        if self._audit_store is None:
            return
        record = AuditRecord(
            client_id=answer_set.client_id,
            questionnaire_id=result.questionnaire_id,
            questionnaire_version=result.questionnaire_version,
            ontology_version=ONTOLOGY_VERSION,
            raw_answers=answer_set.answers,
            score_contributions=[
                {
                    "question_id": c.question_id,
                    "signal": c.signal,
                    "answer": c.answer,
                    "score": c.score,
                    "ontology_path": c.ontology_path,
                }
                for c in result.scores.contributions
            ] if result.scores is not None else [],
            derived_profile=asdict(result.derivation.profile) if result.derivation is not None else None,
            strategy_profile=asdict(result.assessment.strategy_profile) if result.assessment is not None else None,
            gates=[asdict(gate) for gate in result.assessment.gates] if result.assessment is not None else [],
            warnings=result.warnings,
            errors=result.errors,
            valid=result.valid,
        )
        result.processing_run_id = self._audit_store.save_profile_processing_run(record)
