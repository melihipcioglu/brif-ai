"""API tests for Authoritative Plan Input State API V0."""

from __future__ import annotations

import concurrent.futures
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
from brif_ai.brief.persistence.errors import BriefPersistenceError
from brif_ai.brief.persistence.json_repository import JSONBriefRepository
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
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.persistence.json_repository import JSONSpatialRelationshipRepository
from brif_ai.spatial.plan_input import (
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
    PlanInputStatePersistenceError,
    PlanInputStateService,
)
from brif_ai.spatial.plan_preview import PlanPreviewService
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver import RoomGeometrySolver
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.svg_plan import SvgPlanRenderer


def _build_test_snapshot(
    project_id: str = "proj_test_01",
    brief_version: int = 1,
) -> BriefSnapshot:
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
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
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


def _build_test_artifacts(
    project_id: str = "proj_test_01",
    brief_version: int = 1,
) -> tuple[
    MetricSpatialRequirements,
    SiteBuildableEnvelope,
    FloorPlateInput,
    RoomGeometrySolverConfig,
]:
    snapshot = _build_test_snapshot(project_id, brief_version)
    ev_id = snapshot.evidence[0].id
    relationships = [
        SpatialRelationshipInput(
            source_space_id="sn_living_01",
            target_space_id="sn_kitchen_01",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_CONFIRMED,
            priority=Priority.MUST,
            evidence_ids=[ev_id],
            rationale="Adjacency",
        )
    ]
    graph = SpatialRelationshipGraphBuilder().build(
        snapshot,
        relationships,
        created_at=datetime(2026, 8, 19, 12, 5, 0, tzinfo=UTC),
    )
    program = SpatialProgramBuilder().build(snapshot, graph)

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
        ],
        created_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=UTC),
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
            evidence_ids=[ev_id],
        ),
        buildable_envelope=SitePolygonInput(
            vertices=[
                SitePoint(x_m=2.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=18.0),
                SitePoint(x_m=2.0, y_m=18.0),
            ],
            provenance=RelationshipProvenance.USER_CONFIRMED,
            evidence_ids=[ev_id],
        ),
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
    )

    floor_plate_input = FloorPlateInput(
        vertices=[
            SitePoint(x_m=3.0, y_m=3.0),
            SitePoint(x_m=15.0, y_m=3.0),
            SitePoint(x_m=15.0, y_m=15.0),
            SitePoint(x_m=3.0, y_m=15.0),
        ],
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=[ev_id],
    )

    solver_config = RoomGeometrySolverConfig(
        grid_step_m=1.0,
        max_time_seconds=10.0,
    )

    return metric_reqs, site_envelope, floor_plate_input, solver_config


