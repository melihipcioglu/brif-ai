"""Tests for Project Plan Preview Readiness Service and API V0."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
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
    InvalidProjectIdError,
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
from brif_ai.spatial.persistence import JSONSpatialRelationshipRepository
from brif_ai.spatial.plan_input import (
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
)
from brif_ai.spatial.plan_preview import (
    PlanPreviewReadinessBlockerCode,
    ProjectPlanPreviewBlocker,
    ProjectPlanPreviewBlockerCode,
    ProjectPlanPreviewReadinessResult,
    ProjectPlanPreviewReadinessService,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.room_solver.solver import RoomGeometrySolver
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SitePoint,
    SitePolygonInput,
)
from brif_ai.spatial.svg_plan.renderer import SvgPlanRenderer


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
        grid_step_m=0.10,
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


# ---------------------------------------------------------------------------
# Scenarios 1-6: Upstream Missing / Stale / Unready Blockers
# ---------------------------------------------------------------------------


def test_1_no_brief_snapshot_returns_brief_missing(tmp_path: Path) -> None:
    """Missing BriefSnapshot produces 200 + BRIEF_MISSING blocker."""
    service = ProjectPlanPreviewReadinessService(
        brief_repository=JSONBriefRepository(root_dir=tmp_path),
        spatial_repository=JSONSpatialRelationshipRepository(root_dir=tmp_path),
        plan_input_repository=JSONPlanInputStateRepository(root_dir=tmp_path),
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert result.source_brief_version is None
    assert result.plan_input_state_version is None
    assert len(result.project_blockers) == 1
    assert result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.BRIEF_MISSING
    assert result.preparation is None


def test_2_brief_exists_graph_missing_returns_spatial_graph_missing(
    tmp_path: Path,
) -> None:
    """Brief exists but graph is missing produces SPATIAL_GRAPH_MISSING blocker."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    snapshot, _, _, _, _, _ = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=JSONSpatialRelationshipRepository(root_dir=tmp_path),
        plan_input_repository=JSONPlanInputStateRepository(root_dir=tmp_path),
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert result.source_brief_version == 1
    assert len(result.project_blockers) == 1
    assert result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_MISSING
    assert result.preparation is None


def test_3_brief_and_graph_exist_plan_state_missing(tmp_path: Path) -> None:
    """Brief and graph exist but plan input state missing produces PLAN_INPUT_STATE_MISSING."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot, graph, _, _, _, _ = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=JSONPlanInputStateRepository(root_dir=tmp_path),
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert result.source_brief_version == 1
    assert len(result.project_blockers) == 1
    assert result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_MISSING
    assert result.preparation is None


def test_4_stale_graph_brief_version_returns_spatial_graph_stale(
    tmp_path: Path,
) -> None:
    """Graph with older source_brief_version produces SPATIAL_GRAPH_STALE."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot_v2, graph_v1, _, _, _, _ = _build_test_data("proj_01", 1)
    # Advance snapshot to v2 while graph stays at v1
    snapshot_v2 = snapshot_v2.model_copy(update={"brief_version": 2})

    brief_repo.save(snapshot_v2)
    spatial_repo.save(graph_v1)
    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=2,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert len(result.project_blockers) == 1
    assert result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_STALE


def test_5_stale_plan_input_state_brief_version_returns_plan_input_state_stale(
    tmp_path: Path,
) -> None:
    """Plan input state with older source_brief_version produces PLAN_INPUT_STATE_STALE."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot_v2, graph_v2, _, _, _, _ = _build_test_data("proj_01", 2)
    brief_repo.save(snapshot_v2)
    spatial_repo.save(graph_v2)

    plan_input_state_v1 = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,  # Stale brief version 1 != 2
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    plan_input_repo.save(plan_input_state_v1)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert len(result.project_blockers) == 1
    assert result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_STALE


def test_6_brief_readiness_failure_returns_brief_not_ready(tmp_path: Path) -> None:
    """Unready brief with pending questions produces BRIEF_NOT_READY."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot_unready, graph, _, _, _, _ = _build_test_data("proj_01", 1, is_brief_ready=False)
    brief_repo.save(snapshot_unready)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert len(result.project_blockers) == 1
    assert result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.BRIEF_NOT_READY


# ---------------------------------------------------------------------------
# Scenarios 7-12: Downstream Plan Input Partial Blockers & Full Readiness
# ---------------------------------------------------------------------------


def test_7_metric_requirements_missing_blocker_preserved(tmp_path: Path) -> None:
    """When metrics are None in state, preparation METRIC_REQUIREMENTS_MISSING is preserved."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, _, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=None,  # Missing
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert len(result.project_blockers) == 0
    assert result.preparation is not None
    assert result.preparation.ready_for_preview is False
    codes = [b.code for b in result.preparation.blockers]
    assert PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING in codes


def test_8_site_envelope_missing_blocker_preserved(tmp_path: Path) -> None:
    """When site is None in state, preparation SITE_ENVELOPE_MISSING is preserved."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, _, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=None,  # Missing
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert result.preparation is not None
    codes = [b.code for b in result.preparation.blockers]
    assert PlanPreviewReadinessBlockerCode.SITE_ENVELOPE_MISSING in codes


