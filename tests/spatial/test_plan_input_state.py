"""Unit and invariant tests for Authoritative Plan Input State V0."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

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
from brif_ai.spatial.plan_input import (
    UNCHANGED,
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
    PlanInputStateBriefVersionMismatchError,
    PlanInputStateNotFoundError,
    PlanInputStatePersistenceError,
    PlanInputStateProjectMismatchError,
    PlanInputStateService,
    PlanInputStateVersionConflictError,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.models import (
    SiteBuildableEnvelope,
    SitePoint,
    SitePolygonInput,
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
    """Construct valid test spatial artifacts matching project_id and brief_version."""
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
    snapshot = BriefSnapshot(
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
        created_at=datetime(2026, 8, 19, 12, 15, 0, tzinfo=UTC),
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

    return metric_reqs, site_envelope, floor_plate_input, solver_config


# ---------------------------------------------------------------------------
# Test Cases 1-6: Valid State Variants
# ---------------------------------------------------------------------------


def test_1_empty_partial_state_valid() -> None:
    """Empty partial state with all optional inputs None is completely valid."""
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    assert state.schema_version == "authoritative_plan_input_state.v0"
    assert state.project_id == "proj_01"
    assert state.state_version == 1
    assert state.source_brief_version == 1
    assert state.metric_requirements is None
    assert state.site_envelope is None
    assert state.floor_plate_input is None
    assert state.solver_config is None


def test_2_metrics_only_state_valid() -> None:
    """State containing only MetricSpatialRequirements is valid."""
    metrics, _, _, _ = _build_test_artifacts(project_id="proj_01", brief_version=1)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
    )
    assert state.metric_requirements == metrics
    assert state.site_envelope is None


def test_3_site_only_state_valid() -> None:
    """State containing only SiteBuildableEnvelope is valid."""
    _, site, _, _ = _build_test_artifacts(project_id="proj_01", brief_version=1)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        site_envelope=site,
    )
    assert state.site_envelope == site
    assert state.metric_requirements is None


def test_4_floor_plate_input_only_state_valid() -> None:
    """State containing only FloorPlateInput is valid."""
    _, _, fp, _ = _build_test_artifacts(project_id="proj_01", brief_version=1)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        floor_plate_input=fp,
    )
    assert state.floor_plate_input == fp


def test_5_solver_config_only_state_valid() -> None:
    """State containing only RoomGeometrySolverConfig is valid."""
    _, _, _, cfg = _build_test_artifacts(project_id="proj_01", brief_version=1)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        solver_config=cfg,
    )
    assert state.solver_config == cfg


def test_6_fully_populated_state_valid() -> None:
    """Fully populated state with all 4 source inputs is valid."""
    metrics, site, fp, cfg = _build_test_artifacts(project_id="proj_01", brief_version=2)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=3,
        source_brief_version=2,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )
    assert state.metric_requirements == metrics
    assert state.site_envelope == site
    assert state.floor_plate_input == fp
    assert state.solver_config == cfg


# ---------------------------------------------------------------------------
# Test Cases 7-12: Invariants & Validation Errors
# ---------------------------------------------------------------------------


def test_7_metric_project_mismatch_rejected() -> None:
    """MetricSpatialRequirements with mismatched project_id is rejected."""
    metrics, _, _, _ = _build_test_artifacts(project_id="proj_other", brief_version=1)
    with pytest.raises(PlanInputStateProjectMismatchError, match="does not match state project_id"):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
            metric_requirements=metrics,
        )


def test_8_metric_brief_version_mismatch_rejected() -> None:
    """MetricSpatialRequirements with mismatched brief_version is rejected."""
    metrics, _, _, _ = _build_test_artifacts(project_id="proj_01", brief_version=99)
    with pytest.raises(
        PlanInputStateBriefVersionMismatchError, match="does not match state source_brief_version"
    ):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
            metric_requirements=metrics,
        )


def test_9_site_project_mismatch_rejected() -> None:
    """SiteBuildableEnvelope with mismatched project_id is rejected."""
    _, site, _, _ = _build_test_artifacts(project_id="proj_other", brief_version=1)
    with pytest.raises(PlanInputStateProjectMismatchError, match="does not match state project_id"):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
            site_envelope=site,
        )


def test_10_site_brief_version_mismatch_rejected() -> None:
    """SiteBuildableEnvelope with mismatched brief_version is rejected."""
    _, site, _, _ = _build_test_artifacts(project_id="proj_01", brief_version=99)
    with pytest.raises(
        PlanInputStateBriefVersionMismatchError, match="does not match state source_brief_version"
    ):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
            site_envelope=site,
        )


def test_11_naive_created_at_rejected() -> None:
    """Naive datetime without tzinfo is rejected."""
    with pytest.raises(ValidationError, match="timezone-aware"):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0),  # Naive
        )


def test_12_non_utc_created_at_rejected() -> None:
    """Datetime with non-zero UTC offset is rejected."""
    non_utc_tz = timezone(timedelta(hours=3))
    with pytest.raises(ValidationError, match="UTC offset"):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=non_utc_tz),
        )


# ---------------------------------------------------------------------------
# Test Cases 13-23: Service Lifecycle, Updates, Versioning
# ---------------------------------------------------------------------------


def test_13_initialize_creates_state_version_1(tmp_path: Path) -> None:
    """initialize_state creates state_version=1."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    state = service.initialize_state("proj_01", 1)
    assert state.state_version == 1
    assert state.project_id == "proj_01"
    assert state.source_brief_version == 1


