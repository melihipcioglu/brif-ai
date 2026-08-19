"""Focused tests for BRIF.AI Site / Buildable Envelope V0 domain contracts and builder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

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
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.models import SpatialProgram
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.errors import (
    SiteEnvelopeOutsideParcelError,
    SiteEnvelopeWithoutParcelError,
    SiteMissingInputError,
    SitePolygonDegenerateError,
    SitePolygonSelfIntersectionError,
    SiteSchemaVersionMismatchError,
)
from brif_ai.spatial.site.geometry import (
    calculate_polygon_area,
    validate_polygon_geometry,
)
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SiteGeometryRole,
    SitePoint,
    SitePolygon,
    SitePolygonInput,
    generate_site_geometry_id,
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


def _evidence(ev_id: str = "ev_site_01") -> Evidence:
    return Evidence(
        id=ev_id,
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Client provided site boundary cadastre points.",
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
    project_id: str = "proj_site_test",
    brief_version: int = 1,
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
        )
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
        [],
        created_at=datetime(2026, 8, 19, 12, 5, tzinfo=UTC),
    )
    return SpatialProgramBuilder().build(snapshot, graph)


def _sample_square_parcel_input() -> SitePolygonInput:
    return SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
        rationale="Tapu kadastro parsel siniri.",
    )


def _sample_envelope_input() -> SitePolygonInput:
    return SitePolygonInput(
        vertices=[
            SitePoint(x_m=5.0, y_m=5.0),
            SitePoint(x_m=45.0, y_m=5.0),
            SitePoint(x_m=45.0, y_m=35.0),
            SitePoint(x_m=5.0, y_m=35.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
        rationale="Yapilasma oturum alani.",
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_valid_parcel_boundary_created() -> None:
    program = _ready_program()
    parcel_inp = _sample_square_parcel_input()

    builder = SiteBuildableEnvelopeBuilder()
    site_env = builder.build(program, parcel_boundary=parcel_inp)

    assert isinstance(site_env, SiteBuildableEnvelope)
    assert site_env.schema_version == "site_buildable_envelope.v0"
    assert site_env.project_id == program.project_id
    assert site_env.source_brief_version == program.source_brief_version
    assert site_env.source_program_schema_version == "spatial_program.v0"
    assert site_env.created_at == program.created_at
    assert site_env.coordinate_system == "LOCAL_CARTESIAN_METRES"

    assert site_env.parcel_boundary is not None
    assert site_env.parcel_boundary.role == SiteGeometryRole.PARCEL_BOUNDARY
    assert len(site_env.parcel_boundary.vertices) == 4
    assert site_env.buildable_envelope is None
    assert site_env.authoritative_geometry_ids == [site_env.parcel_boundary.id]


def test_valid_parcel_and_buildable_envelope_created() -> None:
    program = _ready_program()
    parcel_inp = _sample_square_parcel_input()
    envelope_inp = _sample_envelope_input()

    builder = SiteBuildableEnvelopeBuilder()
    site_env = builder.build(
        program,
        parcel_boundary=parcel_inp,
        buildable_envelope=envelope_inp,
    )

    assert site_env.parcel_boundary is not None
    assert site_env.parcel_boundary.role == SiteGeometryRole.PARCEL_BOUNDARY
    assert site_env.buildable_envelope is not None
    assert site_env.buildable_envelope.role == SiteGeometryRole.BUILDABLE_ENVELOPE
    assert len(site_env.authoritative_geometry_ids) == 2
    assert site_env.authoritative_geometry_ids == sorted(
        [site_env.parcel_boundary.id, site_env.buildable_envelope.id]
    )


def test_parcel_absence_remains_absence() -> None:
    program = _ready_program()
    builder = SiteBuildableEnvelopeBuilder()
    site_env = builder.build(program, parcel_boundary=None, buildable_envelope=None)

    assert site_env.parcel_boundary is None
    assert site_env.buildable_envelope is None
    assert site_env.authoritative_geometry_ids == []


def test_buildable_envelope_absence_remains_absence() -> None:
    program = _ready_program()
    parcel_inp = _sample_square_parcel_input()
    builder = SiteBuildableEnvelopeBuilder()
    site_env = builder.build(program, parcel_boundary=parcel_inp, buildable_envelope=None)

    assert site_env.parcel_boundary is not None
    assert site_env.buildable_envelope is None


def test_envelope_without_parcel_rejected() -> None:
    program = _ready_program()
    envelope_inp = _sample_envelope_input()
    builder = SiteBuildableEnvelopeBuilder()

    with pytest.raises(
        SiteEnvelopeWithoutParcelError, match="without an enclosing parcel boundary"
    ):
        builder.build(program, parcel_boundary=None, buildable_envelope=envelope_inp)


def test_finite_coordinates_enforced() -> None:
    for bad_val in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError, match="must be finite"):
            SitePoint(x_m=bad_val, y_m=0.0)
        with pytest.raises(ValidationError, match="must be finite"):
            SitePoint(x_m=0.0, y_m=bad_val)


def test_negative_and_zero_local_coordinates_valid() -> None:
    # Centered at origin with negative coordinates
    vertices = [
        SitePoint(x_m=-25.0, y_m=-20.0),
        SitePoint(x_m=25.0, y_m=-20.0),
        SitePoint(x_m=25.0, y_m=20.0),
        SitePoint(x_m=-25.0, y_m=20.0),
    ]
    inp = SitePolygonInput(
        vertices=vertices,
        provenance=RelationshipProvenance.USER_STATED,
    )
    assert len(inp.vertices) == 4
    assert calculate_polygon_area(inp.vertices) == 2000.0


def test_fewer_than_3_distinct_vertices_rejected() -> None:
    with pytest.raises(ValidationError):
        SitePolygonInput(
            vertices=[SitePoint(x_m=0.0, y_m=0.0), SitePoint(x_m=10.0, y_m=0.0)],
            provenance=RelationshipProvenance.USER_STATED,
        )


def test_repeated_closing_vertex_rejected() -> None:
    # Caller repeats vertex 0 at index 3
    with pytest.raises(SitePolygonDegenerateError, match="must not repeat the first vertex"):
        validate_polygon_geometry(
            [
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=10.0),
                SitePoint(x_m=0.0, y_m=0.0),  # Repeated closing vertex
            ]
        )


def test_repeated_non_consecutive_vertex_rejected() -> None:
    # Vertex 0 repeated at index 2
    with pytest.raises(SitePolygonDegenerateError, match="All vertices must be unique"):
        validate_polygon_geometry(
            [
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=0.0),
                SitePoint(x_m=0.0, y_m=0.0),  # Duplicate
                SitePoint(x_m=0.0, y_m=10.0),
            ]
        )


def test_duplicate_consecutive_vertices_rejected() -> None:
    with pytest.raises(SitePolygonDegenerateError, match="All vertices must be unique"):
        validate_polygon_geometry(
            [
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=0.0),  # Duplicate consecutive
                SitePoint(x_m=0.0, y_m=10.0),
            ]
        )


def test_zero_area_collinear_polygon_rejected() -> None:
    # 3 collinear points
    with pytest.raises(SitePolygonDegenerateError, match="must be strictly positive"):
        validate_polygon_geometry(
            [
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
            ]
        )


def test_self_intersecting_polygon_rejected() -> None:
    # Asymmetric self-crossing polygon with non-zero area
    with pytest.raises(SitePolygonSelfIntersectionError, match="Non-adjacent edges .* intersect"):
        validate_polygon_geometry(
            [
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=30.0, y_m=20.0),
                SitePoint(x_m=0.0, y_m=20.0),
                SitePoint(x_m=20.0, y_m=0.0),
            ]
        )


def test_non_adjacent_edge_touching_rejected() -> None:
    # Edge touching non-adjacent vertex
    with pytest.raises(SitePolygonSelfIntersectionError, match="Non-adjacent edges .* intersect"):
        validate_polygon_geometry(
            [
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=20.0),
                SitePoint(x_m=10.0, y_m=0.0),  # Touches bottom edge (0,0)-(20,0)
                SitePoint(x_m=0.0, y_m=20.0),
            ]
        )


def test_adjacent_edges_sharing_endpoint_is_valid() -> None:
    # Normal convex triangle
    vertices = [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=10.0, y_m=0.0),
        SitePoint(x_m=5.0, y_m=10.0),
    ]
    validate_polygon_geometry(vertices)  # No exception raised


def test_clockwise_and_counter_clockwise_polygons_valid() -> None:
    ccw_verts = [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=10.0, y_m=0.0),
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=0.0, y_m=10.0),
    ]
    cw_verts = [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=0.0, y_m=10.0),
        SitePoint(x_m=10.0, y_m=10.0),
        SitePoint(x_m=10.0, y_m=0.0),
    ]
    validate_polygon_geometry(ccw_verts)
    validate_polygon_geometry(cw_verts)
    assert calculate_polygon_area(ccw_verts) == 100.0
    assert calculate_polygon_area(cw_verts) == 100.0


def test_coordinates_serialized_exactly_as_supplied() -> None:
    p = SitePoint(x_m=12.3456789123, y_m=-98.7654321987)
    assert p.x_m == 12.3456789123
    assert p.y_m == -98.7654321987


def test_buildable_envelope_outside_convex_parcel_rejected() -> None:
    program = _ready_program()
    parcel_inp = _sample_square_parcel_input()  # [0, 50] x [0, 40]

    # Envelope with point extending to x=55 (outside parcel)
    bad_envelope_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=55.0, y_m=10.0),  # x=55 exceeds parcel x=50
            SitePoint(x_m=55.0, y_m=30.0),
            SitePoint(x_m=10.0, y_m=30.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    with pytest.raises(SiteEnvelopeOutsideParcelError):
        SiteBuildableEnvelopeBuilder().build(
            program,
            parcel_boundary=parcel_inp,
            buildable_envelope=bad_envelope_inp,
        )


def test_buildable_envelope_outside_concave_parcel_rejected() -> None:
    program = _ready_program()

    # L-shaped concave parcel: 6 vertices
    # (0,0) -> (40,0) -> (40,20) -> (20,20) -> (20,40) -> (0,40)
    # The quadrant (20..40, 20..40) is OUTSIDE the parcel
    concave_parcel = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=40.0, y_m=0.0),
            SitePoint(x_m=40.0, y_m=20.0),
            SitePoint(x_m=20.0, y_m=20.0),
            SitePoint(x_m=20.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    # 1. Envelope with a vertex in the concave cut-out
    bad_env_1 = SitePolygonInput(
        vertices=[
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=35.0, y_m=10.0),
            SitePoint(x_m=35.0, y_m=35.0),  # (35, 35) is in concave cut-out
            SitePoint(x_m=10.0, y_m=35.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    with pytest.raises(SiteEnvelopeOutsideParcelError):
        SiteBuildableEnvelopeBuilder().build(
            program,
            parcel_boundary=concave_parcel,
            buildable_envelope=bad_env_1,
        )

    # 2. Envelope whose vertices are all on/in the parcel edges, but the edge bridges
    # through the concave exterior cut-out without properly crossing parcel edges:
    # Vertices (20, 20) [reflex vertex], (30, 20) [on horizontal edge], (20, 30) [on vertical edge]
    # Midpoint of (30, 20)-(20, 30) is (25, 25), which is strictly in the cut-out!
    corner_bridge_env = SitePolygonInput(
        vertices=[
            SitePoint(x_m=20.0, y_m=20.0),
            SitePoint(x_m=30.0, y_m=20.0),
            SitePoint(x_m=20.0, y_m=30.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    with pytest.raises(SiteEnvelopeOutsideParcelError, match="passes outside the parcel boundary"):
        SiteBuildableEnvelopeBuilder().build(
            program,
            parcel_boundary=concave_parcel,
            buildable_envelope=corner_bridge_env,
        )


def test_buildable_envelope_touching_parcel_boundary_is_valid() -> None:
    program = _ready_program()
    parcel_inp = _sample_square_parcel_input()  # [0, 50] x [0, 40]

    # Envelope coinciding on bottom edge y=0 and right edge x=50
    touching_env = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),  # Touches corner
            SitePoint(x_m=50.0, y_m=0.0),  # Coincides along bottom edge
            SitePoint(x_m=50.0, y_m=30.0),  # Coincides along right edge
            SitePoint(x_m=0.0, y_m=30.0),  # Coincides along left edge
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    site_env = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=parcel_inp,
        buildable_envelope=touching_env,
    )
    assert site_env.buildable_envelope is not None
    assert site_env.parcel_boundary is not None


def test_explicit_provenance_required_with_no_default() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        SitePolygonInput.model_validate(
            {
                "vertices": [
                    {"x_m": 0.0, "y_m": 0.0},
                    {"x_m": 10.0, "y_m": 0.0},
                    {"x_m": 10.0, "y_m": 10.0},
                ],
                "evidence_ids": ["ev_site_01"],
            }
        )

    with pytest.raises(ValidationError, match="Field required"):
        SitePolygon.model_validate(
            {
                "id": "sgeom_test_01",
                "role": SiteGeometryRole.PARCEL_BOUNDARY,
                "vertices": [
                    {"x_m": 0.0, "y_m": 0.0},
                    {"x_m": 10.0, "y_m": 0.0},
                    {"x_m": 10.0, "y_m": 10.0},
                ],
                "evidence_ids": ["ev_site_01"],
            }
        )


def test_user_confirmed_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="requires at least one evidence ID"):
        SitePolygonInput(
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=0.0),
                SitePoint(x_m=10.0, y_m=10.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[],  # Missing evidence
        )


def test_non_confirmed_geometry_does_not_enter_authoritative_ids() -> None:
    program = _ready_program()
    parcel_inp = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=0.0),
            SitePoint(x_m=50.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ],
        provenance=RelationshipProvenance.USER_STATED,  # Not confirmed
        evidence_ids=[],
    )

    site_env = SiteBuildableEnvelopeBuilder().build(program, parcel_boundary=parcel_inp)
    assert site_env.parcel_boundary is not None
    assert site_env.authoritative_geometry_ids == []


def test_deterministic_geometry_id_generation_and_coordinate_invariance() -> None:
    id1 = generate_site_geometry_id("proj_1", SiteGeometryRole.PARCEL_BOUNDARY)
    id2 = generate_site_geometry_id("proj_1", SiteGeometryRole.PARCEL_BOUNDARY)
    assert id1 == id2
    assert id1.startswith("sgeom_")

    program = _ready_program()
    p1 = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=0.0),
            SitePoint(x_m=10.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_STATED,
    )
    p2 = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=99.0, y_m=0.0),  # Modified vertices
            SitePoint(x_m=99.0, y_m=99.0),
        ],
        provenance=RelationshipProvenance.USER_STATED,
    )

    env1 = SiteBuildableEnvelopeBuilder().build(program, parcel_boundary=p1)
    env2 = SiteBuildableEnvelopeBuilder().build(program, parcel_boundary=p2)

    assert env1.parcel_boundary is not None
    assert env2.parcel_boundary is not None
    assert env1.parcel_boundary.id == env2.parcel_boundary.id


def test_repeated_builds_serialize_byte_for_byte_identically() -> None:
    program = _ready_program()
    parcel_inp = _sample_square_parcel_input()
    envelope_inp = _sample_envelope_input()

    builder = SiteBuildableEnvelopeBuilder()
    env1 = builder.build(program, parcel_inp, envelope_inp)
    env2 = builder.build(program, parcel_inp, envelope_inp)

    assert env1 == env2
    assert env1.model_dump_json() == env2.model_dump_json()


def test_strict_spatial_program_source_binding() -> None:
    builder = SiteBuildableEnvelopeBuilder()
    with pytest.raises(SiteMissingInputError):
        builder.build(None)  # type: ignore[arg-type]

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
    with pytest.raises(SiteSchemaVersionMismatchError):
        builder.build(corrupted_program)


def test_strict_utc_timestamps() -> None:
    program = _ready_program()
    builder = SiteBuildableEnvelopeBuilder()

    naive_dt = datetime(2026, 8, 19, 12, 0, 0)
    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        builder.build(program, created_at=naive_dt)

    non_utc_dt = datetime(2026, 8, 19, 15, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(ValidationError, match="created_at must use UTC offset"):
        builder.build(program, created_at=non_utc_dt)


def test_zero_solver_and_regulatory_fields_invariant() -> None:
    forbidden_terms = [
        "setback",
        "taks",
        "kaks",
        "far",
        "zoning",
        "municipality",
        "solver_weight",
        "penalty",
        "score",
        "height_limit",
        "floor_count",
    ]

    for model_cls in (
        SitePoint,
        SitePolygonInput,
        SitePolygon,
        SiteBuildableEnvelope,
    ):
        for field_name in model_cls.model_fields:
            for forbidden in forbidden_terms:
                assert forbidden != field_name.lower(), (
                    f"Forbidden regulatory/solver field {field_name!r} "
                    f"found in {model_cls.__name__}"
                )


def test_concave_parcel_edge_with_global_midpoint_inside_but_interval_outside_rejected() -> None:
    program = _ready_program()

    # Double-notch (comb) concave parcel:
    # Top prongs at x in [0, 15], [35, 65], [85, 100], height y=40
    # Notches at x in [15, 35] and [65, 85], height y=10
    # Bottom baseline at y=0 from x=0 to 100
    comb_parcel = SitePolygonInput(
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=100.0, y_m=0.0),
            SitePoint(x_m=100.0, y_m=40.0),
            SitePoint(x_m=85.0, y_m=40.0),
            SitePoint(x_m=85.0, y_m=10.0),
            SitePoint(x_m=65.0, y_m=10.0),
            SitePoint(x_m=65.0, y_m=40.0),
            SitePoint(x_m=35.0, y_m=40.0),
            SitePoint(x_m=35.0, y_m=10.0),
            SitePoint(x_m=15.0, y_m=10.0),
            SitePoint(x_m=15.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    # Envelope with top edge from (5, 30) to (95, 30) at y=30:
    # Start (5, 30) is inside left prong [0..15]
    # End (95, 30) is inside right prong [85..100]
    # GLOBAL midpoint is (50, 30), which is INSIDE the middle prong [35..65]!
    # But intervals (15..35) and (65..85) pass through the exterior notches!
    comb_bridge_env = SitePolygonInput(
        vertices=[
            SitePoint(x_m=5.0, y_m=5.0),
            SitePoint(x_m=95.0, y_m=5.0),
            SitePoint(x_m=95.0, y_m=30.0),
            SitePoint(x_m=5.0, y_m=30.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_site_01"],
    )

    with pytest.raises(SiteEnvelopeOutsideParcelError, match="passes outside the parcel boundary"):
        SiteBuildableEnvelopeBuilder().build(
            program,
            parcel_boundary=comb_parcel,
            buildable_envelope=comb_bridge_env,
        )


def test_site_buildable_envelope_rejects_swapped_or_invalid_geometry_roles() -> None:
    valid_verts = [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=10.0, y_m=0.0),
        SitePoint(x_m=10.0, y_m=10.0),
    ]

    wrong_parcel_poly = SitePolygon(
        id="sgeom_p1",
        role=SiteGeometryRole.BUILDABLE_ENVELOPE,  # Invalid role for parcel_boundary
        vertices=valid_verts,
        provenance=RelationshipProvenance.USER_STATED,
    )
    wrong_envelope_poly = SitePolygon(
        id="sgeom_e1",
        role=SiteGeometryRole.PARCEL_BOUNDARY,  # Invalid role for buildable_envelope
        vertices=valid_verts,
        provenance=RelationshipProvenance.USER_STATED,
    )

    # 1. parcel_boundary with BUILDABLE_ENVELOPE role must fail
    with pytest.raises(ValidationError, match="parcel_boundary must have role PARCEL_BOUNDARY"):
        SiteBuildableEnvelope(
            project_id="proj_1",
            source_brief_version=1,
            created_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
            parcel_boundary=wrong_parcel_poly,
        )

    # 2. buildable_envelope with PARCEL_BOUNDARY role must fail
    correct_parcel_poly = SitePolygon(
        id="sgeom_p2",
        role=SiteGeometryRole.PARCEL_BOUNDARY,
        vertices=[
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=0.0),
            SitePoint(x_m=20.0, y_m=20.0),
        ],
        provenance=RelationshipProvenance.USER_STATED,
    )
    with pytest.raises(
        ValidationError, match="buildable_envelope must have role BUILDABLE_ENVELOPE"
    ):
        SiteBuildableEnvelope(
            project_id="proj_1",
            source_brief_version=1,
            created_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
            parcel_boundary=correct_parcel_poly,
            buildable_envelope=wrong_envelope_poly,
        )
