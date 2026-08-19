"""Comprehensive test suite for BRIF.AI Authoritative FloorPlate V0."""

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
from brif_ai.spatial.floor_plate.builder import FloorPlateBuilder
from brif_ai.spatial.floor_plate.errors import (
    FloorPlateMissingInputError,
    FloorPlateNonAuthoritativeError,
    FloorPlateOutsideBuildableEnvelopeError,
    FloorPlateSchemaVersionMismatchError,
)
from brif_ai.spatial.floor_plate.models import (
    FloorPlate,
    FloorPlateInput,
    generate_floor_plate_id,
)
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirementInput,
    MetricRequirementType,
    MetricUnit,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.models import SpatialProgram
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.errors import (
    SitePolygonDegenerateError,
    SitePolygonSelfIntersectionError,
)
from brif_ai.spatial.site.models import (
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_input import LayoutSolverInputAssembler, LayoutSolverInputSet
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler


def _ready_program() -> SpatialProgram:
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client wants living room connected to kitchen and garden.",
    )
    spaces = [
        SpaceRequest(
            id="sr_living",
            display_name="Living Room",
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_kitchen",
            display_name="Kitchen",
            space_function=SpaceFunction.COOKING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_bedroom",
            display_name="Master Bedroom",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
    ]
    all_topics = [
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
    open_questions = [
        OpenQuestion(
            id=f"oq_{t.value}",
            question=f"Question on {t.value}",
            reason="Ready fixture",
            related_brief_item_ids=[],
            status=OpenQuestionStatus.ANSWERED,
            resolution_note="Answered and confirmed",
            topic_key=t.value,
        )
        for t in all_topics
    ]
    snapshot = BriefSnapshot(
        project_id="proj_101",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_01",
                display_name="Client",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[ev],
        brief_items=[],
        space_requests=spaces,
        usage_scenarios=[],
        contradictions=[],
        open_questions=open_questions,
    )
    relationships = [
        SpatialRelationshipInput(
            source_space_id="sn_living_01",
            target_space_id="sn_kitchen_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev.id],
            rationale="Open plan living/kitchen",
        ),
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships,
        created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC),
    )
    return SpatialProgramBuilder().build(snapshot, graph)


def _sample_solver_input(
    *,
    parcel_vertices: list[SitePoint] | None = None,
    envelope_vertices: list[SitePoint] | None = None,
) -> LayoutSolverInputSet:
    program = _ready_program()
    ev_id = "ev_01"

    # 1. DirectiveSet
    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    # 2. MetricRequirements
    metric_inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=35.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
            rationale="Confirmed living room size",
        ),
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.TARGET_AREA,
            value=15.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.SHOULD,
            evidence_ids=[ev_id],
            rationale="Confirmed kitchen target area",
        ),
    ]
    metrics = MetricSpatialRequirementsBuilder().build(
        program, metric_inputs, created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC)
    )

    # 3. SiteBuildableEnvelope
    p_verts = parcel_vertices or [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=50.0, y_m=0.0),
        SitePoint(x_m=50.0, y_m=40.0),
        SitePoint(x_m=0.0, y_m=40.0),
    ]
    e_verts = envelope_vertices or [
        SitePoint(x_m=5.0, y_m=5.0),
        SitePoint(x_m=45.0, y_m=5.0),
        SitePoint(x_m=45.0, y_m=35.0),
        SitePoint(x_m=5.0, y_m=35.0),
    ]

    parcel_inp = SitePolygonInput(
        vertices=p_verts,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
        rationale="Cadastral boundary",
    )
    envelope_inp = SitePolygonInput(
        vertices=e_verts,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
        rationale="Zoning setback envelope",
    )
    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=parcel_inp,
        buildable_envelope=envelope_inp,
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    return LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)


def _sample_valid_floor_plate_input() -> FloorPlateInput:
    return FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=25.0),
            SitePoint(x_m=10.0, y_m=25.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
        rationale="Client confirmed ground floor building footprint perimeter",
    )


# -----------------------------------------------------------------------------
# 1. Valid Build & Schema Tests
# -----------------------------------------------------------------------------


