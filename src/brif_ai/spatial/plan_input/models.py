"""Authoritative Plan Input State V0 data contract for BRIF.AI."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import ObjectId
from brif_ai.spatial.floor_plate.models import FloorPlateInput
from brif_ai.spatial.metrics.models import MetricSpatialRequirements
from brif_ai.spatial.plan_input.errors import (
    PlanInputStateBriefVersionMismatchError,
    PlanInputStateProjectMismatchError,
)
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.models import SiteBuildableEnvelope


class AuthoritativePlanInputState(BaseModel):
    """Immutable authoritative plan input state container for a specific project version.

    Persists explicit, non-derived spatial artifacts that feed into the spatial engine:
    - MetricSpatialRequirements
    - SiteBuildableEnvelope
    - FloorPlateInput
    - RoomGeometrySolverConfig

    Derived contracts (e.g. SolverDirectiveSet, LayoutSolverInputSet) and presentational
    configurations (e.g. SvgPlanRenderConfig) are intentionally excluded.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["authoritative_plan_input_state.v0"] = (
        "authoritative_plan_input_state.v0"
    )
    project_id: ObjectId
    state_version: int = Field(ge=1)
    source_brief_version: int = Field(ge=1)
    created_at: datetime
    metric_requirements: MetricSpatialRequirements | None = None
    site_envelope: SiteBuildableEnvelope | None = None
    floor_plate_input: FloorPlateInput | None = None
    solver_config: RoomGeometrySolverConfig | None = None

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        """Enforce strict timezone-aware UTC datetime representation."""
        if not isinstance(value, datetime):
            raise ValueError("created_at must be a datetime object.")
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError("created_at must be a timezone-aware datetime.")
        if offset != timedelta(0):
            raise ValueError("created_at must use UTC offset (zero offset).")
        return value

    @model_validator(mode="after")
    def validate_cross_contract_invariants(self) -> AuthoritativePlanInputState:
        """Validate strict cross-contract project_id and source_brief_version consistency."""
        if self.metric_requirements is not None:
            if self.metric_requirements.project_id != self.project_id:
                raise PlanInputStateProjectMismatchError(
                    f"MetricSpatialRequirements project_id "
                    f"'{self.metric_requirements.project_id}' does not match "
                    f"state project_id '{self.project_id}'."
                )
            if self.metric_requirements.source_brief_version != self.source_brief_version:
                raise PlanInputStateBriefVersionMismatchError(
                    f"MetricSpatialRequirements source_brief_version "
                    f"{self.metric_requirements.source_brief_version} does not match "
                    f"state source_brief_version {self.source_brief_version}."
                )

        if self.site_envelope is not None:
            if self.site_envelope.project_id != self.project_id:
                raise PlanInputStateProjectMismatchError(
                    f"SiteBuildableEnvelope project_id "
                    f"'{self.site_envelope.project_id}' does not match "
                    f"state project_id '{self.project_id}'."
                )
            if self.site_envelope.source_brief_version != self.source_brief_version:
                raise PlanInputStateBriefVersionMismatchError(
                    f"SiteBuildableEnvelope source_brief_version "
                    f"{self.site_envelope.source_brief_version} does not match "
                    f"state source_brief_version {self.source_brief_version}."
                )

        return self
