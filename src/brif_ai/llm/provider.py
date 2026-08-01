"""Provider boundary and provider-neutral failures."""

from __future__ import annotations

from typing import Protocol

from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)


class LocalLLMError(RuntimeError):
    """Base error safe for translation at the API boundary."""


class ModelNotSelectedError(LocalLLMError):
    """No local model was selected by configuration."""


class ProviderUnavailableError(LocalLLMError):
    """The configured local provider could not be reached."""


class ModelNotAvailableError(LocalLLMError):
    """The selected model is not installed in the local provider."""


class ProviderTimeoutError(LocalLLMError):
    """The local provider exceeded the configured request timeout."""


class ProviderResponseError(LocalLLMError):
    """The provider returned malformed or schema-invalid output."""


class LocalLLMProvider(Protocol):
    """Provider-independent local inference interface used by BRIF.AI."""

    async def health(self) -> ProviderHealth: ...

    async def list_models(self) -> list[LocalModelInfo]: ...

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
    ) -> ArchitecturalIntentResult: ...
