"""Tests for ProposedMetricRequirement domain contracts and safety invariants."""

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import Priority
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.llm.contracts import (
    ActionType,
    ArchitecturalIntentResult,
    EntityTarget,
    IntentType,
    PendingProposalContext,
    ProposedAction,
)
from brif_ai.spatial.metrics.models import (
    MetricRequirementType,
    MetricUnit,
    ProposedMetricRequirement,
)
from brif_ai.spatial.models import (
    ProposedSpatialRelationship,
    RelationshipProvenance,
    SpatialRelationType,
)


def test_proposed_metric_requirement_valid_min_area() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_01",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
        rationale="Salon en az 30 m² olmalı",
        requires_user_confirmation=True,
    )
    assert prop.proposal_id == "prop_metric_01"
    assert prop.space_id == "sp_living_room"
    assert prop.requirement_type == MetricRequirementType.MIN_AREA
    assert prop.value == 30.0
    assert prop.unit == MetricUnit.SQUARE_METRE
    assert prop.rationale == "Salon en az 30 m² olmalı"
    assert prop.requires_user_confirmation is True


def test_proposed_metric_requirement_valid_max_area() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_02",
        space_id="sp_kitchen",
        requirement_type=MetricRequirementType.MAX_AREA,
        value=20.0,
        unit=MetricUnit.SQUARE_METRE,
        rationale="Mutfak en fazla 20 m² olsun",
        requires_user_confirmation=True,
    )
    assert prop.requirement_type == MetricRequirementType.MAX_AREA
    assert prop.value == 20.0
    assert prop.unit == MetricUnit.SQUARE_METRE


def test_proposed_metric_requirement_valid_min_clear_width() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_03",
        space_id="sp_corridor",
        requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
        value=1.2,
        unit=MetricUnit.METRE,
        rationale="Koridor net genişliği en az 1.20 metre olsun",
        requires_user_confirmation=True,
    )
    assert prop.requirement_type == MetricRequirementType.MIN_CLEAR_WIDTH
    assert prop.value == 1.2
    assert prop.unit == MetricUnit.METRE


def test_proposed_metric_requirement_rejects_target_area() -> None:
    with pytest.raises(
        ValidationError, match="TARGET_AREA is not supported for conversational proposals in V0"
    ):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_living_room",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
        )


def test_proposed_metric_requirement_unit_mismatch() -> None:
    with pytest.raises(ValidationError, match="requires unit SQUARE_METRE"):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_living_room",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=30.0,
            unit=MetricUnit.METRE,
        )

    with pytest.raises(ValidationError, match="requires unit SQUARE_METRE"):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_kitchen",
            requirement_type=MetricRequirementType.MAX_AREA,
            value=20.0,
            unit=MetricUnit.METRE,
        )

    with pytest.raises(ValidationError, match="requires unit METRE"):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_corridor",
            requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
            value=1.2,
            unit=MetricUnit.SQUARE_METRE,
        )


def test_proposed_metric_requirement_non_positive_value() -> None:
    with pytest.raises(ValidationError, match="strictly positive"):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_living_room",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=0.0,
            unit=MetricUnit.SQUARE_METRE,
        )

    with pytest.raises(ValidationError, match="strictly positive"):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_living_room",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=-10.0,
            unit=MetricUnit.SQUARE_METRE,
        )

    with pytest.raises(ValidationError, match="must be finite"):
        ProposedMetricRequirement(
            proposal_id="prop_metric_invalid",
            space_id="sp_living_room",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=float("inf"),
            unit=MetricUnit.SQUARE_METRE,
        )


def test_pending_proposal_context_with_metric_requirement() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    context = PendingProposalContext(
        context_fingerprint="fp_123",
        generation_id=1,
        metric_requirement=prop,
    )
    assert context.status == "pending_user_confirmation"
    assert context.metric_requirement == prop
    assert context.action is None
    assert context.brief_mutation is None
    assert context.spatial_relationship is None


def test_pending_proposal_context_xor_validation() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    action = ProposedAction(
        action_type=ActionType.SUGGEST_SPACE_RESIZE,
        description="Split room",
        target_entity_id="room_1",
        requires_user_confirmation=True,
    )
    with pytest.raises(
        ValidationError,
        match=(
            "Exactly one of action, brief_mutation, spatial_relationship, "
            "metric_requirement, site_geometry, or floor_plate"
        ),
    ):
        PendingProposalContext(
            context_fingerprint="fp_123",
            generation_id=1,
            metric_requirement=prop,
            action=action,
        )

    with pytest.raises(
        ValidationError,
        match=(
            "Exactly one of action, brief_mutation, spatial_relationship, "
            "metric_requirement, site_geometry, or floor_plate"
        ),
    ):
        PendingProposalContext(
            context_fingerprint="fp_123",
            generation_id=1,
        )


def test_architectural_intent_result_with_metric_requirement_valid() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    result = ArchitecturalIntentResult(
        assistant_message="Salon için en az 30 m² alan gereksinimi öneriyorum.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_1"),
        user_requirements=["Salon en az 30 m² olsun"],
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
    assert len(result.proposed_metric_requirements) == 1
    assert result.needs_user_confirmation is True
    assert result.needs_follow_up is False


def test_architectural_intent_result_metric_requires_confirmation() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    with pytest.raises(
        ValidationError, match="proposed metric requirements require user confirmation"
    ):
        ArchitecturalIntentResult(
            assistant_message="Salon için en az 30 m² alan gereksinimi öneriyorum.",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id="proj_1"),
            user_requirements=["Salon en az 30 m² olsun"],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[],
            proposed_metric_requirements=[prop],
            needs_follow_up=False,
            needs_user_confirmation=False,
            confidence=0.9,
            warnings=[],
        )


def test_architectural_intent_result_metric_forbids_follow_up() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    with pytest.raises(
        ValidationError, match="needs_follow_up must be false when metric requirements are present"
    ):
        ArchitecturalIntentResult(
            assistant_message="Salon için en az 30 m² alan gereksinimi öneriyorum.",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id="proj_1"),
            user_requirements=["Salon en az 30 m² olsun"],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[],
            proposed_metric_requirements=[prop],
            needs_follow_up=True,
            follow_up_question="Başka bir oda için alan belirleyelim mi?",
            follow_up_topic=ElicitationTopic.SPACE_PROGRAM,
            needs_user_confirmation=True,
            confidence=0.9,
            warnings=[],
        )


def test_architectural_intent_result_metric_cannot_mix_proposals() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    spatial_prop = ProposedSpatialRelationship(
        source_space_id="sp_living_room",
        target_space_id="sp_kitchen",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
        requires_user_confirmation=True,
    )
    with pytest.raises(
        ValidationError,
        match="cannot mix proposed spatial relationships with proposed metric requirements",
    ):
        ArchitecturalIntentResult(
            assistant_message="Test",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id="proj_1"),
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[spatial_prop],
            proposed_metric_requirements=[prop],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=0.9,
            warnings=[],
        )


def test_architectural_intent_result_compare_cannot_have_metric() -> None:
    prop = ProposedMetricRequirement(
        proposal_id="prop_metric_1",
        space_id="sp_living_room",
        requirement_type=MetricRequirementType.MIN_AREA,
        value=30.0,
        unit=MetricUnit.SQUARE_METRE,
    )
    with pytest.raises(
        ValidationError,
        match="compare_alternatives cannot produce brief mutations or metric proposals",
    ):
        ArchitecturalIntentResult(
            assistant_message="Alternatif 1 vs Alternatif 2",
            intent=IntentType.COMPARE_ALTERNATIVES,
            target=EntityTarget(project_id="proj_1"),
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
