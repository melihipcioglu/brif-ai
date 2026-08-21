"""API tests for server-authoritative Project Plan Preview Execution API V0.

Endpoint: POST /api/v1/projects/{project_id}/plan/preview
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from brif_ai.brief.persistence import (
    BriefPersistenceError,
    JSONBriefRepository,
)
from brif_ai.brief.service import PersistentBriefService
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.builder import SpatialRelationshipGraphBuilder
from brif_ai.spatial.floor_plate.models import FloorPlateInput
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.models import (
    MetricRequirementInput,
    MetricRequirementType,
    MetricSpatialRequirements,
    MetricUnit,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.persistence import (
    JSONSpatialRelationshipRepository,
    SpatialGraphPersistenceError,
)
from brif_ai.spatial.plan_input import (
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
    PlanInputStatePersistenceError,
    PlanInputStateService,
)
from brif_ai.spatial.plan_preview import (
    PlanPreviewReadinessBlockerCode,
    PlanPreviewRequest,
    PlanPreviewResponse,
    PlanPreviewService,
    ProjectPlanPreviewBlockerCode,
    ProjectPlanPreviewReadinessService,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver import (
    RoomGeometryEngineError,
    RoomGeometryInfeasibleError,
    RoomGeometryInputMismatchError,
)
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.service import PersistentSpatialService
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.solver_policy.errors import SolverPolicyError
from brif_ai.spatial.svg_plan import SvgPlanRenderError

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _build_test_data(
    project_id: str = "proj_test_01",
    brief_version: int = 1,
    *,
    is_brief_ready: bool = True,
) -> tuple[
    BriefSnapshot,
    SpatialRelationshipGraph,
    MetricSpatialRequirements,
    SiteBuildableEnvelope,
    FloorPlateInput,
    RoomGeometrySolverConfig,
]:
    """Construct a full valid test fixture chain."""
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="chat:turn-1",
        excerpt="Living and kitchen adjacent",
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

    ready_snapshot = BriefSnapshot(
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
    graph = SpatialRelationshipGraphBuilder().build(
        ready_snapshot,
        relationships,
        created_at=datetime(2026, 8, 20, 12, 5, 0, tzinfo=UTC),
    )
    program = SpatialProgramBuilder().build(ready_snapshot, graph)

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
        created_at=datetime(2026, 8, 20, 12, 10, 0, tzinfo=UTC),
    )

    site_envelope = SiteBuildableEnvelopeBuilder().build(
        program,
        parcel_boundary=SitePolygonInput(
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=20.0),
                SitePoint(x_m=0.0, y_m=20.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
        ),
        buildable_envelope=SitePolygonInput(
            vertices=[
                SitePoint(x_m=2.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=18.0),
                SitePoint(x_m=2.0, y_m=18.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev.id],
        ),
        created_at=datetime(2026, 8, 20, 12, 15, 0, tzinfo=UTC),
    )

    floor_plate_input = FloorPlateInput(
        vertices=[
            SitePoint(x_m=4.0, y_m=4.0),
            SitePoint(x_m=10.0, y_m=4.0),
            SitePoint(x_m=10.0, y_m=10.0),
            SitePoint(x_m=4.0, y_m=10.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev.id],
        rationale="Rectangular FloorPlate",
    )

    solver_config = RoomGeometrySolverConfig(
        grid_step_m=0.25,
        max_time_seconds=10.0,
    )

    if not is_brief_ready:
        unready_open_questions = [
            OpenQuestion(
                id=f"oq_{t.value}",
                question=f"Question on {t.value}",
                reason="Unready fixture",
                related_brief_item_ids=[],
                status=OpenQuestionStatus.OPEN,
                resolution_note=None,
                topic_key=t.value,
            )
            for t in all_topics
        ]
        snapshot = ready_snapshot.model_copy(update={"open_questions": unready_open_questions})
    else:
        snapshot = ready_snapshot

    return (
        snapshot,
        graph,
        metric_reqs,
        site_envelope,
        floor_plate_input,
        solver_config,
    )


def _setup_app_and_repos(
    tmp_path: Path,
) -> tuple[
    TestClient,
    JSONBriefRepository,
    JSONSpatialRelationshipRepository,
    JSONPlanInputStateRepository,
]:
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    client = TestClient(app)
    return client, brief_repo, spatial_repo, plan_input_repo


def _persist_ready_project(
    brief_repo: JSONBriefRepository,
    spatial_repo: JSONSpatialRelationshipRepository,
    plan_input_repo: JSONPlanInputStateRepository,
    project_id: str = "proj_test_01",
    brief_version: int = 1,
) -> tuple[
    BriefSnapshot,
    SpatialRelationshipGraph,
    AuthoritativePlanInputState,
]:
    snapshot, graph, metrics, site, fp, cfg = _build_test_data(
        project_id,
        brief_version=brief_version,
    )
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id=project_id,
        state_version=1,
        source_brief_version=brief_version,
        created_at=datetime.now(UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)
    return snapshot, graph, plan_input_state


# ---------------------------------------------------------------------------
# Section 16: Readiness Blockers (HTTP 409 + ProjectPlanPreviewReadinessResult)
# ---------------------------------------------------------------------------


def test_01_invalid_project_id_returns_422(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app_and_repos(tmp_path)
    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/invalid!id/plan/preview")
        assert resp.status_code == 422
        assert "Invalid project ID" in resp.json()["detail"]
        mock_gen.assert_not_called()


def test_02_brief_snapshot_missing_returns_409_readiness_blocker(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app_and_repos(tmp_path)
    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["schema_version"] == "project_plan_preview_readiness.v0"
        assert data["ready_for_preview"] is False
        assert data["source_brief_version"] is None
        assert len(data["project_blockers"]) == 1
        assert data["project_blockers"][0]["code"] == ProjectPlanPreviewBlockerCode.BRIEF_MISSING
        mock_gen.assert_not_called()


def test_03_spatial_graph_missing_returns_409_readiness_blocker(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app_and_repos(tmp_path)
    snapshot, _, _, _, _, _ = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert len(data["project_blockers"]) == 1
        assert (
            data["project_blockers"][0]["code"]
            == ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_MISSING
        )
        mock_gen.assert_not_called()


def test_04_plan_input_state_missing_returns_409_readiness_blocker(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, _ = _setup_app_and_repos(tmp_path)
    snapshot, graph, _, _, _, _ = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert len(data["project_blockers"]) == 1
        assert (
            data["project_blockers"][0]["code"]
            == ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_MISSING
        )
        mock_gen.assert_not_called()


def test_05_spatial_graph_stale_returns_409_readiness_blocker(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot, _, metrics, site, fp, cfg = _build_test_data("proj_test_01", 2)
    # Stale graph from brief v1
    _, graph_v1, _, _, _, _ = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph_v1)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=2,
            created_at=datetime.now(UTC),
            metric_requirements=metrics,
            site_envelope=site,
            floor_plate_input=fp,
            solver_config=cfg,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert len(data["project_blockers"]) == 1
        assert (
            data["project_blockers"][0]["code"] == ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_STALE
        )
        mock_gen.assert_not_called()


def test_06_plan_input_state_stale_returns_409_readiness_blocker(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot_v2, graph_v2, _, _, _, _ = _build_test_data("proj_test_01", 2)
    _, _, metrics_v1, site_v1, fp_v1, cfg_v1 = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot_v2)
    spatial_repo.save(graph_v2)
    # Stale plan input with source_brief_version=1
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=metrics_v1,
            site_envelope=site_v1,
            floor_plate_input=fp_v1,
            solver_config=cfg_v1,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert len(data["project_blockers"]) == 1
        assert (
            data["project_blockers"][0]["code"]
            == ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_STALE
        )
        mock_gen.assert_not_called()


def test_07_brief_not_ready_returns_409_readiness_blocker(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot_unready, graph, metrics, site, fp, cfg = _build_test_data(
        "proj_test_01", 1, is_brief_ready=False
    )
    brief_repo.save(snapshot_unready)
    spatial_repo.save(graph)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=metrics,
            site_envelope=site,
            floor_plate_input=fp,
            solver_config=cfg,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert len(data["project_blockers"]) == 1
        assert data["project_blockers"][0]["code"] == ProjectPlanPreviewBlockerCode.BRIEF_NOT_READY
        mock_gen.assert_not_called()


def test_08_directive_derivation_failure_returns_409_readiness_blocker(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    with (
        patch.object(
            SolverPolicyCompiler,
            "compile",
            side_effect=SolverPolicyError("Directive compiler failure"),
        ),
        patch.object(PlanPreviewService, "generate") as mock_gen,
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert len(data["project_blockers"]) == 1
        assert (
            data["project_blockers"][0]["code"]
            == ProjectPlanPreviewBlockerCode.DIRECTIVE_DERIVATION_FAILED
        )
        mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# Section 17: Preparation Blockers (HTTP 409 + ProjectPlanPreviewReadinessResult)
# ---------------------------------------------------------------------------


def test_09_metric_requirements_missing_returns_409_preparation_blocker(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot, graph, _, site, fp, cfg = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=None,
            site_envelope=site,
            floor_plate_input=fp,
            solver_config=cfg,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert data["project_blockers"] == []
        assert data["preparation"] is not None
        assert data["preparation"]["ready_for_preview"] is False
        prep_blockers = [b["code"] for b in data["preparation"]["blockers"]]
        assert PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING in prep_blockers
        mock_gen.assert_not_called()


def test_10_site_envelope_missing_returns_409_preparation_blocker(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot, graph, metrics, _, fp, cfg = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=metrics,
            site_envelope=None,
            floor_plate_input=fp,
            solver_config=cfg,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert data["preparation"] is not None
        prep_blockers = [b["code"] for b in data["preparation"]["blockers"]]
        assert PlanPreviewReadinessBlockerCode.SITE_ENVELOPE_MISSING in prep_blockers
        mock_gen.assert_not_called()


def test_11_floor_plate_input_missing_returns_409_preparation_blocker(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot, graph, metrics, site, _, cfg = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=metrics,
            site_envelope=site,
            floor_plate_input=None,
            solver_config=cfg,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert data["preparation"] is not None
        prep_blockers = [b["code"] for b in data["preparation"]["blockers"]]
        assert PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING in prep_blockers
        mock_gen.assert_not_called()


def test_12_solver_config_missing_returns_409_preparation_blocker(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    snapshot, graph, metrics, site, fp, _ = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=metrics,
            site_envelope=site,
            floor_plate_input=fp,
            solver_config=None,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["ready_for_preview"] is False
        assert data["preparation"] is not None
        prep_blockers = [b["code"] for b in data["preparation"]["blockers"]]
        assert PlanPreviewReadinessBlockerCode.SOLVER_CONFIG_MISSING in prep_blockers
        mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# Section 18: Real Authoritative Ready Project Preview Execution
# ---------------------------------------------------------------------------


def test_13_real_authoritative_ready_project_execution_success(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["error"] is None
    assert data["solution"] is not None
    assert data["document"] is not None

    # Check solution properties
    sol = data["solution"]
    assert sol["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(sol["rooms"]) == 2
    room_ids = {r["space_id"] for r in sol["rooms"]}
    assert room_ids == {"sn_living_01", "sn_kitchen_01"}

    # Check SVG document
    doc = data["document"]
    assert doc["schema_version"] == "svg_plan_document.v0"
    assert doc["svg"].startswith("<svg")
    root = ET.fromstring(doc["svg"])
    assert root.tag.endswith("svg")


# ---------------------------------------------------------------------------
# Section 19: Exact Prepared Request Used Without Mutation
# ---------------------------------------------------------------------------


def test_14_exact_prepared_request_is_passed_to_generate(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    # Evaluate readiness independently to get the exact prepared request
    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    expected_readiness = service.evaluate("proj_test_01")
    assert expected_readiness.ready_for_preview is True
    assert expected_readiness.preparation is not None
    assert expected_readiness.preparation.request is not None
    expected_request = expected_readiness.preparation.request

    captured_requests: list[PlanPreviewRequest] = []
    real_generate = PlanPreviewService.generate

    def _spy_generate(req: PlanPreviewRequest) -> PlanPreviewResponse:
        captured_requests.append(req)
        return real_generate(req)

    with patch.object(PlanPreviewService, "generate", side_effect=_spy_generate):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 200

    assert len(captured_requests) == 1
    actual_request = captured_requests[0]

    # Verify field by field identity
    assert actual_request.solver_input.project_id == expected_request.solver_input.project_id
    assert actual_request.floor_plate.project_id == expected_request.floor_plate.project_id
    assert (
        actual_request.floor_plate.source_brief_version
        == expected_request.floor_plate.source_brief_version
    )
    assert actual_request.solver_config == expected_request.solver_config
    assert actual_request.render_config == expected_request.render_config
    assert actual_request.model_dump(mode="json") == expected_request.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Section 20: No Execution When Blocked
# ---------------------------------------------------------------------------


def test_15_no_execution_when_blocked_spy(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)

    # 1. Project-level blocked: missing brief
    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        assert mock_gen.call_count == 0

    # 2. Preparation-level blocked: missing floor plate input
    snapshot, graph, metrics, site, _, cfg = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)
    plan_input_repo.save(
        AuthoritativePlanInputState(
            project_id="proj_test_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime.now(UTC),
            metric_requirements=metrics,
            site_envelope=site,
            floor_plate_input=None,
            solver_config=cfg,
        )
    )

    with patch.object(PlanPreviewService, "generate") as mock_gen:
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        assert mock_gen.call_count == 0


# ---------------------------------------------------------------------------
# Section 21: No State Mutation
# ---------------------------------------------------------------------------


def test_16_execution_does_not_mutate_authoritative_state(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(
        brief_repo,
        spatial_repo,
        plan_input_repo,
        "proj_test_01",
    )

    # Capture before
    brief_before = brief_repo.get_latest("proj_test_01")
    graph_before = spatial_repo.get_latest("proj_test_01")
    plan_input_before = plan_input_repo.get_latest("proj_test_01")
    versions_before = plan_input_repo.list_versions("proj_test_01")

    # Execute preview multiple times
    for _ in range(3):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 200

    # Capture after
    brief_after = brief_repo.get_latest("proj_test_01")
    graph_after = spatial_repo.get_latest("proj_test_01")
    plan_input_after = plan_input_repo.get_latest("proj_test_01")
    versions_after = plan_input_repo.list_versions("proj_test_01")

    assert brief_before == brief_after
    assert graph_before == graph_after
    assert plan_input_before == plan_input_after
    assert versions_before == versions_after == [1]


# ---------------------------------------------------------------------------
# Section 22: Execution Error Regression Tests
# ---------------------------------------------------------------------------


def test_17_execution_room_geometry_input_mismatch_returns_409(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    with patch.object(
        PlanPreviewService,
        "generate",
        side_effect=RoomGeometryInputMismatchError("Synthetic input mismatch error"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 409
        data = resp.json()
        assert data["success"] is False
        assert data["solution"] is None
        assert data["document"] is None
        assert "Synthetic input mismatch error" in data["error"]


def test_18_execution_room_geometry_infeasible_returns_422(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    with patch.object(
        PlanPreviewService,
        "generate",
        side_effect=RoomGeometryInfeasibleError("Synthetic layout infeasible error"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False
        assert data["solution"] is None
        assert data["document"] is None
        assert "Synthetic layout infeasible error" in data["error"]


def test_19_execution_room_geometry_engine_error_returns_503(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    with patch.object(
        PlanPreviewService,
        "generate",
        side_effect=RoomGeometryEngineError("Synthetic solver crash"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 503
        data = resp.json()
        assert data["success"] is False
        assert data["solution"] is None
        assert data["document"] is None
        assert "Synthetic solver crash" in data["error"]


def test_20_execution_svg_plan_render_error_returns_500(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    with patch.object(
        PlanPreviewService,
        "generate",
        side_effect=SvgPlanRenderError("Synthetic SVG rendering error"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        data = resp.json()
        assert data["success"] is False
        assert data["solution"] is None
        assert data["document"] is None
        assert "Synthetic SVG rendering error" in data["error"]


def test_21_execution_unexpected_runtime_error_returns_500(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    with patch.object(
        PlanPreviewService,
        "generate",
        side_effect=RuntimeError("boom"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        data = resp.json()
        assert data["success"] is False
        assert data["solution"] is None
        assert data["document"] is None
        assert "boom" in data["error"]
        assert "detail" not in data


def test_21b_readiness_unexpected_runtime_error_returns_500(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app_and_repos(tmp_path)

    with (
        patch.object(
            ProjectPlanPreviewReadinessService,
            "evaluate",
            side_effect=RuntimeError("readiness boom"),
        ),
        patch.object(PlanPreviewService, "generate") as mock_gen,
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        data = resp.json()
        assert "detail" in data
        assert "Sunucu hatası" in data["detail"]
        assert "readiness boom" in data["detail"]
        mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# Section 23: Persistence Error Tests
# ---------------------------------------------------------------------------


def test_22_brief_persistence_error_during_readiness_returns_500(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app_and_repos(tmp_path)
    with (
        patch.object(
            PersistentBriefService,
            "get_latest_brief",
            side_effect=BriefPersistenceError("Disk corruption"),
        ),
        patch.object(PlanPreviewService, "generate") as mock_gen,
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        assert "Kalıcı depolama hatası" in resp.json()["detail"]
        mock_gen.assert_not_called()


def test_23_spatial_graph_persistence_error_during_readiness_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app_and_repos(tmp_path)
    snapshot, _, _, _, _, _ = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)

    with (
        patch.object(
            PersistentSpatialService,
            "get_latest_graph",
            side_effect=SpatialGraphPersistenceError("Graph corruption"),
        ),
        patch.object(PlanPreviewService, "generate") as mock_gen,
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        assert "Kalıcı depolama hatası" in resp.json()["detail"]
        mock_gen.assert_not_called()


def test_24_plan_input_persistence_error_during_readiness_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, _ = _setup_app_and_repos(tmp_path)
    snapshot, graph, _, _, _, _ = _build_test_data("proj_test_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    with (
        patch.object(
            PlanInputStateService,
            "get_latest_state",
            side_effect=PlanInputStatePersistenceError("Plan input corruption"),
        ),
        patch.object(PlanPreviewService, "generate") as mock_gen,
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        assert "Kalıcı depolama hatası" in resp.json()["detail"]
        mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# Section 24: Impossible Invariant Defensive Check
# ---------------------------------------------------------------------------


def test_25_defensive_internal_invariant_failure_returns_500(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app_and_repos(tmp_path)

    # Fabricate a mock readiness result that claims ready=True but has preparation=None
    mock_readiness = MagicMock()
    mock_readiness.ready_for_preview = True
    mock_readiness.preparation = None

    with (
        patch.object(
            ProjectPlanPreviewReadinessService,
            "evaluate",
            return_value=mock_readiness,
        ),
        patch.object(PlanPreviewService, "generate") as mock_gen,
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/preview")
        assert resp.status_code == 500
        assert "Sunucu hatası" in resp.json()["detail"]
        mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# Section 25 & 26: Legacy & Readiness Route Integrity
# ---------------------------------------------------------------------------


def test_26_legacy_plan_preview_route_remains_unchanged(tmp_path: Path) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    readiness = service.evaluate("proj_test_01")
    assert readiness.preparation is not None
    assert readiness.preparation.request is not None
    req = readiness.preparation.request

    resp = client.post("/api/v1/plan/preview", json=req.model_dump(mode="json"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["solution"] is not None
    assert data["document"] is not None


def test_27_readiness_get_endpoint_remains_200_for_ready_and_blocked(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, plan_input_repo = _setup_app_and_repos(tmp_path)

    # 1. Blocked project
    resp_blocked = client.get("/api/v1/projects/proj_test_01/plan/preview/readiness")
    assert resp_blocked.status_code == 200
    assert resp_blocked.json()["ready_for_preview"] is False

    # 2. Ready project
    _persist_ready_project(brief_repo, spatial_repo, plan_input_repo, "proj_test_01")
    resp_ready = client.get("/api/v1/projects/proj_test_01/plan/preview/readiness")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["ready_for_preview"] is True
