"""Policy validator and conversation context tests for metric proposals."""

from datetime import UTC, datetime

import pytest
from apps.api.main import build_metric_conversation_context

from brif_ai.brief.models.common import (
    ConfirmationStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefSnapshot,
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.conversation.elicitation.models import ElicitationContext, ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    MetricConversationContext,
    SpaceMetricContext,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
)
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
    ProposedMetricRequirement,
    SpaceMetricRequirements,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialNode,
    SpatialRelationship,
    SpatialRelationshipGraph,
    SpatialRelationType,
)
from brif_ai.spatial.plan_input import AuthoritativePlanInputState

CANONICAL_TOPICS = [
    ElicitationTopic.HOUSEHOLD,
    ElicitationTopic.SPACE_PROGRAM,
    ElicitationTopic.ACCESSIBILITY,
    ElicitationTopic.SPATIAL_RELATIONSHIPS,
    ElicitationTopic.KITCHEN_SERVICE,
    ElicitationTopic.PRIVACY,
    ElicitationTopic.WORK_STUDY,
    ElicitationTopic.STORAGE_SERVICE,
    ElicitationTopic.OUTDOOR_USE,
    ElicitationTopic.DAILY_ROUTINES,
    ElicitationTopic.BUDGET_PRIORITY,
]


def _closed_topic_questions() -> list[OpenQuestion]:
    return [
        OpenQuestion(
            id=f"oq_{topic.value}",
            question=f"{topic.value} tamamlandı mı?",
            reason="Ready brief fixture.",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.ANSWERED,
            resolution_note="Tamamlandı.",
            topic_key=topic.value,
        )
        for topic in CANONICAL_TOPICS
    ]


def _make_brief_snapshot() -> BriefSnapshot:
    return BriefSnapshot(
        project_id="proj_metric_test",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
        ],
        evidence=[
            Evidence(
                id="ev_1",
                source_type=EvidenceSource.CHAT,
                source_reference="ref_1",
                excerpt="Salon ve mutfak",
            )
        ],
        brief_items=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=_closed_topic_questions(),
        space_requests=[
            SpaceRequest(
                id="sr_living",
                display_name="Salon",
                space_function=SpaceFunction.LIVING,
                minimum_quantity=1,
                maximum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_kitchen",
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
                minimum_quantity=1,
                maximum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
        ],
    )


def _make_spatial_graph() -> SpatialRelationshipGraph:
    return SpatialRelationshipGraph(
        project_id="proj_metric_test",
        schema_version="spatial_graph.v0",
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        nodes=[
            SpatialNode(
                id="sn_living_01",
                display_name="Salon",
                function=SpaceFunction.LIVING,
                source_space_request_id="sr_living",
                instance_index=1,
            ),
            SpatialNode(
                id="sn_kitchen_01",
                display_name="Mutfak",
                function=SpaceFunction.COOKING,
                source_space_request_id="sr_kitchen",
                instance_index=1,
            ),
        ],
        relationships=[
            SpatialRelationship(
                id="edge_1",
                source_space_id="sn_living_01",
                target_space_id="sn_kitchen_01",
                relation_type=SpatialRelationType.NEAR,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=["ev_1"],
            )
        ],
    )


def _make_request(
    message: str = "Salon en az 30 m² olsun",
    elicitation_context: ElicitationContext | None = None,
) -> ConversationRequest:
    return ConversationRequest(
        message=message,
        active_context=ActiveContextSnapshot(
            project_id="proj_metric_test",
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        visible_entities=[],
        elicitation_context=elicitation_context,
    )


def test_metric_proposal_requires_metric_context() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    request = _make_request()
    prop = ProposedMetricRequirement(
        proposal_id="prop_1",
        space_id="sn_living_1",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    result = ArchitecturalIntentResult(
        assistant_message="Salon en az 30 m² olsun.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_metric_test"),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[],
        proposed_metric_requirements=[prop],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )
    with pytest.raises(PolicyValidationError, match="Metrik bağlamı"):
        validator.validate(result, request, metric_context=None)


def test_metric_proposal_requires_valid_space_id() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    metric_context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(
                space_id="sn_living_1",
                display_name="Salon",
                function="LIVING_ROOM",
                existing_requirements=[],
            )
        ],
        source_brief_version=1,
    )
    request = _make_request()
    prop = ProposedMetricRequirement(
        proposal_id="prop_1",
        space_id="sn_unknown_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    result = ArchitecturalIntentResult(
        assistant_message="Bilinmeyen oda için alan önerisi.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_metric_test"),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[],
        proposed_metric_requirements=[prop],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )
    with pytest.raises(PolicyValidationError, match="Bilinmeyen mekân kimliği"):
        validator.validate(result, request, metric_context=metric_context)