def test_9_floor_plate_input_missing_blocker_preserved(tmp_path: Path) -> None:
    """When FloorPlateInput is None in state, preparation FLOOR_PLATE_INPUT_MISSING is preserved."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, _, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=None,  # Missing
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert result.preparation is not None
    codes = [b.code for b in result.preparation.blockers]
    assert PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING in codes


def test_10_solver_config_missing_blocker_preserved(tmp_path: Path) -> None:
    """When solver_config is None in state, preparation SOLVER_CONFIG_MISSING is preserved."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, _ = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=None,  # Missing
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert result.preparation is not None
    codes = [b.code for b in result.preparation.blockers]
    assert PlanPreviewReadinessBlockerCode.SOLVER_CONFIG_MISSING in codes


def test_11_and_12_all_inputs_valid_ready_for_preview_true_with_request(
    tmp_path: Path,
) -> None:
    """All valid authoritative inputs evaluate to ready_for_preview=True with PlanPreviewRequest."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is True
    assert len(result.project_blockers) == 0
    assert result.source_brief_version == 1
    assert result.plan_input_state_version == 1
    assert result.preparation is not None
    assert result.preparation.ready_for_preview is True
    assert result.preparation.request is not None
    assert result.preparation.request.solver_config == cfg


# ---------------------------------------------------------------------------
# Scenarios 13-17: Non-Execution Spies and Immutability Checks
# ---------------------------------------------------------------------------


def test_13_successful_readiness_does_not_call_room_geometry_solver(
    tmp_path: Path,
) -> None:
    """Evaluating readiness does NOT invoke RoomGeometrySolver.solve."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    with patch.object(RoomGeometrySolver, "solve") as mock_solve:
        result = service.evaluate("proj_01")
        assert result.ready_for_preview is True
        mock_solve.assert_not_called()


def test_14_successful_readiness_does_not_call_svg_plan_renderer(
    tmp_path: Path,
) -> None:
    """Evaluating readiness does NOT invoke SvgPlanRenderer.render."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    with patch.object(SvgPlanRenderer, "render") as mock_render:
        result = service.evaluate("proj_01")
        assert result.ready_for_preview is True
        mock_render.assert_not_called()


def test_15_16_17_does_not_mutate_snapshot_graph_or_create_new_state_version(
    tmp_path: Path,
) -> None:
    """Evaluating readiness leaves stored Brief, Graph, and PlanInputState versions untouched."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    # Evaluate multiple times
    service.evaluate("proj_01")
    service.evaluate("proj_01")

    # Assert versions and states remain unchanged
    loaded_brief = brief_repo.get_latest("proj_01")
    loaded_graph = spatial_repo.get_latest("proj_01")
    plan_versions = plan_input_repo.list_versions("proj_01")

    assert loaded_brief == snapshot
    assert loaded_graph == graph
    assert plan_versions == [1]


# ---------------------------------------------------------------------------
# Scenarios 18-24: API Integration, Serialization, and Boundaries
# ---------------------------------------------------------------------------


def test_18_endpoint_accepts_no_request_body(tmp_path: Path) -> None:
    """GET endpoint succeeds without request body."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    client = TestClient(app)

    response = client.get("/api/v1/projects/proj_01/plan/preview/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["ready_for_preview"] is True
    assert data["schema_version"] == "project_plan_preview_readiness.v0"
    assert data["project_id"] == "proj_01"


def test_19_result_deterministic_for_identical_persisted_inputs(
    tmp_path: Path,
) -> None:
    """Multiple evaluations produce identical model dumps."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    r1 = service.evaluate("proj_01").model_dump(mode="json")
    r2 = service.evaluate("proj_01").model_dump(mode="json")
    assert r1 == r2


def test_20_project_and_version_metadata_propagated_correctly(
    tmp_path: Path,
) -> None:
    """Project ID, brief version, and state version are properly propagated."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_abc", 5)
    brief_repo.save(snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_abc",
        state_version=3,
        source_brief_version=5,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_abc")
    assert result.project_id == "proj_abc"
    assert result.source_brief_version == 5
    assert result.plan_input_state_version == 3


def test_21_invalid_project_id_returns_422(tmp_path: Path) -> None:
    """Invalid project ID format returns 422 and raises InvalidProjectIdError."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    with pytest.raises(InvalidProjectIdError):
        service.evaluate("invalid!id")

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    client = TestClient(app)

    response = client.get("/api/v1/projects/invalid!id/plan/preview/readiness")
    assert response.status_code == 422
    assert "Invalid project ID" in response.json()["detail"]