def test_valid_authoritative_floor_plate_builds_successfully() -> None:
    solver_input = _sample_solver_input()
    floor_input = _sample_valid_floor_plate_input()

    floor_plate = FloorPlateBuilder().build(solver_input, floor_input)

    assert isinstance(floor_plate, FloorPlate)
    assert floor_plate.schema_version == "floor_plate.v0"
    assert floor_plate.id == generate_floor_plate_id("proj_101")
    assert floor_plate.project_id == "proj_101"
    assert floor_plate.source_brief_version == 1
    assert floor_plate.source_solver_input_schema_version == "layout_solver_input_set.v0"
    assert floor_plate.coordinate_system == "LOCAL_CARTESIAN_METRES"
    assert floor_plate.provenance == RelationshipProvenance.USER_CONFIRMED
    assert floor_plate.evidence_ids == ["ev_01"]
    assert floor_plate.rationale == "Client confirmed ground floor building footprint perimeter"
    assert len(floor_plate.vertices) == 4


def test_deterministic_floor_plate_id_and_invariance_under_coord_changes() -> None:
    solver_input = _sample_solver_input()
    id_1 = generate_floor_plate_id(solver_input.project_id)
    assert id_1 == f"fplate_{id_1.removeprefix('fplate_')}"

    # Change coordinates
    diff_input = FloorPlateInput(
        vertices=[
            SitePoint(x_m=12.0, y_m=12.0),
            SitePoint(x_m=28.0, y_m=12.0),
            SitePoint(x_m=28.0, y_m=22.0),
            SitePoint(x_m=12.0, y_m=22.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
        rationale="Modified perimeter",
    )
    floor_plate_1 = FloorPlateBuilder().build(solver_input, _sample_valid_floor_plate_input())
    floor_plate_2 = FloorPlateBuilder().build(solver_input, diff_input)

    assert floor_plate_1.id == floor_plate_2.id == id_1


def test_repeated_builds_serialize_byte_for_byte_identically() -> None:
    solver_input = _sample_solver_input()
    floor_input = _sample_valid_floor_plate_input()

    fp1 = FloorPlateBuilder().build(solver_input, floor_input)
    fp2 = FloorPlateBuilder().build(solver_input, floor_input)

    assert fp1.model_dump_json(indent=2) == fp2.model_dump_json(indent=2)


def test_raw_vertices_and_order_preserved_without_mutation() -> None:
    solver_input = _sample_solver_input()
    raw_verts = [
        SitePoint(x_m=15.1234567, y_m=12.9876543),
        SitePoint(x_m=35.5, y_m=12.9876543),
        SitePoint(x_m=35.5, y_m=28.75),
        SitePoint(x_m=15.1234567, y_m=28.75),
    ]
    inp = FloorPlateInput(
        vertices=raw_verts,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    fp = FloorPlateBuilder().build(solver_input, inp)

    for in_v, out_v in zip(raw_verts, fp.vertices, strict=True):
        assert in_v.x_m == out_v.x_m
        assert in_v.y_m == out_v.y_m


def test_cw_and_ccw_polygons_valid() -> None:
    solver_input = _sample_solver_input()

    # CCW
    ccw_verts = [
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=30.0, y_m=10.0),
        SitePoint(x_m=30.0, y_m=25.0),
        SitePoint(x_m=10.0, y_m=25.0),
    ]
    fp_ccw = FloorPlateBuilder().build(
        solver_input,
        FloorPlateInput(
            vertices=ccw_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        ),
    )
    assert len(fp_ccw.vertices) == 4

    # CW (reversed)
    cw_verts = list(reversed(ccw_verts))
    fp_cw = FloorPlateBuilder().build(
        solver_input,
        FloorPlateInput(
            vertices=cw_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        ),
    )
    assert len(fp_cw.vertices) == 4


def test_negative_and_zero_coordinates_valid() -> None:
    # Solver input with envelope spanning negative space
    solver_input = _sample_solver_input(
        parcel_vertices=[
            SitePoint(x_m=-50.0, y_m=-40.0),
            SitePoint(x_m=50.0, y_m=-40.0),
            SitePoint(x_m=50.0, y_m=40.0),
            SitePoint(x_m=-50.0, y_m=40.0),
        ],
        envelope_vertices=[
            SitePoint(x_m=-40.0, y_m=-30.0),
            SitePoint(x_m=40.0, y_m=-30.0),
            SitePoint(x_m=40.0, y_m=30.0),
            SitePoint(x_m=-40.0, y_m=30.0),
        ],
    )

    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=-20.0, y_m=-10.0),
            SitePoint(x_m=0.0, y_m=-10.0),
            SitePoint(x_m=0.0, y_m=10.0),
            SitePoint(x_m=-20.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    fp = FloorPlateBuilder().build(solver_input, floor_inp)
    assert fp.vertices[0].x_m == -20.0
    assert fp.vertices[1].x_m == 0.0


# -----------------------------------------------------------------------------
# 2. Geometric Validity & Degeneracy Tests
# -----------------------------------------------------------------------------


def test_non_finite_coordinates_rejected() -> None:
    with pytest.raises(ValidationError):
        SitePoint(x_m=float("nan"), y_m=10.0)

    with pytest.raises(ValidationError):
        SitePoint(x_m=10.0, y_m=float("inf"))


def test_fewer_than_3_vertices_rejected() -> None:
    with pytest.raises(ValidationError):
        FloorPlateInput(
            vertices=[SitePoint(x_m=0.0, y_m=0.0), SitePoint(x_m=10.0, y_m=10.0)],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        )


def test_repeated_closing_vertex_rejected() -> None:
    solver_input = _sample_solver_input()
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=25.0),
            SitePoint(x_m=10.0, y_m=25.0),
            SitePoint(x_m=10.0, y_m=10.0),  # Duplicate closing point
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(SitePolygonDegenerateError, match="must not repeat the first vertex"):
        FloorPlateBuilder().build(solver_input, floor_inp)


def test_duplicate_non_consecutive_vertex_rejected() -> None:
    solver_input = _sample_solver_input()
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=25.0),
            SitePoint(x_m=10.0, y_m=10.0),  # Repeated vertex
            SitePoint(x_m=10.0, y_m=25.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(SitePolygonDegenerateError, match="Duplicate vertex found"):
        FloorPlateBuilder().build(solver_input, floor_inp)


def test_zero_area_collinear_polygon_rejected() -> None:
    solver_input = _sample_solver_input()
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(SitePolygonDegenerateError, match="area must be strictly positive"):
        FloorPlateBuilder().build(solver_input, floor_inp)


def test_self_intersecting_polygon_rejected() -> None:
    solver_input = _sample_solver_input()
    # Asymmetric self-crossing polygon with non-zero area
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=20.0),
            SitePoint(x_m=10.0, y_m=20.0),
            SitePoint(x_m=20.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(SitePolygonSelfIntersectionError, match="intersect, touch, or overlap"):
        FloorPlateBuilder().build(solver_input, floor_inp)


def test_non_adjacent_edge_touching_rejected() -> None:
    solver_input = _sample_solver_input()
    # Edge touching non-adjacent vertex
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=10.0),
            SitePoint(x_m=30.0, y_m=30.0),
            SitePoint(x_m=20.0, y_m=10.0),  # Touches bottom edge (10,10)-(30,10)
            SitePoint(x_m=10.0, y_m=30.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(SitePolygonSelfIntersectionError, match="intersect, touch, or overlap"):
        FloorPlateBuilder().build(solver_input, floor_inp)


# -----------------------------------------------------------------------------
# 3. Containment within Buildable Envelope Tests
# -----------------------------------------------------------------------------


def test_floor_plate_fully_inside_convex_buildable_envelope_accepted() -> None:
    solver_input = _sample_solver_input()
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=25.0, y_m=10.0),
            SitePoint(x_m=25.0, y_m=20.0),
            SitePoint(x_m=10.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    fp = FloorPlateBuilder().build(solver_input, floor_inp)
    assert len(fp.vertices) == 4


def test_floor_plate_touching_buildable_envelope_boundary_accepted() -> None:
    solver_input = _sample_solver_input()
    # Touches envelope edge at y=5.0
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=5.0),
            SitePoint(x_m=25.0, y_m=5.0),
            SitePoint(x_m=25.0, y_m=20.0),
            SitePoint(x_m=10.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    fp = FloorPlateBuilder().build(solver_input, floor_inp)
    assert len(fp.vertices) == 4


def test_floor_plate_equal_to_buildable_envelope_accepted() -> None:
    solver_input = _sample_solver_input()
    # Exactly matches envelope vertices: (5,5), (45,5), (45,35), (5,35)
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=5.0, y_m=5.0),
            SitePoint(x_m=45.0, y_m=5.0),
            SitePoint(x_m=45.0, y_m=35.0),
            SitePoint(x_m=5.0, y_m=35.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    fp = FloorPlateBuilder().build(solver_input, floor_inp)
    assert len(fp.vertices) == 4


def test_floor_plate_outside_convex_buildable_envelope_rejected() -> None:
    solver_input = _sample_solver_input()
    # Crosses outside envelope boundary at x=48 (envelope max x is 45)
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=48.0, y_m=10.0),
            SitePoint(x_m=48.0, y_m=25.0),
            SitePoint(x_m=10.0, y_m=25.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(FloorPlateOutsideBuildableEnvelopeError):
        FloorPlateBuilder().build(solver_input, floor_inp)


def test_floor_plate_outside_concave_buildable_envelope_rejected() -> None:
    # L-shaped buildable envelope: (0,0)-(40,0)-(40,20)-(20,20)-(20,40)-(0,40)
    solver_input = _sample_solver_input(
        parcel_vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=50.0),
            SitePoint(x_m=0.0, y_m=50.0),
        ],
        envelope_vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=40.0, y_m=0.0),
            SitePoint(x_m=40.0, y_m=20.0),
            SitePoint(x_m=20.0, y_m=20.0),
            SitePoint(x_m=20.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ],
    )

    # Floor plate positioned inside the "missing" upper-right corner (25, 25) - (35, 35)
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=25.0, y_m=25.0),
            SitePoint(x_m=35.0, y_m=25.0),
            SitePoint(x_m=35.0, y_m=35.0),
            SitePoint(x_m=25.0, y_m=35.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(FloorPlateOutsideBuildableEnvelopeError):
        FloorPlateBuilder().build(solver_input, floor_inp)


def test_regression_concave_envelope_edge_subinterval_outside_rejected() -> None:
    # U-shaped concave envelope
    # Base: (0,0) to (50,0)
    # Right arm: (50,0) to (50,50) to (35,50) to (35,20)
    # Center cutout: from (35,20) to (15,20)
    # Left arm: (15,20) to (15,50) to (0,50) to (0,0)
    solver_input = _sample_solver_input(
        parcel_vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=60.0, y_m=0.0),
            SitePoint(x_m=60.0, y_m=60.0),
            SitePoint(x_m=0.0, y_m=60.0),
        ],
        envelope_vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=50.0),
            SitePoint(x_m=35.0, y_m=50.0),
            SitePoint(x_m=35.0, y_m=20.0),
            SitePoint(x_m=15.0, y_m=20.0),
            SitePoint(x_m=15.0, y_m=50.0),
            SitePoint(x_m=0.0, y_m=50.0),
        ],
    )

    # Floor plate bridging the two arms across the cutout at y=35
    # Vertices (10, 35) and (40, 35) are inside the left and right arms, but the bridge segment
    # passes across the cutout interval x in [15, 35] outside the envelope!
    floor_inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=5.0, y_m=30.0),
            SitePoint(x_m=45.0, y_m=30.0),
            SitePoint(x_m=45.0, y_m=40.0),
            SitePoint(x_m=5.0, y_m=40.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )

    with pytest.raises(FloorPlateOutsideBuildableEnvelopeError):
        FloorPlateBuilder().build(solver_input, floor_inp)


