"""Provider-neutral local conversation service."""

from __future__ import annotations

from datetime import datetime, timezone

from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationInterpretationResponse,
    ConversationRequest,
    HealthResponse,
    LocalModelInfo,
    ProposalApprovalRecord,
    ProposedAction,
)
from brif_ai.llm.policy_validator import ArchitecturalIntentPolicyValidator
from brif_ai.llm.provider import LocalLLMProvider
from brif_ai.llm.settings import LocalLLMSettings

LLM_DISABLED_MESSAGE = "Yerel yapay zekâ bağlantısı devre dışı. Demo konuşma modu kullanılıyor."


class StaleContextError(ValueError):
    """An asynchronous response or proposal belongs to an older context."""


class LocalLLMConversationService:
    def __init__(
        self,
        settings: LocalLLMSettings,
        provider: LocalLLMProvider,
        policy_validator: ArchitecturalIntentPolicyValidator | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.policy_validator = policy_validator or ArchitecturalIntentPolicyValidator()

    async def health(self) -> HealthResponse:
        provider_health = await self.provider.health()
        model_available = False
        if provider_health.reachable and self.settings.model:
            models = await self.provider.list_models()
            model_available = self.settings.model in {model.name for model in models}
        return HealthResponse(
            status="ok",
            llm_enabled=self.settings.enabled,
            provider=self.settings.provider,
            provider_reachable=provider_health.reachable,
            selected_model=self.settings.model or None,
            model_available=model_available,
        )

    async def list_models(self) -> list[LocalModelInfo]:
        return await self.provider.list_models()

    async def interpret(
        self,
        request: ConversationRequest,
    ) -> ConversationInterpretationResponse:
        if not self.settings.enabled:
            return ConversationInterpretationResponse(
                success=False,
                llm_enabled=False,
                provider=self.settings.provider,
                model=self.settings.model or None,
                context_fingerprint=request.active_context.context_fingerprint,
                generation_id=request.active_context.generation_id,
                result=None,
                error=LLM_DISABLED_MESSAGE,
            )

        result = await self.provider.interpret(
            request,
            ArchitecturalIntentResult.model_json_schema(),
        )
        safe_result = self.policy_validator.validate(result, request)
        return ConversationInterpretationResponse(
            success=True,
            llm_enabled=True,
            provider=self.settings.provider,
            model=self.settings.model,
            context_fingerprint=request.active_context.context_fingerprint,
            generation_id=request.active_context.generation_id,
            result=safe_result,
            error=None,
        )

    @staticmethod
    def ensure_current_context(response_fingerprint: str, current_fingerprint: str) -> None:
        if response_fingerprint != current_fingerprint:
            raise StaleContextError("Eski bağlama ait yerel model cevabı reddedildi.")

    @staticmethod
    def record_user_approval(
        proposed_action: ProposedAction,
        proposal_fingerprint: str,
        current_fingerprint: str,
        *,
        approved_at: datetime | None = None,
    ) -> ProposalApprovalRecord:
        LocalLLMConversationService.ensure_current_context(
            proposal_fingerprint,
            current_fingerprint,
        )
        return ProposalApprovalRecord(
            proposal_status="user_approved",
            approved_at=approved_at or datetime.now(timezone.utc),  # noqa: UP017
            context_fingerprint=current_fingerprint,
            proposed_action=proposed_action,
        )
