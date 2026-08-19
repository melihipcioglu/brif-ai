"""Models and contracts for Plan Preview API V0."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from brif_ai.spatial.floor_plate.models import FloorPlate
from brif_ai.spatial.room_solver.models import (
    RoomGeometrySolution,
    RoomGeometrySolverConfig,
)
from brif_ai.spatial.solver_input.models import LayoutSolverInputSet
from brif_ai.spatial.svg_plan.models import (
    SvgPlanDocument,
    SvgPlanRenderConfig,
)


class PlanPreviewRequest(BaseModel):
    """Request payload containing explicit pre-built spatial artifacts for plan preview."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    solver_input: LayoutSolverInputSet
    floor_plate: FloorPlate
    solver_config: RoomGeometrySolverConfig
    render_config: SvgPlanRenderConfig | None = None


class PlanPreviewResponse(BaseModel):
    """Response envelope returning solved geometry and rendered SVG plan preview."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    solution: RoomGeometrySolution | None = None
    document: SvgPlanDocument | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_state_invariants(self) -> PlanPreviewResponse:
        """Enforce strict mutual exclusion between success and failure states."""
        if self.success:
            if self.solution is None:
                raise ValueError("PlanPreviewResponse with success=True must include solution.")
            if self.document is None:
                raise ValueError("PlanPreviewResponse with success=True must include document.")
            if self.error is not None:
                raise ValueError("PlanPreviewResponse with success=True cannot have error.")
        else:
            if self.solution is not None:
                raise ValueError("PlanPreviewResponse with success=False cannot include solution.")
            if self.document is not None:
                raise ValueError("PlanPreviewResponse with success=False cannot include document.")
            if not self.error or not self.error.strip():
                raise ValueError(
                    "PlanPreviewResponse with success=False must include a non-empty error string."
                )
        return self
