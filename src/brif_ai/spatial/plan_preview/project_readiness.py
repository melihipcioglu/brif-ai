"""Authoritative Project-Scoped Plan Preview Readiness Orchestration V0."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from brif_ai.brief.persistence import (
    BriefPersistenceError,
    BriefRepository,
    InvalidProjectIdError,
    JSONBriefRepository,
)
from brif_ai.brief.service import PersistentBriefService
from brif_ai.core.models.common import ObjectId
from brif_ai.spatial.errors import SpatialGraphError
from brif_ai.spatial.layout.compiler import LayoutProblemCompiler
from brif_ai.spatial.layout.errors import LayoutProblemError
from brif_ai.spatial.persistence import (
    JSONSpatialRelationshipRepository,
    SpatialGraphPersistenceError,
    SpatialRelationshipRepository,
)
from brif_ai.spatial.plan_input import (
    JSONPlanInputStateRepository,
    PlanInputStatePersistenceError,
    PlanInputStateRepository,
    PlanInputStateService,
)
from brif_ai.spatial.plan_preview.readiness import (
    PlanPreviewPreparationService,
    PlanPreviewReadinessResult,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.errors import (
    BriefNotReadyError,
    SpatialProgramError,
)
from brif_ai.spatial.service import PersistentSpatialService
from brif_ai.spatial.solver_policy.compiler import SolverPolicyCompiler
from brif_ai.spatial.solver_policy.errors import SolverPolicyError


class ProjectPlanPreviewBlockerCode(StrEnum):
    """Stable machine-readable reasons why a project cannot prepare a plan preview."""

    BRIEF_MISSING = "BRIEF_MISSING"
    SPATIAL_GRAPH_MISSING = "SPATIAL_GRAPH_MISSING"
    PLAN_INPUT_STATE_MISSING = "PLAN_INPUT_STATE_MISSING"
    SPATIAL_GRAPH_STALE = "SPATIAL_GRAPH_STALE"
    PLAN_INPUT_STATE_STALE = "PLAN_INPUT_STATE_STALE"
    BRIEF_NOT_READY = "BRIEF_NOT_READY"
    DIRECTIVE_DERIVATION_FAILED = "DIRECTIVE_DERIVATION_FAILED"


_PROJECT_BLOCKER_MESSAGES: dict[ProjectPlanPreviewBlockerCode, str] = {
    ProjectPlanPreviewBlockerCode.BRIEF_MISSING: (
        "Projeye ait doğrulanmış BriefSnapshot bulunamadı."
    ),
    ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_MISSING: (
        "Projeye ait SpatialRelationshipGraph bulunamadı."
    ),
    ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_MISSING: (
        "Projeye ait AuthoritativePlanInputState bulunamadı."
    ),
    ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_STALE: (
        "Mekânsal ilişki grafiği kaynak brief sürümü güncel brief sürümü ile eşleşmiyor."
    ),
    ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_STALE: (
        "Plan girdi durumu kaynak brief sürümü güncel brief sürümü ile eşleşmiyor."
    ),
    ProjectPlanPreviewBlockerCode.BRIEF_NOT_READY: (
        "Brief henüz sonraki aşamaya geçiş için hazır değil."
    ),
    ProjectPlanPreviewBlockerCode.DIRECTIVE_DERIVATION_FAILED: (
        "Mekânsal direktif seti (SolverDirectiveSet) türetilemedi."
    ),
}


def _project_blocker(
    code: ProjectPlanPreviewBlockerCode,
    related_ids: list[str] | None = None,
) -> ProjectPlanPreviewBlocker:
    return ProjectPlanPreviewBlocker(
        code=code,
        message=_PROJECT_BLOCKER_MESSAGES[code],
        related_ids=related_ids or [],
    )


class ProjectPlanPreviewBlocker(BaseModel):
    """One deterministic project-level condition blocking plan preview readiness."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: ProjectPlanPreviewBlockerCode
    message: str
    related_ids: list[str] = Field(default_factory=list)