def _setup_app(
    tmp_path: Path,
) -> tuple[
    TestClient,
    JSONBriefRepository,
    JSONSpatialRelationshipRepository,
    JSONPlanInputStateRepository,
]:
    (tmp_path / "projects").mkdir(parents=True, exist_ok=True)
    brief_repo = JSONBriefRepository(tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(tmp_path)
    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    client = TestClient(app)
    return client, brief_repo, spatial_repo, plan_input_repo


def test_01_get_latest_missing_returns_404(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app(tmp_path)
    resp = client.get("/api/v1/projects/proj_test_01/plan/input")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_02_post_initialize_empty_body_success(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=3)
    brief_repo.save(snapshot)

    resp = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["schema_version"] == "authoritative_plan_input_state.v0"
    assert data["project_id"] == "proj_test_01"
    assert data["state_version"] == 1
    assert data["source_brief_version"] == 3
    assert data["metric_requirements"] is None
    assert data["site_envelope"] is None
    assert data["floor_plate_input"] is None
    assert data["solver_config"] is None
    assert "created_at" in data


def test_03_post_initialize_with_explicit_valid_plan_inputs(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    metrics, site, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    payload = {
        "metric_requirements": metrics.model_dump(mode="json"),
        "site_envelope": site.model_dump(mode="json"),
        "floor_plate_input": fp.model_dump(mode="json"),
        "solver_config": cfg.model_dump(mode="json"),
    }

    resp = client.post("/api/v1/projects/proj_test_01/plan/input", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["state_version"] == 1
    assert data["source_brief_version"] == 1
    assert data["metric_requirements"] is not None
    assert data["site_envelope"] is not None
    assert data["floor_plate_input"] is not None
    assert data["solver_config"] is not None


def test_04_post_second_initialization_returns_409(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    resp1 = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    assert resp2.status_code == 409
    assert "already initialized" in resp2.json()["detail"].lower()


def test_05_get_latest_after_initialization(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    metrics, site, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    payload = {
        "metric_requirements": metrics.model_dump(mode="json"),
        "site_envelope": site.model_dump(mode="json"),
        "floor_plate_input": fp.model_dump(mode="json"),
        "solver_config": cfg.model_dump(mode="json"),
    }
    client.post("/api/v1/projects/proj_test_01/plan/input", json=payload)

    resp = client.get("/api/v1/projects/proj_test_01/plan/input")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "proj_test_01"
    assert data["state_version"] == 1
    assert data["source_brief_version"] == 1


def test_06_get_existing_historical_version(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    resp = client.get("/api/v1/projects/proj_test_01/plan/input/versions/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state_version"] == 1


def test_07_get_missing_historical_version_returns_404(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    resp = client.get("/api/v1/projects/proj_test_01/plan/input/versions/2")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_08_invalid_project_id_returns_422(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app(tmp_path)

    # Invalid project ID format (starts with digit)
    resp = client.get("/api/v1/projects/123_invalid/plan/input")
    assert resp.status_code == 422

    resp_init = client.post("/api/v1/projects/123_invalid/plan/input", json={})
    assert resp_init.status_code == 422

    resp_patch = client.patch(
        "/api/v1/projects/123_invalid/plan/input", json={"expected_state_version": 1}
    )
    assert resp_patch.status_code == 422

    resp_ver = client.get("/api/v1/projects/123_invalid/plan/input/versions/1")
    assert resp_ver.status_code == 422


def test_09_patch_with_correct_expected_state_version_increments_by_one(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    cfg = RoomGeometrySolverConfig(grid_step_m=0.5)
    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": cfg.model_dump(mode="json"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state_version"] == 2
    assert data["solver_config"]["grid_step_m"] == 0.5


def test_10_patch_stale_expected_state_version_returns_409(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 99},
    )
    assert resp.status_code == 409
    assert "stale state version" in resp.json()["detail"].lower()
    # Ensure no new version created
    assert plan_input_repo.list_versions("proj_test_01") == [1]


def test_11_patch_before_initialization_returns_404(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 1},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_12_patch_omitted_field_preserves_old_value(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    metrics, site, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics.model_dump(mode="json"),
            "site_envelope": site.model_dump(mode="json"),
            "floor_plate_input": fp.model_dump(mode="json"),
            "solver_config": cfg.model_dump(mode="json"),
        },
    )

    # Patch only solver_config; others omitted
    new_cfg = RoomGeometrySolverConfig(grid_step_m=0.25)
    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": new_cfg.model_dump(mode="json"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state_version"] == 2
    assert data["metric_requirements"] == metrics.model_dump(mode="json")
    assert data["site_envelope"] == site.model_dump(mode="json")
    assert data["floor_plate_input"] == fp.model_dump(mode="json")
    assert data["solver_config"]["grid_step_m"] == 0.25


def test_13_patch_explicit_null_clears_field(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    metrics, site, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics.model_dump(mode="json"),
            "site_envelope": site.model_dump(mode="json"),
            "floor_plate_input": fp.model_dump(mode="json"),
            "solver_config": cfg.model_dump(mode="json"),
        },
    )

    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": None,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state_version"] == 2
    assert data["solver_config"] is None
    assert data["metric_requirements"] is not None


def test_14_patch_concrete_field_replaces_old_value(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    cfg1 = RoomGeometrySolverConfig(grid_step_m=1.0)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"solver_config": cfg1.model_dump(mode="json")},
    )

    cfg2 = RoomGeometrySolverConfig(grid_step_m=0.5)
    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": cfg2.model_dump(mode="json"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["solver_config"]["grid_step_m"] == 0.5


def test_15_patch_can_preserve_three_fields_while_clearing_one(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    metrics, site, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics.model_dump(mode="json"),
            "site_envelope": site.model_dump(mode="json"),
            "floor_plate_input": fp.model_dump(mode="json"),
            "solver_config": cfg.model_dump(mode="json"),
        },
    )

    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "floor_plate_input": None,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["floor_plate_input"] is None
    assert data["metric_requirements"] == metrics.model_dump(mode="json")
    assert data["site_envelope"] == site.model_dump(mode="json")
    assert data["solver_config"] == cfg.model_dump(mode="json")


def test_16_latest_brief_version_is_server_derived(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=7)
    brief_repo.save(snapshot)

    resp = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    assert resp.status_code == 201
    assert resp.json()["source_brief_version"] == 7


def test_17_forbidden_source_brief_version_in_body_returns_422(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    resp_init = client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"source_brief_version": 1},
    )
    assert resp_init.status_code == 422

    client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    resp_patch = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 1, "source_brief_version": 2},
    )
    assert resp_patch.status_code == 422


