"""Unit tests for spatial relationship validator and contradiction matrix."""

from __future__ import annotations

import pytest

from brif_ai.brief.models.common import Priority
from brif_ai.spatial.errors import (
    InvalidEvidenceReferenceError,
    NonexistentSpaceError,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.validator import (
    deduplicate_and_materialize_relationships,
    detect_spatial_conflicts,
    validate_evidence_references,
    validate_spatial_relationship_inputs,
)


def test_validate_spatial_relationship_inputs_success() -> None:
    inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_STATED,
        )
    ]
    validate_spatial_relationship_inputs(inputs, {"sn_a_01", "sn_b_01", "sn_c_01"})


def test_validate_spatial_relationship_inputs_nonexistent_space() -> None:
    inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_ghost_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
        )
    ]
    with pytest.raises(NonexistentSpaceError, match="nonexistent target_space_id 'sn_ghost_01'"):
        validate_spatial_relationship_inputs(inputs, {"sn_a_01", "sn_b_01"})


def test_validate_evidence_references_rules() -> None:
    valid_evidence = {"ev_chat_1", "ev_chat_2"}

    # 1. USER_CONFIRMED with valid evidence_ids passes
    inputs_confirmed_valid = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_chat_1", "ev_chat_2"],
        )
    ]
    validate_evidence_references(inputs_confirmed_valid, valid_evidence)

    # 2. USER_CONFIRMED with nonexistent evidence_id raises InvalidEvidenceReferenceError
    inputs_confirmed_nonexistent = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_ghost_evidence"],
        )
    ]
    with pytest.raises(
        InvalidEvidenceReferenceError,
        match="references nonexistent evidence_id 'ev_ghost_evidence'",
    ):
        validate_evidence_references(inputs_confirmed_nonexistent, valid_evidence)

    # 3. USER_STATED and AI_INFERRED with empty evidence_ids pass
    inputs_unconfirmed_empty = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            evidence_ids=[],
        ),
        SpatialRelationshipInput(
            source_space_id="sn_b_01",
            target_space_id="sn_c_01",
            relation_type=SpatialRelationType.INDIRECT_ACCESS,
            provenance=RelationshipProvenance.AI_INFERRED,
            evidence_ids=[],
        ),
    ]
    validate_evidence_references(inputs_unconfirmed_empty, valid_evidence)

    # 4. USER_STATED with nonexistent evidence_id raises InvalidEvidenceReferenceError
    inputs_stated_nonexistent = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            evidence_ids=["ev_ghost_evidence"],
        )
    ]
    with pytest.raises(
        InvalidEvidenceReferenceError,
        match="references nonexistent evidence_id 'ev_ghost_evidence'",
    ):
        validate_evidence_references(inputs_stated_nonexistent, valid_evidence)


def test_deduplicate_and_materialize_exact_duplicates() -> None:
    input1 = SpatialRelationshipInput(
        source_space_id="sn_living_01",
        target_space_id="sn_kitchen_01",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
        evidence_ids=["ev_1"],
    )
    # Inverse order with same parameters and bidirectional=True
    input2 = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
        evidence_ids=["ev_2"],
    )

    materialized = deduplicate_and_materialize_relationships(
        "proj_01",
        [input1, input2],
    )

    assert len(materialized) == 1
    rel = materialized[0]
    assert rel.source_space_id == "sn_kitchen_01"
    assert rel.target_space_id == "sn_living_01"
    assert rel.relation_type == SpatialRelationType.ADJACENT_TO
    assert rel.provenance == RelationshipProvenance.USER_STATED
    assert rel.evidence_ids == ["ev_1", "ev_2"]


def test_provenance_preservation_without_silent_promotion() -> None:
    inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_bed_01",
            target_space_id="sn_bed_02",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_dining_01",
            relation_type=SpatialRelationType.DIRECT_ACCESS,
            provenance=RelationshipProvenance.AI_INFERRED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_bath_01",
            target_space_id="sn_bed_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_confirmed_1"],
        ),
    ]

    materialized = deduplicate_and_materialize_relationships("proj_01", inputs)
    provenances = {r.relation_type: r.provenance for r in materialized}

    assert provenances[SpatialRelationType.NEAR] == RelationshipProvenance.USER_STATED
    assert provenances[SpatialRelationType.DIRECT_ACCESS] == RelationshipProvenance.AI_INFERRED
    assert provenances[SpatialRelationType.ADJACENT_TO] == RelationshipProvenance.USER_CONFIRMED


@pytest.mark.parametrize(
    ("type_1", "type_2"),
    [
        (SpatialRelationType.ADJACENT_TO, SpatialRelationType.SEPARATED_FROM),
        (SpatialRelationType.NEAR, SpatialRelationType.SEPARATED_FROM),
        (SpatialRelationType.DIRECT_ACCESS, SpatialRelationType.SEPARATED_FROM),
    ],
)
def test_detect_spatial_conflicts_matrix(
    type_1: SpatialRelationType,
    type_2: SpatialRelationType,
) -> None:
    inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=type_1,
            provenance=RelationshipProvenance.USER_STATED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=type_2,
            provenance=RelationshipProvenance.USER_STATED,
        ),
    ]

    materialized = deduplicate_and_materialize_relationships("proj_01", inputs)
    assert len(materialized) == 2

    conflicts = detect_spatial_conflicts(materialized)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.space_a_id == "sn_a_01"
    assert conflict.space_b_id == "sn_b_01"
    assert set(conflict.conflicting_relation_types) == {type_1, type_2}
    assert len(conflict.reason) > 10


def test_compatible_relationships_do_not_produce_conflicts() -> None:
    # Architectural pairings that are NOT logical contradictions:
    # 1. ADJACENT_TO + DIRECT_ACCESS
    # 2. ADJACENT_TO + VISUAL_CONNECTION
    # 3. DIRECT_ACCESS + INDIRECT_ACCESS (multiple routes)
    # 4. ADJACENT_TO + ACOUSTIC_SEPARATION (soundproof wall)
    # 5. ACOUSTIC_SEPARATION + DIRECT_ACCESS (acoustically sealed heavy door)
    # 6. PRIVACY_SEPARATION + VISUAL_CONNECTION (translucent / switchable smart glass)
    inputs = [
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_STATED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.DIRECT_ACCESS,
            provenance=RelationshipProvenance.USER_STATED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.ACOUSTIC_SEPARATION,
            provenance=RelationshipProvenance.USER_STATED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.PRIVACY_SEPARATION,
            provenance=RelationshipProvenance.USER_STATED,
        ),
        SpatialRelationshipInput(
            source_space_id="sn_a_01",
            target_space_id="sn_b_01",
            relation_type=SpatialRelationType.VISUAL_CONNECTION,
            provenance=RelationshipProvenance.USER_STATED,
        ),
    ]
    materialized = deduplicate_and_materialize_relationships("proj_01", inputs)
    conflicts = detect_spatial_conflicts(materialized)
    assert conflicts == []
