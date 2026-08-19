"""Thin application service orchestrating RoomGeometrySolver and SvgPlanRenderer."""

from __future__ import annotations

from brif_ai.spatial.plan_preview.models import (
    PlanPreviewRequest,
    PlanPreviewResponse,
)
from brif_ai.spatial.room_solver.solver import RoomGeometrySolver
from brif_ai.spatial.svg_plan.renderer import SvgPlanRenderer


class PlanPreviewService:
    """Orchestrates solving and SVG rendering over caller-supplied validated solver artifacts."""

    @classmethod
    def generate(cls, request: PlanPreviewRequest) -> PlanPreviewResponse:
        """Execute deterministic room geometry solver and SVG plan view renderer."""
        solution = RoomGeometrySolver.solve(
            solver_input=request.solver_input,
            floor_plate=request.floor_plate,
            config=request.solver_config,
        )
        document = SvgPlanRenderer.render(
            solver_input=request.solver_input,
            floor_plate=request.floor_plate,
            solution=solution,
            config=request.render_config,
        )
        return PlanPreviewResponse(
            success=True,
            solution=solution,
            document=document,
            error=None,
        )