def test_metric_proposal_rejects_during_open_elicitation() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    metric_context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(
                space_id="sn_living_1",
                display_name="Salon",
                function="LIVING_ROOM",
                existing_requirements=[],
            )
        ],
        source_brief_version=1,
    )
    elicitation = ElicitationContext(
        open_question_topics=[ElicitationTopic.HOUSEHOLD],
        answered_question_topics=[],
        allowed_follow_up_topic=None,
        reason="Household open",
    )
    request = _make_request(
        message="4 kişiyiz ve salon 30 m2 olsun",
        elicitation_context=elicitation,
    )
    prop = ProposedMetricRequirement(
        proposal_id="prop_1",
        space_id="sn_living_1",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    result = ArchitecturalIntentResult(
        assistant_message="Salon için alan önerisi.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_metric_test"),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[],
        proposed_metric_requirements=[prop],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )
    with pytest.raises(
        PolicyValidationError, match="Aktif elicitation sırasında metrik önerisi sunulamaz"
    ):
        validator.validate(result, request, metric_context=metric_context)


def test_metric_proposal_rejects_on_neutral_starter() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    metric_context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(
                space_id="sn_living_1",
                display_name="Salon",
                function="LIVING_ROOM",
                existing_requirements=[],
            )
        ],
        source_brief_version=1,
    )
    elicitation = ElicitationContext(
        open_question_topics=[],
        answered_question_topics=[],
        allowed_follow_up_topic=ElicitationTopic.SPACE_PROGRAM,
        reason="Starter",
    )
    request = _make_request(
        message="Başlayalım.",
        elicitation_context=elicitation,
    )
    prop = ProposedMetricRequirement(
        proposal_id="prop_1",
        space_id="sn_living_1",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    result = ArchitecturalIntentResult(
        assistant_message="Salon için alan önerisi.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_metric_test"),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[],
        proposed_metric_requirements=[prop],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )
    with pytest.raises(PolicyValidationError, match="neutral elicitation starter"):
        validator.validate(result, request, metric_context=metric_context)


def test_metric_proposal_sanitization() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    metric_context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(
                space_id="space_living",
                display_name="Salon",
                function="LIVING_ROOM",
                existing_requirements=[],
            )
        ],
        source_brief_version=1,
    )
    request = _make_request()
    prop = ProposedMetricRequirement(
        proposal_id="prop_1",
        space_id="space_living",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
        rationale="Salon space_living için en az 30 m²",
    )
    result = ArchitecturalIntentResult(
        assistant_message="Salon için alan önerisi.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_metric_test"),
        user_requirements=["Salon en az 30 m²"],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[],
        proposed_metric_requirements=[prop],
        needs_follow_up=False,
        follow_up_question=None,
        follow_up_topic=None,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )
    sanitized = validator.validate(result, request, metric_context=metric_context)
    assert sanitized.needs_user_confirmation is True
    assert sanitized.needs_follow_up is False
    assert sanitized.follow_up_question is None
    assert len(sanitized.proposed_metric_requirements) == 1
    # Check internal ID is sanitized out of rationale
    assert "space_living" not in (sanitized.proposed_metric_requirements[0].rationale or "")


