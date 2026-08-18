"""Unit tests for SpatialRelationshipGraphBuilder."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import (
    BriefItemKind,
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
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.errors import (
    InvalidEvidenceReferenceError,
    NonexistentSpaceError,
    SpatialGraphError,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)


def sample_brief_snapshot() -> BriefSnapshot:
    """Construct an approved BriefSnapshot with 3 SpaceRequests."""
    return BriefSnapshot(
        project_id="proj_villa_01",
        schema_version="brief.v0",
        brief_version=3,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_owner",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[
            Evidence(
                id="ev_chat_1",
                source_type=EvidenceSource.CHAT,
                source_reference="chatmsg_1",
                excerpt="Mutfak salona yakın olsun ve bahçeye baksın.",
            ),
            Evidence(
                id="ev_chat_2",
                source_type=EvidenceSource.CHAT,
                source_reference="chatmsg_2",
                excerpt="İki çocuk odası yan yana olsun.",
            ),
        ],
        brief_items=[
            BriefItem(
                id="bi_statement_1",
                kind=BriefItemKind.NEED,
                # Free-text mentioning relations — MUST NEVER BE PARSED BY BUILDER!
                normalized_statement=(
                    "Mutfak ile salon birbirine çok yakın olmalı ve doğrudan geçiş bulunmalı."
                ),
                priority=Priority.MUST,
                stakeholder_ids=["stk_owner"],
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
                stakeholder_ids=["stk_owner"],
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_kitchen",
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
                minimum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_owner"],
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_bedroom",
                display_name="Çocuk Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,  # Multi-instance expansion!
                mandatory=True,
                stakeholder_ids=["stk_owner"],
                evidence_ids=["ev_chat_2"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
        ],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def test_builder_expands_discrete_nodes_from_quantity() -> None:
    snapshot = sample_brief_snapshot()
    builder = SpatialRelationshipGraphBuilder()

    relationships = [
        # Relationship between discrete child bedroom 1 and child bedroom 2
        SpatialRelationshipInput(
            source_space_id="sn_bedroom_01",
            target_space_id="sn_bedroom_02",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=["ev_chat_2"],
        ),
        # Relationship between kitchen and living room
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=["ev_chat_1"],
        ),
    ]

    graph = builder.build(snapshot, relationships)

    assert graph.project_id == "proj_villa_01"
    assert graph.source_brief_version == 3

    # sr_living (1) + sr_kitchen (1) + sr_bedroom (2) = 4 discrete nodes
    assert len(graph.nodes) == 4
    node_ids = [n.id for n in graph.nodes]
    assert node_ids == ["sn_bedroom_01", "sn_bedroom_02", "sn_kitchen_01", "sn_living_01"]

    # Check discrete node properties
    bed1 = graph.nodes[0]
    assert bed1.id == "sn_bedroom_01"
    assert bed1.display_name == "Çocuk Odası 1"
    assert bed1.source_space_request_id == "sr_bedroom"
    assert bed1.instance_index == 1

    bed2 = graph.nodes[1]
    assert bed2.id == "sn_bedroom_02"
    assert bed2.display_name == "Çocuk Odası 2"
    assert bed2.source_space_request_id == "sr_bedroom"
    assert bed2.instance_index == 2

    # Exactly 2 structured relationships
    assert len(graph.relationships) == 2

    # Total pairs for 4 nodes: C(4,2) = 6 pairs.
    # Stated pairs (2): (sn_bedroom_01, sn_bedroom_02) and (sn_kitchen_01, sn_living_01)
    # Remaining unconstrained pairs: 4
    assert len(graph.unconstrained_pairs) == 4
    assert graph.conflicts == []


def test_builder_validates_evidence_referential_integrity() -> None:
    snapshot = sample_brief_snapshot()
    builder = SpatialRelationshipGraphBuilder()

    # 1. USER_CONFIRMED with nonexistent evidence ID
    invalid_rel = [
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_ghost_evidence"],
        )
    ]
    with pytest.raises(
        InvalidEvidenceReferenceError,
        match="references nonexistent evidence_id 'ev_ghost_evidence'",
    ):
        builder.build(snapshot, invalid_rel)

    # 2. USER_CONFIRMED with empty evidence_ids fails validation
    with pytest.raises(
        ValidationError,
        match="USER_CONFIRMED relationship requires at least one evidence_id",
    ):
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[],
        )

    # 3. USER_CONFIRMED with valid evidence ID succeeds
    valid_rel = [
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_chat_1"],
        )
    ]
    graph = builder.build(snapshot, valid_rel)
    assert len(graph.relationships) == 1
    assert graph.relationships[0].evidence_ids == ["ev_chat_1"]
    assert graph.relationships[0].provenance == RelationshipProvenance.USER_CONFIRMED

    # 4. USER_STATED and AI_INFERRED with empty evidence_ids succeed
    unconfirmed_rel = [
        SpatialRelationshipInput(
            source_space_id="sn_bedroom_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            evidence_ids=[],
        ),
        SpatialRelationshipInput(
            source_space_id="sn_bedroom_02",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.INDIRECT_ACCESS,
            provenance=RelationshipProvenance.AI_INFERRED,
            evidence_ids=[],
        ),
    ]
    graph_unconfirmed = builder.build(snapshot, unconfirmed_rel)
    assert len(graph_unconfirmed.relationships) == 2
    assert graph_unconfirmed.relationships[0].provenance == RelationshipProvenance.USER_STATED
    assert graph_unconfirmed.relationships[1].provenance == RelationshipProvenance.AI_INFERRED


def test_builder_does_not_parse_free_text() -> None:
    """Proof that BriefItem.normalized_statement mentioning relations is NOT parsed into edges."""
    snapshot = sample_brief_snapshot()
    builder = SpatialRelationshipGraphBuilder()

    # Pass EMPTY structured relationships
    graph = builder.build(snapshot, relationships=[])

    # Relationships must remain empty despite brief_items free text
    assert graph.relationships == []
    # All 6 combinations among 4 discrete nodes are derived as unconstrained
    assert len(graph.unconstrained_pairs) == 6


def test_builder_preserves_conflicts_as_structured_records() -> None:
    """Contradictory relationships produce SpatialConflict without crashing construction."""
    snapshot = sample_brief_snapshot()
    builder = SpatialRelationshipGraphBuilder()

    contradictory_inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_bedroom_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            evidence_ids=["ev_chat_1"],
        ),
        SpatialRelationshipInput(
            source_space_id="sn_bedroom_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.SEPARATED_FROM,
            provenance=RelationshipProvenance.USER_STATED,
            evidence_ids=["ev_chat_1"],
        ),
    ]

    graph = builder.build(snapshot, contradictory_inputs)

    assert len(graph.relationships) == 2
    assert len(graph.conflicts) == 1
    conflict = graph.conflicts[0]
    assert conflict.space_a_id == "sn_bedroom_01"
    assert conflict.space_b_id == "sn_living_01"
    assert set(conflict.conflicting_relation_types) == {
        SpatialRelationType.NEAR,
        SpatialRelationType.SEPARATED_FROM,
    }


def test_builder_fails_on_nonexistent_space_reference() -> None:
    snapshot = sample_brief_snapshot()
    builder = SpatialRelationshipGraphBuilder()

    invalid_input = [
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_ghost_room_01",
            relation_type=SpatialRelationType.DIRECT_ACCESS,
            provenance=RelationshipProvenance.USER_STATED,
        )
    ]

    with pytest.raises(
        NonexistentSpaceError,
        match="nonexistent target_space_id 'sn_ghost_room_01'",
    ):
        builder.build(snapshot, invalid_input)


def test_builder_fails_on_empty_spaces() -> None:
    empty_snapshot = BriefSnapshot(
        project_id="proj_empty",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
        ],
        evidence=[],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )
    builder = SpatialRelationshipGraphBuilder()
    with pytest.raises(SpatialGraphError, match="No suitable spaces found"):
        builder.build(empty_snapshot)
