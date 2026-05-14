"""Questionnaire definitions and raw answer validation."""

from dataclasses import dataclass, field
from typing import Literal

AnswerValue = str | bool | int | float | list[str] | list[int] | dict[str, object] | None
AnswerType = Literal[
    "boolean",
    "single_choice",
    "multiple_choice",
    "slider",
    "text",
    "image_choice",
    "image_upload",
]
SignalName = Literal[
    "risk_willingness",
    "knowledge",
    "horizon",
    "liquidity_pressure",
    "obligation",
]
NodeKind = Literal["section", "question", "review", "terminal"]
ConditionOperator = Literal["equals", "not_equals", "in", "not_in", "exists"]


@dataclass(frozen=True)
class AnswerOption:
    value: AnswerValue
    label: str
    score: int | None = None
    image_url: str | None = None


@dataclass(frozen=True)
class SliderScale:
    min: int | float
    max: int | float
    step: int | float = 1
    min_label: str | None = None
    max_label: str | None = None


@dataclass(frozen=True)
class RepeatConfig:
    enabled: bool = False
    context: str | None = None
    min_items: int = 0
    max_items: int | None = None


@dataclass(frozen=True)
class NavigationMetadata:
    display_order: int = 0
    section_id: str | None = None
    previous_label: str = "Back"
    next_label: str = "Continue"


@dataclass(frozen=True)
class Question:
    question_id: str
    prompt: str
    answer_type: AnswerType
    required: bool
    target_signal: SignalName | None = None
    options: tuple[AnswerOption, ...] = ()
    ontology_path: str | None = None
    scale: SliderScale | None = None
    max_length: int | None = None

    def option_for(self, value: AnswerValue) -> AnswerOption | None:
        return next((option for option in self.options if option.value == value), None)


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: NodeKind
    question: Question | None = None
    label: str | None = None
    repeat: RepeatConfig | None = None
    navigation: NavigationMetadata = field(default_factory=NavigationMetadata)


@dataclass(frozen=True)
class EdgeCondition:
    question_id: str
    operator: ConditionOperator
    value: AnswerValue = None


@dataclass(frozen=True)
class GraphEdge:
    from_node_id: str
    to_node_id: str
    condition: EdgeCondition | None = None


@dataclass(frozen=True)
class Questionnaire:
    questionnaire_id: str
    version: str
    questions: tuple[Question, ...] = ()
    entry_node_id: str | None = None
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    applies_to_segments: tuple[str, ...] = ()

    def question_by_id(self) -> dict[str, Question]:
        return {question.question_id: question for question in self.all_questions()}

    def node_by_id(self) -> dict[str, GraphNode]:
        return {node.node_id: node for node in self.nodes}

    def all_questions(self) -> tuple[Question, ...]:
        if self.nodes:
            return tuple(node.question for node in self.nodes if node.question is not None)
        return self.questions


@dataclass(frozen=True)
class AnswerSet:
    client_id: str
    answers: dict[str, AnswerValue]
    repeat_context: str | None = None
    repeat_instance_id: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_answers(questionnaire: Questionnaire, answer_set: AnswerSet) -> ValidationResult:
    questions = questionnaire.question_by_id()
    errors: list[str] = []
    warnings: list[str] = []

    graph_result = validate_questionnaire_graph(questionnaire)
    errors.extend(graph_result.errors)
    warnings.extend(graph_result.warnings)

    for question in questionnaire.all_questions():
        if question.required and question.question_id not in answer_set.answers:
            errors.append(f"missing required answer: {question.question_id}")

    for question_id, value in answer_set.answers.items():
        question = questions.get(question_id)
        if question is None:
            errors.append(f"unknown question id: {question_id}")
            continue
        question_errors = _validate_answer_value(question, value)
        if question_errors:
            errors.extend(question_errors)

    for question in questionnaire.all_questions():
        if question.answer_type in {"image_choice", "image_upload"}:
            warnings.append(f"image question deferred from first implementation: {question.question_id}")

    reachable_questions = reachable_question_ids(questionnaire, answer_set)
    if reachable_questions:
        for question_id in answer_set.answers:
            if question_id not in reachable_questions:
                warnings.append(f"answer provided for unreachable question: {question_id}")

    loss_reaction = answer_set.answers.get("loss_reaction")
    decline_comfort = answer_set.answers.get("portfolio_decline_comfort")
    if loss_reaction == "buy_more" and decline_comfort == "very_uncomfortable":
        warnings.append(
            "contradictory answers: aggressive loss reaction with low decline comfort"
        )

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def validate_questionnaire_graph(questionnaire: Questionnaire) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if not questionnaire.nodes:
        return ValidationResult(valid=True, errors=[], warnings=[])

    nodes = questionnaire.node_by_id()
    if len(nodes) != len(questionnaire.nodes):
        errors.append("duplicate node ids")

    question_ids = [node.question.question_id for node in questionnaire.nodes if node.question is not None]
    if len(set(question_ids)) != len(question_ids):
        errors.append("duplicate question ids")

    if questionnaire.entry_node_id is None:
        errors.append("missing entry node")
    elif questionnaire.entry_node_id not in nodes:
        errors.append(f"entry node not found: {questionnaire.entry_node_id}")

    for edge in questionnaire.edges:
        if edge.from_node_id not in nodes:
            errors.append(f"edge source not found: {edge.from_node_id}")
        if edge.to_node_id not in nodes:
            errors.append(f"edge target not found: {edge.to_node_id}")

    if questionnaire.entry_node_id in nodes:
        reachable = _reachable_node_ids(questionnaire)
        for node_id in nodes:
            if node_id not in reachable:
                warnings.append(f"unreachable node: {node_id}")

    if _has_cycle(questionnaire):
        errors.append("graph cycles are not allowed")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def reachable_question_ids(questionnaire: Questionnaire, answer_set: AnswerSet) -> set[str]:
    if not questionnaire.nodes or questionnaire.entry_node_id is None:
        return set()

    nodes = questionnaire.node_by_id()
    reachable_questions: set[str] = set()
    visited: set[str] = set()
    stack = [questionnaire.entry_node_id]

    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = nodes.get(node_id)
        if node is None:
            continue
        if node.question is not None:
            reachable_questions.add(node.question.question_id)

        for edge in questionnaire.edges:
            if edge.from_node_id == node_id and _condition_matches(edge.condition, answer_set.answers):
                stack.append(edge.to_node_id)

    return reachable_questions