def test_build_metric_conversation_context_success() -> None:
    snapshot = _make_brief_snapshot()
    graph = _make_spatial_graph()
    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_metric_test",
        state_version=2,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 11, 0, tzinfo=UTC),
        metric_requirements=MetricSpatialRequirements(
            project_id="proj_metric_test",
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 11, 0, tzinfo=UTC),
            space_requirements=[
                SpaceMetricRequirements(
                    space_id="sn_living_01",
                    requirements=[
                        MetricRequirement(
                            id="mr_1",
                            space_id="sn_living_01",
                            requirement_type=MetricRequirementType.MIN_AREA,
                            value=25.0,
                            unit=MetricUnit.SQUARE_METRE,
                            provenance=RelationshipProvenance.USER_CONFIRMED,
                            priority=Priority.MUST,
                            evidence_ids=["ev_1"],
                        )
                    ],
                )
            ],
            authoritative_requirement_ids=["mr_1"],
        ),
    )
    context = build_metric_conversation_context(snapshot, graph, plan_input_state)
    assert context is not None
    assert context.source_brief_version == 1
    assert context.source_plan_input_state_version == 2
    assert len(context.spaces) == 2
    living = next(s for s in context.spaces if s.space_id == "sn_living_01")
    assert living.display_name == "Salon"
    assert len(living.existing_requirements) == 1
    assert living.existing_requirements[0].requirement_type == MetricRequirementType.MIN_AREA
    assert living.existing_requirements[0].value == 25.0


def test_build_metric_conversation_context_none_when_uninitialized() -> None:
    assert build_metric_conversation_context(None, None, None) is None
    snapshot = _make_brief_snapshot()
    assert build_metric_conversation_context(snapshot, None, None) is None


def _make_metric_context() -> MetricConversationContext:
    return MetricConversationContext(
        spaces=[
            SpaceMetricContext(
                space_id="sn_living_01",
                display_name="Salon",
                function="LIVING",
                existing_requirements=[],
            ),
            SpaceMetricContext(
                space_id="sn_kitchen_01",
                display_name="Mutfak",
                function="COOKING",
                existing_requirements=[],
            ),
            SpaceMetricContext(
                space_id="sn_corridor_01",
                display_name="Koridor",
                function="CIRCULATION",
                existing_requirements=[],
            ),
        ],
        source_brief_version=1,
    )


def _make_metric_result(
    prop: ProposedMetricRequirement,
    assistant_msg: str = "Öneri",
) -> ArchitecturalIntentResult:
    return ArchitecturalIntentResult(
        assistant_message=assistant_msg,
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_metric_test"),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[],
        proposed_metric_requirements=[prop],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )


def test_metric_language_safety_min_area_explicit_accepted() -> None:
    # Case A: "Salon en az 30 m² olsun." MIN_AREA 30 => accepted
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Salon en az 30 m² olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    validated = validator.validate(res, req, metric_context=ctx)
    assert len(validated.proposed_metric_requirements) == 1
    assert validated.proposed_metric_requirements[0].value == 30.0


