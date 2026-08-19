"""Focused tests for BRIF.AI Layout Solver Policy V0 deterministic compiler."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

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
from brif_ai.spatial.layout.models import (
    LayoutConstraint,
    SchematicLayoutProblem,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.solver_policy.errors import (
    SolverPolicyEndpointError,
    SolverPolicyMissingInputError,
    SolverPolicySchemaVersionMismatchError,
)
from brif_ai.spatial.solver_policy.models import (
    ConstraintEnforcement,
    SolverDirective,
    SolverDirectiveSet,
    SolverRelationOperator,
    map_priority_to_enforcement,
    map_relation_type_to_operator,
)

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
        id="ev_policy_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client stated spatial relationship.",
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


def _ready_layout_problem(
    *,
    project_id: str = "proj_policy_test",
    brief_version: int = 1,
    relationships: list[SpatialRelationshipInput] | None = None,
) -> SchematicLayoutProblem:
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
    program = SpatialProgramBuilder().build(snapshot, graph)
    return LayoutProblemCompiler().compile(program)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_valid_schematic_layout_problem_compiles_into_solver_directive_set() -> None:
    rel_confirmed = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_policy_01"],
        rationale="Mutfak salona yakin olmali.",
    )
    problem = _ready_layout_problem(relationships=[rel_confirmed])

    compiler = SolverPolicyCompiler()
    directive_set = compiler.compile(problem)

    assert isinstance(directive_set, SolverDirectiveSet)
    assert directive_set.schema_version == "solver_directive_set.v0"
    assert directive_set.project_id == problem.project_id
    assert directive_set.source_brief_version == problem.source_brief_version
    assert directive_set.source_layout_problem_schema_version == "schematic_layout_problem.v0"
    assert directive_set.created_at == problem.created_at
    assert len(directive_set.spaces) == 4
    assert len(directive_set.directives) == 1
    assert len(directive_set.unconstrained_pairs) > 0

    directive = directive_set.directives[0]
    assert isinstance(directive, SolverDirective)
    assert directive.id == problem.authoritative_constraints[0].id
    assert directive.source_constraint_id == problem.authoritative_constraints[0].id
    assert directive.source_space_id == "sn_kitchen_01"
    assert directive.target_space_id == "sn_living_01"
    assert directive.source_relation_type == SpatialRelationType.NEAR
    assert directive.operator == SolverRelationOperator.PROXIMITY
    assert directive.enforcement == ConstraintEnforcement.REQUIRED
    assert directive.priority == Priority.MUST
    assert directive.provenance == RelationshipProvenance.USER_CONFIRMED
    assert directive.evidence_ids == ["ev_policy_01"]
    assert directive.rationale == "Mutfak salona yakin olmali."
    assert directive.bidirectional is True


def test_must_maps_to_required() -> None:
    assert map_priority_to_enforcement(Priority.MUST) == ConstraintEnforcement.REQUIRED

    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])
    dset = SolverPolicyCompiler().compile(problem)
    assert dset.directives[0].enforcement == ConstraintEnforcement.REQUIRED


def test_should_maps_to_preferred() -> None:
    assert map_priority_to_enforcement(Priority.SHOULD) == ConstraintEnforcement.PREFERRED

    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.SHOULD,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])
    dset = SolverPolicyCompiler().compile(problem)
    assert dset.directives[0].enforcement == ConstraintEnforcement.PREFERRED


def test_could_maps_to_optional() -> None:
    assert map_priority_to_enforcement(Priority.COULD) == ConstraintEnforcement.OPTIONAL

    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.COULD,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])
    dset = SolverPolicyCompiler().compile(problem)
    assert dset.directives[0].enforcement == ConstraintEnforcement.OPTIONAL


def test_unspecified_maps_to_unspecified() -> None:
    assert map_priority_to_enforcement(Priority.UNSPECIFIED) == ConstraintEnforcement.UNSPECIFIED

    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.UNSPECIFIED,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])
    dset = SolverPolicyCompiler().compile(problem)
    assert dset.directives[0].enforcement == ConstraintEnforcement.UNSPECIFIED


def test_user_confirmed_provenance_is_preserved() -> None:
    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])
    dset = SolverPolicyCompiler().compile(problem)
    assert dset.directives[0].provenance == RelationshipProvenance.USER_CONFIRMED


def test_informational_relationships_produce_zero_solver_directives() -> None:
    rel_confirmed = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_policy_01"],
    )
    rel_stated = SpatialRelationshipInput(
        source_space_id="sn_bed_01",
        target_space_id="sn_bed_02",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_STATED,
    )
    problem = _ready_layout_problem(relationships=[rel_confirmed, rel_stated])

    assert len(problem.authoritative_constraints) == 1
    assert len(problem.informational_relationships) == 1

    dset = SolverPolicyCompiler().compile(problem)

    # ONLY authoritative constraint became a directive
    assert len(dset.directives) == 1
    assert dset.directives[0].source_space_id == "sn_kitchen_01"
    assert dset.directives[0].target_space_id == "sn_living_01"

    # informational_relationships is NOT exposed in SolverDirectiveSet schema
    assert not hasattr(dset, "informational_relationships")


def test_every_spatial_relation_type_maps_to_exact_solver_relation_operator() -> None:
    expected_mappings: dict[SpatialRelationType, SolverRelationOperator] = {
        SpatialRelationType.ADJACENT_TO: SolverRelationOperator.ADJACENCY,
        SpatialRelationType.NEAR: SolverRelationOperator.PROXIMITY,
        SpatialRelationType.SEPARATED_FROM: SolverRelationOperator.SEPARATION,
        SpatialRelationType.VISUAL_CONNECTION: SolverRelationOperator.VISUAL_CONNECTIVITY,
        SpatialRelationType.DIRECT_ACCESS: SolverRelationOperator.DIRECT_CONNECTIVITY,
        SpatialRelationType.INDIRECT_ACCESS: SolverRelationOperator.INDIRECT_CONNECTIVITY,
        SpatialRelationType.ACOUSTIC_SEPARATION: SolverRelationOperator.ACOUSTIC_BUFFERING,
        SpatialRelationType.PRIVACY_SEPARATION: SolverRelationOperator.PRIVACY_BUFFERING,
    }

    # Prove every current enum member is covered exactly once
    all_relation_types = set(SpatialRelationType)
    assert set(expected_mappings.keys()) == all_relation_types

    for rel_type, expected_operator in expected_mappings.items():
        assert map_relation_type_to_operator(rel_type) == expected_operator


def test_no_geometric_thresholds_or_numeric_weights_introduced() -> None:
    forbidden_field_substrings = [
        "weight",
        "score",
        "penalty",
        "coefficient",
        "threshold",
        "distance",
        "min_distance",
        "max_distance",
        "shared_wall_length",
        "x",
        "y",
        "width",
        "height",
        "area",
        "polygon",
        "coordinates",
    ]

    for enum_cls in (ConstraintEnforcement, SolverRelationOperator):
        for m in enum_cls:
            for forbidden in forbidden_field_substrings:
                assert forbidden != m.name.lower(), (
                    f"Forbidden term {forbidden!r} found in enum {enum_cls.__name__}.{m.name}"
                )

    for model_cls in (SolverDirective, SolverDirectiveSet):
        for field_name in model_cls.model_fields:
            for forbidden in forbidden_field_substrings:
                assert forbidden != field_name.lower(), (
                    f"Forbidden geometric/tuning field {field_name!r} found in {model_cls.__name__}"
                )


def test_invalid_schema_version_is_rejected() -> None:
    problem = _ready_layout_problem()
    corrupted_problem = SchematicLayoutProblem.model_construct(
        schema_version="schematic_layout_problem.v999",
        project_id=problem.project_id,
        source_brief_version=problem.source_brief_version,
        source_program_schema_version=problem.source_program_schema_version,
        created_at=problem.created_at,
        spaces=problem.spaces,
        authoritative_constraints=problem.authoritative_constraints,
        informational_relationships=problem.informational_relationships,
        unconstrained_pairs=problem.unconstrained_pairs,
    )

    compiler = SolverPolicyCompiler()
    with pytest.raises(SolverPolicySchemaVersionMismatchError) as exc_info:
        compiler.compile(corrupted_problem)

    assert "schematic_layout_problem.v0" in str(exc_info.value)


def test_invalid_endpoints_are_rejected() -> None:
    problem = _ready_layout_problem()
    corrupted_constraint = LayoutConstraint(
        id="srel_phantom_c",
        source_relationship_id="srel_phantom_c",
        source_space_id="sn_kitchen_01",
        target_space_id="sn_phantom_space",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
    )
    corrupted_problem = SchematicLayoutProblem.model_construct(
        schema_version="schematic_layout_problem.v0",
        project_id=problem.project_id,
        source_brief_version=problem.source_brief_version,
        source_program_schema_version=problem.source_program_schema_version,
        created_at=problem.created_at,
        spaces=problem.spaces,
        authoritative_constraints=[corrupted_constraint],
        informational_relationships=[],
        unconstrained_pairs=[],
    )

    compiler = SolverPolicyCompiler()
    with pytest.raises(SolverPolicyEndpointError) as exc_info:
        compiler.compile(corrupted_problem)

    assert "unknown space endpoint" in str(exc_info.value)


def test_deterministic_ordering_is_stable() -> None:
    rel1 = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_policy_01"],
    )
    rel2 = SpatialRelationshipInput(
        source_space_id="sn_bed_01",
        target_space_id="sn_bed_02",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel1, rel2])

    compiler = SolverPolicyCompiler()
    dset = compiler.compile(problem)

    directive_ids = [d.id for d in dset.directives]
    assert directive_ids == sorted(directive_ids)

    space_ids = [s.id for s in dset.spaces]
    assert space_ids == sorted(space_ids)


def test_repeated_compilation_is_byte_for_byte_equivalent() -> None:
    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])

    compiler = SolverPolicyCompiler()
    dset1 = compiler.compile(problem)
    dset2 = compiler.compile(problem)

    assert dset1 == dset2
    assert dset1.model_dump_json() == dset2.model_dump_json()
    assert dset1.created_at == problem.created_at
    assert dset2.created_at == problem.created_at


def test_source_constraint_identity_and_traceability_preserved() -> None:
    rel = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_policy_01"],
    )
    problem = _ready_layout_problem(relationships=[rel])
    dset = SolverPolicyCompiler().compile(problem)

    constraint = problem.authoritative_constraints[0]
    directive = dset.directives[0]

    assert directive.id == constraint.id
    assert directive.source_constraint_id == constraint.id
    assert directive.source_space_id == constraint.source_space_id
    assert directive.target_space_id == constraint.target_space_id


def test_strict_utc_created_at_validation() -> None:
    problem = _ready_layout_problem()
    compiler = SolverPolicyCompiler()

    # Explicit naive datetime must be rejected
    naive_dt = datetime(2026, 8, 19, 12, 0, 0)
    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        compiler.compile(problem, created_at=naive_dt)

    # Non-UTC timezone must be rejected
    non_utc_dt = datetime(2026, 8, 19, 15, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(ValidationError, match="created_at must use UTC offset"):
        compiler.compile(problem, created_at=non_utc_dt)


def test_missing_input_raises_error() -> None:
    compiler = SolverPolicyCompiler()
    with pytest.raises(SolverPolicyMissingInputError):
        compiler.compile(None)  # type: ignore[arg-type]