def test_14_second_update_creates_state_version_2(tmp_path: Path) -> None:
    """update_state increments version to state_version=2."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    service.initialize_state("proj_01", 1)
    metrics, _, _, _ = _build_test_artifacts("proj_01", 1)

    state_v2 = service.update_state(
        "proj_01",
        expected_state_version=1,
        source_brief_version=1,
        metric_requirements=metrics,
    )
    assert state_v2.state_version == 2
    assert state_v2.metric_requirements == metrics


def test_15_source_brief_version_may_stay_unchanged_while_state_version_increments(
    tmp_path: Path,
) -> None:
    """Multiple state updates can occur against the same source_brief_version."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    service.initialize_state("proj_01", 12)
    metrics, site, fp, cfg = _build_test_artifacts("proj_01", 12)

    v2 = service.update_state("proj_01", 1, source_brief_version=12, metric_requirements=metrics)
    v3 = service.update_state("proj_01", 2, source_brief_version=12, site_envelope=site)
    v4 = service.update_state(
        "proj_01", 3, source_brief_version=12, floor_plate_input=fp, solver_config=cfg
    )

    assert v2.state_version == 2 and v2.source_brief_version == 12
    assert v3.state_version == 3 and v3.source_brief_version == 12
    assert v4.state_version == 4 and v4.source_brief_version == 12
    assert service.list_state_versions("proj_01") == [1, 2, 3, 4]


def test_16_stale_expected_state_version_rejected(tmp_path: Path) -> None:
    """Stale expected_state_version raises PlanInputStateVersionConflictError."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    service.initialize_state("proj_01", 1)
    service.update_state("proj_01", 1, source_brief_version=1)

    # Latest is now 2. Passing expected=1 must fail
    with pytest.raises(PlanInputStateVersionConflictError, match="Stale state version"):
        service.update_state("proj_01", expected_state_version=1, source_brief_version=1)


def test_17_historical_versions_remain_readable(tmp_path: Path) -> None:
    """All historical state versions are preserved and individually readable."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    service.initialize_state("proj_01", 1)
    metrics, site, _, _ = _build_test_artifacts("proj_01", 1)
    service.update_state("proj_01", 1, source_brief_version=1, metric_requirements=metrics)
    service.update_state("proj_01", 2, source_brief_version=1, site_envelope=site)

    v1 = service.get_state_version("proj_01", 1)
    v2 = service.get_state_version("proj_01", 2)
    v3 = service.get_state_version("proj_01", 3)

    assert v1 is not None and v1.state_version == 1
    assert v1.metric_requirements is None

    assert v2 is not None and v2.state_version == 2
    assert v2.metric_requirements == metrics
    assert v2.site_envelope is None

    assert v3 is not None and v3.state_version == 3
    assert v3.metric_requirements == metrics
    assert v3.site_envelope == site


