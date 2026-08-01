"""Provider-agnostic local LLM integration for BRIF.AI."""

from brif_ai.llm.contracts import (
    ActionType,
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationInterpretationResponse,
    ConversationRequest,
    EntityTarget,
    HealthResponse,
    IntentType,
    LocalModelInfo,
    ProposalApprovalRecord,
    ProposedAction,
    ProviderHealth,
    VisibleEntity,
)
from brif_ai.llm.ollama_provider import OllamaProvider
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
)
from brif_ai.llm.provider import LocalLLMProvider
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings

__all__ = [
    "ActionType",
    "ActiveContextSnapshot",
    "ArchitecturalIntentPolicyValidator",
    "ArchitecturalIntentResult",
    "ConversationInterpretationResponse",
    "ConversationRequest",
    "EntityTarget",
    "HealthResponse",
    "IntentType",
    "LocalLLMConversationService",
    "LocalLLMProvider",
    "LocalLLMSettings",
    "LocalModelInfo",
    "OllamaProvider",
    "PolicyValidationError",
    "ProposalApprovalRecord",
    "ProposedAction",
    "ProviderHealth",
    "VisibleEntity",
]
