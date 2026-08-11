"""FastAPI boundary for provider-agnostic local LLM conversations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.persistence import (
    BriefNotFoundError,
    BriefPersistenceError,
    BriefRepository,
    BriefVersionConflictError,
    InvalidProjectIdError,
    JSONBriefRepository,
)
from brif_ai.brief.service import PersistentBriefService
from brif_ai.llm.contracts import (
    BriefMutationApprovalRecord,
    BriefMutationApprovalRequest,
    BriefMutationApprovalResponse,
    ConversationInterpretationResponse,
    ConversationRequest,
    HealthResponse,
    LocalModelInfo,
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


def create_app(
    settings: LocalLLMSettings | None = None,
    provider: LocalLLMProvider | None = None,
    cors_environ: Mapping[str, str] | None = None,
    brief_repository: BriefRepository | None = None,
) -> FastAPI:
    resolved_settings = settings or LocalLLMSettings.from_env()
    resolved_provider = provider or OllamaProvider(resolved_settings)
    resolved_brief_repo = brief_repository or JSONBriefRepository()
    persistent_brief_service = PersistentBriefService(resolved_brief_repo)
    service = LocalLLMConversationService(resolved_settings, resolved_provider)

    application = FastAPI(title="BRIF.AI Local LLM API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolve_allowed_origins(cors_environ),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
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
            return await service.interpret(request)
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
            now = datetime.now(timezone.utc)  # noqa: UP017
            new_snapshot = persistent_brief_service.record_brief_mutation_approval(
                current_project_id=request.current_project_id,
                expected_brief_version=request.expected_brief_version,
                proposed_mutation=request.proposed_mutation,
                user_message=request.user_message,
                source_reference=src_ref,
                approved_at=now,
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