def _validate_answer_value(question: Question, value: AnswerValue) -> list[str]:
    errors: list[str] = []

    if value is None:
        if question.required:
            errors.append(f"missing required answer: {question.question_id}")
        return errors

    if question.answer_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"invalid boolean answer for {question.question_id}: {value!r}")
    elif question.answer_type == "single_choice":
        if question.option_for(value) is None:
            errors.append(f"invalid answer for {question.question_id}: {value!r}")
    elif question.answer_type == "multiple_choice":
        if not isinstance(value, list):
            errors.append(f"invalid multiple choice answer for {question.question_id}: {value!r}")
        else:
            allowed = {option.value for option in question.options}
            for item in value:
                if item not in allowed:
                    errors.append(f"invalid answer for {question.question_id}: {item!r}")
    elif question.answer_type == "slider":
        if not isinstance(value, int | float):
            errors.append(f"invalid slider answer for {question.question_id}: {value!r}")
        elif question.scale is not None and not question.scale.min <= value <= question.scale.max:
            errors.append(f"slider answer out of range for {question.question_id}: {value!r}")
    elif question.answer_type == "text":
        if not isinstance(value, str):
            errors.append(f"invalid text answer for {question.question_id}: {value!r}")
        elif question.max_length is not None and len(value) > question.max_length:
            errors.append(f"text answer too long for {question.question_id}")
    elif question.answer_type == "image_choice":
        if question.option_for(value) is None:
            errors.append(f"invalid image choice answer for {question.question_id}: {value!r}")
    elif question.answer_type == "image_upload":
        if not isinstance(value, dict) or "document_id" not in value:
            errors.append(f"invalid image upload answer for {question.question_id}: {value!r}")

    return errors


def _reachable_node_ids(questionnaire: Questionnaire) -> set[str]:
    if questionnaire.entry_node_id is None:
        return set()

    reachable: set[str] = set()
    stack = [questionnaire.entry_node_id]
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(edge.to_node_id for edge in questionnaire.edges if edge.from_node_id == node_id)
    return reachable


def _has_cycle(questionnaire: Questionnaire) -> bool:
    graph: dict[str, list[str]] = {node.node_id: [] for node in questionnaire.nodes}
    for edge in questionnaire.edges:
        graph.setdefault(edge.from_node_id, []).append(edge.to_node_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for next_node_id in graph.get(node_id, []):
            if visit(next_node_id):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in graph)


def _condition_matches(condition: EdgeCondition | None, answers: dict[str, AnswerValue]) -> bool:
    if condition is None:
        return True

    answer = answers.get(condition.question_id)
    if condition.operator == "equals":
        return answer == condition.value
    if condition.operator == "not_equals":
        return answer != condition.value
    if condition.operator == "in":
        return isinstance(condition.value, list) and answer in condition.value
    if condition.operator == "not_in":
        return isinstance(condition.value, list) and answer not in condition.value
    if condition.operator == "exists":
        return condition.question_id in answers
    return False


def questionnaire_from_dict(data: dict) -> Questionnaire:
    """Deserialize a plain dict (e.g. from JSONB) into a Questionnaire domain object."""
    questions = tuple(
        Question(
            question_id=q["question_id"],
            prompt=q["prompt"],
            answer_type=q["answer_type"],
            target_signal=q.get("target_signal"),
            required=q.get("required", True),
            ontology_path=q.get("ontology_path"),
            options=tuple(
                AnswerOption(
                    value=o["value"],
                    label=o["label"],
                    score=o.get("score"),
                    image_url=o.get("image_url"),
                )
                for o in q.get("options", [])
            ),
        )
        for q in data.get("questions", [])
    )
    return Questionnaire(
        questionnaire_id=data["questionnaire_id"],
        version=data["version"],
        questions=questions,
    )


