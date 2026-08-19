"""Focused tests for BRIF.AI Schematic Layout Problem V0 deterministic compiler."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.layout.errors import (
    LayoutProblemAuthoritativeMismatchError,
    LayoutProblemEndpointError,
    LayoutProblemMissingInputError,
    LayoutProblemSchemaVersionMismatchError,
)
from brif_ai.spatial.layout.models import (
    LayoutConstraint,
    LayoutSpace,
    SchematicLayoutProblem,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationship,
    SpatialRelationshipInput,
    SpatialRelationType,
    UnconstrainedPair,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
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
        id="ev_layout_01",
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


def _ready_program(
    *,
    project_id: str = "proj_layout_test",
    brief_version: int = 1,
    relationships: list[SpatialRelationshipInput] | None = None,
) -> SpatialProgram:
    ev = _evidence()
    spaces = [
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
            id="sr_kitchen",
            display_name="Mutfak",
            space_function=SpaceFunction.COOKING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_bed",
            display_name="Yatak Odası",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=2,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_owner"],
            evidence_ids=[ev.id],
        ),
    ]
    snapshot = BriefSnapshot(
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
        evidence=[ev],
        brief_items=[],
        space_requests=spaces,
        usage_scenarios=[],
        contradictions=[],
        open_questions=_closed_topic_questions(),
    )
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships or [],
        created_at=datetime(2026, 8, 19, 12, 5, tzinfo=UTC),
    )
    return SpatialProgramBuilder().build(snapshot, graph)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_valid_spatial_program_compiles_into_layout_problem() -> None:
    rel_confirmed = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_layout_01"],
    )
    program = _ready_program(relationships=[rel_confirmed])

    compiler = LayoutProblemCompiler()
    problem = compiler.compile(program)

    assert isinstance(problem, SchematicLayoutProblem)
    assert problem.schema_version == "schematic_layout_problem.v0"
    assert problem.project_id == program.project_id
    assert problem.source_brief_version == program.source_brief_version
    assert problem.source_program_schema_version == "spatial_program.v0"
    assert problem.created_at == program.created_at
    assert len(problem.spaces) == 4
    assert len(problem.authoritative_constraints) == 1
    assert len(problem.informational_relationships) == 0
    assert len(problem.unconstrained_pairs) > 0


def test_all_program_spaces_are_preserved_deterministically() -> None:
    program = _ready_program()
    problem = LayoutProblemCompiler().compile(program)

    assert len(problem.spaces) == len(program.spaces)
    for p_space, l_space in zip(program.spaces, problem.spaces, strict=True):
        assert isinstance(l_space, LayoutSpace)
        assert l_space.id == p_space.id
        assert l_space.source_program_space_id == p_space.id
        assert l_space.display_name == p_space.display_name
        assert l_space.function == p_space.function
        assert l_space.instance_index == p_space.instance_index
        assert l_space.mandatory == p_space.mandatory
        assert l_space.stakeholder_ids == p_space.stakeholder_ids
        assert l_space.evidence_ids == p_space.evidence_ids


def test_user_confirmed_authoritative_relationship_becomes_authoritative_constraint() -> None:
    rel_input = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_layout_01"],
        rationale="Mutfak salona yakın konumlanmalıdır.",
    )
    program = _ready_program(relationships=[rel_input])
    problem = LayoutProblemCompiler().compile(program)

    assert len(problem.authoritative_constraints) == 1
    assert len(problem.informational_relationships) == 0

    constraint = problem.authoritative_constraints[0]
    assert isinstance(constraint, LayoutConstraint)
    assert constraint.id == program.relationships[0].id
    assert constraint.source_relationship_id == program.relationships[0].id
    assert constraint.source_space_id == "sn_kitchen_01"
    assert constraint.target_space_id == "sn_living_01"
    assert constraint.relation_type == SpatialRelationType.NEAR
    assert constraint.provenance == RelationshipProvenance.USER_CONFIRMED
    assert constraint.priority == Priority.MUST
    assert constraint.evidence_ids == ["ev_layout_01"]
    assert constraint.rationale == "Mutfak salona yakın konumlanmalıdır."


def test_user_stated_and_ai_inferred_remain_informational() -> None:
    rel_confirmed = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_layout_01"],
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
    program = _ready_program(relationships=[rel_confirmed, rel_stated, rel_inferred])
    problem = LayoutProblemCompiler().compile(program)

    # Only USER_CONFIRMED became an authoritative constraint
    assert len(problem.authoritative_constraints) == 1
    assert problem.authoritative_constraints[0].source_space_id == "sn_kitchen_01"
    assert problem.authoritative_constraints[0].target_space_id == "sn_living_01"

    # USER_STATED and AI_INFERRED remain strictly informational
    assert len(problem.informational_relationships) == 2
    info_provenances = {r.provenance for r in problem.informational_relationships}
    assert info_provenances == {
        RelationshipProvenance.USER_STATED,
        RelationshipProvenance.AI_INFERRED,
    }


def test_priority_preserved_without_solver_hard_soft_conversion() -> None:
    rel_should = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.SHOULD,
        evidence_ids=["ev_layout_01"],
    )
    rel_could = SpatialRelationshipInput(
        source_space_id="sn_bed_01",
        target_space_id="sn_bed_02",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.COULD,
        evidence_ids=["ev_layout_01"],
    )
    program = _ready_program(relationships=[rel_should, rel_could])
    problem = LayoutProblemCompiler().compile(program)

    assert len(problem.authoritative_constraints) == 2
    priorities = {c.priority for c in problem.authoritative_constraints}
    assert priorities == {Priority.SHOULD, Priority.COULD}


def test_unconstrained_pairs_are_preserved_without_invented_relations() -> None:
    program = _ready_program(relationships=[])
    problem = LayoutProblemCompiler().compile(program)

    assert len(problem.authoritative_constraints) == 0
    assert len(problem.informational_relationships) == 0
    assert len(problem.unconstrained_pairs) == len(program.unconstrained_pairs)

    for p_pair, l_pair in zip(
        program.unconstrained_pairs, problem.unconstrained_pairs, strict=True
    ):
        assert isinstance(l_pair, UnconstrainedPair)
        assert l_pair.space_a_id == p_pair.space_a_id
        assert l_pair.space_b_id == p_pair.space_b_id


def test_authoritative_relationship_id_mismatch_is_rejected() -> None:
    program = _ready_program()

    # Create an artificial program object with an unconfirmed relationship falsely
    # listed in authoritative_ids by using model_construct to test compiler resilience
    fake_rel = SpatialRelationship(
        id="srel_unconfirmed_fake",
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
    )
    corrupted_program = SpatialProgram.model_construct(
        schema_version="spatial_program.v0",
        project_id=program.project_id,
        source_brief_version=program.source_brief_version,
        created_at=program.created_at,
        spaces=program.spaces,
        relationships=[fake_rel],
        unconstrained_pairs=[],
        authoritative_relationship_ids=["srel_unconfirmed_fake"],
    )

    compiler = LayoutProblemCompiler()
    with pytest.raises(LayoutProblemAuthoritativeMismatchError) as exc_info:
        compiler.compile(corrupted_program)

    assert "non-confirmed provenance" in str(exc_info.value)


def test_invalid_endpoint_is_rejected() -> None:
    program = _ready_program()
    # Construct a program with a relationship referencing a phantom space
    corrupted_rel = SpatialRelationship(
        id="srel_phantom",
        source_space_id="sn_kitchen_01",
        target_space_id="sn_phantom_space",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_layout_01"],
    )
    corrupted_program = SpatialProgram.model_construct(
        schema_version="spatial_program.v0",
        project_id=program.project_id,
        source_brief_version=program.source_brief_version,
        created_at=program.created_at,
        spaces=program.spaces,
        relationships=[corrupted_rel],
        unconstrained_pairs=[],
        authoritative_relationship_ids=["srel_phantom"],
    )

    compiler = LayoutProblemCompiler()
    with pytest.raises(LayoutProblemEndpointError) as exc_info:
        compiler.compile(corrupted_program)

    assert "unknown space endpoint" in str(exc_info.value)


def test_incompatible_program_schema_version_is_rejected() -> None:
    program = _ready_program()
    corrupted_program = SpatialProgram.model_construct(
        schema_version="spatial_program.v999",
        project_id=program.project_id,
        source_brief_version=program.source_brief_version,
        created_at=program.created_at,
        spaces=program.spaces,
        relationships=program.relationships,
        unconstrained_pairs=program.unconstrained_pairs,
        authoritative_relationship_ids=program.authoritative_relationship_ids,
    )

    compiler = LayoutProblemCompiler()
    with pytest.raises(LayoutProblemSchemaVersionMismatchError) as exc_info:
        compiler.compile(corrupted_program)

    assert "spatial_program.v0" in str(exc_info.value)


def test_missing_input_raises_error() -> None:
    compiler = LayoutProblemCompiler()
    with pytest.raises(LayoutProblemMissingInputError):
        compiler.compile(None)  # type: ignore[arg-type]


def test_determinism_and_repeated_compilation_stability() -> None:
    rel_input = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_layout_01"],
    )
    program = _ready_program(relationships=[rel_input])

    compiler = LayoutProblemCompiler()
    prob1 = compiler.compile(program)
    prob2 = compiler.compile(program)

    assert prob1 == prob2
    assert prob1.model_dump_json() == prob2.model_dump_json()
    assert prob1.created_at == program.created_at
    assert prob2.created_at == program.created_at


def test_zero_geometry_fields_in_schema() -> None:
    forbidden_field_substrings = [
        "coord",
        "dimension",
        "area",
        "width",
        "length",
        "height",
        "polygon",
        "rectangle",
        "point",
        "bound",
        "floor",
        "door",
        "window",
        "wall",
        "corridor",
        "circulation",
        "setback",
        "zoning",
    ]

    for model_cls in (LayoutSpace, LayoutConstraint, SchematicLayoutProblem):
        fields = set(model_cls.model_fields.keys())
        for field_name in fields:
            for forbidden in forbidden_field_substrings:
                assert forbidden not in field_name.lower(), (
                    f"Forbidden geometric field {field_name!r} found in {model_cls.__name__}"
                )
