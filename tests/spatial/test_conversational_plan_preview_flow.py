"""End-to-end backend tests for Authoritative Plan Input -> Conversational Plan Preview V0.

Tests:
1. Real authoritative ready project -> solver -> SVG preview success
2. Approved floor plate coordinates strictly bound room placements in solver
3. Missing floor plate -> 409 Conflict and solver call count == 0
4. Missing metric requirements -> 409 Conflict and solver call count == 0
5. Missing spatial graph -> 409 Conflict and solver call count == 0
6. Stale spatial graph / plan input state -> 409 Conflict and solver call count == 0
7. Preview execution never mutates state_version, BriefSnapshot, or SpatialRelationshipGraph
8. Preview execution never reads any demo JSON fixture
9. Non-rectangular floor plate is rejected by V0 solver capability gate
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from apps.api.main import create_app
from fastapi.testclient import TestClient

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
from brif_ai.brief.persistence import JSONBriefRepository
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.floor_plate.models import FloorPlateInput
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
from brif_ai.spatial.persistence import JSONSpatialRelationshipRepository
from brif_ai.spatial.plan_input import (
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
)
from brif_ai.spatial.plan_preview import (
    PlanPreviewReadinessBlockerCode,
    PlanPreviewService,
    ProjectPlanPreviewBlockerCode,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SitePoint,
    SitePolygonInput,
)


def _setup_test_project(
    repo_dir: Path,
    project_id: str = "proj_preview_conv_01",
    brief_version: int = 1,
    *,
    fp_vertices: list[SitePoint] | None = None,
    site_vertices: list[SitePoint] | None = None,
    include_floor_plate: bool = True,
    include_metrics: bool = True,
    include_spatial_graph: bool = True,
    include_site: bool = True,
    graph_brief_version: int | None = None,
    state_brief_version: int | None = None,
    living_display_name: str = "Living Room",
    kitchen_display_name: str = "Kitchen",
) -> tuple[
    JSONBriefRepository,
    JSONSpatialRelationshipRepository,
    JSONPlanInputStateRepository,
    BriefSnapshot,
    AuthoritativePlanInputState,
]:
    brief_repo = JSONBriefRepository(repo_dir / "briefs")
    spatial_repo = JSONSpatialRelationshipRepository(repo_dir / "spatial")
    plan_input_repo = JSONPlanInputStateRepository(repo_dir / "plan_input")

    # 1. Brief
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Salon ve mutfak bitisik",
    )
    spaces = [
        SpaceRequest(
            id="sr_living",
            display_name=living_display_name,
            space_function=SpaceFunction.LIVING,
            minimum_quantity=1,
            mandatory=True,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            stakeholder_ids=["stk_01"],
            evidence_ids=[ev.id],
        ),
        SpaceRequest(
            id="sr_kitchen",
            display_name=kitchen_display_name,
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
    ready_open_questions = [
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
    brief_snapshot = BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
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
        open_questions=ready_open_questions,
    )
    brief_repo.save(brief_snapshot)

    # 2. Spatial Graph
    effective_graph_version = (
        graph_brief_version if graph_brief_version is not None else brief_version
    )
    relationships = [
        SpatialRelationshipInput(
            source_space_id="sn_living_01",
            target_space_id="sn_kitchen_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev.id],
            rationale="Adjacency",
        )
    ]
    dummy_snapshot_for_graph = brief_snapshot.model_copy(
        update={"brief_version": effective_graph_version}
    )
    graph = SpatialRelationshipGraphBuilder().build(
        dummy_snapshot_for_graph,
        relationships,
        created_at=datetime(2026, 8, 20, 12, 5, 0, tzinfo=UTC),
    )
    if include_spatial_graph:
        spatial_repo.save(graph)

    # 3. Spatial Program for state builders
    effective_state_version = (
        state_brief_version if state_brief_version is not None else brief_version
    )
    dummy_snapshot_for_state = brief_snapshot.model_copy(
        update={"brief_version": effective_state_version}
    )
    dummy_graph_for_state = graph.model_copy(
        update={"source_brief_version": effective_state_version}
    )
    program = SpatialProgramBuilder().build(dummy_snapshot_for_state, dummy_graph_for_state)

    # 4. Plan Input State
    # Site
    site_env = None
    if include_site:
        s_verts = site_vertices or [
            SitePoint(x_m=0.0, y_m=0.0),
            SitePoint(x_m=30.0, y_m=0.0),
            SitePoint(x_m=30.0, y_m=40.0),
            SitePoint(x_m=0.0, y_m=40.0),
        ]
        min_x = min(v.x_m for v in s_verts)
        max_x = max(v.x_m for v in s_verts)
        min_y = min(v.y_m for v in s_verts)
        max_y = max(v.y_m for v in s_verts)
        parcel_verts = [
            SitePoint(x_m=min_x - 5.0, y_m=min_y - 5.0),
            SitePoint(x_m=max_x + 5.0, y_m=min_y - 5.0),
            SitePoint(x_m=max_x + 5.0, y_m=max_y + 5.0),
            SitePoint(x_m=min_x - 5.0, y_m=max_y + 5.0),
        ]
        site_env = SiteBuildableEnvelopeBuilder().build(
            program,
            parcel_boundary=SitePolygonInput(
                vertices=parcel_verts,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                evidence_ids=[ev.id],
            ),
            buildable_envelope=SitePolygonInput(
                vertices=s_verts,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                evidence_ids=[ev.id],
            ),
            created_at=datetime(2026, 8, 20, 12, 10, 0, tzinfo=UTC),
        )

    # Metrics
    metric_reqs = None
    if include_metrics:
        metric_reqs = MetricSpatialRequirementsBuilder().build(
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
            created_at=datetime(2026, 8, 20, 12, 15, 0, tzinfo=UTC),
        )

    # Floor Plate
    fp_input = None
    if include_floor_plate:
        f_verts = fp_vertices or [
            SitePoint(x_m=4.0, y_m=4.0),
            SitePoint(x_m=16.0, y_m=4.0),
            SitePoint(x_m=16.0, y_m=22.0),
            SitePoint(x_m=4.0, y_m=22.0),
        ]
        fp_input = FloorPlateInput(
            vertices=f_verts,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
            rationale="Rectangular FloorPlate 12x18",
        )

    solver_config = RoomGeometrySolverConfig(
        grid_step_m=0.25,
        max_time_seconds=5.0,
    )

    plan_input_state = AuthoritativePlanInputState(
        project_id=project_id,
        state_version=1,
        source_brief_version=effective_state_version,
        created_at=datetime(2026, 8, 20, 12, 20, 0, tzinfo=UTC),
        metric_requirements=metric_reqs,
        site_envelope=site_env,
        floor_plate_input=fp_input,
        solver_config=solver_config,
    )
    plan_input_repo.save(plan_input_state)

    return (
        brief_repo,
        spatial_repo,
        plan_input_repo,
        brief_snapshot,
        plan_input_state,
    )


def test_01_real_authoritative_ready_project_execution_success(tmp_path: Path) -> None:
    """End-to-end test: ready authoritative project executes solver and returns 200 with SVG."""
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(tmp_path)
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    response = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["solution"] is not None
    assert data["solution"]["status"] == "FEASIBLE"
    assert len(data["solution"]["rooms"]) == 2
    assert data["document"] is not None
    assert "<svg" in data["document"]["svg"]


def test_02_floor_plate_coordinates_solver_boundary_assertion(tmp_path: Path) -> None:
    """Verified floor plate coordinates strictly bound all room placements in the solver."""
    # Place floor plate at offset [10, 22] x [20, 38]
    fp_verts = [
        SitePoint(x_m=10.0, y_m=20.0),
        SitePoint(x_m=22.0, y_m=20.0),
        SitePoint(x_m=22.0, y_m=38.0),
        SitePoint(x_m=10.0, y_m=38.0),
    ]
    site_verts = [
        SitePoint(x_m=0.0, y_m=0.0),
        SitePoint(x_m=40.0, y_m=0.0),
        SitePoint(x_m=40.0, y_m=50.0),
        SitePoint(x_m=0.0, y_m=50.0),
    ]
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(
        tmp_path, fp_vertices=fp_verts, site_vertices=site_verts
    )
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    response = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
    assert response.status_code == 200
    rooms = response.json()["solution"]["rooms"]
    for r in rooms:
        # Assert each room is inside [10, 22] x [20, 38]
        assert r["x_m"] >= 10.0 - 1e-6
        assert r["y_m"] >= 20.0 - 1e-6
        assert (r["x_m"] + r["width_m"]) <= 22.0 + 1e-6
        assert (r["y_m"] + r["depth_m"]) <= 38.0 + 1e-6


def test_03_missing_floor_plate_returns_409_and_solver_call_count_zero(tmp_path: Path) -> None:
    """Missing floor plate returns 409 Conflict and solver call count == 0."""
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(
        tmp_path, include_floor_plate=False
    )
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    with patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as spy_gen:
        response = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
        assert response.status_code == 409
        data = response.json()
        assert data["schema_version"] == "project_plan_preview_readiness.v0"
        assert data["ready_for_preview"] is False
        blocker_codes = [b["code"] for b in data["preparation"]["blockers"]]
        assert PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING.value in blocker_codes
        assert spy_gen.call_count == 0


def test_04_missing_metrics_returns_409_and_solver_call_count_zero(tmp_path: Path) -> None:
    """Missing metrics returns 409 Conflict and solver call count == 0."""
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(tmp_path, include_metrics=False)
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    with patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as spy_gen:
        response = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
        assert response.status_code == 409
        data = response.json()
        assert data["ready_for_preview"] is False
        blocker_codes = [b["code"] for b in data["preparation"]["blockers"]]
        assert PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING.value in blocker_codes
        assert spy_gen.call_count == 0


def test_05_missing_spatial_graph_returns_409_and_solver_call_count_zero(tmp_path: Path) -> None:
    """Missing spatial graph returns 409 Conflict and solver call count == 0."""
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(
        tmp_path, include_spatial_graph=False
    )
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    with patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as spy_gen:
        response = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
        assert response.status_code == 409
        data = response.json()
        assert data["ready_for_preview"] is False
        blocker_codes = [b["code"] for b in data["project_blockers"]]
        assert ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_MISSING.value in blocker_codes
        assert spy_gen.call_count == 0


def test_06_stale_graph_brief_version_returns_409_and_solver_call_count_zero(
    tmp_path: Path,
) -> None:
    """Stale spatial graph (version mismatch) returns 409 Conflict and solver call count == 0."""
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(
        tmp_path, brief_version=2, graph_brief_version=1, state_brief_version=2
    )
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    with patch.object(PlanPreviewService, "generate", wraps=PlanPreviewService.generate) as spy_gen:
        response = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
        assert response.status_code == 409
        data = response.json()
        assert data["ready_for_preview"] is False
        blocker_codes = [b["code"] for b in data["project_blockers"]]
        assert ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_STALE.value in blocker_codes
        assert spy_gen.call_count == 0


def test_07_preview_never_mutates_state_version_brief_or_spatial(tmp_path: Path) -> None:
    """Preview execution never mutates state_version, BriefSnapshot, or SpatialGraph."""
    brief_repo, spatial_repo, plan_repo, init_brief, init_state = _setup_test_project(tmp_path)
    init_graph = spatial_repo.get_latest("proj_preview_conv_01")

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    res = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
    assert res.status_code == 200

    after_brief = brief_repo.get_latest("proj_preview_conv_01")
    after_graph = spatial_repo.get_latest("proj_preview_conv_01")
    after_state = plan_repo.get_latest("proj_preview_conv_01")

    assert after_brief == init_brief
    assert after_graph == init_graph
    assert after_state == init_state
    assert after_state is not None and after_state.state_version == init_state.state_version


def test_08_no_demo_fixture_read_during_project_preview(tmp_path: Path) -> None:
    """Verified that no demo JSON fixture is accessed or read during project preview execution."""
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(tmp_path)
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    orig_read_text = Path.read_text

    def guarded_read_text(
        self: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if "plan_preview_request.demo.json" in str(self) or "demo.json" in str(self):
            raise AssertionError(f"Demo fixture read detected during project preview: {self}")
        return orig_read_text(self, encoding=encoding, errors=errors)

    with patch.object(Path, "read_text", guarded_read_text):
        res = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
        assert res.status_code == 200


def test_09_non_rectangular_floor_plate_rejected_by_solver(tmp_path: Path) -> None:
    """Non-rectangular (e.g. 5 vertices) floor plate is rejected with 422 by V0 capability gate."""
    # 5-vertex polygon inside buildable envelope
    fp_verts_5 = [
        SitePoint(x_m=4.0, y_m=4.0),
        SitePoint(x_m=16.0, y_m=4.0),
        SitePoint(x_m=16.0, y_m=16.0),
        SitePoint(x_m=10.0, y_m=22.0),
        SitePoint(x_m=4.0, y_m=22.0),
    ]
    brief_repo, spatial_repo, plan_repo, _, _ = _setup_test_project(
        tmp_path, fp_vertices=fp_verts_5
    )
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_repo,
    )
    client = TestClient(app)

    res = client.post("/api/v1/projects/proj_preview_conv_01/plan/preview")
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert "RoomGeometrySolver V0 requires exactly 4 vertices" in data["error"]