# -----------------------------------------------------------------------------
# 4. Authority & Evidence Validation Tests
# -----------------------------------------------------------------------------


def test_user_confirmed_accepted() -> None:
    solver_input = _sample_solver_input()
    inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=20.0),
            SitePoint(x_m=10.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    fp = FloorPlateBuilder().build(solver_input, inp)
    assert fp.provenance == RelationshipProvenance.USER_CONFIRMED


def test_user_stated_rejected_with_typed_error() -> None:
    solver_input = _sample_solver_input()
    inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=20.0),
            SitePoint(x_m=10.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_STATED,
        evidence_ids=[],
    )

    with pytest.raises(
        FloorPlateNonAuthoritativeError,
        match="non-authoritative provenance 'USER_STATED'",
    ):
        FloorPlateBuilder().build(solver_input, inp)


def test_ai_inferred_rejected_with_typed_error() -> None:
    solver_input = _sample_solver_input()
    inp = FloorPlateInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=10.0),
            SitePoint(x_m=20.0, y_m=20.0),
            SitePoint(x_m=10.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.AI_INFERRED,
        evidence_ids=[],
    )

    with pytest.raises(
        FloorPlateNonAuthoritativeError,
        match="non-authoritative provenance 'AI_INFERRED'",
    ):
        FloorPlateBuilder().build(solver_input, inp)