def test_updating_nonexistent_project_raises_not_found(tmp_path: Path) -> None:
    """Updating a project with no initialized state raises PlanInputStateNotFoundError."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    with pytest.raises(PlanInputStateNotFoundError, match="No existing plan input state"):
        service.update_state("proj_missing", expected_state_version=1, source_brief_version=1)


def test_18_list_versions_deterministic_ascending(tmp_path: Path) -> None:
    """list_state_versions returns all versions in ascending numerical order."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    service.initialize_state("proj_01", 1)
    service.update_state("proj_01", 1, source_brief_version=1)
    service.update_state("proj_01", 2, source_brief_version=1)
    service.update_state("proj_01", 3, source_brief_version=1)

    assert service.list_state_versions("proj_01") == [1, 2, 3, 4]


def test_19_existing_stored_version_cannot_be_silently_overwritten(tmp_path: Path) -> None:
    """Direct repository save of an existing version with different data raises error."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    state_v1 = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    repo.save(state_v1)

    # Attempting to save version 1 again with modified source_brief_version
    metrics, _, _, _ = _build_test_artifacts("proj_01", 1)
    state_v1_modified = state_v1.model_copy(update={"metric_requirements": metrics})

    with pytest.raises(PlanInputStateVersionConflictError, match="already exists"):
        repo.save(state_v1_modified)


def test_20_update_can_change_exactly_one_field(tmp_path: Path) -> None:
    """An update can modify a single field while leaving all others untouched."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    metrics, site, _, _ = _build_test_artifacts("proj_01", 1)
    service.initialize_state("proj_01", 1, metric_requirements=metrics, site_envelope=site)

    _, _, fp, _ = _build_test_artifacts("proj_01", 1)
    v2 = service.update_state(
        "proj_01",
        1,
        source_brief_version=1,
        floor_plate_input=fp,  # Only floor_plate_input passed
    )

    assert v2.floor_plate_input == fp
    assert v2.metric_requirements == metrics  # Preserved
    assert v2.site_envelope == site  # Preserved


def test_21_unchanged_preserves_existing_value(tmp_path: Path) -> None:
    """Passing UNCHANGED explicitly preserves existing field values."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    metrics, site, _, _ = _build_test_artifacts("proj_01", 1)
    service.initialize_state("proj_01", 1, metric_requirements=metrics, site_envelope=site)

    v2 = service.update_state(
        "proj_01",
        1,
        source_brief_version=1,
        metric_requirements=UNCHANGED,
        site_envelope=UNCHANGED,
    )

    assert v2.metric_requirements == metrics
    assert v2.site_envelope == site


def test_22_explicit_none_clears_an_existing_optional_value(tmp_path: Path) -> None:
    """Explicitly passing None clears an existing populated field."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    metrics, site, _, _ = _build_test_artifacts("proj_01", 1)
    service.initialize_state("proj_01", 1, metric_requirements=metrics, site_envelope=site)

    v2 = service.update_state(
        "proj_01",
        1,
        source_brief_version=1,
        metric_requirements=None,  # Explicitly cleared
        site_envelope=UNCHANGED,
    )

    assert v2.metric_requirements is None
    assert v2.site_envelope == site


