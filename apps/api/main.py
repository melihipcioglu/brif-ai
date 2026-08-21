"""FastAPI boundary for provider-agnostic local LLM conversations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

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
    HealthResponse,
    LocalModelInfo,
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


def create_app(
    settings: LocalLLMSettings | None = None,
    provider: LocalLLMProvider | None = None,
    cors_environ: Mapping[str, str] | None = None,
    brief_repository: BriefRepository | None = None,
    spatial_repository: SpatialRelationshipRepository | None = None,
    plan_input_repository: PlanInputStateRepository | None = None,
) -> FastAPI:
    resolved_settings = settings or LocalLLMSettings.from_env()
    resolved_provider = provider or OllamaProvider(resolved_settings)
    resolved_brief_repo = brief_repository or JSONBriefRepository()
    persistent_brief_service = PersistentBriefService(resolved_brief_repo)
    resolved_spatial_repo = spatial_repository or JSONSpatialRelationshipRepository()
    persistent_spatial_service = PersistentSpatialService(resolved_spatial_repo)
    resolved_plan_input_repo = plan_input_repository or JSONPlanInputStateRepository()
    persistent_plan_input_service = PlanInputStateService(resolved_plan_input_repo)
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
                    )

            # Step 6: Replace client brief content with authoritative snapshot
            prepared_request = request.model_copy(update={"brief_snapshot": authoritative_snapshot})

            # Step 7: Execute LLM interpretation
            interpretation_result = await service.interpret(prepared_request)

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

            return interpretation_result.model_copy(
                update={"resulting_brief_snapshot": resulting_snapshot}
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
