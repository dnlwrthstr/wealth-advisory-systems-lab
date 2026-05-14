"""Score questionnaire answers into intermediate profiling signals."""

from dataclasses import dataclass, field

from .questionnaire import AnswerSet, Questionnaire, validate_answers


@dataclass(frozen=True)
class ScoreContribution:
    question_id: str
    signal: str
    answer: object
    score: int
    ontology_path: str | None = None


@dataclass(frozen=True)
class ProfileScores:
    client_id: str
    questionnaire_id: str
    questionnaire_version: str
    risk_willingness_score: float
    knowledge_score: float
    horizon_score: int
    liquidity_pressure_score: int
    obligation_score: int
    contributions: list[ScoreContribution] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def score_answers(questionnaire: Questionnaire, answer_set: AnswerSet) -> ProfileScores:
    validation = validate_answers(questionnaire, answer_set)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))

    questions = questionnaire.question_by_id()
    contributions: list[ScoreContribution] = []
    grouped_scores: dict[str, list[int]] = {
        "risk_willingness": [],
        "knowledge": [],
        "horizon": [],
        "liquidity_pressure": [],
        "obligation": [],
    }

    for question_id, answer in answer_set.answers.items():
        question = questions[question_id]
        if question.target_signal is None:
            continue

        score = _score_answer(question, answer)
        if score is None:
            continue

        grouped_scores[question.target_signal].append(score)
        contributions.append(
            ScoreContribution(
                question_id=question_id,
                signal=question.target_signal,
                answer=answer,
                score=score,
                ontology_path=question.ontology_path,
            )
        )

    return ProfileScores(
        client_id=answer_set.client_id,
        questionnaire_id=questionnaire.questionnaire_id,
        questionnaire_version=questionnaire.version,
        risk_willingness_score=_average(grouped_scores["risk_willingness"]),
        knowledge_score=_average(grouped_scores["knowledge"]),
        horizon_score=_single_score(grouped_scores["horizon"], "horizon"),
        liquidity_pressure_score=_single_score(
            grouped_scores["liquidity_pressure"], "liquidity_pressure"
        ),
        obligation_score=max(grouped_scores["obligation"], default=0),
        contributions=contributions,
        warnings=validation.warnings,
    )


def _average(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _single_score(values: list[int], signal: str) -> int:
    if not values:
        return 0
    return values[0]


def _score_answer(question, answer) -> int | None:
    if question.answer_type in {"single_choice", "boolean", "image_choice"}:
        option = question.option_for(answer)
        if option is None:
            raise ValueError(f"invalid answer for {question.question_id}: {answer!r}")
        if option.score is None:
            raise ValueError(f"missing score for {question.question_id}: {answer!r}")
        return option.score

    if question.answer_type == "multiple_choice":
        if not isinstance(answer, list):
            raise ValueError(f"invalid answer for {question.question_id}: {answer!r}")
        total = 0
        for item in answer:
            option = question.option_for(item)
            if option is None:
                raise ValueError(f"invalid answer for {question.question_id}: {item!r}")
            total += option.score or 0
        return total

    if question.answer_type == "slider":
        if not isinstance(answer, int | float):
            raise ValueError(f"invalid answer for {question.question_id}: {answer!r}")
        return int(answer)

    return None