def test_18_forbidden_project_id_in_body_returns_422(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    resp_init = client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"project_id": "proj_test_01"},
    )
    assert resp_init.status_code == 422

    client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    resp_patch = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 1, "project_id": "proj_test_01"},
    )
    assert resp_patch.status_code == 422


def test_19_forbidden_state_version_in_body_returns_422(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    resp_init = client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"state_version": 1},
    )
    assert resp_init.status_code == 422

    client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    resp_patch = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 1, "state_version": 2},
    )
    assert resp_patch.status_code == 422


def test_20_forbidden_created_at_in_body_returns_422(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    resp_init = client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"created_at": "2026-08-21T12:00:00Z"},
    )
    assert resp_init.status_code == 422

    client.post("/api/v1/projects/proj_test_01/plan/input", json={})
    resp_patch = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 1, "created_at": "2026-08-21T12:00:00Z"},
    )
    assert resp_patch.status_code == 422


def test_21_wrong_project_metric_spatial_requirements_returns_422(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    metrics_other, _, _, _ = _build_test_artifacts("proj_test_other", brief_version=1)
    resp = client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"metric_requirements": metrics_other.model_dump(mode="json")},
    )
    assert resp.status_code == 422
    assert plan_input_repo.get_latest("proj_test_01") is None


def test_22_wrong_project_site_buildable_envelope_returns_422(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snapshot = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snapshot)

    _, site_other, _, _ = _build_test_artifacts("proj_test_other", brief_version=1)
    resp = client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"site_envelope": site_other.model_dump(mode="json")},
    )
    assert resp.status_code == 422
    assert plan_input_repo.get_latest("proj_test_01") is None


def test_23_stale_metric_source_brief_version_after_brief_advances_patch_rejected(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    # Brief v1
    snap_v1 = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap_v1)

    metrics_v1, site_v1, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics_v1.model_dump(mode="json"),
            "site_envelope": site_v1.model_dump(mode="json"),
            "floor_plate_input": fp.model_dump(mode="json"),
            "solver_config": cfg.model_dump(mode="json"),
        },
    )

    # Advance Brief to v2
    snap_v2 = _build_test_snapshot("proj_test_01", brief_version=2)
    brief_repo.save(snap_v2)

    # PATCH only changing solver_config carrying old metric_requirements (v1) forward
    new_cfg = RoomGeometrySolverConfig(grid_step_m=0.25)
    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": new_cfg.model_dump(mode="json"),
        },
    )
    assert resp.status_code == 422
    assert "source_brief_version" in resp.json()["detail"].lower()
    # Ensure no new plan input version created
    assert plan_input_repo.list_versions("proj_test_01") == [1]


