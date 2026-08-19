"""Comprehensive test suite for BRIF.AI Room Geometry Solver V0."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

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
from brif_ai.spatial.floor_plate.errors import FloorPlateOutsideBuildableEnvelopeError
from brif_ai.spatial.floor_plate.models import (
    FloorPlate,
    FloorPlateInput,
    generate_floor_plate_id,
)
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
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
from brif_ai.spatial.room_solver.errors import (
    RoomGeometryGridAlignmentError,
    RoomGeometryInfeasibleError,
    RoomGeometryInputMismatchError,
    RoomGeometryUnderconstrainedSpaceError,
    RoomGeometryUnsupportedDirectiveError,
    RoomGeometryUnsupportedFloorPlateError,
    RoomGeometryUnsupportedMetricError,
    RoomGeometryUnsupportedOptionalSpaceError,
)
from brif_ai.spatial.room_solver.models import (
    RoomGeometrySolution,
    RoomGeometrySolverConfig,
    RoomRectangle,
)
from brif_ai.spatial.room_solver.solver import RoomGeometrySolver
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_input import LayoutSolverInputAssembler, LayoutSolverInputSet
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.solver_policy.models import (
    ConstraintEnforcement,
    SolverRelationOperator,
)

_FLOAT_TOL = 1e-6


def _ready_program_two_rooms() -> SpatialProgram:
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client wants living room connected to kitchen.",
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


def _ready_program_three_rooms() -> SpatialProgram:
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client wants living room connected to kitchen and bedroom.",
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
            display_name="Bedroom",
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
        SpatialRelationshipInput(
            source_space_id="sn_living_01",
            target_space_id="sn_bedroom_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev.id],
            rationale="Living adjacent to bedroom",
        ),
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships,
        created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC),
    )
    return SpatialProgramBuilder().build(snapshot, graph)


def _sample_two_room_setup(
    *,
    fp_width: float = 6.0,
    fp_depth: float = 6.0,
    fp_origin_x: float = 0.0,
    fp_origin_y: float = 0.0,
    living_min_area: float = 20.0,
    kitchen_min_area: float = 10.0,
    living_max_area: float | None = None,
    kitchen_min_width: float | None = None,
) -> tuple[LayoutSolverInputSet, FloorPlate]:
    program = _ready_program_two_rooms()
    ev_id = "ev_01"

    # Directive set
    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    # Metrics
    metric_inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=living_min_area,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
        ),
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=kitchen_min_area,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
        ),
    ]
    if living_max_area is not None:
        metric_inputs.append(
            MetricRequirementInput(
                space_id="sn_living_01",
                requirement_type=MetricRequirementType.MAX_AREA,
                value=living_max_area,
                unit=MetricUnit.SQUARE_METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=[ev_id],
            )
        )
    if kitchen_min_width is not None:
        metric_inputs.append(
            MetricRequirementInput(
                space_id="sn_kitchen_01",
                requirement_type=MetricRequirementType.MIN_CLEAR_WIDTH,
                value=kitchen_min_width,
                unit=MetricUnit.METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=[ev_id],
            )
        )

    metrics = MetricSpatialRequirementsBuilder().build(
        program, metric_inputs, created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC)
    )

    # Site envelope (large enough to contain floor plate)
    p_min_x = min(fp_origin_x, 0.0) - 10.0
    p_min_y = min(fp_origin_y, 0.0) - 10.0
    p_max_x = max(fp_origin_x + fp_width, 50.0) + 10.0
    p_max_y = max(fp_origin_y + fp_depth, 50.0) + 10.0

    parcel_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=p_min_x, y_m=p_min_y),
            SitePoint(x_m=p_max_x, y_m=p_min_y),
            SitePoint(x_m=p_max_x, y_m=p_max_y),
            SitePoint(x_m=p_min_x, y_m=p_max_y),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
    )
    envelope_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=p_min_x + 2.0, y_m=p_min_y + 2.0),
            SitePoint(x_m=p_max_x - 2.0, y_m=p_min_y + 2.0),
            SitePoint(x_m=p_max_x - 2.0, y_m=p_max_y - 2.0),
            SitePoint(x_m=p_min_x + 2.0, y_m=p_max_y - 2.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
    )
    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=parcel_inp,
        buildable_envelope=envelope_inp,
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    fp_input = FloorPlateInput(
        vertices=[
            SitePoint(x_m=fp_origin_x, y_m=fp_origin_y),
            SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y),
            SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y + fp_depth),
            SitePoint(x_m=fp_origin_x, y_m=fp_origin_y + fp_depth),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
        rationale="Rectangular FloorPlate perimeter",
    )
    floor_plate = FloorPlateBuilder().build(solver_input, fp_input)

    return solver_input, floor_plate


def _sample_three_room_setup() -> tuple[LayoutSolverInputSet, FloorPlate]:
    program = _ready_program_three_rooms()
    ev_id = "ev_01"

    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    metric_inputs = [
        MetricRequirementInput(
            space_id="sn_living_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=20.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
        ),
        MetricRequirementInput(
            space_id="sn_kitchen_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=10.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
        ),
        MetricRequirementInput(
            space_id="sn_bedroom_01",
            requirement_type=MetricRequirementType.MIN_AREA,
            value=12.0,
            unit=MetricUnit.SQUARE_METRE,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
        ),
    ]

    metrics = MetricSpatialRequirementsBuilder().build(
        program, metric_inputs, created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC)
    )

    parcel_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=50.0),
            SitePoint(x_m=0.0, y_m=50.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
    )
    envelope_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=2.0, y_m=2.0),
            SitePoint(x_m=48.0, y_m=2.0),
            SitePoint(x_m=48.0, y_m=48.0),
            SitePoint(x_m=2.0, y_m=48.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
    )
    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=parcel_inp,
        buildable_envelope=envelope_inp,
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    fp_input = FloorPlateInput(
        vertices=[
            SitePoint(x_m=5.0, y_m=5.0),
            SitePoint(x_m=15.0, y_m=5.0),
            SitePoint(x_m=15.0, y_m=15.0),
            SitePoint(x_m=5.0, y_m=15.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
    )
    floor_plate = FloorPlateBuilder().build(solver_input, fp_input)

    return solver_input, floor_plate


# -----------------------------------------------------------------------------
# 1. Successful Solves & Geometry Verification Tests
# -----------------------------------------------------------------------------


def test_valid_two_room_solve_with_adjacency() -> None:
    solver_input, floor_plate = _sample_two_room_setup(fp_width=6.0, fp_depth=6.0)
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)

    assert isinstance(solution, RoomGeometrySolution)
    assert solution.schema_version == "room_geometry_solution.v0"
    assert solution.project_id == solver_input.project_id
    assert solution.source_brief_version == 1
    assert solution.source_solver_input_schema_version == "layout_solver_input_set.v0"
    assert solution.source_floor_plate_schema_version == "floor_plate.v0"
    assert solution.source_floor_plate_id == floor_plate.id
    assert solution.status == "FEASIBLE"
    assert len(solution.rooms) == 2

    # Check non-zero dimensions and metrics
    r_living = next(r for r in solution.rooms if r.space_id == "sn_living_01")
    r_kitchen = next(r for r in solution.rooms if r.space_id == "sn_kitchen_01")

    assert r_living.area_m2 >= 20.0 - _FLOAT_TOL
    assert r_kitchen.area_m2 >= 10.0 - _FLOAT_TOL
    assert r_living.width_m > 0
    assert r_living.depth_m > 0
    assert r_kitchen.width_m > 0
    assert r_kitchen.depth_m > 0

    # Adjacency positive shared edge verification
    shared_v = (
        abs(r_living.x_m + r_living.width_m - r_kitchen.x_m) <= _FLOAT_TOL
        or abs(r_kitchen.x_m + r_kitchen.width_m - r_living.x_m) <= _FLOAT_TOL
    ) and (
        min(r_living.y_m + r_living.depth_m, r_kitchen.y_m + r_kitchen.depth_m)
        - max(r_living.y_m, r_kitchen.y_m)
        >= config.grid_step_m - _FLOAT_TOL
    )

    shared_h = (
        abs(r_living.y_m + r_living.depth_m - r_kitchen.y_m) <= _FLOAT_TOL
        or abs(r_kitchen.y_m + r_kitchen.depth_m - r_living.y_m) <= _FLOAT_TOL
    ) and (
        min(r_living.x_m + r_living.width_m, r_kitchen.x_m + r_kitchen.width_m)
        - max(r_living.x_m, r_kitchen.x_m)
        >= config.grid_step_m - _FLOAT_TOL
    )

    assert shared_v or shared_h


def test_valid_three_room_solve_with_multiple_adjacencies() -> None:
    solver_input, floor_plate = _sample_three_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)

    assert len(solution.rooms) == 3
    room_ids = {r.space_id for r in solution.rooms}
    assert room_ids == {"sn_living_01", "sn_kitchen_01", "sn_bedroom_01"}


def test_real_calculated_coordinates_produced() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    for r in solution.rooms:
        assert r.width_m > 0
        assert r.depth_m > 0
        assert r.area_m2 > 0
        assert abs(r.area_m2 - round(r.width_m * r.depth_m, 9)) <= _FLOAT_TOL


def test_all_rooms_inside_floor_plate() -> None:
    solver_input, floor_plate = _sample_two_room_setup(
        fp_origin_x=10.0, fp_origin_y=10.0, fp_width=8.0, fp_depth=6.0
    )
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    for r in solution.rooms:
        assert r.x_m >= 10.0 - _FLOAT_TOL
        assert r.y_m >= 10.0 - _FLOAT_TOL
        assert r.x_m + r.width_m <= 18.0 + _FLOAT_TOL
        assert r.y_m + r.depth_m <= 16.0 + _FLOAT_TOL


def test_all_rooms_non_overlapping() -> None:
    solver_input, floor_plate = _sample_three_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    rooms = solution.rooms
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            r1, r2 = rooms[i], rooms[j]
            disjoint_x = (r1.x_m + r1.width_m <= r2.x_m + _FLOAT_TOL) or (
                r2.x_m + r2.width_m <= r1.x_m + _FLOAT_TOL
            )
            disjoint_y = (r1.y_m + r1.depth_m <= r2.y_m + _FLOAT_TOL) or (
                r2.y_m + r2.depth_m <= r1.y_m + _FLOAT_TOL
            )
            assert disjoint_x or disjoint_y


def test_max_area_enforced() -> None:
    # Living room min 20m2, max 22m2 in a 6x6 floor plate
    solver_input, floor_plate = _sample_two_room_setup(living_min_area=20.0, living_max_area=22.0)
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    r_living = next(r for r in solution.rooms if r.space_id == "sn_living_01")
    assert 20.0 - _FLOAT_TOL <= r_living.area_m2 <= 22.0 + _FLOAT_TOL


def test_min_clear_width_enforced() -> None:
    # Kitchen min clear width 2.5m
    solver_input, floor_plate = _sample_two_room_setup(kitchen_min_width=2.5)
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    r_kitchen = next(r for r in solution.rooms if r.space_id == "sn_kitchen_01")
    assert r_kitchen.width_m >= 2.5 - _FLOAT_TOL
    assert r_kitchen.depth_m >= 2.5 - _FLOAT_TOL


def test_infeasible_packing_raises_room_geometry_infeasible_error() -> None:
    # 25m2 + 25m2 = 50m2 inside 36m2 floor plate -> infeasible
    solver_input, floor_plate = _sample_two_room_setup(living_min_area=25.0, kitchen_min_area=25.0)
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryInfeasibleError, match="mathematically INFEASIBLE"):
        RoomGeometrySolver.solve(solver_input, floor_plate, config)


# -----------------------------------------------------------------------------
# 2. FloorPlate Capability Gate Tests
# -----------------------------------------------------------------------------


def test_non_rectangular_floor_plate_rejected_as_unsupported() -> None:
    solver_input, _ = _sample_two_room_setup()
    # 5-vertex polygon
    fp_5_verts = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=5.0),
            SitePoint(x_m=5.0, y_m=10.0),
            SitePoint(x_m=0.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedFloorPlateError, match="requires exactly 4 vertices"):
        RoomGeometrySolver.solve(solver_input, fp_5_verts, config)


def test_concave_floor_plate_rejected_as_unsupported() -> None:
    solver_input, _ = _sample_two_room_setup()
    # L-shaped 6-vertex polygon
    fp_l_shape = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=5.0),
            SitePoint(x_m=5.0, y_m=5.0),
            SitePoint(x_m=5.0, y_m=10.0),
            SitePoint(x_m=0.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedFloorPlateError):
        RoomGeometrySolver.solve(solver_input, fp_l_shape, config)


def test_cw_and_ccw_rectangular_floor_plate_accepted() -> None:
    solver_input, _ = _sample_two_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    # CCW
    fp_ccw = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=6.0, y_m=0.0),
            SitePoint(x_m=6.0, y_m=6.0),
            SitePoint(x_m=0.0, y_m=6.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    sol_ccw = RoomGeometrySolver.solve(solver_input, fp_ccw, config)
    assert len(sol_ccw.rooms) == 2

    # CW (reversed vertices)
    fp_cw = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=0.0, y_m=6.0),
            SitePoint(x_m=6.0, y_m=6.0),
            SitePoint(x_m=6.0, y_m=0.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    sol_cw = RoomGeometrySolver.solve(solver_input, fp_cw, config)
    assert len(sol_cw.rooms) == 2


def test_arbitrary_rectangle_start_vertex_accepted() -> None:
    solver_input, _ = _sample_two_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    # Start from top-right corner
    fp_shifted = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=6.0, y_m=6.0),
            SitePoint(x_m=0.0, y_m=6.0),
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=6.0, y_m=0.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    sol = RoomGeometrySolver.solve(solver_input, fp_shifted, config)
    assert len(sol.rooms) == 2


def test_negative_floor_plate_origin_supported() -> None:
    solver_input, floor_plate = _sample_two_room_setup(
        fp_origin_x=-10.0, fp_origin_y=-10.0, fp_width=6.0, fp_depth=6.0
    )
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    for r in solution.rooms:
        assert r.x_m >= -10.0 - _FLOAT_TOL
        assert r.y_m >= -10.0 - _FLOAT_TOL
        assert r.x_m + r.width_m <= -4.0 + _FLOAT_TOL
        assert r.y_m + r.depth_m <= -4.0 + _FLOAT_TOL


# -----------------------------------------------------------------------------
# 3. Cross-Contract & Re-Validation Checks
# -----------------------------------------------------------------------------


def test_project_mismatch_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    bad_fp = floor_plate.model_copy(
        update={"project_id": "proj_999", "id": generate_floor_plate_id("proj_999")}
    )
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryInputMismatchError, match="project_id mismatch"):
        RoomGeometrySolver.solve(solver_input, bad_fp, config)


def test_brief_version_mismatch_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    bad_fp = floor_plate.model_copy(update={"source_brief_version": 2})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryInputMismatchError, match="source_brief_version mismatch"):
        RoomGeometrySolver.solve(solver_input, bad_fp, config)


def test_floor_plate_outside_buildable_envelope_rejected_at_solver_boundary() -> None:
    solver_input, _ = _sample_two_room_setup()
    # FloorPlate completely outside the site buildable envelope
    outside_fp = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=100.0, y_m=100.0),
            SitePoint(x_m=106.0, y_m=100.0),
            SitePoint(x_m=106.0, y_m=106.0),
            SitePoint(x_m=100.0, y_m=106.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(FloorPlateOutsideBuildableEnvelopeError):
        RoomGeometrySolver.solve(solver_input, outside_fp, config)


# -----------------------------------------------------------------------------
# 4. Unsupported Semantics Rejection Tests
# -----------------------------------------------------------------------------


def test_optional_layout_space_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    # Modify living room to mandatory=False
    spaces_mod = [
        solver_input.spaces[0].model_copy(update={"mandatory": False}),
        solver_input.spaces[1],
    ]
    bad_input = solver_input.model_copy(update={"spaces": spaces_mod})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedOptionalSpaceError, match="is optional"):
        RoomGeometrySolver.solve(bad_input, floor_plate, config)


def test_missing_min_area_rejected_as_underconstrained() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    # Empty requirements for living room
    smr_mod = [
        solver_input.space_metric_requirements[0].model_copy(update={"requirements": []}),
        solver_input.space_metric_requirements[1],
    ]
    bad_input = solver_input.model_copy(update={"space_metric_requirements": smr_mod})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(
        RoomGeometryUnderconstrainedSpaceError, match="lacks a mandatory hard MIN_AREA"
    ):
        RoomGeometrySolver.solve(bad_input, floor_plate, config)


def test_target_area_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    target_req = MetricRequirement(
        id="mreq_target_01",
        space_id="sn_living_01",
        requirement_type=MetricRequirementType.TARGET_AREA,
        value=25.0,
        unit=MetricUnit.SQUARE_METRE,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_01"],
    )
    smr_mod = [
        solver_input.space_metric_requirements[0].model_copy(
            update={
                "requirements": [
                    *solver_input.space_metric_requirements[0].requirements,
                    target_req,
                ]
            }
        ),
        solver_input.space_metric_requirements[1],
    ]
    bad_input = solver_input.model_copy(update={"space_metric_requirements": smr_mod})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedMetricError, match="TARGET_AREA"):
        RoomGeometrySolver.solve(bad_input, floor_plate, config)


def test_should_and_could_metric_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    req_should = (
        solver_input.space_metric_requirements[0]
        .requirements[0]
        .model_copy(update={"priority": Priority.SHOULD})
    )
    smr_mod = [
        solver_input.space_metric_requirements[0].model_copy(update={"requirements": [req_should]}),
        solver_input.space_metric_requirements[1],
    ]
    bad_input = solver_input.model_copy(update={"space_metric_requirements": smr_mod})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedMetricError, match="only MUST is supported"):
        RoomGeometrySolver.solve(bad_input, floor_plate, config)


def test_preferred_and_optional_directive_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    dir_preferred = solver_input.directives[0].model_copy(
        update={"enforcement": ConstraintEnforcement.PREFERRED}
    )
    bad_input = solver_input.model_copy(update={"directives": [dir_preferred]})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedDirectiveError, match="only REQUIRED is supported"):
        RoomGeometrySolver.solve(bad_input, floor_plate, config)


def test_required_proximity_and_separation_rejected() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    dir_proximity = solver_input.directives[0].model_copy(
        update={"operator": SolverRelationOperator.PROXIMITY}
    )
    bad_input = solver_input.model_copy(update={"directives": [dir_proximity]})
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryUnsupportedDirectiveError, match="only ADJACENCY is supported"):
        RoomGeometrySolver.solve(bad_input, floor_plate, config)


def test_floor_width_not_aligned_with_grid_rejected() -> None:
    # 6.05m width with 0.10m grid -> not integer multiple
    solver_input, floor_plate = _sample_two_room_setup(fp_width=6.05, fp_depth=6.0)
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryGridAlignmentError, match="not exact integer multiples"):
        RoomGeometrySolver.solve(solver_input, floor_plate, config)


def test_floor_depth_not_aligned_with_grid_rejected() -> None:
    # 6.05m depth with 0.10m grid -> not integer multiple
    solver_input, floor_plate = _sample_two_room_setup(fp_width=6.0, fp_depth=6.05)
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    with pytest.raises(RoomGeometryGridAlignmentError, match="not exact integer multiples"):
        RoomGeometrySolver.solve(solver_input, floor_plate, config)


# -----------------------------------------------------------------------------
# 5. Metric Quantization Behavior Tests
# -----------------------------------------------------------------------------


def test_min_area_quantization_never_weakens_minimum() -> None:
    step = Decimal("0.1")
    step_sq = step * step
    val = Decimal("15.01")
    cells = int((val / step_sq).to_integral_value(rounding=ROUND_CEILING))
    # 15.01 / 0.01 = 1501 cells = 15.01 m2
    assert cells * float(step_sq) >= float(val)


def test_max_area_quantization_never_exceeds_maximum() -> None:
    step = Decimal("0.1")
    step_sq = step * step
    val = Decimal("15.99")
    cells = int((val / step_sq).to_integral_value(rounding=ROUND_FLOOR))
    # 15.99 / 0.01 = 1599 cells = 15.99 m2
    assert cells * float(step_sq) <= float(val)


def test_min_clear_width_quantization_never_weakens_width() -> None:
    step = Decimal("0.1")
    val = Decimal("2.55")
    cells = int((val / step).to_integral_value(rounding=ROUND_CEILING))
    # 2.55 / 0.1 = 26 cells = 2.6 m
    assert cells * float(step) >= float(val)


# -----------------------------------------------------------------------------
# 6. Determinism & Solution Contract Tests
# -----------------------------------------------------------------------------


def test_deterministic_repeated_solve_json() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    sol1 = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    sol2 = RoomGeometrySolver.solve(solver_input, floor_plate, config)

    assert sol1.model_dump_json(indent=2) == sol2.model_dump_json(indent=2)


def test_room_output_sorted_by_space_id() -> None:
    solver_input, floor_plate = _sample_three_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    space_ids = [r.space_id for r in solution.rooms]
    assert space_ids == sorted(space_ids)


def test_solution_timestamp_deterministic() -> None:
    solver_input, floor_plate = _sample_two_room_setup()
    config = RoomGeometrySolverConfig(grid_step_m=0.10)

    solution = RoomGeometrySolver.solve(solver_input, floor_plate, config)
    expected_ts = max(solver_input.created_at, floor_plate.created_at)
    assert solution.created_at == expected_ts


def test_zero_design_objective_and_forbidden_fields_invariant() -> None:
    forbidden_terms = [
        "wall",
        "door",
        "window",
        "corridor",
        "circulation",
        "cost",
        "penalty",
        "weight",
        "taks",
        "kaks",
    ]
    for model_cls in (RoomGeometrySolverConfig, RoomRectangle, RoomGeometrySolution):
        for field_name in model_cls.model_fields:
            for forbidden in forbidden_terms:
                assert forbidden not in field_name.lower(), (
                    f"Forbidden field {field_name!r} in {model_cls.__name__}"
                )


# -----------------------------------------------------------------------------
# 7. Direct Model Invariant Tests
# -----------------------------------------------------------------------------


def test_direct_room_rectangle_validation() -> None:
    # Valid
    rect = RoomRectangle(
        space_id="sn_living_01",
        x_m=0.0,
        y_m=0.0,
        width_m=4.0,
        depth_m=5.0,
        area_m2=20.0,
    )
    assert rect.area_m2 == 20.0

    # Non-positive width
    with pytest.raises(ValidationError):
        RoomRectangle(
            space_id="sn_living_01",
            x_m=0.0,
            y_m=0.0,
            width_m=0.0,
            depth_m=5.0,
            area_m2=0.0,
        )

    # Mismatched area
    with pytest.raises(ValidationError, match="does not match width_m \\* depth_m"):
        RoomRectangle(
            space_id="sn_living_01",
            x_m=0.0,
            y_m=0.0,
            width_m=4.0,
            depth_m=5.0,
            area_m2=25.0,
        )


def test_direct_room_geometry_solution_validation() -> None:
    r1 = RoomRectangle(
        space_id="sn_kitchen_01", x_m=0.0, y_m=0.0, width_m=2.0, depth_m=5.0, area_m2=10.0
    )
    r2 = RoomRectangle(
        space_id="sn_living_01", x_m=2.0, y_m=0.0, width_m=4.0, depth_m=5.0, area_m2=20.0
    )

    # Valid
    sol = RoomGeometrySolution(
        project_id="proj_101",
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        source_floor_plate_schema_version="floor_plate.v0",
        source_floor_plate_id="fplate_1234567890123456",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        grid_step_m=0.10,
        rooms=[r1, r2],
    )
    assert len(sol.rooms) == 2

    # Duplicate space ID
    with pytest.raises(ValidationError, match="Duplicate space_id"):
        RoomGeometrySolution(
            project_id="proj_101",
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id="fplate_1234567890123456",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            grid_step_m=0.10,
            rooms=[r1, r1],
        )

    # Unsorted rooms
    with pytest.raises(ValidationError, match="Rooms must be sorted deterministically"):
        RoomGeometrySolution(
            project_id="proj_101",
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id="fplate_1234567890123456",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            grid_step_m=0.10,
            rooms=[r2, r1],
        )

    # Overlapping rooms
    r_overlap = RoomRectangle(
        space_id="sn_living_01", x_m=1.0, y_m=0.0, width_m=4.0, depth_m=5.0, area_m2=20.0
    )
    with pytest.raises(ValidationError, match="overlap geometrically"):
        RoomGeometrySolution(
            project_id="proj_101",
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id="fplate_1234567890123456",
            created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
            coordinate_system="LOCAL_CARTESIAN_METRES",
            grid_step_m=0.10,
            rooms=[r1, r_overlap],
        )


def test_config_validation() -> None:
    # Valid
    cfg = RoomGeometrySolverConfig(grid_step_m=0.10, max_time_seconds=15.0)
    assert cfg.grid_step_m == 0.10

    # 0 grid_step_m
    with pytest.raises(ValidationError):
        RoomGeometrySolverConfig(grid_step_m=0.0)

    # Negative grid_step_m
    with pytest.raises(ValidationError):
        RoomGeometrySolverConfig(grid_step_m=-0.1)

    # NaN / Inf
    with pytest.raises(ValidationError):
        RoomGeometrySolverConfig(grid_step_m=float("nan"))
