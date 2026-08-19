"""Comprehensive test suite for BRIF.AI SVG Plan View V0."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

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
from brif_ai.spatial.room_solver.models import (
    RoomGeometrySolution,
    RoomRectangle,
)
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_input import LayoutSolverInputAssembler, LayoutSolverInputSet
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.svg_plan.errors import (
    SvgPlanInputMismatchError,
    SvgPlanInvalidGeometryError,
    SvgPlanUnknownSpaceError,
)
from brif_ai.spatial.svg_plan.models import (
    SvgPlanDocument,
    SvgPlanRenderConfig,
)
from brif_ai.spatial.svg_plan.renderer import SvgPlanRenderer, _fmt


def _build_two_room_fixture(
    *,
    living_name: str = "Living Room",
    kitchen_name: str = "Kitchen",
    fp_origin_x: float = 4.0,
    fp_origin_y: float = 4.0,
    fp_width: float = 6.0,
    fp_depth: float = 6.0,
    living_x: float = 4.0,
    living_y: float = 4.0,
    living_w: float = 3.4,
    living_d: float = 5.9,
    kitchen_x: float = 7.4,
    kitchen_y: float = 4.0,
    kitchen_w: float = 1.9,
    kitchen_d: float = 5.3,
) -> tuple[LayoutSolverInputSet, FloorPlate, RoomGeometrySolution]:
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client requested living room adjacent to kitchen.",
    )
    spaces = [
        SpaceRequest(
            id="sr_living",
            display_name=living_name,
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_kitchen",
            display_name=kitchen_name,
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
        project_id="proj_living_kitchen_01",
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
            rationale="Open-plan connection",
        ),
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships,
        created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC),
    )
    program = SpatialProgramBuilder().build(snapshot, graph)

    layout_problem = LayoutProblemCompiler().compile(program)
    directive_set = SolverPolicyCompiler().compile(layout_problem)

    metrics = MetricSpatialRequirementsBuilder().build(
        program,
        [
            MetricRequirementInput(
                space_id="sn_living_01",
                requirement_type=MetricRequirementType.MIN_AREA,
                value=20.0,
                unit=MetricUnit.SQUARE_METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=[ev.id],
            ),
            MetricRequirementInput(
                space_id="sn_kitchen_01",
                requirement_type=MetricRequirementType.MIN_AREA,
                value=10.0,
                unit=MetricUnit.SQUARE_METRE,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=[ev.id],
            ),
        ],
        created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC),
    )

    p_min_x = min(fp_origin_x, 0.0) - 10.0
    p_min_y = min(fp_origin_y, 0.0) - 10.0
    p_max_x = max(fp_origin_x + fp_width, 50.0) + 10.0
    p_max_y = max(fp_origin_y + fp_depth, 50.0) + 10.0

    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=SitePolygonInput(
            vertices=[
                SitePoint(x_m=p_min_x, y_m=p_min_y),
                SitePoint(x_m=p_max_x, y_m=p_min_y),
                SitePoint(x_m=p_max_x, y_m=p_max_y),
                SitePoint(x_m=p_min_x, y_m=p_max_y),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
        ),
        buildable_envelope=SitePolygonInput(
            vertices=[
                SitePoint(x_m=p_min_x + 2.0, y_m=p_min_y + 2.0),
                SitePoint(x_m=p_max_x - 2.0, y_m=p_min_y + 2.0),
                SitePoint(x_m=p_max_x - 2.0, y_m=p_max_y - 2.0),
                SitePoint(x_m=p_min_x + 2.0, y_m=p_max_y - 2.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
        ),
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    solver_input = LayoutSolverInputAssembler.assemble(directive_set, metrics, site_env)

    floor_plate = FloorPlateBuilder().build(
        solver_input,
        FloorPlateInput(
            vertices=[
                SitePoint(x_m=fp_origin_x, y_m=fp_origin_y),
                SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y),
                SitePoint(x_m=fp_origin_x + fp_width, y_m=fp_origin_y + fp_depth),
                SitePoint(x_m=fp_origin_x, y_m=fp_origin_y + fp_depth),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
            rationale="Rectangular FloorPlate perimeter",
        ),
    )

    r_kitchen = RoomRectangle(
        space_id="sn_kitchen_01",
        x_m=kitchen_x,
        y_m=kitchen_y,
        width_m=kitchen_w,
        depth_m=kitchen_d,
        area_m2=round(kitchen_w * kitchen_d, 9),
    )
    r_living = RoomRectangle(
        space_id="sn_living_01",
        x_m=living_x,
        y_m=living_y,
        width_m=living_w,
        depth_m=living_d,
        area_m2=round(living_w * living_d, 9),
    )

    solution = RoomGeometrySolution(
        schema_version="room_geometry_solution.v0",
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        source_floor_plate_schema_version="floor_plate.v0",
        source_floor_plate_id=floor_plate.id,
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        grid_step_m=0.10,
        status="FEASIBLE",
        rooms=[r_kitchen, r_living],
    )

    return solver_input, floor_plate, solution


# -----------------------------------------------------------------------------
# 1. Successful Render & Contract Tests
# -----------------------------------------------------------------------------


def test_valid_two_room_solution_renders_svg() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    assert isinstance(doc, SvgPlanDocument)
    assert doc.schema_version == "svg_plan_document.v0"
    assert doc.project_id == solver_input.project_id
    assert doc.source_brief_version == 1
    assert doc.source_solver_input_schema_version == "layout_solver_input_set.v0"
    assert doc.source_floor_plate_schema_version == "floor_plate.v0"
    assert doc.source_floor_plate_id == floor_plate.id
    assert doc.source_room_solution_schema_version == "room_geometry_solution.v0"
    assert doc.coordinate_system == "LOCAL_CARTESIAN_METRES"
    assert doc.width_px > 0
    assert doc.height_px > 0
    assert "<svg" in doc.svg


def test_svg_parses_successfully_with_element_tree() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    root = ET.fromstring(doc.svg)
    assert root.tag.endswith("svg")
    assert root.attrib["width"] == _fmt(doc.width_px)
    assert root.attrib["height"] == _fmt(doc.height_px)


def test_floor_plate_polygon_rendered() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    config = SvgPlanRenderConfig(scale_px_per_m=100.0, margin_px=50.0)
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)

    root = ET.fromstring(doc.svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    polygons = root.findall(".//svg:polygon", ns)
    assert len(polygons) == 1
    assert "floor-plate" in polygons[0].attrib.get("class", "")


def test_every_room_rectangle_rendered_with_data_space_id() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    root = ET.fromstring(doc.svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    groups = root.findall(".//svg:g", ns)
    assert len(groups) == 2

    space_ids = [g.attrib.get("data-space-id") for g in groups]
    assert space_ids == ["sn_kitchen_01", "sn_living_01"]


def test_layout_space_display_name_used_as_visible_label() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture(
        living_name="Oturma Odası", kitchen_name="Mutfak"
    )
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    assert "Oturma Odası" in doc.svg
    assert "Mutfak" in doc.svg


def test_area_label_rendered_when_enabled_and_absent_when_disabled() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()

    # Enabled
    cfg_on = SvgPlanRenderConfig(show_area_labels=True)
    doc_on = SvgPlanRenderer.render(solver_input, floor_plate, solution, cfg_on)
    assert "m²" in doc_on.svg

    # Disabled
    cfg_off = SvgPlanRenderConfig(show_area_labels=False)
    doc_off = SvgPlanRenderer.render(solver_input, floor_plate, solution, cfg_off)
    assert "m²" not in doc_off.svg


def test_space_id_hidden_by_default_and_visible_when_configured() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()

    # Default (hidden)
    doc_def = SvgPlanRenderer.render(solver_input, floor_plate, solution)
    root_def = ET.fromstring(doc_def.svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    id_texts_def = [
        t for t in root_def.findall(".//svg:text", ns) if "room-id" in t.attrib.get("class", "")
    ]
    assert len(id_texts_def) == 0

    # Configured (visible)
    cfg_id = SvgPlanRenderConfig(show_space_ids=True)
    doc_id = SvgPlanRenderer.render(solver_input, floor_plate, solution, cfg_id)
    root_id = ET.fromstring(doc_id.svg)
    id_texts_id = [
        t for t in root_id.findall(".//svg:text", ns) if "room-id" in t.attrib.get("class", "")
    ]
    assert len(id_texts_id) == 2


def test_deterministic_room_ordering_and_repeated_render_byte_for_byte_identical() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    config = SvgPlanRenderConfig(scale_px_per_m=80.0, margin_px=40.0)

    doc1 = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)
    doc2 = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)

    assert doc1.svg == doc2.svg
    assert doc1.model_dump_json(indent=2) == doc2.model_dump_json(indent=2)


# -----------------------------------------------------------------------------
# 2. Coordinate Transformation & Geometry Tests
# -----------------------------------------------------------------------------


def test_negative_project_coordinates_correctly_translated() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture(
        fp_origin_x=-10.0,
        fp_origin_y=-10.0,
        fp_width=6.0,
        fp_depth=6.0,
        living_x=-10.0,
        living_y=-10.0,
        living_w=3.4,
        living_d=5.9,
        kitchen_x=-6.6,
        kitchen_y=-10.0,
        kitchen_w=1.9,
        kitchen_d=5.3,
    )
    config = SvgPlanRenderConfig(scale_px_per_m=100.0, margin_px=50.0)
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)

    root = ET.fromstring(doc.svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    rects = root.findall(".//svg:rect", ns)
    # Background + 2 room rects
    assert len(rects) == 3
    room_rects = [r for r in rects if "room-rect" in r.attrib.get("class", "")]
    for r in room_rects:
        rx = float(r.attrib["x"])
        ry = float(r.attrib["y"])
        rw = float(r.attrib["width"])
        rh = float(r.attrib["height"])
        assert rx >= 50.0
        assert ry >= 50.0
        assert rx + rw <= 650.0
        assert ry + rh <= 650.0


def test_svg_y_axis_inversion_correct() -> None:
    # Floor plate [0, 10] x [0, 10], room at bottom in Cartesian (y=0) should have high Y in SVG
    solver_input, floor_plate, solution = _build_two_room_fixture(
        fp_origin_x=0.0,
        fp_origin_y=0.0,
        fp_width=10.0,
        fp_depth=10.0,
        living_x=0.0,
        living_y=0.0,
        living_w=5.0,
        living_d=4.0,
        kitchen_x=5.0,
        kitchen_y=0.0,
        kitchen_w=4.0,
        kitchen_d=4.0,
    )
    config = SvgPlanRenderConfig(scale_px_per_m=100.0, margin_px=0.0)
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)

    root = ET.fromstring(doc.svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    # In Cartesian: room y=0 to y=4. In SVG with Y-inversion:
    # svg_y = 0 + (10 - 4) * 100 = 600
    living_group = root.find('.//svg:g[@data-space-id="sn_living_01"]', ns)
    assert living_group is not None
    living_rect = living_group.find("svg:rect", ns)
    assert living_rect is not None
    assert float(living_rect.attrib["y"]) == 600.0


def test_margin_and_dimensions_in_pixels() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture(
        fp_origin_x=0.0,
        fp_origin_y=0.0,
        fp_width=10.0,
        fp_depth=5.0,
        living_x=0.0,
        living_y=0.0,
        living_w=4.0,
        living_d=4.0,
        kitchen_x=4.0,
        kitchen_y=0.0,
        kitchen_w=4.0,
        kitchen_d=4.0,
    )
    config = SvgPlanRenderConfig(scale_px_per_m=50.0, margin_px=20.0)
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)

    expected_width = 10.0 * 50.0 + 2 * 20.0  # 540
    expected_height = 5.0 * 50.0 + 2 * 20.0  # 290
    assert doc.width_px == expected_width
    assert doc.height_px == expected_height


def test_zero_margin_accepted() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture(
        fp_origin_x=0.0,
        fp_origin_y=0.0,
        fp_width=10.0,
        fp_depth=10.0,
        living_x=0.0,
        living_y=0.0,
        living_w=4.0,
        living_d=4.0,
        kitchen_x=4.0,
        kitchen_y=0.0,
        kitchen_w=4.0,
        kitchen_d=4.0,
    )
    config = SvgPlanRenderConfig(scale_px_per_m=100.0, margin_px=0.0)
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution, config)

    assert doc.width_px == 1000.0
    assert doc.height_px == 1000.0


def test_source_geometry_remains_unchanged_after_render() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    fp_verts_before = [(v.x_m, v.y_m) for v in floor_plate.vertices]
    r_coords_before = [(r.x_m, r.y_m, r.width_m, r.depth_m) for r in solution.rooms]

    _ = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    fp_verts_after = [(v.x_m, v.y_m) for v in floor_plate.vertices]
    r_coords_after = [(r.x_m, r.y_m, r.width_m, r.depth_m) for r in solution.rooms]

    assert fp_verts_before == fp_verts_after
    assert r_coords_before == r_coords_after


def test_non_rectangular_valid_floor_plate_rendered() -> None:
    # 5-vertex polygon floor plate
    solver_input, _, solution = _build_two_room_fixture(
        fp_width=20.0, fp_depth=20.0, living_x=2.0, living_y=2.0, kitchen_x=6.0, kitchen_y=2.0
    )
    fp_poly = FloorPlate(
        id=generate_floor_plate_id(solver_input.project_id),
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=10.0),
            SitePoint(x_m=10.0, y_m=20.0),
            SitePoint(x_m=0.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    # Update solution to match fp_poly id
    sol_updated = solution.model_copy(update={"source_floor_plate_id": fp_poly.id})
    doc = SvgPlanRenderer.render(solver_input, fp_poly, sol_updated)
    assert doc is not None
    assert "<polygon" in doc.svg


# -----------------------------------------------------------------------------
# 3. XML Safety & Turkish UTF-8 Tests
# -----------------------------------------------------------------------------


def test_special_xml_characters_and_turkish_characters_escaped_safely() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture(
        living_name='Oturma & "Salon" <1>', kitchen_name="Çocuk Odası / Mutfak & Bar"
    )
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    # Valid XML parse
    root = ET.fromstring(doc.svg)
    assert root is not None
    # Text content preserved in parsed XML
    ns = {"svg": "http://www.w3.org/2000/svg"}
    titles = [t.text for t in root.findall(".//svg:title", ns)]
    assert 'Oturma & "Salon" <1>' in titles
    assert "Çocuk Odası / Mutfak & Bar" in titles


def test_attribute_safe_data_space_id_serialization() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    root = ET.fromstring(doc.svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    g_elements = root.findall(".//svg:g", ns)
    for g in g_elements:
        attr = g.attrib.get("data-space-id")
        assert attr in ("sn_kitchen_01", "sn_living_01")


def test_negative_zero_pixel_formatting_never_emits_negative_zero() -> None:
    assert _fmt(-0.0) == "0"
    assert _fmt(-0.000001, precision=2) == "0"
    assert _fmt(0.0) == "0"


# -----------------------------------------------------------------------------
# 4. Error Handling & Validation Tests
# -----------------------------------------------------------------------------


def test_project_mismatch_rejected() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    bad_sol = solution.model_copy(update={"project_id": "proj_other"})
    with pytest.raises(SvgPlanInputMismatchError, match="project_id mismatch"):
        SvgPlanRenderer.render(solver_input, floor_plate, bad_sol)


def test_brief_version_mismatch_rejected() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    bad_sol = solution.model_copy(update={"source_brief_version": 2})
    with pytest.raises(SvgPlanInputMismatchError, match="source_brief_version mismatch"):
        SvgPlanRenderer.render(solver_input, floor_plate, bad_sol)


def test_floor_plate_id_mismatch_rejected() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    bad_sol = solution.model_copy(update={"source_floor_plate_id": "fplate_9999999999999999"})
    with pytest.raises(SvgPlanInputMismatchError, match="source_floor_plate_id mismatch"):
        SvgPlanRenderer.render(solver_input, floor_plate, bad_sol)


def test_solution_space_set_mismatch_rejected() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    # Remove one room from solution
    bad_sol = solution.model_copy(update={"rooms": [solution.rooms[0]]})
    with pytest.raises(SvgPlanUnknownSpaceError, match="Missing in solution"):
        SvgPlanRenderer.render(solver_input, floor_plate, bad_sol)


def test_room_outside_floor_plate_rejected_with_invalid_geometry_error() -> None:
    solver_input, floor_plate, _ = _build_two_room_fixture(
        fp_origin_x=0.0, fp_origin_y=0.0, fp_width=10.0, fp_depth=10.0
    )
    # Room placed at x=15 (outside 10m floor plate)
    bad_room1 = RoomRectangle(
        space_id="sn_kitchen_01", x_m=1.0, y_m=1.0, width_m=2.0, depth_m=2.0, area_m2=4.0
    )
    bad_room2 = RoomRectangle(
        space_id="sn_living_01", x_m=15.0, y_m=1.0, width_m=2.0, depth_m=2.0, area_m2=4.0
    )
    bad_sol = RoomGeometrySolution(
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        source_floor_plate_schema_version="floor_plate.v0",
        source_floor_plate_id=floor_plate.id,
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        grid_step_m=0.10,
        rooms=[bad_room1, bad_room2],
    )
    with pytest.raises(SvgPlanInvalidGeometryError, match="extends outside FloorPlate"):
        SvgPlanRenderer.render(solver_input, floor_plate, bad_sol)


def test_concave_floor_plate_edge_escape_rejected_with_invalid_geometry_error() -> None:
    # Concave L-shaped floor plate
    # Corners are [0,0], [10,0], [10,4], [4,4], [4,10], [0,10]
    # A room from [1, 1] to [9, 9] would have its top-right corner at [9,9] outside the cutout
    solver_input, _, solution = _build_two_room_fixture(fp_width=10.0, fp_depth=10.0)
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
            SitePoint(x_m=10.0, y_m=4.0),
            SitePoint(x_m=4.0, y_m=4.0),
            SitePoint(x_m=4.0, y_m=10.0),
            SitePoint(x_m=0.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_01"],
    )
    # Room placed in cutout region [5, 9] x [5, 9]
    bad_r1 = RoomRectangle(
        space_id="sn_kitchen_01", x_m=1.0, y_m=1.0, width_m=2.0, depth_m=2.0, area_m2=4.0
    )
    bad_r2 = RoomRectangle(
        space_id="sn_living_01", x_m=5.0, y_m=5.0, width_m=3.0, depth_m=3.0, area_m2=9.0
    )
    bad_sol = RoomGeometrySolution(
        project_id=solver_input.project_id,
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        source_floor_plate_schema_version="floor_plate.v0",
        source_floor_plate_id=fp_l_shape.id,
        created_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        coordinate_system="LOCAL_CARTESIAN_METRES",
        grid_step_m=0.10,
        rooms=[bad_r1, bad_r2],
    )
    with pytest.raises(SvgPlanInvalidGeometryError):
        SvgPlanRenderer.render(solver_input, fp_l_shape, bad_sol)


def test_config_validation() -> None:
    # Valid
    cfg = SvgPlanRenderConfig(scale_px_per_m=100.0, margin_px=0.0)
    assert cfg.scale_px_per_m == 100.0
    assert cfg.margin_px == 0.0

    # Negative scale
    with pytest.raises(ValidationError):
        SvgPlanRenderConfig(scale_px_per_m=-10.0)

    # Negative margin
    with pytest.raises(ValidationError):
        SvgPlanRenderConfig(margin_px=-1.0)

    # NaN / Inf
    with pytest.raises(ValidationError):
        SvgPlanRenderConfig(scale_px_per_m=float("nan"))
    with pytest.raises(ValidationError):
        SvgPlanRenderConfig(margin_px=float("inf"))


def test_direct_svg_plan_document_validation() -> None:
    valid_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">'
        '<rect width="100" height="100" />'
        "</svg>"
    )
    doc = SvgPlanDocument(
        project_id="proj_101",
        source_brief_version=1,
        source_solver_input_schema_version="layout_solver_input_set.v0",
        source_floor_plate_schema_version="floor_plate.v0",
        source_floor_plate_id="fplate_1234567890123456",
        source_room_solution_schema_version="room_geometry_solution.v0",
        coordinate_system="LOCAL_CARTESIAN_METRES",
        width_px=100.0,
        height_px=100.0,
        svg=valid_svg,
    )
    assert doc.width_px == 100.0

    # Malformed XML
    with pytest.raises(ValidationError, match="Malformed SVG XML"):
        SvgPlanDocument(
            project_id="proj_101",
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id="fplate_1234567890123456",
            source_room_solution_schema_version="room_geometry_solution.v0",
            coordinate_system="LOCAL_CARTESIAN_METRES",
            width_px=100.0,
            height_px=100.0,
            svg="<svg><unclosed></svg>",
        )

    # Wrong root tag
    with pytest.raises(ValidationError, match="Expected root <svg> element"):
        SvgPlanDocument(
            project_id="proj_101",
            source_brief_version=1,
            source_solver_input_schema_version="layout_solver_input_set.v0",
            source_floor_plate_schema_version="floor_plate.v0",
            source_floor_plate_id="fplate_1234567890123456",
            source_room_solution_schema_version="room_geometry_solution.v0",
            coordinate_system="LOCAL_CARTESIAN_METRES",
            width_px=100.0,
            height_px=100.0,
            svg="<div>Not SVG</div>",
        )


def test_zero_forbidden_architectural_elements_rendered() -> None:
    solver_input, floor_plate, solution = _build_two_room_fixture()
    doc = SvgPlanRenderer.render(solver_input, floor_plate, solution)

    forbidden_terms = [
        "door",
        "window",
        "wall",
        "corridor",
        "furniture",
        "column",
        "beam",
        "stair",
        "elevator",
        "taks",
        "kaks",
    ]
    for term in forbidden_terms:
        assert f"<{term}" not in doc.svg.lower()
        assert f'class="{term}' not in doc.svg.lower()
