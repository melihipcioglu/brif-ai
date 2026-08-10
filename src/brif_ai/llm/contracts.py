"""Strict contracts for provider-agnostic local LLM conversations."""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

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


class CompareMode(StrEnum):
    OPEN_ALTERNATIVES = "open_alternatives"
    EXPLICIT_AXES = "explicit_axes"
    ENTITY_CHOICE = "entity_choice"


class CompareGoalFamily(StrEnum):
    GENERAL_USE = "general_use"
    SOCIAL_INTERACTION = "social_interaction"
    FUNCTIONAL_COORDINATION = "functional_coordination"
    PRIVACY = "privacy"
    FOCUS_COLLABORATION = "focus_collaboration"
    FOCUS = "focus"
    FLEXIBILITY = "flexibility"
    ORDERED_FLOW = "ordered_flow"


class CompareApproach(StrEnum):
    INTEGRATED_FLOW = "integrated_flow"
    PARALLEL_RHYTHMS = "parallel_rhythms"
    ADAPTABLE_USE = "adaptable_use"
    ORDERED_USE = "ordered_use"
    SHARED_ACTIVITY = "shared_activity"
    INDIVIDUAL_BALANCE = "individual_balance"
    PRIVACY_BALANCE = "privacy_balance"
    AXIS_1 = "axis_1"
    AXIS_2 = "axis_2"
    CHOICE_1 = "choice_1"
    CHOICE_2 = "choice_2"


class CompareOutcome(StrEnum):
    CONTINUOUS_INTERACTION = "continuous_interaction"
    INDEPENDENT_SIMULTANEOUS_USE = "independent_simultaneous_use"
    ADAPTABLE_DAILY_USE = "adaptable_daily_use"
    PREDICTABLE_ROUTINE = "predictable_routine"
    CONTROLLED_PERSONAL_USE = "controlled_personal_use"
    EASY_DAILY_USE = "easy_daily_use"
    FOCUSED_ACTIVITY = "focused_activity"
    SHARED_INTERACTION = "shared_interaction"
    ORDER_AND_OVERSIGHT = "order_and_oversight"
    FLEXIBLE_SELF_DIRECTED_USE = "flexible_self_directed_use"
    EXPRESSIVE_CHARACTER = "expressive_character"
    CALM_SIMPLICITY = "calm_simplicity"
    INDIVIDUAL_PRODUCTIVITY = "individual_productivity"
    COLLABORATIVE_PRODUCTIVITY = "collaborative_productivity"
    INDOOR_CONTINUITY = "indoor_continuity"
    OUTDOOR_EXPERIENCE = "outdoor_experience"
    OPEN_SHARED_USE = "open_shared_use"
    SEPARATED_CONTROLLED_USE = "separated_controlled_use"
    CONTEXTUAL_PRIORITY = "contextual_priority"


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
    pending_proposals: list[PendingProposalContext] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pending_proposals(self) -> ConversationRequest:
        visible_ids = {
            entity.entity_id
            for entity in self.visible_entities
            if entity.project_id == self.active_context.project_id
            and (
                self.active_context.building_id is None
                or entity.building_id == self.active_context.building_id
            )
            and (
                self.active_context.level_id is None
                or entity.level_id == self.active_context.level_id
            )
        }
        for proposal in self.pending_proposals:
            if proposal.context_fingerprint != self.active_context.context_fingerprint:
                raise ValueError("pending proposal context fingerprint must match active context")
            if proposal.generation_id != self.active_context.generation_id:
                raise ValueError("pending proposal generation must match active context")
            if not proposal.action.requires_user_confirmation:
                raise ValueError("pending proposal must require user confirmation")
            target_id = proposal.action.target_entity_id
            if target_id is not None and target_id not in visible_ids:
                raise ValueError("pending proposal target must be visible in active context")
        return self


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


class PendingProposalContext(StrictContract):
    status: Literal["pending_user_confirmation"] = "pending_user_confirmation"
    context_fingerprint: NonEmptyString
    generation_id: int = Field(ge=0)
    action: ProposedAction


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


class CompareDecisionPlan(StrictContract):
    mode: CompareMode
    approach_1: CompareApproach
    outcome_1: CompareOutcome
    approach_2: CompareApproach
    outcome_2: CompareOutcome
    confidence: float = Field(ge=0, le=1)


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
    status: Literal["ok", "degraded", "unavailable"]
    llm_enabled: bool
    provider: str
    provider_reachable: bool
    selected_model: str | None
    model_available: bool
    message: str | None = None


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
