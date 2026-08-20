"""Deterministic preparation and readiness evaluation for Plan Preview V0."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brif_ai.spatial.errors import SpatialGraphError
from brif_ai.spatial.floor_plate.builder import FloorPlateBuilder
from brif_ai.spatial.floor_plate.errors import FloorPlateError
from brif_ai.spatial.floor_plate.models import FloorPlateInput
from brif_ai.spatial.metrics.models import MetricSpatialRequirements
from brif_ai.spatial.plan_preview.models import PlanPreviewRequest
from brif_ai.spatial.room_solver.models import RoomGeometrySolverConfig
from brif_ai.spatial.site.models import SiteBuildableEnvelope
from brif_ai.spatial.solver_input.assembler import LayoutSolverInputAssembler
from brif_ai.spatial.solver_input.errors import SolverInputError
from brif_ai.spatial.solver_policy.models import SolverDirectiveSet
from brif_ai.spatial.svg_plan.models import SvgPlanRenderConfig


class PlanPreviewReadinessBlockerCode(StrEnum):
    """Stable machine-readable reasons why a plan preview request cannot be prepared."""

    DIRECTIVE_SET_MISSING = "DIRECTIVE_SET_MISSING"
    METRIC_REQUIREMENTS_MISSING = "METRIC_REQUIREMENTS_MISSING"
    SITE_ENVELOPE_MISSING = "SITE_ENVELOPE_MISSING"
    FLOOR_PLATE_INPUT_MISSING = "FLOOR_PLATE_INPUT_MISSING"
    SOLVER_CONFIG_MISSING = "SOLVER_CONFIG_MISSING"
    SOLVER_INPUT_INVALID = "SOLVER_INPUT_INVALID"
    FLOOR_PLATE_INVALID = "FLOOR_PLATE_INVALID"


_BLOCKER_MESSAGES: dict[PlanPreviewReadinessBlockerCode, str] = {
    PlanPreviewReadinessBlockerCode.DIRECTIVE_SET_MISSING: (
        "Mekânsal direktif seti (SolverDirectiveSet) eksik."
    ),
    PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING: (
        "Metrik mekânsal gereksinimler (MetricSpatialRequirements) eksik."
    ),
    PlanPreviewReadinessBlockerCode.SITE_ENVELOPE_MISSING: (
        "Parsel yapılaşma zarfı (SiteBuildableEnvelope) eksik."
    ),
    PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING: (
        "Taban oturumu girdisi (FloorPlateInput) eksik."
    ),
    PlanPreviewReadinessBlockerCode.SOLVER_CONFIG_MISSING: (
        "Mekân geometri çözücü yapılandırması (RoomGeometrySolverConfig) eksik."
    ),
    PlanPreviewReadinessBlockerCode.SOLVER_INPUT_INVALID: (
        "Yerleşim çözücü girdi seti doğrulanamadı veya kaynaklar birbiriyle uyuşmuyor."
    ),
    PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INVALID: (
        "Taban oturumu doğrulanamadı veya yapılaşma zarfı sınırları dışında."
    ),
}


def _blocker(
    code: PlanPreviewReadinessBlockerCode,
    related_ids: list[str] | None = None,
) -> PlanPreviewReadinessBlocker:
    return PlanPreviewReadinessBlocker(
        code=code,
        message=_BLOCKER_MESSAGES[code],
        related_ids=related_ids or [],
    )


class PlanPreviewReadinessBlocker(BaseModel):
    """One deterministic condition blocking plan preview request preparation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: PlanPreviewReadinessBlockerCode
    message: str
    related_ids: list[str] = Field(default_factory=list)


