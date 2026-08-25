"""FastAPI boundary for provider-agnostic local LLM conversations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

from brif_ai.brief.models.common import (
    Priority,
)
from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.mutation import (
    NoActiveElicitationQuestionError,
    append_chat_evidence_and_resolve_spatial_question,
)
from brif_ai.brief.persistence import (
    BriefNotFoundError,
    BriefPersistenceError,
    BriefRepository,
    BriefVersionConflictError,
    InvalidProjectIdError,
    JSONBriefRepository,
)
from brif_ai.brief.service import PersistentBriefService
from brif_ai.core.models.common import ObjectId
from brif_ai.llm.contracts import (
    BriefMutationApprovalRecord,
    BriefMutationApprovalRequest,
    BriefMutationApprovalResponse,
    ConversationInterpretationResponse,
    ConversationRequest,
    ExistingMetricRequirementContext,
    FloorPlateApprovalRecord,
    FloorPlateApprovalRequest,
    FloorPlateApprovalResponse,
    HealthResponse,
    LocalModelInfo,
    MetricConversationContext,
    MetricRequirementApprovalRecord,
    MetricRequirementApprovalRequest,
    MetricRequirementApprovalResponse,
    SiteGeometryApprovalRecord,
    SiteGeometryApprovalRequest,
    SiteGeometryApprovalResponse,
    SpaceMetricContext,
    SpatialRelationshipApprovalRecord,
    SpatialRelationshipApprovalRequest,
    SpatialRelationshipApprovalResponse,
)
from brif_ai.llm.ollama_provider import OllamaProvider
from brif_ai.llm.policy_validator import PolicyValidationError
from brif_ai.llm.provider import (
    LocalLLMProvider,
    ModelNotAvailableError,
    ModelNotSelectedError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.service import LocalLLMConversationService, StaleContextError
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.floor_plate import (
    FloorPlateInput,
    FloorPlateOutsideBuildableEnvelopeError,
    FloorPlateSourceBindingError,
    generate_floor_plate_id,
    validate_floor_plate_inside_buildable_envelope,
    validate_floor_plate_source_binding,
)
from brif_ai.spatial.metrics.builder import MetricSpatialRequirementsBuilder
from brif_ai.spatial.metrics.errors import (
    DuplicateMetricRequirementError,
    MetricInvalidEvidenceError,
    MetricInvalidValueError,
    MetricNonexistentSpaceError,
    MetricRangeConflictError,
    MetricUnitMismatchError,
)
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementInput,
)
from brif_ai.spatial.metrics.source_binding import (
    MetricSourceBindingError,
    validate_metric_source_binding,
)
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipGraph,
    SpatialRelationshipInput,
    project_space_requests_to_spatial_nodes,
)
from brif_ai.spatial.persistence import (
    JSONSpatialRelationshipRepository,
    SpatialGraphPersistenceError,
    SpatialRelationshipRepository,
)
from brif_ai.spatial.plan_input import (
    UNCHANGED,
    AuthoritativePlanInputState,
    JSONPlanInputStateRepository,
    PlanInputApprovalEvidencePersistenceError,
    PlanInputApprovalEvidenceRepository,
    PlanInputStateBriefVersionMismatchError,
    PlanInputStateInitializeRequest,
    PlanInputStateNotFoundError,
    PlanInputStatePersistenceError,
    PlanInputStateProjectMismatchError,
    PlanInputStateRepository,
    PlanInputStateService,
    PlanInputStateUpdateRequest,
    PlanInputStateValidationError,
    PlanInputStateVersionConflictError,
)
from brif_ai.spatial.plan_preview import (
    PlanPreviewRequest,
    PlanPreviewResponse,
    PlanPreviewService,
    ProjectPlanPreviewReadinessResult,
    ProjectPlanPreviewReadinessService,
)
from brif_ai.spatial.program.builder import SpatialProgramBuilder
from brif_ai.spatial.program.errors import (
    BriefNotReadyError,
    SpatialProgramConflictBlockerError,
    SpatialProgramMissingInputError,
    SpatialProgramNodeMismatchError,
    SpatialProgramProjectMismatchError,
    SpatialProgramVersionMismatchError,
)
from brif_ai.spatial.room_solver import (
    RoomGeometryEngineError,
    RoomGeometryGridAlignmentError,
    RoomGeometryInfeasibleError,
    RoomGeometryInputMismatchError,
    RoomGeometryUnderconstrainedSpaceError,
    RoomGeometryUnsupportedDirectiveError,
    RoomGeometryUnsupportedFloorPlateError,
    RoomGeometryUnsupportedMetricError,
    RoomGeometryUnsupportedOptionalSpaceError,
)
from brif_ai.spatial.service import PersistentSpatialService
from brif_ai.spatial.site.approval_evidence import (
    SiteApprovalEvidenceRepository,
    SiteEvidencePersistenceError,
)
from brif_ai.spatial.site.builder import SiteBuildableEnvelopeBuilder
from brif_ai.spatial.site.errors import (
    SiteEnvelopeOutsideParcelError,
    SiteEnvelopeWithoutParcelError,
    SiteInvalidCoordinateError,
    SitePolygonDegenerateError,
    SitePolygonSelfIntersectionError,
)
from brif_ai.spatial.site.geometry import validate_polygon_geometry
from brif_ai.spatial.site.models import SiteGeometryRole, SitePolygonInput
from brif_ai.spatial.site.source_binding import (
    SiteSourceBindingError,
    validate_site_geometry_source_binding,
)
from brif_ai.spatial.svg_plan import (
    SvgPlanInputMismatchError,
    SvgPlanInvalidGeometryError,
    SvgPlanRenderError,
    SvgPlanUnknownSpaceError,
)

ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
UI_ORIGIN_ENV = "BRIF_AI_UI_ORIGIN"


def resolve_allowed_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    """Return fixed development origins plus one validated loopback UI port."""

    values = os.environ if environ is None else environ
    configured_origin = values.get(UI_ORIGIN_ENV, "").strip()
    origins = list(ALLOWED_ORIGINS)
    if not configured_origin:
        return origins

    try:
        parsed = urlsplit(configured_origin)
        port = parsed.port
    except ValueError as error:
        raise ValueError(
            f"{UI_ORIGIN_ENV} must be an HTTP origin on localhost or 127.0.0.1"
        ) from error

    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or port is None
        or not 1 <= port <= 65535
    ):
        raise ValueError(f"{UI_ORIGIN_ENV} must be an HTTP origin on localhost or 127.0.0.1")

    for host in ("127.0.0.1", "localhost"):
        origin = f"http://{host}:{port}"
        if origin not in origins:
            origins.append(origin)
    return origins


def _validate_project_id_param(project_id: str) -> str:
    """Validate project ID parameter strictly against ObjectId contract."""
    if not isinstance(project_id, str) or not project_id.strip():
        raise InvalidProjectIdError("Project ID must be a non-empty string.")
    try:
        return str(TypeAdapter(ObjectId).validate_python(project_id.strip()))
    except Exception as err:
        raise InvalidProjectIdError(f"Invalid project ID format: {project_id!r}") from err


def build_metric_conversation_context(
    snapshot: BriefSnapshot | None,
    graph: SpatialRelationshipGraph | None,
    plan_input_state: AuthoritativePlanInputState | None,
) -> MetricConversationContext | None:
    """Build server-authoritative metric conversation context from SpatialProgram."""
    if snapshot is None or graph is None:
        return None
    if plan_input_state is not None and (
        plan_input_state.project_id != snapshot.project_id
        or plan_input_state.source_brief_version != snapshot.brief_version
    ):
        return None
    try:
        program = SpatialProgramBuilder().build(snapshot, graph)
    except (
        BriefNotReadyError,
        SpatialProgramConflictBlockerError,
        SpatialProgramMissingInputError,
        SpatialProgramNodeMismatchError,
        SpatialProgramProjectMismatchError,
        SpatialProgramVersionMismatchError,
    ):
        return None

    existing_reqs_by_space: dict[str, list[ExistingMetricRequirementContext]] = {}
    if plan_input_state is not None and plan_input_state.metric_requirements is not None:
        for space_req in plan_input_state.metric_requirements.space_requirements:
            existing_reqs_by_space[space_req.space_id] = [
                ExistingMetricRequirementContext(
                    requirement_type=r.requirement_type,
                    value=r.value,
                    unit=r.unit,
                )
                for r in space_req.requirements
            ]

    spaces_context = [
        SpaceMetricContext(
            space_id=p_space.id,
            display_name=p_space.display_name,
            function=(
                p_space.function.value
                if hasattr(p_space.function, "value")
                else str(p_space.function)
            ),
            existing_requirements=existing_reqs_by_space.get(p_space.id, []),
        )
        for p_space in program.spaces
    ]

    return MetricConversationContext(
        spaces=spaces_context,
        source_brief_version=snapshot.brief_version,
        source_plan_input_state_version=(
            plan_input_state.state_version if plan_input_state is not None else None
        ),
    )


def create_app(
    settings: LocalLLMSettings | None = None,
    provider: LocalLLMProvider | None = None,
    cors_environ: Mapping[str, str] | None = None,
    brief_repository: BriefRepository | None = None,
    spatial_repository: SpatialRelationshipRepository | None = None,
    plan_input_repository: PlanInputStateRepository | None = None,
    plan_input_evidence_repository: PlanInputApprovalEvidenceRepository | None = None,
    site_evidence_repository: SiteApprovalEvidenceRepository | None = None,
) -> FastAPI:
    resolved_settings = settings or LocalLLMSettings.from_env()
    resolved_provider = provider or OllamaProvider(resolved_settings)
    resolved_brief_repo = brief_repository or JSONBriefRepository()
    persistent_brief_service = PersistentBriefService(resolved_brief_repo)
    resolved_spatial_repo = spatial_repository or JSONSpatialRelationshipRepository()
    persistent_spatial_service = PersistentSpatialService(resolved_spatial_repo)
    resolved_plan_input_repo = plan_input_repository or JSONPlanInputStateRepository()
    persistent_plan_input_service = PlanInputStateService(resolved_plan_input_repo)
    persistent_plan_input_evidence_repository = (
        plan_input_evidence_repository
        or PlanInputApprovalEvidenceRepository(
            root_dir=(
                resolved_plan_input_repo.root_dir
                if isinstance(resolved_plan_input_repo, JSONPlanInputStateRepository)
                else None
            )
        )
    )
    persistent_site_evidence_repository = (
        site_evidence_repository or SiteApprovalEvidenceRepository()
    )
    project_readiness_service = ProjectPlanPreviewReadinessService(
        brief_service=persistent_brief_service,
        spatial_service=persistent_spatial_service,
        plan_input_service=persistent_plan_input_service,
    )
    service = LocalLLMConversationService(resolved_settings, resolved_provider)

    application = FastAPI(title="BRIF.AI Local LLM API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolve_allowed_origins(cors_environ),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @application.get("/api/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return await service.health()

    @application.get("/api/v1/llm/models", response_model=list[LocalModelInfo])
    async def list_models() -> Any:
        try:
            return await service.list_models()
        except ProviderTimeoutError as error:
            return JSONResponse(status_code=504, content={"detail": str(error)})
        except ProviderUnavailableError as error:
            return JSONResponse(status_code=503, content={"detail": str(error)})
        except ProviderResponseError as error:
            return JSONResponse(status_code=502, content={"detail": str(error)})

    @application.get("/api/v1/projects/{project_id}/brief", response_model=BriefSnapshot)
    async def get_project_brief(project_id: str) -> Any:
        try:
            snapshot = persistent_brief_service.get_latest_brief(project_id)
            if snapshot is None:
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Project brief for '{project_id}' not found."},
                )
            return snapshot
        except InvalidProjectIdError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except BriefPersistenceError as error:
            return JSONResponse(status_code=500, content={"detail": str(error)})

    @application.get("/api/v1/projects/{project_id}/brief/versions")
    async def list_brief_versions(project_id: str) -> Any:
        try:
            versions = persistent_brief_service.list_brief_versions(project_id)
            return {"project_id": project_id, "versions": versions}
        except InvalidProjectIdError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except BriefPersistenceError as error:
            return JSONResponse(status_code=500, content={"detail": str(error)})

    @application.get(
        "/api/v1/projects/{project_id}/brief/versions/{brief_version}", response_model=BriefSnapshot
    )
    async def get_brief_version(project_id: str, brief_version: int) -> Any:
        try:
            snapshot = persistent_brief_service.get_brief_version(project_id, brief_version)
            if snapshot is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "detail": (
                            f"Brief version {brief_version} for project '{project_id}' not found."
                        )
                    },
                )
            return snapshot
        except InvalidProjectIdError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except BriefPersistenceError as error:
            return JSONResponse(status_code=500, content={"detail": str(error)})

    @application.post(
        "/api/v1/projects/{project_id}/brief/initialize", response_model=BriefSnapshot
    )
    async def initialize_project_brief(project_id: str, snapshot: BriefSnapshot) -> Any:
        try:
            return persistent_brief_service.initialize_brief(project_id, snapshot)
        except InvalidProjectIdError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except ValueError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except BriefVersionConflictError as error:
            return JSONResponse(status_code=409, content={"detail": str(error)})
        except BriefPersistenceError as error:
            return JSONResponse(status_code=500, content={"detail": str(error)})

    @application.post(
        "/api/v1/conversation/interpret",
        response_model=ConversationInterpretationResponse,
    )
    async def interpret(request: ConversationRequest) -> Any:
        try:
            project_id = request.active_context.project_id

            # Step 1: Extract client expected version
            client_expected_version: int | None = None
            if request.brief_snapshot is not None:
                client_expected_version = request.brief_snapshot.brief_version

            # Step 2: Fetch authoritative snapshot from persistence
            authoritative_snapshot = persistent_brief_service.get_latest_brief(project_id)

            # Step 3: No silent initialization — 404 if uninitialized
            if authoritative_snapshot is None:
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Project brief for '{project_id}' not found."},
                )

            # Step 4: Stale context rejection — 409 without calling LLM
            if (
                client_expected_version is not None
                and client_expected_version != authoritative_snapshot.brief_version
            ):
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"Stale brief version: client sent {client_expected_version}, "
                            f"server has {authoritative_snapshot.brief_version}."
                        )
                    },
                )

            # Step 5: Pre-LLM skip command check
            skip_commands = ("geçelim", "bunu geç", "cevaplamak istemiyorum")
            message_lower = request.message.strip().casefold()
            if message_lower in skip_commands:
                # Find active OPEN question with topic_key
                has_active_open = any(
                    oq.status.value == "OPEN" and oq.topic_key
                    for oq in authoritative_snapshot.open_questions
                )
                if has_active_open:
                    new_snapshot = persistent_brief_service.dismiss_active_open_question(
                        project_id=project_id,
                        expected_brief_version=authoritative_snapshot.brief_version,
                    )
                    return ConversationInterpretationResponse(
                        success=True,
                        llm_enabled=resolved_settings.enabled,
                        provider=resolved_settings.provider,
                        model=resolved_settings.model or None,
                        context_fingerprint=request.active_context.context_fingerprint,
                        generation_id=request.active_context.generation_id,
                        result=None,
                        error=None,
                        resulting_brief_snapshot=new_snapshot,
                        authoritative_brief_version=new_snapshot.brief_version,
                    )

            # Step 6: Replace client brief with authoritative snapshot and build metric context
            authoritative_graph = persistent_spatial_service.get_latest_graph(project_id)
            authoritative_plan_input = persistent_plan_input_service.get_latest_state(project_id)
            authoritative_metric_context = build_metric_conversation_context(
                authoritative_snapshot,
                authoritative_graph,
                authoritative_plan_input,
            )
            prepared_request = request.model_copy(
                update={
                    "brief_snapshot": authoritative_snapshot,
                }
            )

            # Step 7: Execute LLM interpretation
            plan_input_version = (
                authoritative_plan_input.state_version
                if authoritative_plan_input is not None
                else None
            )
            interpretation_result = await service.interpret(
                prepared_request,
                metric_context=authoritative_metric_context,
                plan_input_state_version=plan_input_version,
            )

            # Step 8: Post-LLM OpenQuestion persistence
            resulting_snapshot: BriefSnapshot | None = None
            if (
                interpretation_result.result is not None
                and interpretation_result.result.needs_follow_up
                and interpretation_result.result.follow_up_topic is not None
                and interpretation_result.result.follow_up_question is not None
            ):
                try:
                    resulting_snapshot = persistent_brief_service.add_open_question(
                        project_id=project_id,
                        expected_brief_version=authoritative_snapshot.brief_version,
                        question_text=interpretation_result.result.follow_up_question,
                        reason=(
                            f"Elicitation topic: "
                            f"{interpretation_result.result.follow_up_topic.value}"
                        ),
                        topic_key=interpretation_result.result.follow_up_topic.value,
                    )
                except BriefVersionConflictError:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "detail": (
                                "Race condition: brief was modified while LLM was processing. "
                                "Please retry."
                            )
                        },
                    )

            plan_input_version = (
                authoritative_plan_input.state_version
                if authoritative_plan_input is not None
                else None
            )
            return interpretation_result.model_copy(
                update={
                    "resulting_brief_snapshot": resulting_snapshot,
                    "authoritative_brief_version": authoritative_snapshot.brief_version,
                    "authoritative_plan_input_state_version": plan_input_version,
                }
            )
        except ModelNotSelectedError as error:
            return _error_response(request, resolved_settings, str(error), 409)
        except ModelNotAvailableError as error:
            return _error_response(request, resolved_settings, str(error), 409)
        except ProviderTimeoutError as error:
            return _error_response(request, resolved_settings, str(error), 504)
        except ProviderUnavailableError as error:
            return _error_response(request, resolved_settings, str(error), 503)
        except ProviderResponseError as error:
            return _error_response(request, resolved_settings, str(error), 502)
        except PolicyValidationError:
            return _error_response(
                request,
                resolved_settings,
                "Yerel model aktif proje kapsamıyla uyumsuz bir hedef üretti.",
                422,
            )

    @application.post(
        "/api/v1/brief/mutations/approve",
        response_model=BriefMutationApprovalResponse,
    )
    async def approve_brief_mutation(request: BriefMutationApprovalRequest) -> Any:
        try:
            if request.proposal_fingerprint != request.current_fingerprint:
                raise StaleContextError("Farklı bağlama ait öneri onaylanamaz.")
            if request.proposal_generation_id != request.current_generation_id:
                raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

            src_ref = request.source_reference or request.current_fingerprint
            now = datetime.now(UTC)
            new_snapshot = persistent_brief_service.record_brief_mutation_approval(
                current_project_id=request.current_project_id,
                expected_brief_version=request.expected_brief_version,
                proposed_mutation=request.proposed_mutation,
                user_message=request.user_message,
                source_reference=src_ref,
                approved_at=now,
                answers_current_open_question=request.answers_current_open_question,
            )
            record = BriefMutationApprovalRecord(
                mutation_id=request.proposed_mutation.mutation_id,
                proposed_brief_mutation=request.proposed_mutation,
                proposal_status="user_approved",
                approved_at=now,
                context_fingerprint=request.current_fingerprint,
                generation_id=request.current_generation_id,
                resulting_brief_version=new_snapshot.brief_version,
            )
            return BriefMutationApprovalResponse(
                success=True,
                resulting_snapshot=new_snapshot,
                approval_record=record,
                error=None,
            )
        except (BriefVersionConflictError, StaleContextError) as error:
            return JSONResponse(
                status_code=409,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except BriefNotFoundError as error:
            return JSONResponse(
                status_code=404,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except NoActiveElicitationQuestionError as error:
            return JSONResponse(
                status_code=422,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (InvalidProjectIdError, ValueError) as error:
            return JSONResponse(
                status_code=422,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except BriefPersistenceError as error:
            return JSONResponse(
                status_code=500,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=f"Onay işlemi sırasında sunucu hatası oluştu: {error}",
                ).model_dump(mode="json"),
            )

    @application.get(
        "/api/v1/projects/{project_id}/spatial/graph",
        response_model=SpatialRelationshipGraph,
    )
    async def get_project_spatial_graph(project_id: str) -> Any:
        try:
            graph = persistent_spatial_service.get_latest_graph(project_id)
            if graph is None:
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Spatial relationship graph for '{project_id}' not found."},
                )
            return graph
        except (InvalidProjectIdError, SpatialGraphPersistenceError) as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.post(
        "/api/v1/spatial/relationships/approve",
        response_model=SpatialRelationshipApprovalResponse,
    )
    async def approve_spatial_relationship(request: SpatialRelationshipApprovalRequest) -> Any:
        try:
            if request.proposal_fingerprint != request.current_fingerprint:
                raise StaleContextError("Farklı bağlama ait öneri onaylanamaz.")
            if request.proposal_generation_id != request.current_generation_id:
                raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

            # 1. Fetch authoritative persisted BriefSnapshot
            persisted_brief = persistent_brief_service.get_latest_brief(request.current_project_id)
            if persisted_brief is None:
                raise BriefNotFoundError(
                    f"Cannot approve spatial relationship: Project '{request.current_project_id}' "
                    "brief is not initialized."
                )

            if persisted_brief.brief_version != request.expected_brief_version:
                raise BriefVersionConflictError(
                    f"Stale brief approval: Current persisted brief version for "
                    f"'{request.current_project_id}' is {persisted_brief.brief_version}, "
                    f"but client expected version {request.expected_brief_version}."
                )

            # 2. Derive authoritative spatial nodes and validate endpoints
            valid_nodes = project_space_requests_to_spatial_nodes(persisted_brief.space_requests)
            valid_node_ids = {node.id for node in valid_nodes}
            prop = request.proposed_relationship
            if prop.source_space_id not in valid_node_ids:
                raise PolicyValidationError(
                    f"Unknown source space ID {prop.source_space_id!r} in spatial proposal"
                )
            if prop.target_space_id not in valid_node_ids:
                raise PolicyValidationError(
                    f"Unknown target space ID {prop.target_space_id!r} in spatial proposal"
                )
            if prop.source_space_id == prop.target_space_id:
                raise PolicyValidationError(
                    f"Self-relationship not allowed for space {prop.source_space_id!r}"
                )

            # 3. Create or reuse CHAT Evidence in memory (plus resolve open question if requested)
            src_ref = request.source_reference or request.current_fingerprint
            now = datetime.now(UTC)
            resolve_topic = (
                "spatial_relationships" if request.answers_current_open_question else None
            )
            new_snapshot, evidence = append_chat_evidence_and_resolve_spatial_question(
                snapshot=persisted_brief,
                user_message=request.user_message,
                source_reference=src_ref,
                resolve_topic=resolve_topic,
                approved_at=now,
            )

            # 4. Construct SpatialRelationshipInput with USER_CONFIRMED and real evidence ID
            rel_input = SpatialRelationshipInput(
                source_space_id=prop.source_space_id,
                target_space_id=prop.target_space_id,
                relation_type=prop.relation_type,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=prop.priority,
                evidence_ids=[evidence.id],
                rationale=prop.rationale,
                bidirectional=prop.bidirectional,
            )

            # 5. Build resulting SpatialRelationshipGraph in memory using existing graph (or None)
            existing_graph = persistent_spatial_service.get_latest_graph(request.current_project_id)
            is_new_version = (
                existing_graph is None
                or new_snapshot.brief_version != existing_graph.source_brief_version
            )
            new_graph = persistent_spatial_service.build_updated_graph_in_memory(
                snapshot=new_snapshot,
                existing_graph=existing_graph,
                new_relationship=rel_input,
                created_at=now if is_new_version else None,
            )

            # 6. Atomic Persistence: all in-memory validation and building succeeded!
            if new_snapshot.brief_version != persisted_brief.brief_version:
                persistent_brief_service.repository.save(new_snapshot)

            saved_graph = persistent_spatial_service.save_graph(new_graph)

            record = SpatialRelationshipApprovalRecord(
                proposal_status="user_approved",
                approved_at=now,
                context_fingerprint=request.current_fingerprint,
                generation_id=request.current_generation_id,
                proposed_spatial_relationship=request.proposed_relationship,
                resulting_brief_version=new_snapshot.brief_version,
                resulting_evidence_id=evidence.id,
            )

            return SpatialRelationshipApprovalResponse(
                success=True,
                resulting_snapshot=new_snapshot,
                resulting_spatial_graph=saved_graph,
                approval_record=record,
                error=None,
            )
        except (BriefVersionConflictError, StaleContextError) as error:
            return JSONResponse(
                status_code=409,
                content=SpatialRelationshipApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    resulting_spatial_graph=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except BriefNotFoundError as error:
            return JSONResponse(
                status_code=404,
                content=SpatialRelationshipApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    resulting_spatial_graph=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (PolicyValidationError, ValueError, InvalidProjectIdError) as error:
            return JSONResponse(
                status_code=422,
                content=SpatialRelationshipApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    resulting_spatial_graph=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (BriefPersistenceError, SpatialGraphPersistenceError) as error:
            return JSONResponse(
                status_code=500,
                content=SpatialRelationshipApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    resulting_spatial_graph=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content=SpatialRelationshipApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    resulting_spatial_graph=None,
                    approval_record=None,
                    error=f"Mekânsal ilişki onayı sırasında sunucu hatası oluştu: {error}",
                ).model_dump(mode="json"),
            )

    @application.post(
        "/api/v1/plan/preview",
        response_model=PlanPreviewResponse,
    )
    async def preview_plan(request: PlanPreviewRequest) -> Any:
        try:
            return PlanPreviewService.generate(request)
        except (
            RoomGeometryInputMismatchError,
            SvgPlanInputMismatchError,
            SvgPlanUnknownSpaceError,
        ) as error:
            return JSONResponse(
                status_code=409,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            RoomGeometryUnsupportedFloorPlateError,
            RoomGeometryUnsupportedOptionalSpaceError,
            RoomGeometryUnsupportedMetricError,
            RoomGeometryUnsupportedDirectiveError,
            RoomGeometryUnderconstrainedSpaceError,
            RoomGeometryGridAlignmentError,
            RoomGeometryInfeasibleError,
            SvgPlanInvalidGeometryError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except RoomGeometryEngineError as error:
            return JSONResponse(
                status_code=503,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except SvgPlanRenderError as error:
            return JSONResponse(
                status_code=500,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=f"Plan önizlemesi sırasında sunucu hatası oluştu: {error}",
                ).model_dump(mode="json"),
            )

    @application.get(
        "/api/v1/projects/{project_id}/plan/input",
        response_model=AuthoritativePlanInputState,
    )
    async def get_project_plan_input_state(project_id: str) -> Any:
        try:
            validated_pid = _validate_project_id_param(project_id)
            state = persistent_plan_input_service.get_latest_state(validated_pid)
            if state is None:
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Plan input state for project '{project_id}' not found."},
                )
            if state.project_id != validated_pid:
                raise PlanInputStatePersistenceError(
                    f"Persisted plan input state project_id mismatch: expected '{validated_pid}', "
                    f"found '{state.project_id}'"
                )
            return state
        except InvalidProjectIdError as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except PlanInputStatePersistenceError as error:
            return JSONResponse(
                status_code=500,
                content={"detail": str(error)},
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Sunucu hatası: {error}"},
            )

    @application.get(
        "/api/v1/projects/{project_id}/plan/input/versions/{state_version}",
        response_model=AuthoritativePlanInputState,
    )
    async def get_project_plan_input_state_version(
        project_id: str,
        state_version: int,
    ) -> Any:
        try:
            validated_pid = _validate_project_id_param(project_id)
            if state_version < 1:
                return JSONResponse(
                    status_code=422,
                    content={"detail": f"Invalid state version {state_version}: must be >= 1."},
                )
            state = persistent_plan_input_service.get_state_version(validated_pid, state_version)
            if state is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "detail": (
                            f"Plan input state version {state_version} "
                            f"for project '{project_id}' not found."
                        )
                    },
                )
            if state.project_id != validated_pid or state.state_version != state_version:
                raise PlanInputStatePersistenceError(
                    f"Persisted plan input state mismatch: expected project '{validated_pid}' "
                    f"version {state_version}, found project '{state.project_id}' "
                    f"version {state.state_version}"
                )
            return state
        except InvalidProjectIdError as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except PlanInputStatePersistenceError as error:
            return JSONResponse(
                status_code=500,
                content={"detail": str(error)},
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Sunucu hatası: {error}"},
            )

    @application.post(
        "/api/v1/projects/{project_id}/plan/input",
        response_model=AuthoritativePlanInputState,
        status_code=201,
    )
    async def initialize_project_plan_input_state(
        project_id: str,
        request: PlanInputStateInitializeRequest,
    ) -> Any:
        try:
            validated_pid = _validate_project_id_param(project_id)
            latest_brief = persistent_brief_service.get_latest_brief(validated_pid)
            if latest_brief is None:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"Cannot initialize plan input state: "
                            f"BriefSnapshot for project '{project_id}' does not exist."
                        )
                    },
                )
            if latest_brief.project_id != validated_pid:
                raise BriefPersistenceError(
                    f"Persisted brief project_id mismatch: expected '{validated_pid}', "
                    f"found '{latest_brief.project_id}'"
                )

            existing_state = persistent_plan_input_service.get_latest_state(validated_pid)
            if existing_state is not None:
                if existing_state.project_id != validated_pid:
                    raise PlanInputStatePersistenceError(
                        f"Persisted plan input state project_id mismatch: "
                        f"expected '{validated_pid}', found '{existing_state.project_id}'"
                    )
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"Plan input state for project '{project_id}' is already initialized "
                            f"(version {existing_state.state_version})."
                        )
                    },
                )

            return persistent_plan_input_service.initialize_state(
                project_id=validated_pid,
                source_brief_version=latest_brief.brief_version,
                metric_requirements=request.metric_requirements,
                site_envelope=request.site_envelope,
                floor_plate_input=request.floor_plate_input,
                solver_config=request.solver_config,
            )
        except InvalidProjectIdError as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except PlanInputStateVersionConflictError as error:
            return JSONResponse(
                status_code=409,
                content={"detail": str(error)},
            )
        except (
            PlanInputStateProjectMismatchError,
            PlanInputStateBriefVersionMismatchError,
            PlanInputStateValidationError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except (BriefPersistenceError, PlanInputStatePersistenceError) as error:
            return JSONResponse(
                status_code=500,
                content={"detail": str(error)},
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Sunucu hatası: {error}"},
            )

    @application.patch(
        "/api/v1/projects/{project_id}/plan/input",
        response_model=AuthoritativePlanInputState,
    )
    async def update_project_plan_input_state(
        project_id: str,
        request: PlanInputStateUpdateRequest,
    ) -> Any:
        try:
            validated_pid = _validate_project_id_param(project_id)
            latest_brief = persistent_brief_service.get_latest_brief(validated_pid)
            if latest_brief is None:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"Cannot update plan input state: "
                            f"BriefSnapshot for project '{project_id}' does not exist."
                        )
                    },
                )
            if latest_brief.project_id != validated_pid:
                raise BriefPersistenceError(
                    f"Persisted brief project_id mismatch: expected '{validated_pid}', "
                    f"found '{latest_brief.project_id}'"
                )

            current_state = persistent_plan_input_service.get_latest_state(validated_pid)
            if current_state is None:
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Plan input state for project '{project_id}' not found."},
                )
            if current_state.project_id != validated_pid:
                raise PlanInputStatePersistenceError(
                    f"Persisted plan input state project_id mismatch: expected '{validated_pid}', "
                    f"found '{current_state.project_id}'"
                )

            metrics_arg = (
                request.metric_requirements
                if "metric_requirements" in request.model_fields_set
                else UNCHANGED
            )
            site_arg = (
                request.site_envelope if "site_envelope" in request.model_fields_set else UNCHANGED
            )
            fp_arg = (
                request.floor_plate_input
                if "floor_plate_input" in request.model_fields_set
                else UNCHANGED
            )
            solver_cfg_arg = (
                request.solver_config if "solver_config" in request.model_fields_set else UNCHANGED
            )

            return persistent_plan_input_service.update_state(
                project_id=validated_pid,
                expected_state_version=request.expected_state_version,
                source_brief_version=latest_brief.brief_version,
                metric_requirements=metrics_arg,
                site_envelope=site_arg,
                floor_plate_input=fp_arg,
                solver_config=solver_cfg_arg,
            )
        except InvalidProjectIdError as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except PlanInputStateNotFoundError as error:
            return JSONResponse(
                status_code=404,
                content={"detail": str(error)},
            )
        except PlanInputStateVersionConflictError as error:
            return JSONResponse(
                status_code=409,
                content={"detail": str(error)},
            )
        except (
            PlanInputStateProjectMismatchError,
            PlanInputStateBriefVersionMismatchError,
            PlanInputStateValidationError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except (BriefPersistenceError, PlanInputStatePersistenceError) as error:
            return JSONResponse(
                status_code=500,
                content={"detail": str(error)},
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Sunucu hatası: {error}"},
            )

    @application.post(
        "/api/v1/projects/{project_id}/plan/input/metrics/approve",
        response_model=MetricRequirementApprovalResponse,
    )
    async def approve_metric_requirement(
        project_id: str,
        request: MetricRequirementApprovalRequest,
    ) -> Any:
        try:
            clean_project_id = _validate_project_id_param(project_id)
            if request.current_project_id != clean_project_id:
                raise PolicyValidationError(
                    f"Route project_id '{clean_project_id}' does not match "
                    f"payload current_project_id '{request.current_project_id}'."
                )

            if request.proposal_fingerprint != request.current_fingerprint:
                raise StaleContextError("Farklı bağlama ait öneri onaylanamaz.")
            if request.proposal_generation_id != request.current_generation_id:
                raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

            # 1. Fetch authoritative persisted BriefSnapshot
            persisted_brief = persistent_brief_service.get_latest_brief(clean_project_id)
            if persisted_brief is None:
                raise BriefNotFoundError(
                    f"Cannot approve metric requirement: Project '{clean_project_id}' "
                    "brief is not initialized."
                )

            if persisted_brief.brief_version != request.expected_brief_version:
                raise BriefVersionConflictError(
                    f"Stale brief approval: Current persisted brief version for "
                    f"'{clean_project_id}' is {persisted_brief.brief_version}, "
                    f"but client expected version {request.expected_brief_version}."
                )

            # 2. Fetch authoritative spatial graph & validate project/version
            persisted_graph = persistent_spatial_service.get_latest_graph(clean_project_id)
            if persisted_graph is None:
                raise SpatialProgramMissingInputError(
                    f"Spatial relationship graph for project '{clean_project_id}' not found."
                )
            if persisted_graph.project_id != clean_project_id:
                raise SpatialProgramProjectMismatchError(
                    snapshot_project_id=clean_project_id,
                    graph_project_id=persisted_graph.project_id,
                )
            if persisted_graph.source_brief_version != persisted_brief.brief_version:
                raise SpatialProgramVersionMismatchError(
                    snapshot_version=persisted_brief.brief_version,
                    graph_source_version=persisted_graph.source_brief_version,
                )

            # 3. Derive SpatialProgram and validate target space
            program = SpatialProgramBuilder().build(persisted_brief, persisted_graph)
            prop = request.proposed_requirement

            target_space = next((s for s in program.spaces if s.id == prop.space_id), None)
            if target_space is None:
                raise MetricNonexistentSpaceError(
                    f"Target space {prop.space_id!r} is not part of the active SpatialProgram."
                )

            now = datetime.now(UTC)

            # 4. Fetch authoritative plan input state
            current_plan_input_state = persistent_plan_input_service.get_latest_state(
                clean_project_id
            )

            if (
                current_plan_input_state is not None
                and current_plan_input_state.source_brief_version != request.expected_brief_version
            ):
                raise PlanInputStateVersionConflictError(
                    "Stale plan input state source brief: proposal expects brief version "
                    f"{request.expected_brief_version}, but current plan input state is bound to "
                    f"brief version {current_plan_input_state.source_brief_version}."
                )

            # 5. Revalidate the exact source message at the authoritative approval boundary.
            validate_metric_source_binding(
                user_message=request.user_message,
                proposed_requirement=prop,
                available_spaces={space.id: space.display_name for space in program.spaces},
            )

            candidate_evidence = persistent_plan_input_evidence_repository.build_chat_evidence(
                project_id=clean_project_id,
                source_reference=request.source_reference,
                user_message=request.user_message,
                created_at=now,
            )
            persisted_candidate_evidence = persistent_plan_input_evidence_repository.get_evidence(
                clean_project_id,
                candidate_evidence.id,
            )

            existing_requirement: MetricRequirement | None = None
            if (
                current_plan_input_state is not None
                and current_plan_input_state.metric_requirements is not None
            ):
                existing_requirement = next(
                    (
                        requirement
                        for space_requirements in (
                            current_plan_input_state.metric_requirements.space_requirements
                        )
                        if space_requirements.space_id == prop.space_id
                        for requirement in space_requirements.requirements
                        if requirement.requirement_type == prop.requirement_type
                    ),
                    None,
                )

            semantic_match = (
                existing_requirement is not None
                and existing_requirement.value == prop.value
                and existing_requirement.unit == prop.unit
                and existing_requirement.provenance == RelationshipProvenance.USER_CONFIRMED
                and existing_requirement.priority == Priority.MUST
            )
            evidence_record_matches = (
                persisted_candidate_evidence is not None
                and persisted_candidate_evidence.project_id == clean_project_id
                and persisted_candidate_evidence.source_reference == request.source_reference
                and persisted_candidate_evidence.user_message == request.user_message
            )
            exact_replay = (
                semantic_match
                and existing_requirement is not None
                and candidate_evidence.id in existing_requirement.evidence_ids
                and evidence_record_matches
            )

            # Full replay is the only safe stale-version exception: it performs no write.
            if exact_replay:
                assert current_plan_input_state is not None
                assert existing_requirement is not None
                replay_record = MetricRequirementApprovalRecord(
                    proposal_status="user_approved",
                    approved_at=now,
                    project_id=clean_project_id,
                    proposal_id=prop.proposal_id,
                    space_id=prop.space_id,
                    requirement_type=prop.requirement_type,
                    value=prop.value,
                    unit=prop.unit,
                    operation="replayed",
                    state_changed=False,
                    previous_value=existing_requirement.value,
                    resulting_evidence_id=candidate_evidence.id,
                    resulting_state_version=current_plan_input_state.state_version,
                    context_fingerprint=request.current_fingerprint,
                    generation_id=request.current_generation_id,
                )
                return MetricRequirementApprovalResponse(
                    success=True,
                    resulting_plan_input_state=current_plan_input_state,
                    approval_record=replay_record,
                    error=None,
                )

            # 6. Validate expected plan input state version for every mutating operation.
            if request.expected_plan_input_state_version is None:
                if current_plan_input_state is not None:
                    raise PlanInputStateVersionConflictError(
                        f"Expected plan input state to be uninitialized, but version "
                        f"{current_plan_input_state.state_version} exists."
                    )
            else:
                if current_plan_input_state is None:
                    raise PlanInputStateVersionConflictError(
                        f"Expected plan input state version "
                        f"{request.expected_plan_input_state_version}, "
                        "but plan input state does not exist."
                    )
                if (
                    current_plan_input_state.state_version
                    != request.expected_plan_input_state_version
                ):
                    raise PlanInputStateVersionConflictError(
                        f"Stale plan input state: expected "
                        f"{request.expected_plan_input_state_version}, "
                        f"but latest version is {current_plan_input_state.state_version}."
                    )

            operation: Literal["created", "replaced", "evidence_merged"]
            if existing_requirement is None:
                operation = "created"
                approved_evidence_ids = [candidate_evidence.id]
                approved_rationale = prop.rationale
            elif semantic_match:
                operation = "evidence_merged"
                approved_evidence_ids = sorted(
                    {*existing_requirement.evidence_ids, candidate_evidence.id}
                )
                approved_rationale = existing_requirement.rationale
            else:
                operation = "replaced"
                approved_evidence_ids = [candidate_evidence.id]
                approved_rationale = prop.rationale

            # 7. Collect existing requirements and replace only the matching key.
            existing_inputs: list[MetricRequirementInput] = []
            if (
                current_plan_input_state is not None
                and current_plan_input_state.metric_requirements is not None
            ):
                for space_req in current_plan_input_state.metric_requirements.space_requirements:
                    for req in space_req.requirements:
                        if (
                            req.space_id == prop.space_id
                            and req.requirement_type == prop.requirement_type
                        ):
                            continue  # will be replaced
                        existing_inputs.append(
                            MetricRequirementInput(
                                space_id=req.space_id,
                                requirement_type=req.requirement_type,
                                value=req.value,
                                unit=req.unit,
                                provenance=req.provenance,
                                priority=req.priority,
                                evidence_ids=req.evidence_ids,
                                rationale=req.rationale,
                            )
                        )

            # The approved fact is bound to revision-message evidence, never generated geometry.
            approved_input = MetricRequirementInput(
                space_id=prop.space_id,
                requirement_type=prop.requirement_type,
                value=prop.value,
                unit=prop.unit,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                priority=Priority.MUST,
                evidence_ids=approved_evidence_ids,
                rationale=approved_rationale,
            )
            all_inputs = [*existing_inputs, approved_input]

            # 8. Validate the complete candidate before any persistence.
            builder = MetricSpatialRequirementsBuilder()
            new_metric_spatial_requirements = builder.build(
                program=program,
                requirements=all_inputs,
                created_at=now,
            )

            # 9. Evidence-first immutable persistence.
            saved_evidence = persistent_plan_input_evidence_repository.save_chat_evidence(
                project_id=clean_project_id,
                source_reference=request.source_reference,
                user_message=request.user_message,
                created_at=now,
            )
            if saved_evidence.id != candidate_evidence.id:  # pragma: no cover - defensive guard
                raise PlanInputApprovalEvidencePersistenceError(
                    "Saved plan-input approval evidence identity changed unexpectedly."
                )

            # 10. Initialize or compare-and-swap the sole authoritative metric state.
            if current_plan_input_state is None:
                new_state = persistent_plan_input_service.initialize_state(
                    project_id=clean_project_id,
                    source_brief_version=persisted_brief.brief_version,
                    metric_requirements=new_metric_spatial_requirements,
                    created_at=now,
                )
            else:
                new_state = persistent_plan_input_service.update_state(
                    project_id=clean_project_id,
                    expected_state_version=current_plan_input_state.state_version,
                    source_brief_version=persisted_brief.brief_version,
                    metric_requirements=new_metric_spatial_requirements,
                    created_at=now,
                )

            record = MetricRequirementApprovalRecord(
                proposal_status="user_approved",
                approved_at=now,
                project_id=clean_project_id,
                proposal_id=prop.proposal_id,
                space_id=prop.space_id,
                requirement_type=prop.requirement_type,
                value=prop.value,
                unit=prop.unit,
                operation=operation,
                state_changed=True,
                previous_value=(
                    existing_requirement.value if existing_requirement is not None else None
                ),
                resulting_evidence_id=saved_evidence.id,
                resulting_state_version=new_state.state_version,
                context_fingerprint=request.current_fingerprint,
                generation_id=request.current_generation_id,
            )

            return MetricRequirementApprovalResponse(
                success=True,
                resulting_plan_input_state=new_state,
                approval_record=record,
                error=None,
            )
        except (
            BriefVersionConflictError,
            StaleContextError,
            PlanInputStateVersionConflictError,
            SpatialProgramProjectMismatchError,
            SpatialProgramVersionMismatchError,
            SpatialProgramMissingInputError,
            BriefNotReadyError,
            SpatialProgramConflictBlockerError,
            SpatialProgramNodeMismatchError,
            MetricNonexistentSpaceError,
        ) as error:
            return JSONResponse(
                status_code=409,
                content=MetricRequirementApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except BriefNotFoundError as error:
            return JSONResponse(
                status_code=404,
                content=MetricRequirementApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            PolicyValidationError,
            InvalidProjectIdError,
            MetricRangeConflictError,
            MetricUnitMismatchError,
            MetricInvalidValueError,
            MetricInvalidEvidenceError,
            DuplicateMetricRequirementError,
            PlanInputStateValidationError,
            PlanInputStateBriefVersionMismatchError,
            PlanInputStateProjectMismatchError,
            MetricSourceBindingError,
            ValueError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content=MetricRequirementApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            BriefPersistenceError,
            SpatialGraphPersistenceError,
            PlanInputStatePersistenceError,
            PlanInputApprovalEvidencePersistenceError,
        ) as error:
            return JSONResponse(
                status_code=500,
                content=MetricRequirementApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content=MetricRequirementApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )

    @application.post(
        "/api/v1/projects/{project_id}/plan/input/site/approve",
        response_model=SiteGeometryApprovalResponse,
    )
    async def approve_site_geometry(
        project_id: str,
        request: SiteGeometryApprovalRequest,
    ) -> Any:
        try:
            clean_project_id = _validate_project_id_param(project_id)
            if request.current_project_id != clean_project_id:
                raise PolicyValidationError(
                    f"Route project_id '{clean_project_id}' does not match "
                    f"payload current_project_id '{request.current_project_id}'."
                )

            if request.proposal_fingerprint != request.current_fingerprint:
                raise StaleContextError("Farklı bağlama ait öneri onaylanamaz.")
            if request.proposal_generation_id != request.current_generation_id:
                raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

            # 1. Fetch authoritative persisted BriefSnapshot
            persisted_brief = persistent_brief_service.get_latest_brief(clean_project_id)
            if persisted_brief is None:
                raise BriefNotFoundError(
                    f"Cannot approve site geometry: Project '{clean_project_id}' "
                    "brief is not initialized."
                )

            if persisted_brief.brief_version != request.expected_brief_version:
                raise BriefVersionConflictError(
                    f"Stale brief approval: Current persisted brief version for "
                    f"'{clean_project_id}' is {persisted_brief.brief_version}, "
                    f"but client expected version {request.expected_brief_version}."
                )

            # 2. Strict source re-validation
            if not request.user_message or not request.user_message.strip():
                raise PolicyValidationError(
                    "Kullanıcı mesajı (user_message) site onayı için zorunludur."
                )
            try:
                validate_site_geometry_source_binding(
                    user_message=request.user_message,
                    proposed_role=request.proposed_geometry.role,
                    proposed_vertices=request.proposed_geometry.vertices,
                )
            except SiteSourceBindingError as err:
                raise PolicyValidationError(f"Kaynak doğrulama hatası: {err}") from err

            # 3. Fetch authoritative spatial graph & build SpatialProgram
            persisted_graph = persistent_spatial_service.get_latest_graph(clean_project_id)
            if persisted_graph is None:
                raise SpatialProgramMissingInputError(
                    f"Spatial relationship graph for project '{clean_project_id}' not found."
                )
            if persisted_graph.project_id != clean_project_id:
                raise SpatialProgramProjectMismatchError(
                    snapshot_project_id=clean_project_id,
                    graph_project_id=persisted_graph.project_id,
                )
            if persisted_graph.source_brief_version != persisted_brief.brief_version:
                raise SpatialProgramVersionMismatchError(
                    snapshot_version=persisted_brief.brief_version,
                    graph_source_version=persisted_graph.source_brief_version,
                )

            program = SpatialProgramBuilder().build(persisted_brief, persisted_graph)
            prop = request.proposed_geometry
            now = datetime.now(UTC)

            # 4. Fetch authoritative plan input state
            current_plan_input_state = persistent_plan_input_service.get_latest_state(
                clean_project_id
            )

            # 5. Idempotent semantic replay check
            if (
                current_plan_input_state is not None
                and current_plan_input_state.site_envelope is not None
            ):
                cur_env = current_plan_input_state.site_envelope
                if prop.role == SiteGeometryRole.PARCEL_BOUNDARY:
                    if (
                        cur_env.parcel_boundary is not None
                        and cur_env.parcel_boundary.provenance
                        == RelationshipProvenance.USER_CONFIRMED
                        and cur_env.buildable_envelope is None
                    ):
                        cur_v = cur_env.parcel_boundary.vertices
                        prop_v = prop.vertices
                        if len(cur_v) == len(prop_v) and all(
                            Decimal(str(cv.x_m)) == Decimal(str(pv.x_m))
                            and Decimal(str(cv.y_m)) == Decimal(str(pv.y_m))
                            for cv, pv in zip(cur_v, prop_v, strict=True)
                        ):
                            record = SiteGeometryApprovalRecord(
                                proposal_status="user_approved",
                                approved_at=now,
                                project_id=clean_project_id,
                                proposal_id=prop.proposal_id,
                                geometry_id=cur_env.parcel_boundary.id,
                                role=SiteGeometryRole.PARCEL_BOUNDARY,
                                resulting_state_version=current_plan_input_state.state_version,
                                context_fingerprint=request.current_fingerprint,
                                generation_id=request.current_generation_id,
                            )
                            return SiteGeometryApprovalResponse(
                                success=True,
                                resulting_plan_input_state=current_plan_input_state,
                                approval_record=record,
                                error=None,
                            )
                elif (
                    prop.role == SiteGeometryRole.BUILDABLE_ENVELOPE
                    and cur_env.buildable_envelope is not None
                    and cur_env.buildable_envelope.provenance
                    == RelationshipProvenance.USER_CONFIRMED
                ):
                    cur_v = cur_env.buildable_envelope.vertices
                    prop_v = prop.vertices
                    if len(cur_v) == len(prop_v) and all(
                        Decimal(str(cv.x_m)) == Decimal(str(pv.x_m))
                        and Decimal(str(cv.y_m)) == Decimal(str(pv.y_m))
                        for cv, pv in zip(cur_v, prop_v, strict=True)
                    ):
                        record = SiteGeometryApprovalRecord(
                            proposal_status="user_approved",
                            approved_at=now,
                            project_id=clean_project_id,
                            proposal_id=prop.proposal_id,
                            geometry_id=cur_env.buildable_envelope.id,
                            role=SiteGeometryRole.BUILDABLE_ENVELOPE,
                            resulting_state_version=current_plan_input_state.state_version,
                            context_fingerprint=request.current_fingerprint,
                            generation_id=request.current_generation_id,
                        )
                        return SiteGeometryApprovalResponse(
                            success=True,
                            resulting_plan_input_state=current_plan_input_state,
                            approval_record=record,
                            error=None,
                        )

            # 6. Validate expected plan input state version
            if request.expected_plan_input_state_version is None:
                if current_plan_input_state is not None:
                    raise PlanInputStateVersionConflictError(
                        f"Expected plan input state to be uninitialized, but version "
                        f"{current_plan_input_state.state_version} exists."
                    )
            else:
                if current_plan_input_state is None:
                    raise PlanInputStateVersionConflictError(
                        f"Expected plan input state version "
                        f"{request.expected_plan_input_state_version}, "
                        "but plan input state does not exist."
                    )
                if (
                    current_plan_input_state.state_version
                    != request.expected_plan_input_state_version
                ):
                    raise PlanInputStateVersionConflictError(
                        f"Stale plan input state: expected "
                        f"{request.expected_plan_input_state_version}, "
                        f"but latest version is {current_plan_input_state.state_version}."
                    )

            # 7. Persist site geometry evidence record
            evidence = persistent_site_evidence_repository.save_site_evidence(
                project_id=clean_project_id,
                source_reference=request.source_reference,
                user_message=request.user_message,
            )

            # 8. Build SiteBuildableEnvelope using SiteBuildableEnvelopeBuilder
            site_builder = SiteBuildableEnvelopeBuilder()
            if prop.role == SiteGeometryRole.PARCEL_BOUNDARY:
                parcel_input = SitePolygonInput(
                    vertices=prop.vertices,
                    provenance=RelationshipProvenance.USER_CONFIRMED,
                    evidence_ids=[evidence.id],
                    rationale=prop.rationale,
                )
                # Replacing parcel boundary ALWAYS clears existing buildable_envelope
                new_site_envelope = site_builder.build(
                    program=program,
                    parcel_boundary=parcel_input,
                    buildable_envelope=None,
                    created_at=now,
                )
                if new_site_envelope.parcel_boundary is None:
                    raise PolicyValidationError("Parsel sınırı üretilemedi.")
                geometry_id = new_site_envelope.parcel_boundary.id
            elif prop.role == SiteGeometryRole.BUILDABLE_ENVELOPE:
                if (
                    current_plan_input_state is None
                    or current_plan_input_state.site_envelope is None
                    or current_plan_input_state.site_envelope.parcel_boundary is None
                ):
                    raise SiteEnvelopeWithoutParcelError(
                        "Yapılaşma zarfı onayı için önce geçerli bir parsel sınırı tanımlanmalıdır."
                    )
                existing_parcel = current_plan_input_state.site_envelope.parcel_boundary
                if existing_parcel.provenance != RelationshipProvenance.USER_CONFIRMED:
                    raise PolicyValidationError(
                        "Mevcut parsel sınırı kullanıcı onaylı (USER_CONFIRMED) olmadığı için "
                        "yapılaşma zarfı onaylanamaz."
                    )
                if (
                    existing_parcel.id
                    not in current_plan_input_state.site_envelope.authoritative_geometry_ids
                ):
                    raise PolicyValidationError(
                        "Mevcut parsel sınırı yetkili geometri listesinde bulunamadı."
                    )
                parcel_input = SitePolygonInput(
                    vertices=existing_parcel.vertices,
                    provenance=RelationshipProvenance.USER_CONFIRMED,
                    evidence_ids=existing_parcel.evidence_ids,
                    rationale=existing_parcel.rationale,
                )
                envelope_input = SitePolygonInput(
                    vertices=prop.vertices,
                    provenance=RelationshipProvenance.USER_CONFIRMED,
                    evidence_ids=[evidence.id],
                    rationale=prop.rationale,
                )
                new_site_envelope = site_builder.build(
                    program=program,
                    parcel_boundary=parcel_input,
                    buildable_envelope=envelope_input,
                    created_at=now,
                )
                if new_site_envelope.buildable_envelope is None:
                    raise PolicyValidationError("Yapılaşma zarfı üretilemedi.")
                geometry_id = new_site_envelope.buildable_envelope.id
            else:
                raise PolicyValidationError(f"Desteklenmeyen site geometri rolü: {prop.role}")

            # 9. Persist AuthoritativePlanInputState (advance version N -> N+1)
            if current_plan_input_state is None:
                new_state = persistent_plan_input_service.initialize_state(
                    project_id=clean_project_id,
                    source_brief_version=persisted_brief.brief_version,
                    site_envelope=new_site_envelope,
                    created_at=now,
                )
            else:
                new_state = persistent_plan_input_service.update_state(
                    project_id=clean_project_id,
                    expected_state_version=current_plan_input_state.state_version,
                    source_brief_version=persisted_brief.brief_version,
                    site_envelope=new_site_envelope,
                    created_at=now,
                )

            record = SiteGeometryApprovalRecord(
                proposal_status="user_approved",
                approved_at=now,
                project_id=clean_project_id,
                proposal_id=prop.proposal_id,
                geometry_id=geometry_id,
                role=prop.role,
                resulting_state_version=new_state.state_version,
                context_fingerprint=request.current_fingerprint,
                generation_id=request.current_generation_id,
            )
            return SiteGeometryApprovalResponse(
                success=True,
                resulting_plan_input_state=new_state,
                approval_record=record,
                error=None,
            )
        except (
            BriefVersionConflictError,
            PlanInputStateVersionConflictError,
            SpatialProgramProjectMismatchError,
            SpatialProgramVersionMismatchError,
            SpatialProgramMissingInputError,
            BriefNotReadyError,
            SpatialProgramConflictBlockerError,
            SpatialProgramNodeMismatchError,
            StaleContextError,
        ) as error:
            return JSONResponse(
                status_code=409,
                content=SiteGeometryApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            BriefNotFoundError,
            PlanInputStateNotFoundError,
        ) as error:
            return JSONResponse(
                status_code=404,
                content=SiteGeometryApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            PolicyValidationError,
            InvalidProjectIdError,
            SiteEnvelopeOutsideParcelError,
            SiteEnvelopeWithoutParcelError,
            SiteInvalidCoordinateError,
            SitePolygonDegenerateError,
            SitePolygonSelfIntersectionError,
            SiteSourceBindingError,
            PlanInputStateValidationError,
            PlanInputStateBriefVersionMismatchError,
            PlanInputStateProjectMismatchError,
            ValueError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content=SiteGeometryApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            BriefPersistenceError,
            SpatialGraphPersistenceError,
            PlanInputStatePersistenceError,
            SiteEvidencePersistenceError,
        ):
            return JSONResponse(
                status_code=500,
                content=SiteGeometryApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error="Kalıcı depolama hatası oluştu.",
                ).model_dump(mode="json"),
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content=SiteGeometryApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error="Sunucu içi beklenmeyen bir hata oluştu.",
                ).model_dump(mode="json"),
            )

    @application.post(
        "/api/v1/projects/{project_id}/plan/input/floor-plate/approve",
        response_model=FloorPlateApprovalResponse,
    )
    async def approve_floor_plate(
        project_id: str,
        request: FloorPlateApprovalRequest,
    ) -> Any:
        try:
            clean_project_id = _validate_project_id_param(project_id)
            if request.current_project_id != clean_project_id:
                raise PolicyValidationError(
                    f"Route project_id '{clean_project_id}' does not match "
                    f"payload current_project_id '{request.current_project_id}'."
                )

            if request.proposal_fingerprint != request.current_fingerprint:
                raise StaleContextError("Farklı bağlama ait öneri onaylanamaz.")
            if request.proposal_generation_id != request.current_generation_id:
                raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

            # 1. Fetch authoritative persisted BriefSnapshot
            persisted_brief = persistent_brief_service.get_latest_brief(clean_project_id)
            if persisted_brief is None:
                raise BriefNotFoundError(
                    f"Cannot approve floor plate: Project '{clean_project_id}' "
                    "brief is not initialized."
                )

            if persisted_brief.brief_version != request.expected_brief_version:
                raise BriefVersionConflictError(
                    f"Stale brief approval: Current persisted brief version for "
                    f"'{clean_project_id}' is {persisted_brief.brief_version}, "
                    f"but client expected version {request.expected_brief_version}."
                )

            # 2. Strict source re-validation
            if not request.user_message or not request.user_message.strip():
                raise PolicyValidationError(
                    "Kullanıcı mesajı (user_message) taban oturumu onayı için zorunludur."
                )
            prop = request.proposed_floor_plate
            try:
                validate_floor_plate_source_binding(
                    user_message=request.user_message,
                    proposed_vertices=prop.vertices,
                )
            except FloorPlateSourceBindingError as err:
                raise PolicyValidationError(f"Kaynak doğrulama hatası: {err}") from err

            now = datetime.now(UTC)

            # 3. Fetch authoritative plan input state
            current_plan_input_state = persistent_plan_input_service.get_latest_state(
                project_id=clean_project_id,
            )

            # 4. Semantic Replay Check (Exact Replay Idempotence)
            if (
                current_plan_input_state is not None
                and current_plan_input_state.floor_plate_input is not None
            ):
                cur_fp = current_plan_input_state.floor_plate_input
                if (
                    cur_fp.provenance == RelationshipProvenance.USER_CONFIRMED
                    and cur_fp.rationale == prop.rationale
                ):
                    cur_v = cur_fp.vertices
                    prop_v = prop.vertices
                    if len(cur_v) == len(prop_v) and all(
                        Decimal(str(cv.x_m)) == Decimal(str(pv.x_m))
                        and Decimal(str(cv.y_m)) == Decimal(str(pv.y_m))
                        for cv, pv in zip(cur_v, prop_v, strict=True)
                    ):
                        floor_plate_id = generate_floor_plate_id(clean_project_id)
                        record = FloorPlateApprovalRecord(
                            proposal_status="user_approved",
                            approved_at=now,
                            project_id=clean_project_id,
                            proposal_id=prop.proposal_id,
                            floor_plate_id=floor_plate_id,
                            resulting_state_version=current_plan_input_state.state_version,
                            context_fingerprint=request.current_fingerprint,
                            generation_id=request.current_generation_id,
                        )
                        return FloorPlateApprovalResponse(
                            success=True,
                            resulting_plan_input_state=current_plan_input_state,
                            approval_record=record,
                            error=None,
                        )

            # 5. Validate expected plan input state version
            if request.expected_plan_input_state_version is None:
                if current_plan_input_state is not None:
                    raise PlanInputStateVersionConflictError(
                        f"Expected plan input state to be uninitialized, but version "
                        f"{current_plan_input_state.state_version} exists."
                    )
            else:
                if current_plan_input_state is None:
                    raise PlanInputStateVersionConflictError(
                        f"Expected plan input state version "
                        f"{request.expected_plan_input_state_version}, "
                        "but plan input state does not exist."
                    )
                if (
                    current_plan_input_state.state_version
                    != request.expected_plan_input_state_version
                ):
                    raise PlanInputStateVersionConflictError(
                        f"Stale plan input state: expected "
                        f"{request.expected_plan_input_state_version}, "
                        f"but latest version is {current_plan_input_state.state_version}."
                    )

            # 6. Validate polygon geometry (minimum 3, simplicity, finite coords)
            try:
                validate_polygon_geometry(prop.vertices)
            except (
                SiteInvalidCoordinateError,
                SitePolygonDegenerateError,
                SitePolygonSelfIntersectionError,
                ValueError,
            ) as err:
                raise PolicyValidationError(f"Taban oturumu geometrisi geçersiz: {err}") from err

            # 7. Check containment inside buildable envelope IF buildable envelope is present
            if (
                current_plan_input_state is not None
                and current_plan_input_state.site_envelope is not None
                and current_plan_input_state.site_envelope.buildable_envelope is not None
            ):
                env_v = current_plan_input_state.site_envelope.buildable_envelope.vertices
                validate_floor_plate_inside_buildable_envelope(
                    floor_plate_vertices=prop.vertices,
                    envelope_vertices=env_v,
                )

            # 8. Persist floor plate evidence record
            evidence = persistent_site_evidence_repository.save_site_evidence(
                project_id=clean_project_id,
                source_reference=request.source_reference,
                user_message=request.user_message,
            )

            # 9. Construct authoritative FloorPlateInput
            floor_plate_input = FloorPlateInput(
                vertices=prop.vertices,
                provenance=RelationshipProvenance.USER_CONFIRMED,
                evidence_ids=[evidence.id],
                rationale=prop.rationale,
            )

            # 10. Persist AuthoritativePlanInputState (advance version N -> N+1)
            if current_plan_input_state is None:
                new_state = persistent_plan_input_service.initialize_state(
                    project_id=clean_project_id,
                    source_brief_version=persisted_brief.brief_version,
                    floor_plate_input=floor_plate_input,
                    created_at=now,
                )
            else:
                new_state = persistent_plan_input_service.update_state(
                    project_id=clean_project_id,
                    expected_state_version=current_plan_input_state.state_version,
                    source_brief_version=persisted_brief.brief_version,
                    floor_plate_input=floor_plate_input,
                    created_at=now,
                )

            floor_plate_id = generate_floor_plate_id(clean_project_id)
            record = FloorPlateApprovalRecord(
                proposal_status="user_approved",
                approved_at=now,
                project_id=clean_project_id,
                proposal_id=prop.proposal_id,
                floor_plate_id=floor_plate_id,
                resulting_state_version=new_state.state_version,
                context_fingerprint=request.current_fingerprint,
                generation_id=request.current_generation_id,
            )
            return FloorPlateApprovalResponse(
                success=True,
                resulting_plan_input_state=new_state,
                approval_record=record,
                error=None,
            )
        except (
            BriefVersionConflictError,
            PlanInputStateVersionConflictError,
            StaleContextError,
        ) as error:
            return JSONResponse(
                status_code=409,
                content=FloorPlateApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            BriefNotFoundError,
            PlanInputStateNotFoundError,
        ) as error:
            return JSONResponse(
                status_code=404,
                content=FloorPlateApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            PolicyValidationError,
            InvalidProjectIdError,
            FloorPlateOutsideBuildableEnvelopeError,
            SiteInvalidCoordinateError,
            SitePolygonDegenerateError,
            SitePolygonSelfIntersectionError,
            FloorPlateSourceBindingError,
            PlanInputStateValidationError,
            PlanInputStateBriefVersionMismatchError,
            PlanInputStateProjectMismatchError,
            ValueError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content=FloorPlateApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            BriefPersistenceError,
            PlanInputStatePersistenceError,
            SiteEvidencePersistenceError,
        ):
            return JSONResponse(
                status_code=500,
                content=FloorPlateApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error="Kalıcı depolama hatası oluştu.",
                ).model_dump(mode="json"),
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content=FloorPlateApprovalResponse(
                    success=False,
                    resulting_plan_input_state=None,
                    approval_record=None,
                    error="Sunucu içi beklenmeyen bir hata oluştu.",
                ).model_dump(mode="json"),
            )

    @application.get(
        "/api/v1/projects/{project_id}/plan/preview/readiness",
        response_model=ProjectPlanPreviewReadinessResult,
    )
    async def get_project_plan_preview_readiness(project_id: str) -> Any:
        try:
            return project_readiness_service.evaluate(project_id)
        except InvalidProjectIdError as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except (
            BriefPersistenceError,
            SpatialGraphPersistenceError,
            PlanInputStatePersistenceError,
        ) as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Kalıcı depolama hatası: {error}"},
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Sunucu hatası: {error}"},
            )

    @application.post(
        "/api/v1/projects/{project_id}/plan/preview",
        response_model=PlanPreviewResponse,
        responses={
            409: {"model": ProjectPlanPreviewReadinessResult},
        },
    )
    async def execute_project_plan_preview(project_id: str) -> Any:
        try:
            readiness = project_readiness_service.evaluate(project_id)
            if not readiness.ready_for_preview:
                return JSONResponse(
                    status_code=409,
                    content=readiness.model_dump(mode="json"),
                )

            if readiness.preparation is None or readiness.preparation.request is None:
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Sunucu hatası: Hazır durum için hazırlık isteği bulunamadı."
                    },
                )

            preview_request = readiness.preparation.request
        except InvalidProjectIdError as error:
            return JSONResponse(
                status_code=422,
                content={"detail": str(error)},
            )
        except (
            BriefPersistenceError,
            SpatialGraphPersistenceError,
            PlanInputStatePersistenceError,
        ) as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Kalıcı depolama hatası: {error}"},
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Sunucu hatası: {error}"},
            )

        try:
            return PlanPreviewService.generate(preview_request)
        except (
            RoomGeometryInputMismatchError,
            SvgPlanInputMismatchError,
            SvgPlanUnknownSpaceError,
        ) as error:
            return JSONResponse(
                status_code=409,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except (
            RoomGeometryUnsupportedFloorPlateError,
            RoomGeometryUnsupportedOptionalSpaceError,
            RoomGeometryUnsupportedMetricError,
            RoomGeometryUnsupportedDirectiveError,
            RoomGeometryUnderconstrainedSpaceError,
            RoomGeometryGridAlignmentError,
            RoomGeometryInfeasibleError,
            SvgPlanInvalidGeometryError,
        ) as error:
            return JSONResponse(
                status_code=422,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except RoomGeometryEngineError as error:
            return JSONResponse(
                status_code=503,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except SvgPlanRenderError as error:
            return JSONResponse(
                status_code=500,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content=PlanPreviewResponse(
                    success=False,
                    solution=None,
                    document=None,
                    error=f"Plan önizlemesi sırasında sunucu hatası oluştu: {error}",
                ).model_dump(mode="json"),
            )

    return application


def _error_response(
    request: ConversationRequest,
    settings: LocalLLMSettings,
    message: str,
    status_code: int,
) -> JSONResponse:
    envelope = ConversationInterpretationResponse(
        success=False,
        llm_enabled=settings.enabled,
        provider=settings.provider,
        model=settings.model or None,
        context_fingerprint=request.active_context.context_fingerprint,
        generation_id=request.active_context.generation_id,
        result=None,
        error=message,
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))


app = create_app()
