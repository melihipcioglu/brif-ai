"""FastAPI boundary for provider-agnostic local LLM conversations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from brif_ai.llm.contracts import (
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
) -> FastAPI:
    resolved_settings = settings or LocalLLMSettings.from_env()
    resolved_provider = provider or OllamaProvider(resolved_settings)
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
    async def list_models() -> list[LocalModelInfo] | JSONResponse:
        try:
            return await service.list_models()
        except ProviderTimeoutError as error:
            return JSONResponse(status_code=504, content={"detail": str(error)})
        except ProviderUnavailableError as error:
            return JSONResponse(status_code=503, content={"detail": str(error)})
        except ProviderResponseError as error:
            return JSONResponse(status_code=502, content={"detail": str(error)})

    @application.post(
        "/api/v1/conversation/interpret",
        response_model=ConversationInterpretationResponse,
    )
    async def interpret(
        request: ConversationRequest,
    ) -> ConversationInterpretationResponse | JSONResponse:
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
    async def approve_brief_mutation(
        request: BriefMutationApprovalRequest,
    ) -> BriefMutationApprovalResponse | JSONResponse:
        try:
            new_snapshot, record = service.record_brief_mutation_approval(
                proposal_fingerprint=request.proposal_fingerprint,
                current_fingerprint=request.current_fingerprint,
                proposal_generation_id=request.proposal_generation_id,
                current_generation_id=request.current_generation_id,
                proposed_mutation=request.proposed_mutation,
                user_message=request.user_message,
                snapshot=request.brief_snapshot,
                current_project_id=request.current_project_id,
                source_reference=request.source_reference,
            )
            return BriefMutationApprovalResponse(
                success=True,
                resulting_snapshot=new_snapshot,
                approval_record=record,
                error=None,
            )
        except StaleContextError as error:
            return JSONResponse(
                status_code=409,
                content=BriefMutationApprovalResponse(
                    success=False,
                    resulting_snapshot=None,
                    approval_record=None,
                    error=str(error),
                ).model_dump(mode="json"),
            )
        except ValueError as error:
            return JSONResponse(
                status_code=422,
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
