"""HTTP routes and Pydantic ↔ domain serialization for the profile API."""

from advice.products import ProductProfile
from advice.service import SuitabilityService
from fastapi import APIRouter, HTTPException
from profiling import (
    AnswerOption,
    AnswerSet,
    ClientProfile,
    EdgeCondition,
    GraphEdge,
    GraphNode,
    InstrumentKnowledge,
    NavigationMetadata,
    Question,
    Questionnaire,
    RepeatConfig,
    SliderScale,
)
from profiling.service import ProfilingService

from .schemas.admin import (
    ClientProfileResultPayload,
    ClientSegmentPayload,
    GateDecisionPayload,
    ProcessAnswersRequest,
    ProcessAnswersResponse,
    ProfileScoresPayload,
    QuestionnairePayload,
    ScoreContributionPayload,
    StrategyProfilePayload,
)
from .schemas.suitability import SuitabilityRequest, SuitabilityResponse

_CLIENT_SEGMENTS: dict[str, ClientSegmentPayload] = {
    "private_client": ClientSegmentPayload(
        segment_id="private_client",
        label="Private client",
        description="Standard advisory client with suitability and appropriateness checks.",
        minimum_liquid_net_worth=250000,
        review_policy="standard",
    ),
    "hnw": ClientSegmentPayload(
        segment_id="hnw",
        label="High net worth",
        description="Higher-complexity client with enhanced review before advice is finalized.",
        minimum_liquid_net_worth=1000000,
        review_policy="enhanced",
    ),
    "family_office": ClientSegmentPayload(
        segment_id="family_office",
        label="Family office",
        description="Multi-portfolio client with specialist review and broader mandate controls.",
        minimum_liquid_net_worth=5000000,
        review_policy="specialist",
    ),
}


def build_router(
    profiling: ProfilingService,
    suitability: SuitabilityService,
) -> APIRouter:
    router = APIRouter(tags=["profile"])

    @router.post("/suitability", response_model=SuitabilityResponse)
    def evaluate_suitability(request: SuitabilityRequest) -> SuitabilityResponse:
        profile = _profile_payload_to_domain(request.client)
        product = ProductProfile(**request.product.model_dump())
        result = suitability.evaluate(profile, product)
        return SuitabilityResponse(
            client_id=result.client_id,
            product_id=result.product_id,
            liquidity_ratio=result.liquidity_ratio,
            risk_capacity=result.risk_capacity,
            combined_risk_profile=result.combined_risk_profile,
            suitable=result.suitable,
            flags=result.flags,
        )

    @router.get("/admin/questionnaires", response_model=list[QuestionnairePayload])
    def list_questionnaires() -> list[QuestionnairePayload]:
        return [_questionnaire_to_payload(q) for q in profiling.list_questionnaires()]

    @router.post("/admin/questionnaires", response_model=QuestionnairePayload)
    def save_questionnaire(payload: QuestionnairePayload) -> QuestionnairePayload:
        questionnaire = _payload_to_questionnaire(payload)
        profiling.register_questionnaire(questionnaire)
        return _questionnaire_to_payload(questionnaire)

    @router.get(
        "/admin/questionnaires/{questionnaire_id}",
        response_model=QuestionnairePayload,
    )
    def get_questionnaire(questionnaire_id: str) -> QuestionnairePayload:
        q = profiling.get_questionnaire(questionnaire_id)
        if q is None:
            raise HTTPException(status_code=404, detail="questionnaire not found")
        return _questionnaire_to_payload(q)

    @router.post(
        "/admin/questionnaires/{questionnaire_id}/process",
        response_model=ProcessAnswersResponse,
    )
    def process_answers(
        questionnaire_id: str,
        request: ProcessAnswersRequest,
    ) -> ProcessAnswersResponse:
        answer_set = AnswerSet(
            client_id=request.answer_set.client_id,
            answers=request.answer_set.answers,
            repeat_context=request.answer_set.repeat_context,
            repeat_instance_id=request.answer_set.repeat_instance_id,
        )
        product = ProductProfile(**request.product.model_dump()) if request.product is not None else None
        ctx = request.financial_context
        try:
            result = profiling.process(
                questionnaire_id,
                answer_set,
                age=ctx.age,
                annual_income=ctx.annual_income,
                liquid_net_worth=ctx.liquid_net_worth,
                restrictions=ctx.restrictions,
                product=product,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="questionnaire not found")
        return _processing_result_to_response(result)

    @router.get("/admin/client-segments", response_model=list[ClientSegmentPayload])
    def list_client_segments() -> list[ClientSegmentPayload]:
        return list(_CLIENT_SEGMENTS.values())

    @router.post("/admin/client-segments", response_model=ClientSegmentPayload)
    def save_client_segment(segment: ClientSegmentPayload) -> ClientSegmentPayload:
        _CLIENT_SEGMENTS[segment.segment_id] = segment
        return segment

    return router