def questionnaire_to_dict(questionnaire: Questionnaire) -> dict:
    """Serialize a Questionnaire domain object to a plain dict suitable for JSONB storage."""
    return {
        "questionnaire_id": questionnaire.questionnaire_id,
        "version": questionnaire.version,
        "questions": [
            {
                "question_id": q.question_id,
                "prompt": q.prompt,
                "answer_type": q.answer_type,
                "target_signal": q.target_signal,
                "required": q.required,
                "ontology_path": q.ontology_path,
                "options": [
                    {
                        "value": o.value,
                        "label": o.label,
                        "score": o.score,
                        "image_url": o.image_url,
                    }
                    for o in q.options
                ],
            }
            for q in questionnaire.all_questions()
        ],
    }


def example_questionnaire() -> Questionnaire:
    questions = (
        Question(
                question_id="loss_reaction",
                prompt="What would you most likely do if your portfolio fell by 15%?",
                answer_type="single_choice",
                target_signal="risk_willingness",
                required=True,
                ontology_path="client_profile.risk_tolerance.questionnaire.loss_scenarios.loss_10_percent",
                options=(
                    AnswerOption("sell", "Sell to avoid further losses", 0),
                    AnswerOption("hold", "Hold the portfolio", 1),
                    AnswerOption("buy_more", "Invest more at lower prices", 2),
                ),
            ),
        Question(
                question_id="portfolio_decline_comfort",
                prompt="How comfortable are you with temporary portfolio declines?",
                answer_type="single_choice",
                target_signal="risk_willingness",
                required=True,
                ontology_path="client_profile.risk_tolerance.questionnaire.loss_scenarios.loss_20_percent",
                options=(
                    AnswerOption("very_uncomfortable", "Very uncomfortable", 0),
                    AnswerOption("somewhat_comfortable", "Somewhat comfortable", 1),
                    AnswerOption("comfortable", "Comfortable", 2),
                ),
            ),
        Question(
                question_id="investment_experience",
                prompt="Which investments have you previously used?",
                answer_type="single_choice",
                target_signal="knowledge",
                required=True,
                ontology_path="client_profile.knowledge_and_experience.instruments.funds_etfs",
                options=(
                    AnswerOption("savings_only", "Savings accounts only", 0),
                    AnswerOption("funds_and_etfs", "Funds or ETFs", 1),
                    AnswerOption("complex_products", "Complex products", 2),
                ),
            ),
        Question(
                question_id="product_knowledge",
                prompt="How would you describe your investment product knowledge?",
                answer_type="single_choice",
                target_signal="knowledge",
                required=True,
                ontology_path="client_profile.knowledge_and_experience",
                options=(
                    AnswerOption("limited", "Limited", 0),
                    AnswerOption("general", "General", 1),
                    AnswerOption("advanced", "Advanced", 2),
                ),
            ),
        Question(
                question_id="horizon",
                prompt="When do you expect to need most of this invested capital?",
                answer_type="single_choice",
                target_signal="horizon",
                required=True,
                ontology_path="client_profile.investment_objectives.investment_horizon",
                options=(
                    AnswerOption("under_3_years", "Under 3 years", 2),
                    AnswerOption("3_to_7_years", "3 to 7 years", 6),
                    AnswerOption("7_to_15_years", "7 to 15 years", 12),
                    AnswerOption("over_15_years", "Over 15 years", 18),
                ),
            ),
        Question(
                question_id="liquidity_need",
                prompt="How much liquidity do you expect to need over the next 12 months?",
                answer_type="single_choice",
                target_signal="liquidity_pressure",
                required=True,
                ontology_path="client_profile.financial_situation.liquidity_needs",
                options=(
                    AnswerOption("low", "Low", 25_000),
                    AnswerOption("moderate", "Moderate", 60_000),
                    AnswerOption("high", "High", 150_000),
                ),
            ),
        Question(
                question_id="has_dependents",
                prompt="Do you have dependents or similar financial obligations?",
                answer_type="boolean",
                target_signal="obligation",
                required=True,
                ontology_path="client_profile.financial_situation",
                options=(
                    AnswerOption(False, "No", 0),
                    AnswerOption(True, "Yes", 1),
                ),
            ),
    )
    nodes = tuple(
        GraphNode(
            node_id=question.question_id,
            kind="question",
            question=question,
            navigation=NavigationMetadata(display_order=index * 10),
        )
        for index, question in enumerate(questions, start=1)
    )
    edges = tuple(
        GraphEdge(from_node_id=current.question_id, to_node_id=next_question.question_id)
        for current, next_question in zip(questions, questions[1:])
    )

    return Questionnaire(
        questionnaire_id="client_profile_v1",
        version="1.0",
        questions=questions,
        entry_node_id="loss_reaction",
        nodes=nodes,
        edges=edges,
    )