def test_24_brief_advances_and_stale_artifacts_cleared_patch_succeeds(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap_v1 = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap_v1)

    metrics_v1, site_v1, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics_v1.model_dump(mode="json"),
            "site_envelope": site_v1.model_dump(mode="json"),
            "floor_plate_input": fp.model_dump(mode="json"),
            "solver_config": cfg.model_dump(mode="json"),
        },
    )

    # Advance Brief to v2
    snap_v2 = _build_test_snapshot("proj_test_01", brief_version=2)
    brief_repo.save(snap_v2)

    # Clear stale metrics and site
    resp = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "metric_requirements": None,
            "site_envelope": None,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state_version"] == 2
    assert data["source_brief_version"] == 2
    assert data["metric_requirements"] is None
    assert data["site_envelope"] is None
    assert data["floor_plate_input"] is not None


def test_25_persisted_latest_state_with_wrong_project_id_returns_500(
    tmp_path: Path,
) -> None:
    client, _, _, plan_input_repo = _setup_app(tmp_path)
    # Persist a state for proj_test_02 but place it or return it for proj_test_01
    bad_state = AuthoritativePlanInputState(
        schema_version="authoritative_plan_input_state.v0",
        project_id="proj_test_02",
        state_version=1,
        source_brief_version=1,
        created_at=datetime.now(UTC),
    )

    with patch.object(plan_input_repo, "get_latest", return_value=bad_state):
        resp = client.get("/api/v1/projects/proj_test_01/plan/input")
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()


def test_26_persisted_historical_state_with_wrong_project_id_returns_500(
    tmp_path: Path,
) -> None:
    client, _, _, plan_input_repo = _setup_app(tmp_path)
    bad_state = AuthoritativePlanInputState(
        schema_version="authoritative_plan_input_state.v0",
        project_id="proj_test_02",
        state_version=1,
        source_brief_version=1,
        created_at=datetime.now(UTC),
    )

    with patch.object(plan_input_repo, "get_version", return_value=bad_state):
        resp = client.get("/api/v1/projects/proj_test_01/plan/input/versions/1")
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()


def test_27_persisted_historical_state_with_wrong_state_version_returns_500(
    tmp_path: Path,
) -> None:
    client, _, _, plan_input_repo = _setup_app(tmp_path)
    bad_state = AuthoritativePlanInputState(
        schema_version="authoritative_plan_input_state.v0",
        project_id="proj_test_01",
        state_version=2,
        source_brief_version=1,
        created_at=datetime.now(UTC),
    )

    with patch.object(plan_input_repo, "get_version", return_value=bad_state):
        resp = client.get("/api/v1/projects/proj_test_01/plan/input/versions/1")
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()


def test_28_persisted_latest_brief_wrong_project_id_during_post_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    bad_brief = _build_test_snapshot("proj_test_02", brief_version=1)

    with patch.object(brief_repo, "get_latest", return_value=bad_brief):
        resp = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()


def test_29_persisted_latest_brief_wrong_project_id_during_patch_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    bad_brief = _build_test_snapshot("proj_test_02", brief_version=1)
    with patch.object(brief_repo, "get_latest", return_value=bad_brief):
        resp = client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()


def test_30_brief_persistence_error_returns_500(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)

    with patch.object(
        brief_repo,
        "get_latest",
        side_effect=BriefPersistenceError("Disk read failure"),
    ):
        resp_post = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        assert resp_post.status_code == 500

        resp_patch = client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        assert resp_patch.status_code == 500