class PlanPreviewReadinessResult(BaseModel):
    """Complete deterministic readiness evaluation and optional prepared request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ready_for_preview: bool
    blockers: list[PlanPreviewReadinessBlocker] = Field(default_factory=list)
    request: PlanPreviewRequest | None = None

    @model_validator(mode="after")
    def validate_state_invariants(self) -> PlanPreviewReadinessResult:
        """Enforce strict mutual exclusion between ready and blocked states."""
        if self.ready_for_preview:
            if self.blockers:
                raise ValueError(
                    "PlanPreviewReadinessResult with ready_for_preview=True "
                    "must have empty blockers."
                )
            if self.request is None:
                raise ValueError(
                    "PlanPreviewReadinessResult with ready_for_preview=True must include request."
                )
        else:
            if not self.blockers:
                raise ValueError(
                    "PlanPreviewReadinessResult with ready_for_preview=False "
                    "must include at least one blocker."
                )
            if self.request is not None:
                raise ValueError(
                    "PlanPreviewReadinessResult with ready_for_preview=False "
                    "cannot include request."
                )
        return self


class PlanPreviewPreparationService:
    """Deterministic service preparing PlanPreviewRequest from authoritative artifacts."""

    @classmethod
    def prepare(
        cls,
        directive_set: SolverDirectiveSet | None,
        metric_requirements: MetricSpatialRequirements | None,
        site_envelope: SiteBuildableEnvelope | None,
        floor_plate_input: FloorPlateInput | None,
        solver_config: RoomGeometrySolverConfig | None,
        render_config: SvgPlanRenderConfig | None = None,
        *,
        floor_plate_builder: FloorPlateBuilder | None = None,
    ) -> PlanPreviewReadinessResult:
        """Evaluate readiness and prepare PlanPreviewRequest if all artifacts are valid."""
        missing_blockers: list[PlanPreviewReadinessBlocker] = []

        # 1. Canonical missing blocker check
        if directive_set is None:
            missing_blockers.append(_blocker(PlanPreviewReadinessBlockerCode.DIRECTIVE_SET_MISSING))
        if metric_requirements is None:
            missing_blockers.append(
                _blocker(PlanPreviewReadinessBlockerCode.METRIC_REQUIREMENTS_MISSING)
            )
        if site_envelope is None:
            missing_blockers.append(_blocker(PlanPreviewReadinessBlockerCode.SITE_ENVELOPE_MISSING))
        if floor_plate_input is None:
            missing_blockers.append(
                _blocker(PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INPUT_MISSING)
            )
        if solver_config is None:
            missing_blockers.append(_blocker(PlanPreviewReadinessBlockerCode.SOLVER_CONFIG_MISSING))

        if missing_blockers:
            return PlanPreviewReadinessResult(
                ready_for_preview=False,
                blockers=missing_blockers,
                request=None,
            )

        assert directive_set is not None
        assert metric_requirements is not None
        assert site_envelope is not None
        assert floor_plate_input is not None
        assert solver_config is not None

        # 2. Assemble solver input
        try:
            solver_input = LayoutSolverInputAssembler.assemble(
                directive_set=directive_set,
                metric_requirements=metric_requirements,
                site_envelope=site_envelope,
            )
        except (SolverInputError, SpatialGraphError, ValueError):
            return PlanPreviewReadinessResult(
                ready_for_preview=False,
                blockers=[_blocker(PlanPreviewReadinessBlockerCode.SOLVER_INPUT_INVALID)],
                request=None,
            )

        # 3. Build floor plate
        builder = floor_plate_builder or FloorPlateBuilder()
        try:
            floor_plate = builder.build(
                solver_input=solver_input,
                floor_plate=floor_plate_input,
            )
        except (FloorPlateError, SpatialGraphError, ValueError):
            return PlanPreviewReadinessResult(
                ready_for_preview=False,
                blockers=[_blocker(PlanPreviewReadinessBlockerCode.FLOOR_PLATE_INVALID)],
                request=None,
            )

        # 4. Construct PlanPreviewRequest
        request = PlanPreviewRequest(
            solver_input=solver_input,
            floor_plate=floor_plate,
            solver_config=solver_config,
            render_config=render_config,
        )

        return PlanPreviewReadinessResult(
            ready_for_preview=True,
            blockers=[],
            request=request,
        )