def test_metric_language_safety_min_area_unqualified_rejected() -> None:
    # Case B: "Salon 30 m² olsun." MIN_AREA 30 => PolicyValidationError
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Salon 30 m² olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="açık asgari niteleyici"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_safety_min_area_approximate_rejected() -> None:
    # Case C: "Salon yaklaşık 30 m² olsun." MIN_AREA 30 => PolicyValidationError
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Salon yaklaşık 30 m² olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="yaklaşık/belirsiz ifade"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_safety_min_area_invented_value_rejected() -> None:
    # Case D: "Salon en az 30 m² olsun." MIN_AREA 40 => PolicyValidationError
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Salon en az 30 m² olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=40.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="eşleşmiyor"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_negative_source_value_cannot_bind_positive_proposal() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    proposal = ProposedMetricRequirement(
        proposal_id="p_negative_source",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=35.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    with pytest.raises(PolicyValidationError, match="eşleşmiyor"):
        validator.validate(
            _make_metric_result(proposal),
            _make_request("Salon en az -35 m² olsun."),
            metric_context=_make_metric_context(),
        )


def test_metric_language_safety_max_area_explicit_accepted() -> None:
    # Case E: "Mutfak en fazla 20 m2 olsun." MAX_AREA 20 => accepted
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Mutfak en fazla 20 m2 olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_kitchen_01",
        requirement_type=MetricRequirementType.MAX_AREA,
        value=20.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    validated = validator.validate(res, req, metric_context=ctx)
    assert len(validated.proposed_metric_requirements) == 1
    assert validated.proposed_metric_requirements[0].value == 20.0


def test_metric_language_safety_min_clear_width_decimal_comma_accepted() -> None:
    # Case F: "Koridor net genişliği en az 1,20 metre olsun." MIN_CLEAR_WIDTH 1.20 => accepted
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Koridor net genişliği en az 1,20 metre olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_corridor_01",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=1.20,
        unit=MetricUnit.METRE,
    )
    res = _make_metric_result(prop)
    validated = validator.validate(res, req, metric_context=ctx)
    assert len(validated.proposed_metric_requirements) == 1
    assert validated.proposed_metric_requirements[0].value == 1.20


def test_metric_language_safety_min_clear_width_unqualified_rejected() -> None:
    # Case G: "Koridor 1.20 metre olsun." MIN_CLEAR_WIDTH 1.20 => rejected
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Koridor 1.20 metre olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_corridor_01",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=1.20,
        unit=MetricUnit.METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="açık asgari niteleyici"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_safety_no_numeric_value_rejected() -> None:
    # Case H: "Salon büyük olsun." MIN_AREA 30 => rejected
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Salon büyük olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="sayısal değer bulunamadı"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_cross_clause_qualifier_rejected() -> None:
    # A: "Mutfak en az 10 m² olsun, salon 30 m² olsun." -> Salon MIN_AREA 30 => REJECT
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Mutfak en az 10 m² olsun, salon 30 m² olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="açık asgari niteleyici"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_cross_clause_value_rejected() -> None:
    # B: "Mutfak en az 20 m² olsun, salon en az 30 m² olsun." -> Mutfak MIN_AREA 30 => REJECT
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Mutfak en az 20 m² olsun, salon en az 30 m² olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_kitchen_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="eşleşmiyor"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_min_clear_width_missing_width_word_rejected() -> None:
    # C: "Koridor en az 1.20 metre olsun." -> MIN_CLEAR_WIDTH 1.20 => REJECT (no width wording)
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Koridor en az 1.20 metre olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_corridor_01",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=1.20,
        unit=MetricUnit.METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="net genişlik ifadesi"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_min_clear_width_missing_metre_unit_rejected() -> None:
    # D: "Koridor net genişliği minimum 1.20 olsun." -> MIN_CLEAR_WIDTH 1.20 => REJECT
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Koridor net genişliği minimum 1.20 olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_corridor_01",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=1.20,
        unit=MetricUnit.METRE,
    )
    res = _make_metric_result(prop)
    with pytest.raises(PolicyValidationError, match="uzunluk birimi"):
        validator.validate(res, req, metric_context=ctx)


def test_metric_language_min_clear_width_standalone_m_accepted() -> None:
    # E: "Koridor net genişliği minimum 1.20 m olsun." -> MIN_CLEAR_WIDTH 1.20 => ACCEPT
    validator = ArchitecturalIntentPolicyValidator()
    ctx = _make_metric_context()
    req = _make_request("Koridor net genişliği minimum 1.20 m olsun.")
    prop = ProposedMetricRequirement(
        proposal_id="p1",
        space_id="sn_corridor_01",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=1.20,
        unit=MetricUnit.METRE,
    )
    res = _make_metric_result(prop)
    validated = validator.validate(res, req, metric_context=ctx)
    assert len(validated.proposed_metric_requirements) == 1
    assert validated.proposed_metric_requirements[0].value == 1.20


