"""Tests for deterministic validation and node grounding of structured spatial proposals."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from brif_ai.brief.models.common import ConfirmationStatus, EvidenceSource, Priority
from brif_ai.brief.models.snapshot import BriefSnapshot, Evidence, SpaceRequest, Stakeholder
from brif_ai.conversation.elicitation.spatial import (
    format_spatial_relationship_statement,
    validate_and_ground_spatial_proposals,
)
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.models import (
    ProposedSpatialRelationship,
    RelationshipProvenance,
    SpatialRelationType,
)


@pytest.fixture
def sample_snapshot() -> BriefSnapshot:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    ev = Evidence(
        id="ev_test",
        source_type=EvidenceSource.CHAT,
        excerpt="Test evidence",
        source_reference="msg_1",
    )
    return BriefSnapshot(
        project_id="proj_spatial_test",
        schema_version="brief.v0",
        brief_version=1,
        created_at=now,
        stakeholders=[
            Stakeholder(
                id="stk_1",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[ev],
        brief_items=[],
        space_requests=[
            SpaceRequest(
                id="sr_bed",
                display_name="Yatak Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_child",
                display_name="Çocuk Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_living",
                display_name="Salon",
                space_function=SpaceFunction.LIVING,
                minimum_quantity=1,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_kitchen",
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
                minimum_quantity=1,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_guest",
                display_name="Misafir Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=1,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_garden",
                display_name="Bahçe",
                space_function=SpaceFunction.OTHER,
                minimum_quantity=1,
                mandatory=False,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
        ],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def test_ground_valid_discrete_nodes(sample_snapshot: BriefSnapshot) -> None:
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_bed_01",
            target_space_id="sn_bed_02",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    grounded = validate_and_ground_spatial_proposals(proposals, sample_snapshot)
    assert len(grounded) == 1
    assert grounded[0].source_space_id == "sn_bed_01"
    assert grounded[0].target_space_id == "sn_bed_02"
    assert grounded[0].relation_type == SpatialRelationType.NEAR
    assert grounded[0].provenance == RelationshipProvenance.USER_STATED


def test_ground_space_request_distinct_resolution(sample_snapshot: BriefSnapshot) -> None:
    # If LLM uses space request IDs for distinct spaces
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sr_kitchen",
            target_space_id="sr_living",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    grounded = validate_and_ground_spatial_proposals(proposals, sample_snapshot)
    assert len(grounded) == 1
    assert grounded[0].source_space_id == "sn_kitchen_01"
    assert grounded[0].target_space_id == "sn_living_01"


def test_reject_hallucinated_space_ids(sample_snapshot: BriefSnapshot) -> None:
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_sauna_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    grounded = validate_and_ground_spatial_proposals(proposals, sample_snapshot)
    assert grounded == []


def test_reject_self_relationship_on_proposal() -> None:
    with pytest.raises(ValueError, match="self-relationship not allowed"):
        ProposedSpatialRelationship(
            source_space_id="sn_living_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )


def test_format_spatial_relationship_statement(sample_snapshot: BriefSnapshot) -> None:
    proposal = ProposedSpatialRelationship(
        source_space_id="sn_bed_01",
        target_space_id="sn_bed_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
        requires_user_confirmation=True,
    )
    statement = format_spatial_relationship_statement(proposal, sample_snapshot)
    assert "Yatak Odası 1 ile Yatak Odası 2" in statement
    assert "birbirine yakın" in statement
    assert "Bu mekânsal ilişkiyi onaylıyor musunuz?" in statement