# --- Pydantic ↔ domain conversion helpers ---


def _profile_payload_to_domain(payload) -> ClientProfile:
    ik = payload.instrument_knowledge.model_dump()
    return ClientProfile(
        client_id=payload.client_id,
        age=payload.age,
        annual_income=payload.annual_income,
        liquid_net_worth=payload.liquid_net_worth,
        investment_horizon_years=payload.investment_horizon_years,
        liquidity_need_12m=payload.liquidity_need_12m,
        risk_tolerance=payload.risk_tolerance,
        investment_knowledge=payload.investment_knowledge,
        instrument_knowledge=InstrumentKnowledge(**ik),
        has_dependents=payload.has_dependents,
        restrictions=payload.restrictions,
    )


def _processing_result_to_response(result) -> ProcessAnswersResponse:
    scores_payload = None
    if result.scores is not None:
        scores_payload = ProfileScoresPayload(
            risk_willingness_score=result.scores.risk_willingness_score,
            knowledge_score=result.scores.knowledge_score,
            horizon_score=result.scores.horizon_score,
            liquidity_pressure_score=result.scores.liquidity_pressure_score,
            obligation_score=result.scores.obligation_score,
            contributions=[
                ScoreContributionPayload(
                    question_id=c.question_id,
                    signal=c.signal,
                    answer=c.answer,
                    score=c.score,
                    ontology_path=c.ontology_path,
                )
                for c in result.scores.contributions
            ],
        )

    profile_payload = None
    if result.derivation is not None:
        p = result.derivation.profile
        ik = p.instrument_knowledge
        profile_payload = ClientProfileResultPayload(
            client_id=p.client_id,
            age=p.age,
            annual_income=p.annual_income,
            liquid_net_worth=p.liquid_net_worth,
            investment_horizon_years=p.investment_horizon_years,
            liquidity_need_12m=p.liquidity_need_12m,
            risk_tolerance=p.risk_tolerance,
            investment_knowledge=p.investment_knowledge,
            instrument_knowledge={
                "equities": ik.equities,
                "bonds": ik.bonds,
                "funds_etfs": ik.funds_etfs,
                "derivatives": ik.derivatives,
                "structured_products": ik.structured_products,
            },
            has_dependents=p.has_dependents,
            restrictions=list(p.restrictions),
        )

    strategy_payload = None
    gates = []
    if result.assessment is not None:
        sp = result.assessment.strategy_profile
        strategy_payload = StrategyProfilePayload(
            strategy=sp.strategy,
            risk_profile_category=sp.risk_profile_category,
            risk_capacity=sp.risk_capacity,
            combined_risk_profile=sp.combined_risk_profile,
            liquidity_ratio=sp.liquidity_ratio,
            suitability_envelope=sp.suitability_envelope,
        )
        gates = [
            GateDecisionPayload(
                gate_id=gate.gate_id,
                gate_type=gate.gate_type,
                severity=gate.severity,
                passed=gate.passed,
                message=gate.message,
                ontology_path=gate.ontology_path,
            )
            for gate in result.assessment.gates
        ]

    return ProcessAnswersResponse(
        processing_run_id=result.processing_run_id,
        valid=result.valid,
        errors=result.errors,
        warnings=result.warnings,
        questionnaire_id=result.questionnaire_id,
        questionnaire_version=result.questionnaire_version,
        scores=scores_payload,
        profile=profile_payload,
        strategy_profile=strategy_payload,
        gates=gates,
        passed=result.assessment.passed if result.assessment is not None else None,
        requires_review=result.assessment.requires_review if result.assessment is not None else None,
    )