def test_31_plan_input_state_persistence_error_returns_500(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    with patch.object(
        plan_input_repo,
        "save",
        side_effect=PlanInputStatePersistenceError("I/O write failure"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        assert resp.status_code == 500


def test_32_get_does_not_mutate_state(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    state_before = plan_input_repo.get_latest("proj_test_01")
    client.get("/api/v1/projects/proj_test_01/plan/input")
    client.get("/api/v1/projects/proj_test_01/plan/input/versions/1")
    state_after = plan_input_repo.get_latest("proj_test_01")

    assert state_before == state_after
    assert plan_input_repo.list_versions("proj_test_01") == [1]


def test_33_patch_creates_only_one_new_historical_version(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    assert plan_input_repo.list_versions("proj_test_01") == [1]

    client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 1},
    )
    assert plan_input_repo.list_versions("proj_test_01") == [1, 2]


def test_34_post_patch_never_call_room_geometry_solver(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    with patch.object(RoomGeometrySolver, "solve") as mock_solve:
        client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        mock_solve.assert_not_called()


def test_35_post_patch_never_call_svg_plan_renderer(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    with patch.object(SvgPlanRenderer, "render") as mock_render:
        client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        mock_render.assert_not_called()


def test_36_post_patch_never_call_plan_preview_service_generate(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    with patch.object(PlanPreviewService, "generate") as mock_generate:
        client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        mock_generate.assert_not_called()


def test_37_existing_project_plan_preview_readiness_remains_functional(
    tmp_path: Path,
) -> None:
    client, brief_repo, spatial_repo, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    # Missing spatial graph and plan input
    resp = client.get("/api/v1/projects/proj_test_01/plan/preview/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready_for_preview"] is False
    assert any(b["code"] == "SPATIAL_GRAPH_MISSING" for b in data["project_blockers"])


def test_38_existing_plan_preview_post_route_remains_unchanged(tmp_path: Path) -> None:
    client, _, _, _ = _setup_app(tmp_path)
    # Calling POST /api/v1/plan/preview with empty body returns 422 validation error
    resp = client.post("/api/v1/plan/preview", json={})
    assert resp.status_code == 422


def test_39_absent_vs_null_three_step_semantic_test(tmp_path: Path) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    metrics_a, site_a, fp_a, cfg_a = _build_test_artifacts("proj_test_01", brief_version=1)

    # Initial state with all 4 artifacts
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics_a.model_dump(mode="json"),
            "site_envelope": site_a.model_dump(mode="json"),
            "floor_plate_input": fp_a.model_dump(mode="json"),
            "solver_config": cfg_a.model_dump(mode="json"),
        },
    )

    # PATCH 1: expected_state_version=1, solver_config=null
    resp1 = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": None,
        },
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["state_version"] == 2
    assert data1["metric_requirements"] == metrics_a.model_dump(mode="json")
    assert data1["site_envelope"] == site_a.model_dump(mode="json")
    assert data1["floor_plate_input"] == fp_a.model_dump(mode="json")
    assert data1["solver_config"] is None

    # PATCH 2: expected_state_version=2, solver_config absent
    resp2 = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={"expected_state_version": 2},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["state_version"] == 3
    assert data2["metric_requirements"] == metrics_a.model_dump(mode="json")
    assert data2["site_envelope"] == site_a.model_dump(mode="json")
    assert data2["floor_plate_input"] == fp_a.model_dump(mode="json")
    assert data2["solver_config"] is None


def test_40_brief_version_transition_provenance_invariant(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)

    # 1. State v1 on brief v1
    snap_v1 = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap_v1)
    metrics_v1, site_v1, fp, cfg = _build_test_artifacts("proj_test_01", brief_version=1)
    client.post(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "metric_requirements": metrics_v1.model_dump(mode="json"),
            "site_envelope": site_v1.model_dump(mode="json"),
            "floor_plate_input": fp.model_dump(mode="json"),
            "solver_config": cfg.model_dump(mode="json"),
        },
    )

    # 2. Brief advances to v2
    snap_v2 = _build_test_snapshot("proj_test_01", brief_version=2)
    brief_repo.save(snap_v2)

    # 3. PATCH carrying stale metrics/site fails
    new_cfg = RoomGeometrySolverConfig(grid_step_m=0.25)
    resp_stale = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "solver_config": new_cfg.model_dump(mode="json"),
        },
    )
    assert resp_stale.status_code == 422
    assert plan_input_repo.list_versions("proj_test_01") == [1]

    # 4. PATCH clearing stale metrics/site succeeds
    resp_ok = client.patch(
        "/api/v1/projects/proj_test_01/plan/input",
        json={
            "expected_state_version": 1,
            "metric_requirements": None,
            "site_envelope": None,
            "solver_config": new_cfg.model_dump(mode="json"),
        },
    )
    assert resp_ok.status_code == 200
    data_ok = resp_ok.json()
    assert data_ok["state_version"] == 2
    assert data_ok["source_brief_version"] == 2
    assert data_ok["metric_requirements"] is None
    assert data_ok["site_envelope"] is None
    assert data_ok["solver_config"]["grid_step_m"] == 0.25