def test_metric_language_turkish_target_suffix_is_bound_to_salon() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    context = _make_metric_context()
    request = _make_request("Salonu en az 35 m² yap.")
    proposal = ProposedMetricRequirement(
        proposal_id="p_suffix",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=35.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    validated = validator.validate(
        _make_metric_result(proposal),
        request,
        metric_context=context,
    )

    assert validated.proposed_metric_requirements == [proposal]


def test_metric_language_softened_turkish_target_suffix_is_bound_to_kitchen() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    context = _make_metric_context()
    request = _make_request("Mutfağı en fazla 20 m² yap.")
    proposal = ProposedMetricRequirement(
        proposal_id="p_soft_suffix",
        space_id="sn_kitchen_01",
        requirement_type=MetricRequirementType.MAX_AREA,
        value=20.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    validated = validator.validate(
        _make_metric_result(proposal),
        request,
        metric_context=context,
    )

    assert validated.proposed_metric_requirements == [proposal]


def test_metric_language_ambiguous_target_binding_is_rejected() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(
                space_id="sn_child_01",
                display_name="Çocuk Odası",
                function="SLEEPING",
            ),
            SpaceMetricContext(
                space_id="sn_child_02",
                display_name="Çocuk Odası",
                function="SLEEPING",
            ),
        ],
        source_brief_version=1,
    )
    request = _make_request("Çocuk odasını en az 12 m² yap.")
    proposal = ProposedMetricRequirement(
        proposal_id="p_ambiguous",
        space_id="sn_child_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=12.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    with pytest.raises(PolicyValidationError, match="belirsiz"):
        validator.validate(_make_metric_result(proposal), request, metric_context=context)


def test_metric_language_separately_named_targets_in_one_clause_are_ambiguous() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(space_id="sn_room_01", display_name="Oda", function="SLEEPING"),
            SpaceMetricContext(
                space_id="sn_big_kitchen_01",
                display_name="Büyük Mutfak",
                function="COOKING",
            ),
        ],
        source_brief_version=1,
    )
    proposal = ProposedMetricRequirement(
        proposal_id="p_two_targets",
        space_id="sn_big_kitchen_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=35.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    with pytest.raises(PolicyValidationError, match="belirsiz"):
        validator.validate(
            _make_metric_result(proposal),
            _make_request("Oda ile Büyük Mutfağı en az 35 m² yap."),
            metric_context=context,
        )


def test_metric_language_longer_target_safely_shadows_nested_generic_name() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    context = MetricConversationContext(
        spaces=[
            SpaceMetricContext(space_id="sn_room_01", display_name="Oda", function="SLEEPING"),
            SpaceMetricContext(
                space_id="sn_child_01",
                display_name="Çocuk Odası",
                function="SLEEPING",
            ),
        ],
        source_brief_version=1,
    )
    proposal = ProposedMetricRequirement(
        proposal_id="p_nested_target",
        space_id="sn_child_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=12.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    validated = validator.validate(
        _make_metric_result(proposal),
        _make_request("Çocuk odasını en az 12 m² yap."),
        metric_context=context,
    )

    assert validated.proposed_metric_requirements == [proposal]


def test_metric_language_wrong_target_binding_is_rejected() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    request = _make_request("Mutfak en az 12 m² olsun.")
    proposal = ProposedMetricRequirement(
        proposal_id="p_wrong_target",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=12.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    with pytest.raises(PolicyValidationError, match="açıkça bağlanmıyor"):
        validator.validate(
            _make_metric_result(proposal),
            request,
            metric_context=_make_metric_context(),
        )


def test_metric_language_forged_requirement_type_is_rejected() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    request = _make_request("Salon en az 35 m² olsun.")
    forged = ProposedMetricRequirement(
        proposal_id="p_forged_type",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.MAX_AREA,
        value=35.0,
        unit=MetricUnit.SQUARE_METRE,
    )

    with pytest.raises(PolicyValidationError, match="açık azami niteleyici"):
        validator.validate(
            _make_metric_result(forged),
            request,
            metric_context=_make_metric_context(),
        )