def test_user_confirmed_input_without_evidence_rejected() -> None:
    with pytest.raises(ValidationError, match="requires at least one evidence ID"):
        FloorPlateInput(
            vertices=[
                SitePoint(x_m=10.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=20.0),
                SitePoint(x_m=10.0, y_m=20.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[],
        )


def test_duplicate_evidence_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="Duplicate evidence IDs"):
        FloorPlateInput(
            vertices=[
                SitePoint(x_m=10.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=20.0),
                SitePoint(x_m=10.0, y_m=20.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01", "ev_01"],
        )


# -----------------------------------------------------------------------------
# 5. Input Presence, Schema, and Timestamp Tests
# -----------------------------------------------------------------------------


def test_missing_inputs_raise_typed_errors() -> None:
    solver_input = _sample_solver_input()
    floor_inp = _sample_valid_floor_plate_input()

    with pytest.raises(FloorPlateMissingInputError, match="solver_input must not be None"):
        FloorPlateBuilder().build(None, floor_inp)  # type: ignore[arg-type]

    with pytest.raises(FloorPlateMissingInputError, match="floor_plate must not be None"):
        FloorPlateBuilder().build(solver_input, None)  # type: ignore[arg-type]


def test_incompatible_solver_input_schema_version_rejected() -> None:
    solver_input = _sample_solver_input()
    bad_input = solver_input.model_copy(update={"schema_version": "layout_solver_input_set.v1"})
    floor_inp = _sample_valid_floor_plate_input()

    with pytest.raises(
        FloorPlateSchemaVersionMismatchError, match="Unsupported solver_input schema_version"
    ):
        FloorPlateBuilder().build(bad_input, floor_inp)


def test_timestamp_determinism_and_utc_enforcement() -> None:
    solver_input = _sample_solver_input()
    floor_inp = _sample_valid_floor_plate_input()

    # 1. Default timestamp matches solver_input.created_at
    fp_default = FloorPlateBuilder().build(solver_input, floor_inp)
    assert fp_default.created_at == solver_input.created_at

    # 2. Explicit UTC timestamp accepted
    explicit_dt = datetime(2026, 8, 19, 15, 30, 0, tzinfo=UTC)
    fp_explicit = FloorPlateBuilder().build(solver_input, floor_inp, created_at=explicit_dt)
    assert fp_explicit.created_at == explicit_dt

    # 3. Naive datetime rejected
    naive_dt = datetime(2026, 8, 19, 15, 30, 0)
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        FloorPlateBuilder().build(solver_input, floor_inp, created_at=naive_dt)

    # 4. Non-UTC datetime rejected
    non_utc_dt = datetime(2026, 8, 19, 18, 30, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(ValueError, match="created_at must use UTC offset"):
        FloorPlateBuilder().build(solver_input, floor_inp, created_at=non_utc_dt)


# -----------------------------------------------------------------------------
# 6. Direct Model Validation Tests
# -----------------------------------------------------------------------------


def test_direct_floor_plate_rejects_non_deterministic_id() -> None:
    solver_input = _sample_solver_input()
    raw_verts = [
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=20.0),
        SitePoint(x_m=10.0, y_m=20.0),
    ]

    with pytest.raises(ValidationError, match="does not match expected deterministic id"):
        FloorPlate(
            id="fplate_fabricated_id_001",
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=raw_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        )


def test_direct_floor_plate_rejects_non_confirmed_provenance() -> None:
    solver_input = _sample_solver_input()
    raw_verts = [
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=20.0),
        SitePoint(x_m=10.0, y_m=20.0),
    ]
    fplate_id = generate_floor_plate_id(solver_input.project_id)

    with pytest.raises(ValidationError):
        FloorPlate(
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=raw_verts,
            provenance=RelationshipProvenance.USER_STATED,  # type: ignore[arg-type]
            evidence_ids=["ev_01"],
        )


def test_direct_floor_plate_requires_explicit_provenance() -> None:
    solver_input = _sample_solver_input()
    raw_verts = [
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=20.0),
        SitePoint(x_m=10.0, y_m=20.0),
    ]
    fplate_id = generate_floor_plate_id(solver_input.project_id)

    # Omitting provenance must raise ValidationError
    with pytest.raises(ValidationError, match="provenance"):
        FloorPlate(
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=raw_verts,
            evidence_ids=["ev_01"],
        )  # type: ignore[call-arg]


def test_direct_floor_plate_rejects_duplicate_evidence_ids() -> None:
    solver_input = _sample_solver_input()
    raw_verts = [
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=20.0),
        SitePoint(x_m=10.0, y_m=20.0),
    ]
    fplate_id = generate_floor_plate_id(solver_input.project_id)

    with pytest.raises(ValidationError, match="Duplicate evidence IDs"):
        FloorPlate(
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=raw_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01", "ev_01"],
        )