def _payload_to_questionnaire(payload: QuestionnairePayload) -> Questionnaire:
    questions = tuple(_payload_to_question(q) for q in payload.questions)
    nodes = tuple(
        GraphNode(
            node_id=node.node_id,
            kind=node.kind,
            question=_payload_to_question(node.question) if node.question is not None else None,
            label=node.label,
            repeat=RepeatConfig(**node.repeat.model_dump()) if node.repeat is not None else None,
            navigation=NavigationMetadata(**node.navigation.model_dump()),
        )
        for node in payload.nodes
    )
    if nodes and not questions:
        questions = tuple(node.question for node in nodes if node.question is not None)
    return Questionnaire(
        questionnaire_id=payload.questionnaire_id,
        version=payload.version,
        questions=questions,
        entry_node_id=payload.entry_node_id,
        nodes=nodes,
        edges=tuple(
            GraphEdge(
                from_node_id=edge.from_node_id,
                to_node_id=edge.to_node_id,
                condition=EdgeCondition(**edge.condition.model_dump())
                if edge.condition is not None
                else None,
            )
            for edge in payload.edges
        ),
        applies_to_segments=tuple(payload.applies_to_segments),
    )


def _payload_to_question(question) -> Question:
    return Question(
        question_id=question.question_id,
        prompt=question.prompt,
        answer_type=question.answer_type,
        target_signal=question.target_signal,
        required=question.required,
        ontology_path=question.ontology_path,
        scale=SliderScale(**question.scale.model_dump()) if question.scale is not None else None,
        max_length=question.max_length,
        options=tuple(
            AnswerOption(
                value=option.value,
                label=option.label,
                score=option.score,
                image_url=option.image_url,
            )
            for option in question.options
        ),
    )


def _questionnaire_to_payload(questionnaire: Questionnaire) -> QuestionnairePayload:
    return QuestionnairePayload(
        questionnaire_id=questionnaire.questionnaire_id,
        version=questionnaire.version,
        questions=[_question_to_dict(q) for q in questionnaire.all_questions()],
        entry_node_id=questionnaire.entry_node_id,
        nodes=[
            {
                "node_id": node.node_id,
                "kind": node.kind,
                "question": _question_to_dict(node.question) if node.question is not None else None,
                "label": node.label,
                "repeat": node.repeat.__dict__ if node.repeat is not None else None,
                "navigation": node.navigation.__dict__,
            }
            for node in questionnaire.nodes
        ],
        edges=[
            {
                "from_node_id": edge.from_node_id,
                "to_node_id": edge.to_node_id,
                "condition": edge.condition.__dict__ if edge.condition is not None else None,
            }
            for edge in questionnaire.edges
        ],
        applies_to_segments=list(questionnaire.applies_to_segments),
    )


def _question_to_dict(question: Question) -> dict:
    return {
        "question_id": question.question_id,
        "prompt": question.prompt,
        "answer_type": question.answer_type,
        "target_signal": question.target_signal,
        "required": question.required,
        "ontology_path": question.ontology_path,
        "scale": question.scale.__dict__ if question.scale is not None else None,
        "max_length": question.max_length,
        "options": [
            {
                "value": option.value,
                "label": option.label,
                "score": option.score,
                "image_url": option.image_url,
            }
            for option in question.options
        ],
    }
