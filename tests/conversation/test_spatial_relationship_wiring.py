"""Acceptance and unit tests for Conversation -> Spatial Relationship wiring."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import (
    ConfirmationStatus,
    EvidenceSource,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefItem,
    BriefSnapshot,
    Evidence,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    PendingProposalContext,
    ProposedAction,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
)
from brif_ai.spatial.models import (
    ProposedSpatialRelationship,
    RelationshipProvenance,
    SpatialRelationType,
    project_space_requests_to_spatial_nodes,
)


def sample_brief_with_quantities() -> BriefSnapshot:
    return BriefSnapshot(
        project_id="proj_villa_test",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
        ],
        evidence=[
            Evidence(
                id="ev_chat_1",
                source_type=EvidenceSource.CHAT,
                source_reference="chat_1",
                excerpt="Çocuk odaları birbirine yakın olsun.",
            )
        ],
        brief_items=[
            BriefItem(
                id="bi_1",
                kind="NEED",  # type: ignore[arg-type]
                normalized_statement="Mutfak salona bitişik olmalı.",
                priority=Priority.MUST,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            )
        ],
        space_requests=[
            SpaceRequest(
                id="sr_living",
                display_name="Salon",
                space_function=SpaceFunction.LIVING,
                minimum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_child_room",
                display_name="Çocuk Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,  # Multi-instance
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
        ],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def test_acceptance_1_two_instance_resolution() -> None:
    """Requirement 1: Confirmed SpaceRequest with minimum_quantity=2 expands to 2 nodes."""
    snapshot = sample_brief_with_quantities()
    nodes = project_space_requests_to_spatial_nodes(snapshot.space_requests)

    assert len(nodes) == 3
    node_ids = [n.id for n in nodes]
    assert "sn_child_room_01" in node_ids
    assert "sn_child_room_02" in node_ids
    assert "sn_living_01" in node_ids

    child_1 = next(n for n in nodes if n.id == "sn_child_room_01")
    child_2 = next(n for n in nodes if n.id == "sn_child_room_02")
    assert child_1.display_name == "Çocuk Odası 1"
    assert child_2.display_name == "Çocuk Odası 2"
    assert child_1.source_space_request_id == "sr_child_room"
    assert child_2.source_space_request_id == "sr_child_room"


def test_acceptance_2_structured_conversation_proposal() -> None:
    """Requirement 2: Structured result represents NEAR without mutations or actions."""
    proposal = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
        rationale="Kullanıcı çocuk odalarının yakın olmasını istedi.",
        requires_user_confirmation=True,
    )

    result = ArchitecturalIntentResult(
        assistant_message="Çocuk odaları birbirine yakın olacak şekilde planlanmasını öneriyorum.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_villa_test"),
        user_requirements=["Çocuk odaları yakın olsun"],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[proposal],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.95,
        warnings=[],
    )

    assert len(result.proposed_spatial_relationships) == 1
    assert result.proposed_spatial_relationships[0].relation_type == SpatialRelationType.NEAR
    assert result.proposed_spatial_relationships[0].provenance == RelationshipProvenance.USER_STATED
    assert result.proposed_actions == []
    assert result.proposed_brief_mutations == []


def test_acceptance_3_unknown_node_rejection() -> None:
    """Requirement 3: Proposal referencing an invented/unknown node ID fails deterministically."""
    snapshot = sample_brief_with_quantities()
    validator = ArchitecturalIntentPolicyValidator()

    request = ConversationRequest(
        message="Çocuk odası bahçeye baksın",
        active_context=ActiveContextSnapshot(
            project_id="proj_villa_test",
            context_fingerprint="ctx_1",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=snapshot,
    )

    invalid_proposal = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_invented_garden_01",  # Invented node
        relation_type=SpatialRelationType.VISUAL_CONNECTION,
        provenance=RelationshipProvenance.USER_STATED,
    )

    result = ArchitecturalIntentResult(
        assistant_message="Bahçe bağlantısı önerildi.",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(project_id="proj_villa_test"),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[],
        proposed_spatial_relationships=[invalid_proposal],
        needs_follow_up=False,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )

    with pytest.raises(
        PolicyValidationError,
        match="Bilinmeyen hedef mekân kimliği 'sn_invented_garden_01'",
    ):
        validator.validate_semantic_integrity(result, request)


def test_acceptance_4_self_relation_rejection() -> None:
    """Requirement 4: node A -> node A fails."""
    with pytest.raises(ValidationError, match="self-relationship not allowed"):
        ProposedSpatialRelationship(
            source_space_id="sn_child_room_01",
            target_space_id="sn_child_room_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
        )


def test_acceptance_5_llm_cannot_confirm() -> None:
    """Requirement 5: Proposal with provenance=USER_CONFIRMED rejected at contract level."""
    with pytest.raises(ValidationError, match="cannot have provenance USER_CONFIRMED"):
        ProposedSpatialRelationship(
            source_space_id="sn_child_room_01",
            target_space_id="sn_child_room_02",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_CONFIRMED,
        )


def test_single_proposal_category_per_result_invariant() -> None:
    """Constraint 4: Enforce a single proposal category per ArchitecturalIntentResult."""
    proposal = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )
    action = ProposedAction(
        action_type="suggest_space_resize",  # type: ignore[arg-type]
        target_entity_id="sn_living_01",
        description="Salonu büyüt",
        requires_user_confirmation=True,
    )

    # Mixing spatial proposal with action must fail
    with pytest.raises(
        ValidationError,
        match="cannot mix proposed spatial relationships with proposed actions",
    ):
        ArchitecturalIntentResult(
            assistant_message="Öneriler",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id="proj_villa_test"),
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[action],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[proposal],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=0.9,
            warnings=[],
        )


def test_pending_proposal_context_xor_validation() -> None:
    """PendingProposalContext must contain exactly ONE proposal category."""
    spatial_prop = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )
    action_prop = ProposedAction(
        action_type="suggest_space_resize",  # type: ignore[arg-type]
        target_entity_id="sn_living_01",
        description="Salonu büyüt",
        requires_user_confirmation=True,
    )

    # Valid with only spatial
    ctx_valid = PendingProposalContext(
        context_fingerprint="ctx_1",
        generation_id=1,
        spatial_relationship=spatial_prop,
    )
    assert ctx_valid.spatial_relationship is not None
    assert ctx_valid.action is None
    assert ctx_valid.brief_mutation is None

    # Invalid with both spatial and action
    with pytest.raises(
        ValidationError,
        match="Exactly one of action, brief_mutation, spatial_relationship, or metric_requirement",
    ):
        PendingProposalContext(
            context_fingerprint="ctx_1",
            generation_id=1,
            action=action_prop,
            spatial_relationship=spatial_prop,
        )

    # Invalid with none
    with pytest.raises(
        ValidationError,
        match="Exactly one of action, brief_mutation, spatial_relationship, or metric_requirement",
    ):
        PendingProposalContext(
            context_fingerprint="ctx_1",
            generation_id=1,
        )
