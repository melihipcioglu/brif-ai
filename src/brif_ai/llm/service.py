"""Provider-neutral local conversation service."""

from __future__ import annotations

from datetime import datetime, timezone

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.mutation import ProposedBriefMutation, apply_approved_brief_mutation
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    BriefMutationApprovalRecord,
    ConversationInterpretationResponse,
    ConversationRequest,
    HealthResponse,
    LocalModelInfo,
    ProposalApprovalRecord,
    ProposedAction,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    ScopeMismatchError,
)
from brif_ai.llm.provider import (
    LocalLLMProvider,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
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
        selected_model = self.settings.model or None
        if not self.settings.enabled:
            return HealthResponse(
                status="degraded",
                llm_enabled=False,
                provider=self.settings.provider,
                provider_reachable=False,
                selected_model=selected_model,
                model_available=False,
                message="Yerel yapay zekâ bağlantısı bilinçli olarak devre dışı.",
            )

        try:
            models = await self.provider.list_models()
        except (ProviderUnavailableError, ProviderTimeoutError) as error:
            return HealthResponse(
                status="unavailable",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=False,
                selected_model=selected_model,
                model_available=False,
                message=str(error),
            )
        except ProviderResponseError:
            return HealthResponse(
                status="degraded",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=True,
                selected_model=selected_model,
                model_available=False,
                message="Yerel sağlayıcının model listesi doğrulanamadı.",
            )
        except Exception:
            return HealthResponse(
                status="unavailable",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=False,
                selected_model=selected_model,
                model_available=False,
                message="Yerel yapay zekâ sağlık kontrolü tamamlanamadı.",
            )

        if selected_model is None:
            return HealthResponse(
                status="degraded",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=True,
                selected_model=None,
                model_available=False,
                message="Yerel model seçilmedi.",
            )

        model_available = selected_model in {model.name for model in models}
        return HealthResponse(
            status="ok" if model_available else "degraded",
            llm_enabled=True,
            provider=self.settings.provider,
            provider_reachable=True,
            selected_model=selected_model,
            model_available=model_available,
            message=(
                "Yerel yapay zekâ bağlantısı hazır."
                if model_available
                else "Seçilen yerel model yüklü değil."
            ),
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
        try:
            safe_result = self.policy_validator.validate(result, request)
        except ScopeMismatchError:
            safe_result = self.policy_validator.recover_scope_mismatch(result, request)
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

    @staticmethod
    def record_brief_mutation_approval(
        proposed_mutation: ProposedBriefMutation,
        proposal_fingerprint: str,
        current_fingerprint: str,
        proposal_generation_id: int,
        current_generation_id: int,
        user_message: str,
        snapshot: BriefSnapshot,
        *,
        approved_at: datetime | None = None,
    ) -> tuple[BriefSnapshot, BriefMutationApprovalRecord]:
        LocalLLMConversationService.ensure_current_context(
            proposal_fingerprint,
            current_fingerprint,
        )
        if proposal_generation_id != current_generation_id:
            raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

        ts = approved_at or datetime.now(timezone.utc)  # noqa: UP017
        new_snapshot = apply_approved_brief_mutation(
            snapshot,
            proposed_mutation,
            user_message,
            source_reference=current_fingerprint,
            approved_at=ts,
        )

        record = BriefMutationApprovalRecord(
            proposal_status="user_approved",
            approved_at=ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc),  # noqa: UP017
            context_fingerprint=current_fingerprint,
            generation_id=current_generation_id,
            mutation_id=proposed_mutation.mutation_id,
            proposed_brief_mutation=proposed_mutation,
            resulting_brief_version=new_snapshot.brief_version,
        )
        return new_snapshot, record
