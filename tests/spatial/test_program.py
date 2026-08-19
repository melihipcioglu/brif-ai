"""Focused tests for BRIF.AI Spatial Program V0 deterministic pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import (
    ConfirmationStatus,
    EvidenceSource,
    OpenQuestionStatus,
)
from brif_ai.brief.models.snapshot import (
    BriefSnapshot,
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
    SpatialRelationType,
    project_space_requests_to_spatial_nodes,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.errors import (
    BriefNotReadyError,
    SpatialProgramConflictBlockerError,
    SpatialProgramMissingInputError,
    SpatialProgramNodeMismatchError,
    SpatialProgramProjectMismatchError,
    SpatialProgramVersionMismatchError,
)
from brif_ai.spatial.program.models import SpatialProgram

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


def _evidence() -> Evidence:
    return Evidence(
        id="ev_ready_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client stated space requirements.",
    )


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


def _ready_snapshot(
    *,
    project_id: str = "proj_test_program",
    brief_version: int = 1,
    space_requests: list[SpaceRequest] | None = None,
    open_questions: list[OpenQuestion] | None = None,
    evidence: list[Evidence] | None = None,
) -> BriefSnapshot:
    ev = evidence or [_evidence()]
    spaces = space_requests or [
        SpaceRequest(
            id="sr_living",
            display_name="Salon",
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev[0].id],
        ),
        SpaceRequest(
            id="sr_kitchen",
            display_name="Mutfak",
            space_function=SpaceFunction.COOKING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev[0].id],
        ),
        SpaceRequest(
            id="sr_bed",
            display_name="Yatak Odası",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=2,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev[0].id],
        ),
    ]
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
        created_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_owner",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=ev,
        brief_items=[],
        space_requests=spaces,
        usage_scenarios=[],
        contradictions=[],
        open_questions=open_questions if open_questions is not None else _closed_topic_questions(),
    )


def _matching_graph(
    snapshot: BriefSnapshot,
    relationships: list[SpatialRelationshipInput] | None = None,
) -> SpatialRelationshipGraph:
    builder = SpatialRelationshipGraphBuilder()
    return builder.build(
        snapshot,
        relationships or [],
        created_at=datetime(2026, 8, 19, 12, 5, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_ready_brief_and_matching_graph_produces_spatial_program() -> None:
    snapshot = _ready_snapshot()
    rel_input = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_ready_01"],
    )
    graph = _matching_graph(snapshot, [rel_input])

    builder = SpatialProgramBuilder()
    program = builder.build(snapshot, graph)

    assert isinstance(program, SpatialProgram)
    assert program.schema_version == "spatial_program.v0"
    assert program.project_id == snapshot.project_id
    assert program.source_brief_version == snapshot.brief_version
    assert program.created_at == graph.created_at
    assert len(program.spaces) == 4
    assert len(program.relationships) == 1
    assert program.relationships[0].relation_type == SpatialRelationType.NEAR
    assert program.relationships[0].provenance == RelationshipProvenance.USER_CONFIRMED
    assert program.authoritative_relationship_ids == [program.relationships[0].id]
    assert len(program.unconstrained_pairs) > 0


def test_multi_quantity_space_request_produces_discrete_program_spaces() -> None:
    snapshot = _ready_snapshot()
    graph = _matching_graph(snapshot)

    program = SpatialProgramBuilder().build(snapshot, graph)

    bed_spaces = [s for s in program.spaces if s.source_space_request_id == "sr_bed"]
    assert len(bed_spaces) == 2

    s1, s2 = bed_spaces
    assert s1.id == "sn_bed_01"
    assert s1.display_name == "Yatak Odası 1"
    assert s1.function == SpaceFunction.SLEEPING
    assert s1.instance_index == 1
    assert s1.mandatory is True
    assert s1.stakeholder_ids == ["stk_owner"]
    assert s1.evidence_ids == ["ev_ready_01"]

    assert s2.id == "sn_bed_02"
    assert s2.display_name == "Yatak Odası 2"
    assert s2.function == SpaceFunction.SLEEPING
    assert s2.instance_index == 2
    assert s2.mandatory is True
    assert s2.stakeholder_ids == ["stk_owner"]
    assert s2.evidence_ids == ["ev_ready_01"]

    living_space = next(s for s in program.spaces if s.source_space_request_id == "sr_living")
    assert living_space.id == "sn_living_01"
    assert living_space.display_name == "Salon"
    assert living_space.instance_index == 1


def test_project_mismatch_is_rejected() -> None:
    snapshot = _ready_snapshot(project_id="proj_alpha")
    alt_snapshot = _ready_snapshot(project_id="proj_beta")
    graph = _matching_graph(alt_snapshot)

    builder = SpatialProgramBuilder()
    with pytest.raises(SpatialProgramProjectMismatchError) as exc_info:
        builder.build(snapshot, graph)

    assert "proj_alpha" in str(exc_info.value)
    assert "proj_beta" in str(exc_info.value)
    assert exc_info.value.snapshot_project_id == "proj_alpha"
    assert exc_info.value.graph_project_id == "proj_beta"


def test_version_mismatch_is_rejected() -> None:
    snapshot = _ready_snapshot(brief_version=3)
    alt_snapshot = _ready_snapshot(brief_version=2)
    graph = _matching_graph(alt_snapshot)

    builder = SpatialProgramBuilder()
    with pytest.raises(SpatialProgramVersionMismatchError) as exc_info:
        builder.build(snapshot, graph)

    assert "brief v3" in str(exc_info.value)
    assert "source_brief_version is v2" in str(exc_info.value)
    assert exc_info.value.snapshot_version == 3
    assert exc_info.value.graph_source_version == 2


def test_unready_brief_cannot_produce_program() -> None:
    # Unready brief: missing all closed topic questions (uncovered required topics)
    snapshot = _ready_snapshot(open_questions=[])
    graph = _matching_graph(snapshot)

    builder = SpatialProgramBuilder()
    with pytest.raises(BriefNotReadyError) as exc_info:
        builder.build(snapshot, graph)

    assert exc_info.value.readiness_result.ready_for_next_stage is False
    assert len(exc_info.value.readiness_result.blockers) > 0


def test_proposed_space_request_fails_readiness_and_blocks_program() -> None:
    ev = _evidence()
    pending_spaces = [
        SpaceRequest(
            id="sr_living",
            display_name="Salon",
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_sauna",
            display_name="Sauna",
            space_function=SpaceFunction.SANITARY,
            minimum_quantity=1,
            mandatory=False,
            confirmation_status=ConfirmationStatus.PROPOSED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
    ]
    snapshot = _ready_snapshot(space_requests=pending_spaces)
    graph = _matching_graph(snapshot)

    builder = SpatialProgramBuilder()
    with pytest.raises(BriefNotReadyError) as exc_info:
        builder.build(snapshot, graph)

    blocker_codes = [b.code.value for b in exc_info.value.readiness_result.blockers]
    assert "PENDING_CONFIRMATIONS" in blocker_codes


def test_spatial_conflicts_block_program_construction() -> None:
    snapshot = _ready_snapshot()
    # Create graph with contradictory relationships
    rel1 = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_ready_01"],
    )
    rel2 = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.SEPARATED_FROM,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_ready_01"],
    )
    graph = _matching_graph(snapshot, [rel1, rel2])
    assert len(graph.conflicts) == 1

    builder = SpatialProgramBuilder()
    with pytest.raises(SpatialProgramConflictBlockerError) as exc_info:
        builder.build(snapshot, graph)

    assert len(exc_info.value.conflicts) == 1
    assert "unresolved spatial conflict" in str(exc_info.value)


def test_unconstrained_pairs_are_preserved_without_invented_relations() -> None:
    snapshot = _ready_snapshot()
    graph = _matching_graph(snapshot, [])

    # 4 spaces -> 4 * 3 / 2 = 6 unconstrained pairs
    assert len(graph.unconstrained_pairs) == 6

    program = SpatialProgramBuilder().build(snapshot, graph)
    assert len(program.relationships) == 0
    assert len(program.unconstrained_pairs) == 6

    # Verify canonical ordering of unconstrained pairs
    for pair in program.unconstrained_pairs:
        assert pair.space_a_id < pair.space_b_id


def test_provenance_preserved_and_authoritative_boundary_explicit() -> None:
    snapshot = _ready_snapshot()
    rel_confirmed = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_ready_01"],
    )
    rel_stated = SpatialRelationshipInput(
        source_space_id="sn_bed_01",
        target_space_id="sn_bed_02",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_STATED,
    )
    rel_inferred = SpatialRelationshipInput(
        source_space_id="sn_bed_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.VISUAL_CONNECTION,
        provenance=RelationshipProvenance.AI_INFERRED,
    )
    graph = _matching_graph(snapshot, [rel_confirmed, rel_stated, rel_inferred])

    program = SpatialProgramBuilder().build(snapshot, graph)

    assert len(program.relationships) == 3
    provenance_map = {r.id: r.provenance for r in program.relationships}

    # Only USER_CONFIRMED is listed in authoritative_relationship_ids
    assert len(program.authoritative_relationship_ids) == 1
    confirmed_id = program.authoritative_relationship_ids[0]
    assert provenance_map[confirmed_id] == RelationshipProvenance.USER_CONFIRMED

    # All provenances preserved without promotion
    provenances = {r.provenance for r in program.relationships}
    assert provenances == {
        RelationshipProvenance.USER_CONFIRMED,
        RelationshipProvenance.USER_STATED,
        RelationshipProvenance.AI_INFERRED,
    }


def test_determinism_and_repeated_build_stability() -> None:
    snapshot = _ready_snapshot()
    rel_input = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_ready_01"],
    )
    graph = _matching_graph(snapshot, [rel_input])

    builder = SpatialProgramBuilder()
    prog1 = builder.build(snapshot, graph)
    prog2 = builder.build(snapshot, graph)

    assert prog1 == prog2
    assert prog1.model_dump_json() == prog2.model_dump_json()
    assert prog1.created_at == graph.created_at
    assert prog2.created_at == graph.created_at


def test_graph_nodes_mismatch_with_snapshot_raises_error() -> None:
    snapshot = _ready_snapshot()
    # Construct an inconsistent graph with an extra fake node
    nodes = project_space_requests_to_spatial_nodes(snapshot.space_requests)
    from brif_ai.spatial.models import SpatialNode

    fake_node = SpatialNode(
        id="sn_phantom_01",
        display_name="Hayalet Oda",
        function=SpaceFunction.STORAGE,
        source_space_request_id="sr_phantom",
        instance_index=1,
        mandatory=False,
    )
    inconsistent_graph = SpatialRelationshipGraph(
        schema_version="spatial_graph.v0",
        project_id=snapshot.project_id,
        source_brief_version=snapshot.brief_version,
        created_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
        nodes=[*nodes, fake_node],
        relationships=[],
        unconstrained_pairs=[],
        conflicts=[],
    )

    builder = SpatialProgramBuilder()
    with pytest.raises(SpatialProgramNodeMismatchError) as exc_info:
        builder.build(snapshot, inconsistent_graph)

    assert "Graph nodes do not match" in str(exc_info.value)


def test_missing_snapshot_or_graph_raises_error() -> None:
    builder = SpatialProgramBuilder()
    with pytest.raises(SpatialProgramMissingInputError):
        builder.build(None, None)  # type: ignore[arg-type]


def test_authoritative_relationship_ids_must_match_user_confirmed_contract() -> None:
    snapshot = _ready_snapshot()
    graph = _matching_graph(snapshot)
    program = SpatialProgramBuilder().build(snapshot, graph)

    # Violating authoritative_relationship_ids manually triggers validation error
    with pytest.raises(ValidationError, match="authoritative_relationship_ids mismatch"):
        SpatialProgram(
            schema_version="spatial_program.v0",
            project_id=program.project_id,
            source_brief_version=program.source_brief_version,
            created_at=program.created_at,
            spaces=program.spaces,
            relationships=program.relationships,
            unconstrained_pairs=program.unconstrained_pairs,
            authoritative_relationship_ids=["fake_rel_id"],
        )