class ProjectPlanPreviewReadinessResult(BaseModel):
    """Authoritative project-scoped plan preview readiness evaluation result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["project_plan_preview_readiness.v0"] = (
        "project_plan_preview_readiness.v0"
    )
    project_id: ObjectId
    source_brief_version: int | None = None
    plan_input_state_version: int | None = None
    ready_for_preview: bool
    project_blockers: list[ProjectPlanPreviewBlocker] = Field(default_factory=list)
    preparation: PlanPreviewReadinessResult | None = None

    @model_validator(mode="after")
    def validate_invariants(self) -> ProjectPlanPreviewReadinessResult:
        """Enforce strict consistency between ready and blocked states."""
        if self.ready_for_preview:
            if self.project_blockers:
                raise ValueError("ready_for_preview=True must have empty project_blockers.")
            if self.preparation is None:
                raise ValueError(
                    "ready_for_preview=True requires a successful preparation result "
                    "(preparation cannot be None)."
                )
            if not self.preparation.ready_for_preview:
                raise ValueError(
                    "ready_for_preview=True requires a successful preparation result "
                    "(preparation.ready_for_preview=True)."
                )
        else:
            if self.project_blockers:
                if self.preparation is not None:
                    raise ValueError(
                        "Project-blocked state (project_blockers non-empty) "
                        "must have preparation=None."
                    )
            else:
                if self.preparation is None:
                    raise ValueError(
                        "ready_for_preview=False with empty project_blockers "
                        "requires a blocked preparation result."
                    )
                if self.preparation.ready_for_preview:
                    raise ValueError(
                        "ready_for_preview=False cannot have a successful preparation result "
                        "(preparation.ready_for_preview=True)."
                    )
        return self


class ProjectPlanPreviewReadinessService:
    """Deterministic domain service evaluating project-scoped plan preview readiness."""

    def __init__(
        self,
        brief_service: PersistentBriefService | None = None,
        spatial_service: PersistentSpatialService | None = None,
        plan_input_service: PlanInputStateService | None = None,
        *,
        brief_repository: BriefRepository | None = None,
        spatial_repository: SpatialRelationshipRepository | None = None,
        plan_input_repository: PlanInputStateRepository | None = None,
        spatial_program_builder: SpatialProgramBuilder | None = None,
        layout_problem_compiler: LayoutProblemCompiler | None = None,
        solver_policy_compiler: SolverPolicyCompiler | None = None,
        preparation_service: type[PlanPreviewPreparationService] = PlanPreviewPreparationService,
    ) -> None:
        self.brief_service = brief_service or PersistentBriefService(
            brief_repository or JSONBriefRepository()
        )
        self.spatial_service = spatial_service or PersistentSpatialService(
            spatial_repository or JSONSpatialRelationshipRepository()
        )
        self.plan_input_service = plan_input_service or PlanInputStateService(
            plan_input_repository or JSONPlanInputStateRepository()
        )
        self.spatial_program_builder = spatial_program_builder or SpatialProgramBuilder()
        self.layout_problem_compiler = layout_problem_compiler or LayoutProblemCompiler()
        self.solver_policy_compiler = solver_policy_compiler or SolverPolicyCompiler()
        self.preparation_service = preparation_service

    def evaluate(self, project_id: str) -> ProjectPlanPreviewReadinessResult:
        """Evaluate plan preview readiness for a project using authoritative server state."""
        if not isinstance(project_id, str) or not project_id.strip():
            raise InvalidProjectIdError("Project ID must be a non-empty string.")
        try:
            validated_pid = TypeAdapter(ObjectId).validate_python(project_id.strip())
        except Exception as err:
            raise InvalidProjectIdError(f"Invalid project ID format: {project_id!r}") from err

        # 1. Fetch latest authoritative BriefSnapshot
        latest_brief = self.brief_service.get_latest_brief(validated_pid)
        if latest_brief is None:
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=None,
                plan_input_state_version=None,
                ready_for_preview=False,
                project_blockers=[_project_blocker(ProjectPlanPreviewBlockerCode.BRIEF_MISSING)],
                preparation=None,
            )
        if latest_brief.project_id != validated_pid:
            raise BriefPersistenceError(
                f"Persisted brief project_id mismatch: expected '{validated_pid}', "
                f"found '{latest_brief.project_id}'"
            )

        # 2. Fetch latest SpatialRelationshipGraph
        latest_graph = self.spatial_service.get_latest_graph(validated_pid)
        if latest_graph is None:
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                plan_input_state_version=None,
                ready_for_preview=False,
                project_blockers=[
                    _project_blocker(ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_MISSING)
                ],
                preparation=None,
            )
        if latest_graph.project_id != validated_pid:
            raise SpatialGraphPersistenceError(
                f"Persisted spatial relationship graph project_id mismatch: "
                f"expected '{validated_pid}', found '{latest_graph.project_id}'"
            )

        # 3. Fetch latest AuthoritativePlanInputState
        latest_plan_input = self.plan_input_service.get_latest_state(validated_pid)
        if latest_plan_input is None:
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                plan_input_state_version=None,
                ready_for_preview=False,
                project_blockers=[
                    _project_blocker(ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_MISSING)
                ],
                preparation=None,
            )
        if latest_plan_input.project_id != validated_pid:
            raise PlanInputStatePersistenceError(
                f"Persisted plan input state project_id mismatch: "
                f"expected '{validated_pid}', found '{latest_plan_input.project_id}'"
            )

        # 4. Source version consistency checks
        if latest_graph.source_brief_version != latest_brief.brief_version:
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                plan_input_state_version=latest_plan_input.state_version,
                ready_for_preview=False,
                project_blockers=[
                    _project_blocker(
                        ProjectPlanPreviewBlockerCode.SPATIAL_GRAPH_STALE,
                        related_ids=[
                            f"graph_source_brief_version:{latest_graph.source_brief_version}",
                            f"brief_version:{latest_brief.brief_version}",
                        ],
                    )
                ],
                preparation=None,
            )

        if latest_plan_input.source_brief_version != latest_brief.brief_version:
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                plan_input_state_version=latest_plan_input.state_version,
                ready_for_preview=False,
                project_blockers=[
                    _project_blocker(
                        ProjectPlanPreviewBlockerCode.PLAN_INPUT_STATE_STALE,
                        related_ids=[
                            f"plan_input_source_brief_version:{latest_plan_input.source_brief_version}",
                            f"brief_version:{latest_brief.brief_version}",
                        ],
                    )
                ],
                preparation=None,
            )

        # 5. Deterministic derivation pipeline
        try:
            program = self.spatial_program_builder.build(latest_brief, latest_graph)
            problem = self.layout_problem_compiler.compile(program)
            directive_set = self.solver_policy_compiler.compile(problem)
        except BriefNotReadyError as err:
            related: list[str] = []
            if hasattr(err, "readiness_result") and getattr(err.readiness_result, "blockers", None):
                related = [b.code.value for b in err.readiness_result.blockers]
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                plan_input_state_version=latest_plan_input.state_version,
                ready_for_preview=False,
                project_blockers=[
                    _project_blocker(
                        ProjectPlanPreviewBlockerCode.BRIEF_NOT_READY,
                        related_ids=related,
                    )
                ],
                preparation=None,
            )
        except (
            SpatialProgramError,
            LayoutProblemError,
            SolverPolicyError,
            SpatialGraphError,
        ) as err:
            return ProjectPlanPreviewReadinessResult(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                plan_input_state_version=latest_plan_input.state_version,
                ready_for_preview=False,
                project_blockers=[
                    _project_blocker(
                        ProjectPlanPreviewBlockerCode.DIRECTIVE_DERIVATION_FAILED,
                        related_ids=[str(err)],
                    )
                ],
                preparation=None,
            )

        # 6. Evaluate preparation via existing PlanPreviewPreparationService
        prep_result = self.preparation_service.prepare(
            directive_set=directive_set,
            metric_requirements=latest_plan_input.metric_requirements,
            site_envelope=latest_plan_input.site_envelope,
            floor_plate_input=latest_plan_input.floor_plate_input,
            solver_config=latest_plan_input.solver_config,
        )

        return ProjectPlanPreviewReadinessResult(
            project_id=validated_pid,
            source_brief_version=latest_brief.brief_version,
            plan_input_state_version=latest_plan_input.state_version,
            ready_for_preview=prep_result.ready_for_preview,
            project_blockers=[],
            preparation=prep_result,
        )