def test_direct_floor_plate_rejects_non_utc_and_naive_timestamps() -> None:
    solver_input = _sample_solver_input()
    raw_verts = [
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=10.0),
        SitePoint(x_m=20.0, y_m=20.0),
        SitePoint(x_m=10.0, y_m=20.0),
    ]
    fplate_id = generate_floor_plate_id(solver_input.project_id)

    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        FloorPlate(
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 12, 0, 0),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=raw_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        )

    with pytest.raises(ValidationError, match="created_at must use UTC offset"):
        FloorPlate(
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 15, 0, 0, tzinfo=timezone(timedelta(hours=3))),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=raw_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        )


def test_direct_floor_plate_rejects_invalid_geometry() -> None:
    solver_input = _sample_solver_input()
    fplate_id = generate_floor_plate_id(solver_input.project_id)

    with pytest.raises(SitePolygonDegenerateError, match="must not repeat the first vertex"):
        FloorPlate(
            id=fplate_id,
            project_id=solver_input.project_id,
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            vertices=[
                SitePoint(x_m=10.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=10.0),
                SitePoint(x_m=20.0, y_m=20.0),
                SitePoint(x_m=10.0, y_m=10.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=["ev_01"],
        )


# -----------------------------------------------------------------------------
# 7. Non-Inference & Architectural Invariant Tests
# -----------------------------------------------------------------------------


def test_no_buildable_envelope_fallback_or_automatic_floor_plate_generation() -> None:
    solver_input = _sample_solver_input()

    # If floor_plate is None, builder must fail rather than defaulting to buildable_envelope
    with pytest.raises(FloorPlateMissingInputError):
        FloorPlateBuilder().build(solver_input, None)  # type: ignore[arg-type]


def test_zero_solver_execution_and_geometry_generation_invariant() -> None:
    forbidden_terms = [
        "room_x",
        "room_y",
        "room_width",
        "room_height",
        "corridor",
        "circulation",
        "wall",
        "door",
        "window",
        "slab",
        "cp_sat",
        "or_tools",
        "milp",
        "solver_penalty",
        "solver_weight",
    ]

    for model_cls in (FloorPlateInput, FloorPlate):
        for field_name in model_cls.model_fields:
            for forbidden in forbidden_terms:
                assert forbidden not in field_name.lower(), (
                    f"Forbidden solver/geometry field {field_name!r} found in {model_cls.__name__}"
                )


def test_floor_plate_semantic_docstring_note() -> None:
    doc = FloorPlate.__doc__ or ""
    import brif_ai.spatial.floor_plate.models as fp_mod

    combined = (fp_mod.__doc__ or "") + doc
    assert "schematic room-layout containment boundary" in combined
    assert "wall thickness" in combined
    assert "structural slab" in combined
    assert "construction-ready" in combined
