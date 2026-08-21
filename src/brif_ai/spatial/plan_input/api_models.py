"""API request models for Authoritative Plan Input State V0."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from brif_ai.spatial.floor_plate.models import FloorPlateInput
from brif_ai.spatial.metrics.models import MetricSpatialRequirements
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.models import SiteBuildableEnvelope


class PlanInputStateInitializeRequest(BaseModel):
    """Request payload for initializing AuthoritativePlanInputState (version 1).

    All spatial input artifacts are optional. Server controls project_id, state_version,
    source_brief_version, and created_at.
    """

    model_config = ConfigDict(extra="forbid")

    metric_requirements: MetricSpatialRequirements | None = None
    site_envelope: SiteBuildableEnvelope | None = None
    floor_plate_input: FloorPlateInput | None = None
    solver_config: RoomGeometrySolverConfig | None = None


class PlanInputStateUpdateRequest(BaseModel):
    """Request payload for updating AuthoritativePlanInputState with optimistic concurrency.

    Distinguishes omitted fields (preserve existing) from explicit null (clear to None)
    via model_fields_set.
    """

    model_config = ConfigDict(extra="forbid")

    expected_state_version: int = Field(ge=1)
    metric_requirements: MetricSpatialRequirements | None = None
    site_envelope: SiteBuildableEnvelope | None = None
    floor_plate_input: FloorPlateInput | None = None
    solver_config: RoomGeometrySolverConfig | None = None