def test_41_api_optimistic_concurrency_race(tmp_path: Path) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    # Competing patches with expected_state_version=1 and different payloads
    def _do_patch(grid_size: float) -> int:
        c = RoomGeometrySolverConfig(grid_step_m=grid_size)
        r = client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={
                "expected_state_version": 1,
                "solver_config": c.model_dump(mode="json"),
            },
        )
        return int(r.status_code)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_do_patch, float(i)) for i in range(1, 5)]
        status_codes = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Exactly one winner (200), losers get conflict (409)
    assert status_codes.count(200) == 1
    assert status_codes.count(409) == 3
    assert plan_input_repo.list_versions("proj_test_01") == [1, 2]


def test_42_persisted_latest_plan_input_wrong_project_id_during_post_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    bad_state = AuthoritativePlanInputState(
        schema_version="authoritative_plan_input_state.v0",
        project_id="proj_test_02",
        state_version=1,
        source_brief_version=1,
        created_at=datetime.now(UTC),
    )
    with patch.object(plan_input_repo, "get_latest", return_value=bad_state):
        resp = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()


def test_43_persisted_latest_plan_input_wrong_project_id_during_patch_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, plan_input_repo = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    bad_state = AuthoritativePlanInputState(
        schema_version="authoritative_plan_input_state.v0",
        project_id="proj_test_02",
        state_version=1,
        source_brief_version=1,
        created_at=datetime.now(UTC),
    )
    with patch.object(plan_input_repo, "get_latest", return_value=bad_state):
        resp = client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        assert resp.status_code == 500
        assert "mismatch" in resp.json()["detail"].lower()
        # No version created
        assert plan_input_repo.list_versions("proj_test_01") == []


def test_44_unexpected_value_error_from_initialize_state_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)

    with patch.object(
        PlanInputStateService,
        "initialize_state",
        side_effect=ValueError("Unexpected internal ValueError"),
    ):
        resp = client.post("/api/v1/projects/proj_test_01/plan/input", json={})
        assert resp.status_code == 500
        assert "sunucu hatas" in resp.json()["detail"].lower()


def test_45_unexpected_value_error_from_update_state_returns_500(
    tmp_path: Path,
) -> None:
    client, brief_repo, _, _ = _setup_app(tmp_path)
    snap = _build_test_snapshot("proj_test_01", brief_version=1)
    brief_repo.save(snap)
    client.post("/api/v1/projects/proj_test_01/plan/input", json={})

    with patch.object(
        PlanInputStateService,
        "update_state",
        side_effect=ValueError("Unexpected internal ValueError"),
    ):
        resp = client.patch(
            "/api/v1/projects/proj_test_01/plan/input",
            json={"expected_state_version": 1},
        )
        assert resp.status_code == 500
        assert "sunucu hatas" in resp.json()["detail"].lower()
