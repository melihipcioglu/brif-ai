"""Unit tests for strict immutable Spatial Relationship contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import Priority
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialNode,
    SpatialRelationship,
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
    SpatialRelationType,
    UnconstrainedPair,
    generate_relationship_id,
    generate_spatial_node_id,
)


def test_spatial_relation_type_enums() -> None:
    expected = {
        "ADJACENT_TO",
        "NEAR",
        "SEPARATED_FROM",
        "VISUAL_CONNECTION",
        "DIRECT_ACCESS",
        "INDIRECT_ACCESS",
        "ACOUSTIC_SEPARATION",
        "PRIVACY_SEPARATION",
    }
    assert {e.value for e in SpatialRelationType} == expected


def test_relationship_provenance_enums() -> None:
    expected = {"USER_STATED", "AI_INFERRED", "USER_CONFIRMED"}
    assert {e.value for e in RelationshipProvenance} == expected


def test_generate_spatial_node_id() -> None:
    id1 = generate_spatial_node_id("sr_child_bedroom", 1)
    id2 = generate_spatial_node_id("sr_child_bedroom", 2)
    assert id1 == "sn_child_bedroom_01"
    assert id2 == "sn_child_bedroom_02"
    assert id1 != id2


def test_spatial_node_immutability_and_validation() -> None:
    node = SpatialNode(
        id="sn_living_01",
        display_name="Salon",
        function=SpaceFunction.LIVING,
        source_space_request_id="sr_living",
        instance_index=1,
        mandatory=True,
    )
    assert node.id == "sn_living_01"
    assert node.display_name == "Salon"
    assert node.function == SpaceFunction.LIVING
    assert node.instance_index == 1

    with pytest.raises(ValidationError):
        # Frozen contract rejection
        node.display_name = "Yeni Salon"

    with pytest.raises(ValidationError, match="extra"):
        SpatialNode(
            id="sn_living_01",
            display_name="Salon",
            function=SpaceFunction.LIVING,
            source_space_request_id="sr_living",
            extra_field="invalid",  # type: ignore[call-arg]
        )


def test_spatial_relationship_input_self_relation_rejection() -> None:
    with pytest.raises(ValidationError, match="self-relationship not allowed"):
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_kitchen_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_STATED,
        )


def test_spatial_relationship_input_user_confirmed_requires_evidence() -> None:
    # USER_CONFIRMED with empty evidence_ids must fail
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

    # USER_CONFIRMED with evidence_id succeeds
    rel_confirmed = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_chat_1"],
    )
    assert rel_confirmed.provenance == RelationshipProvenance.USER_CONFIRMED

    # USER_STATED and AI_INFERRED can have empty evidence_ids
    rel_stated = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
        evidence_ids=[],
    )
    assert rel_stated.evidence_ids == []

    rel_inferred = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.AI_INFERRED,
        evidence_ids=[],
    )
    assert rel_inferred.evidence_ids == []


def test_spatial_relationship_input_duplicate_evidence_rejection() -> None:
    with pytest.raises(ValidationError, match="duplicate evidence id"):
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_STATED,
            evidence_ids=["ev_1", "ev_1"],
        )


def test_generate_relationship_id_deterministic() -> None:
    id1 = generate_relationship_id(
        "proj_01",
        SpatialRelationType.ADJACENT_TO,
        "sn_a_01",
        "sn_b_01",
        bidirectional=True,
    )
    id2 = generate_relationship_id(
        "proj_01",
        SpatialRelationType.ADJACENT_TO,
        "sn_b_01",
        "sn_a_01",
        bidirectional=True,
    )
    assert id1 == id2
    assert id1.startswith("srel_")


def test_unconstrained_pair_ordering_validation() -> None:
    pair = UnconstrainedPair(space_a_id="sn_a_01", space_b_id="sn_b_01")
    assert pair.space_a_id == "sn_a_01"
    assert pair.space_b_id == "sn_b_01"

    with pytest.raises(ValidationError, match="must connect two distinct spaces"):
        UnconstrainedPair(space_a_id="sn_a_01", space_b_id="sn_a_01")

    with pytest.raises(ValidationError, match="space_a_id <= space_b_id"):
        UnconstrainedPair(space_a_id="sn_z_01", space_b_id="sn_a_01")


def test_spatial_relationship_graph_serialization_round_trip() -> None:
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    node1 = SpatialNode(
        id="sn_kitchen_01",
        display_name="Mutfak",
        function=SpaceFunction.COOKING,
        source_space_request_id="sr_kitchen",
        instance_index=1,
    )
    node2 = SpatialNode(
        id="sn_living_01",
        display_name="Salon",
        function=SpaceFunction.LIVING,
        source_space_request_id="sr_living",
        instance_index=1,
    )
    rel = SpatialRelationship(
        id="srel_test1",
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_chat_1"],
        bidirectional=True,
    )
    graph = SpatialRelationshipGraph(
        schema_version="spatial_graph.v0",
        project_id="proj_house",
        source_brief_version=2,
        created_at=now,
        nodes=[node1, node2],
        relationships=[rel],
        unconstrained_pairs=[],
        conflicts=[],
    )

    dumped = graph.model_dump(mode="json")
    restored = SpatialRelationshipGraph.model_validate(dumped)
    assert restored == graph
    assert restored.nodes[0].display_name == "Mutfak"
    assert restored.relationships[0].provenance == RelationshipProvenance.USER_CONFIRMED


def test_spatial_relationship_graph_integrity_validation() -> None:
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    node1 = SpatialNode(
        id="sn_kitchen_01",
        display_name="Mutfak",
        function=SpaceFunction.COOKING,
        source_space_request_id="sr_kitchen",
        instance_index=1,
    )

    # Unknown target space in relationship
    rel_invalid = SpatialRelationship(
        id="srel_test1",
        source_space_id="sn_kitchen_01",
        target_space_id="sn_nonexistent_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )
    with pytest.raises(
        ValidationError,
        match="references unknown target_space_id 'sn_nonexistent_01'",
    ):
        SpatialRelationshipGraph(
            project_id="proj_house",
            source_brief_version=1,
            created_at=now,
            nodes=[node1],
            relationships=[rel_invalid],
        )

    # Duplicate node ID
    with pytest.raises(ValidationError, match="duplicate spatial node id 'sn_kitchen_01'"):
        SpatialRelationshipGraph(
            project_id="proj_house",
            source_brief_version=1,
            created_at=now,
            nodes=[node1, node1],
            relationships=[],
        )
