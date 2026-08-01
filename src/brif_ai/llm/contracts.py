"""Strict contracts for provider-agnostic local LLM conversations."""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover - compatibility for local Python 3.10 tooling

    class StrEnum(str, Enum):  # noqa: UP042
        pass


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictContract(BaseModel):
    """Reject model- or client-supplied fields outside the published contract."""

    model_config = ConfigDict(extra="forbid")


class IntentType(StrEnum):
    GATHER_REQUIREMENT = "gather_requirement"
    MODIFY_SPACE = "modify_space"
    MODIFY_RELATIONSHIP = "modify_relationship"
    EXPLAIN_PLAN = "explain_plan"
    COMPARE_ALTERNATIVES = "compare_alternatives"
    INSPECT_CONSTRAINT = "inspect_constraint"
    REQUEST_VISUAL_PREFERENCE = "request_visual_preference"
    UNKNOWN = "unknown"


class ActionType(StrEnum):
    HIGHLIGHT_ENTITY = "highlight_entity"
    FOCUS_ENTITY = "focus_entity"
    EXPLAIN_PLAN = "explain_plan"
    REQUEST_CLARIFICATION = "request_clarification"
    SUGGEST_SPACE_RESIZE = "suggest_space_resize"
    SUGGEST_RELATIONSHIP_CHANGE = "suggest_relationship_change"
    SUGGEST_ORIENTATION_CHANGE = "suggest_orientation_change"
    COMPARE_ALTERNATIVES = "compare_alternatives"
    INSPECT_CONSTRAINT = "inspect_constraint"


PLAN_CHANGE_ACTIONS = frozenset(
    {
        ActionType.SUGGEST_SPACE_RESIZE,
        ActionType.SUGGEST_RELATIONSHIP_CHANGE,
        ActionType.SUGGEST_ORIENTATION_CHANGE,
    }
)


class ActiveContextSnapshot(StrictContract):
    project_id: NonEmptyString
    building_id: NonEmptyString | None = None
    level_id: NonEmptyString | None = None
    zone_id: NonEmptyString | None = None
    entity_id: NonEmptyString | None = None
    context_fingerprint: NonEmptyString
    generation_id: int = Field(ge=0)


class VisibleEntity(StrictContract):
    entity_id: NonEmptyString
    entity_type: NonEmptyString
    name: NonEmptyString
    project_id: NonEmptyString
    building_id: NonEmptyString | None = None
    level_id: NonEmptyString | None = None
    zone_id: NonEmptyString | None = None


class ConversationRequest(StrictContract):
    message: NonEmptyString
    active_context: ActiveContextSnapshot
    visible_entities: list[VisibleEntity]
    conversation_summary: str = ""
    current_decisions: list[str] = Field(default_factory=list)


class EntityTarget(StrictContract):
    project_id: NonEmptyString | None = None
    building_id: NonEmptyString | None = None
    level_id: NonEmptyString | None = None
    zone_id: NonEmptyString | None = None
    entity_id: NonEmptyString | None = None


class ProposedAction(StrictContract):
    action_type: ActionType
    target_entity_id: NonEmptyString | None = None
    description: NonEmptyString
    requires_user_confirmation: bool


class ArchitecturalIntentResult(StrictContract):
    assistant_message: NonEmptyString
    intent: IntentType
    target: EntityTarget
    user_requirements: list[str]
    interpreted_priorities: list[str]
    constraints_to_check: list[str]
    missing_information: list[str]
    proposed_actions: list[ProposedAction]
    needs_follow_up: bool
    follow_up_question: NonEmptyString | None
    needs_user_confirmation: bool
    confidence: float = Field(ge=0, le=1)
    warnings: list[str]

    @model_validator(mode="after")
    def validate_safety_invariants(self) -> ArchitecturalIntentResult:
        if self.needs_follow_up and self.follow_up_question is None:
            raise ValueError("follow_up_question is required when needs_follow_up is true")

        if self.proposed_actions and not self.needs_user_confirmation:
            raise ValueError("proposed actions require user confirmation")

        for action in self.proposed_actions:
            if action.action_type in PLAN_CHANGE_ACTIONS:
                target_entity_id = action.target_entity_id or self.target.entity_id
                if target_entity_id is None:
                    raise ValueError("a plan change suggestion requires a known target entity")
                if not action.requires_user_confirmation:
                    raise ValueError("plan change suggestions require explicit user confirmation")

        if self.intent is IntentType.EXPLAIN_PLAN and any(
            action.action_type in PLAN_CHANGE_ACTIONS for action in self.proposed_actions
        ):
            raise ValueError("explain_plan cannot contain plan change suggestions")

        return self


class ProviderHealth(StrictContract):
    provider: NonEmptyString
    reachable: bool
    message: str | None = None


class LocalModelInfo(StrictContract):
    name: NonEmptyString
    digest: str | None = None
    size: int | None = Field(default=None, ge=0)
    modified_at: str | None = None


class HealthResponse(StrictContract):
    status: str
    llm_enabled: bool
    provider: str
    provider_reachable: bool
    selected_model: str | None
    model_available: bool


class ConversationInterpretationResponse(StrictContract):
    success: bool
    llm_enabled: bool
    provider: str
    model: str | None
    context_fingerprint: str
    generation_id: int = Field(ge=0)
    result: ArchitecturalIntentResult | None
    error: str | None


class ProposalApprovalRecord(StrictContract):
    proposal_status: str
    approved_at: datetime
    context_fingerprint: NonEmptyString
    proposed_action: ProposedAction