def test_22_persistence_error_safely_mapped_to_500(tmp_path: Path) -> None:
    """Persistence failure safely maps to 500 error."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )
    client = TestClient(app)

    with patch.object(
        PersistentBriefService,
        "get_latest_brief",
        side_effect=BriefPersistenceError("Disk read failure"),
    ):
        response = client.get("/api/v1/projects/proj_01/plan/preview/readiness")
        assert response.status_code == 500
        assert "Kalıcı depolama hatası" in response.json()["detail"]


def test_22b_unexpected_value_error_returns_500(tmp_path: Path) -> None:
    """Unexpected ValueError from readiness service maps to 500 Internal Server Error."""
    app = create_app(
        brief_repository=JSONBriefRepository(root_dir=tmp_path),
        spatial_repository=JSONSpatialRelationshipRepository(root_dir=tmp_path),
        plan_input_repository=JSONPlanInputStateRepository(root_dir=tmp_path),
    )
    client = TestClient(app)

    with patch.object(
        ProjectPlanPreviewReadinessService,
        "evaluate",
        side_effect=ValueError("Unexpected internal value error"),
    ):
        response = client.get("/api/v1/projects/proj_01/plan/preview/readiness")
        assert response.status_code == 500
        assert "Sunucu hatası" in response.json()["detail"]


def test_23_existing_plan_preview_post_endpoint_unchanged(tmp_path: Path) -> None:
    """Existing POST /api/v1/plan/preview endpoint behavior remains intact."""
    app = create_app(
        brief_repository=JSONBriefRepository(root_dir=tmp_path),
        spatial_repository=JSONSpatialRelationshipRepository(root_dir=tmp_path),
        plan_input_repository=JSONPlanInputStateRepository(root_dir=tmp_path),
    )
    client = TestClient(app)

    # Calling with empty body returns 422
    response = client.post("/api/v1/plan/preview", json={})
    assert response.status_code == 422


def test_24_conversation_ui_demo_fixture_remains_unchanged() -> None:
    """Conversation UI demo JSON fixture file exists and is untouched."""
    fixture_path = Path("prototypes/conversation_ui_v0/data/plan_preview_request.demo.json")
    assert fixture_path.exists()
    content = fixture_path.read_text(encoding="utf-8")
    assert "fplate_a2ab8e0ec7fd4b44" in content
    assert "proj_living_kitchen_01" in content


def test_25_directive_derivation_failure_returns_directive_derivation_failed(
    tmp_path: Path,
) -> None:
    """Derivation exception (e.g. node mismatch) produces DIRECTIVE_DERIVATION_FAILED blocker."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    plan_input_repo = JSONPlanInputStateRepository(root_dir=tmp_path)

    snapshot, graph, metrics, site, fp, cfg = _build_test_data("proj_01", 1)
    # Mutate snapshot with an extra space request not in graph to trigger node mismatch error
    extra_space = SpaceRequest(
        id="sr_bedroom",
        display_name="Bedroom",
        space_function=SpaceFunction.SLEEPING,
        minimum_quantity=1,
        mandatory=True,
        confirmation_status=ConfirmationStatus.CONFIRMED,
        stakeholder_ids=["stk_01"],
        evidence_ids=["ev_01"],
    )
    mismatched_snapshot = snapshot.model_copy(
        update={"space_requests": [*snapshot.space_requests, extra_space]}
    )

    brief_repo.save(mismatched_snapshot)
    spatial_repo.save(graph)

    plan_input_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    plan_input_repo.save(plan_input_state)

    service = ProjectPlanPreviewReadinessService(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
        plan_input_repository=plan_input_repo,
    )

    result = service.evaluate("proj_01")
    assert result.ready_for_preview is False
    assert len(result.project_blockers) == 1
    assert (
        result.project_blockers[0].code == ProjectPlanPreviewBlockerCode.DIRECTIVE_DERIVATION_FAILED
    )


def test_project_readiness_result_model_invariants() -> None:
    """Enforce strict mutual exclusion and validation rules on ProjectPlanPreviewReadinessResult."""
    # ready=True with blockers must fail
    with pytest.raises(ValueError, match="ready_for_preview=True must have empty project_blockers"):
        ProjectPlanPreviewReadinessResult(
            project_id="proj_01",
            ready_for_preview=True,
            project_blockers=[
                ProjectPlanPreviewBlocker(
                    code=ProjectPlanPreviewBlockerCode.BRIEF_MISSING,
                    message="Missing",
                )
            ],
            preparation=None,
        )

    # ready=True without preparation must fail
    with pytest.raises(ValueError, match="requires a successful preparation result"):
        ProjectPlanPreviewReadinessResult(
            project_id="proj_01",
            ready_for_preview=True,
            project_blockers=[],
            preparation=None,
        )

    # ready=False with no blockers and no preparation must fail
    with pytest.raises(ValueError, match="ready_for_preview=False must contain project_blockers"):
        ProjectPlanPreviewReadinessResult(
            project_id="proj_01",
            ready_for_preview=False,
            project_blockers=[],
            preparation=None,
        )
