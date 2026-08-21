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
