"""Application service orchestrating Authoritative Plan Input State persistence and updates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from brif_ai.spatial.floor_plate.models import FloorPlateInput
from brif_ai.spatial.metrics.models import MetricSpatialRequirements
from brif_ai.spatial.plan_input.errors import (
    PlanInputStateNotFoundError,
    PlanInputStateVersionConflictError,
)
from brif_ai.spatial.plan_input.json_repository import JSONPlanInputStateRepository
from brif_ai.spatial.plan_input.models import AuthoritativePlanInputState
from brif_ai.spatial.plan_input.repository import PlanInputStateRepository
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.models import SiteBuildableEnvelope


class _UnchangedSentinel:
    """Sentinel indicating that an existing field value should be preserved during update."""

    def __repr__(self) -> str:
        return "UNCHANGED"


UNCHANGED: Final[_UnchangedSentinel] = _UnchangedSentinel()


class PlanInputStateService:
    """Deterministic domain service managing AuthoritativePlanInputState lifecycle."""

    def __init__(self, repository: PlanInputStateRepository | None = None) -> None:
        self.repository = repository or JSONPlanInputStateRepository()

    def get_latest_state(self, project_id: str) -> AuthoritativePlanInputState | None:
        """Retrieve the latest plan input state for project_id or None if not found."""
        return self.repository.get_latest(project_id)

    def get_state_version(
        self, project_id: str, state_version: int
    ) -> AuthoritativePlanInputState | None:
        """Retrieve a specific state_version plan input state for project_id or None."""
        return self.repository.get_version(project_id, state_version)

    def list_state_versions(self, project_id: str) -> list[int]:
        """List all available state_version numbers for project_id in ascending order."""
        return self.repository.list_versions(project_id)

    def initialize_state(
        self,
        project_id: str,
        source_brief_version: int,
        *,
        metric_requirements: MetricSpatialRequirements | None = None,
        site_envelope: SiteBuildableEnvelope | None = None,
        floor_plate_input: FloorPlateInput | None = None,
        solver_config: RoomGeometrySolverConfig | None = None,
        created_at: datetime | None = None,
    ) -> AuthoritativePlanInputState:
        """Initialize state_version=1 for a project."""
        existing = self.repository.get_latest(project_id)
        if existing is not None:
            raise PlanInputStateVersionConflictError(
                f"Plan input state for project '{project_id}' is already initialized "
                f"(latest version {existing.state_version})."
            )

        ts = created_at if created_at is not None else datetime.now(UTC)

        state = AuthoritativePlanInputState(
            schema_version="authoritative_plan_input_state.v0",
            project_id=project_id,
            state_version=1,
            source_brief_version=source_brief_version,
            created_at=ts,
            metric_requirements=metric_requirements,
            site_envelope=site_envelope,
            floor_plate_input=floor_plate_input,
            solver_config=solver_config,
        )

        return self.repository.save(state)

    def update_state(
        self,
        project_id: str,
        expected_state_version: int,
        *,
        source_brief_version: int,
        metric_requirements: (MetricSpatialRequirements | None | _UnchangedSentinel) = UNCHANGED,
        site_envelope: SiteBuildableEnvelope | None | _UnchangedSentinel = UNCHANGED,
        floor_plate_input: FloorPlateInput | None | _UnchangedSentinel = UNCHANGED,
        solver_config: (RoomGeometrySolverConfig | None | _UnchangedSentinel) = UNCHANGED,
        created_at: datetime | None = None,
    ) -> AuthoritativePlanInputState:
        """Atomically advance the plan input state to state_version = expected + 1.

        Validates current version, merges unchanged/updated fields, constructs a new
        immutable AuthoritativePlanInputState, validates all invariants, and persists.
        """
        current_state = self.repository.get_latest(project_id)
        if current_state is None:
            raise PlanInputStateNotFoundError(
                f"No existing plan input state found for project '{project_id}'."
            )

        if current_state.state_version != expected_state_version:
            raise PlanInputStateVersionConflictError(
                f"Stale state version: expected {expected_state_version}, "
                f"but latest state version is {current_state.state_version}."
            )

        resolved_metrics = (
            current_state.metric_requirements
            if isinstance(metric_requirements, _UnchangedSentinel)
            else metric_requirements
        )
        resolved_site = (
            current_state.site_envelope
            if isinstance(site_envelope, _UnchangedSentinel)
            else site_envelope
        )
        resolved_fp = (
            current_state.floor_plate_input
            if isinstance(floor_plate_input, _UnchangedSentinel)
            else floor_plate_input
        )
        resolved_solver_cfg = (
            current_state.solver_config
            if isinstance(solver_config, _UnchangedSentinel)
            else solver_config
        )

        ts = created_at if created_at is not None else datetime.now(UTC)

        new_state = AuthoritativePlanInputState(
            schema_version="authoritative_plan_input_state.v0",
            project_id=project_id,
            state_version=current_state.state_version + 1,
            source_brief_version=source_brief_version,
            created_at=ts,
            metric_requirements=resolved_metrics,
            site_envelope=resolved_site,
            floor_plate_input=resolved_fp,
            solver_config=resolved_solver_cfg,
        )

        return self.repository.save(new_state)