def test_23_failed_validation_does_not_persist_a_new_version(tmp_path: Path) -> None:
    """If in-memory validation fails, no new version file is written to disk."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    service = PlanInputStateService(repository=repo)

    service.initialize_state("proj_01", 1)
    mismatched_metrics, _, _, _ = _build_test_artifacts("proj_other", 1)

    with pytest.raises(PlanInputStateProjectMismatchError):
        service.update_state(
            "proj_01",
            1,
            source_brief_version=1,
            metric_requirements=mismatched_metrics,
        )

    # Disk state must remain at version 1
    assert service.list_state_versions("proj_01") == [1]
    latest = service.get_latest_state("proj_01")
    assert latest is not None and latest.state_version == 1


# ---------------------------------------------------------------------------
# Test Cases 24-30: Persistence, Serialization, Forbidden Fields
# ---------------------------------------------------------------------------


def test_24_json_round_trip_exact_model_equality(tmp_path: Path) -> None:
    """Complete JSON persistence round-trip yields an identical Pydantic model."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    metrics, site, fp, cfg = _build_test_artifacts("proj_01", 2)
    original_state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=2,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )

    repo.save(original_state)
    loaded_latest = repo.get_latest("proj_01")
    loaded_v1 = repo.get_version("proj_01", 1)

    assert loaded_latest == original_state
    assert loaded_v1 == original_state


def test_25_malformed_persisted_json_produces_safe_persistence_error(tmp_path: Path) -> None:
    """Corrupted JSON files raise PlanInputStatePersistenceError."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    repo.save(state)

    # Corrupt version file
    version_file = tmp_path / "projects" / "proj_01" / "plan_input" / "versions" / "000001.json"
    version_file.write_text("{corrupt: json content", encoding="utf-8")

    with pytest.raises(PlanInputStatePersistenceError, match="Failed to read plan input state"):
        repo.get_version("proj_01", 1)


def test_26_unknown_schema_version_rejected(tmp_path: Path) -> None:
    """JSON with unrecognized schema_version raises PlanInputStatePersistenceError."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
    )
    repo.save(state)

    version_file = tmp_path / "projects" / "proj_01" / "plan_input" / "versions" / "000001.json"
    data = json.loads(version_file.read_text(encoding="utf-8"))
    data["schema_version"] = "unknown_plan_input.v99"
    version_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(PlanInputStatePersistenceError):
        repo.get_version("proj_01", 1)


def test_27_no_solver_directive_set_field_exists() -> None:
    """SolverDirectiveSet is a derived pipeline artifact and must not be a field."""
    assert "solver_directive_set" not in AuthoritativePlanInputState.model_fields
    assert "directive_set" not in AuthoritativePlanInputState.model_fields

    with pytest.raises(ValidationError, match="extra_forbidden"):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
            directive_set={"mock": "data"},  # type: ignore[call-arg]
        )


def test_28_no_layout_solver_input_set_field_exists() -> None:
    """LayoutSolverInputSet is a derived solver artifact and must not be a field."""
    assert "solver_input" not in AuthoritativePlanInputState.model_fields
    assert "layout_solver_input_set" not in AuthoritativePlanInputState.model_fields

    with pytest.raises(ValidationError, match="extra_forbidden"):
        AuthoritativePlanInputState(
            project_id="proj_01",
            state_version=1,
            source_brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
            solver_input={"mock": "data"},  # type: ignore[call-arg]
        )


def test_29_no_room_geometry_solution_or_geometry_output_exists() -> None:
    """RoomGeometrySolution and SvgPlanDocument are engine outputs, not plan input state."""
    fields = AuthoritativePlanInputState.model_fields
    assert "solution" not in fields
    assert "room_geometry_solution" not in fields
    assert "document" not in fields
    assert "svg_document" not in fields
    assert "render_config" not in fields


def test_30_deterministic_serialization(tmp_path: Path) -> None:
    """JSON serialization produces identical byte output with sorted keys and compact formatting."""
    repo = JSONPlanInputStateRepository(root_dir=tmp_path)
    metrics, site, fp, cfg = _build_test_artifacts("proj_01", 1)
    state = AuthoritativePlanInputState(
        project_id="proj_01",
        state_version=1,
        source_brief_version=1,
        created_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC),
        metric_requirements=metrics,
        site_envelope=site,
        floor_plate_input=fp,
        solver_config=cfg,
    )

    repo.save(state)
    version_file = tmp_path / "projects" / "proj_01" / "plan_input" / "versions" / "000001.json"
    content_1 = version_file.read_text(encoding="utf-8")

    # Serialize again and compare string content
    serialized_2 = repo._canonical_json(state.model_dump(mode="json"))
    assert content_1 == serialized_2
