"""Strict contracts for provider-agnostic local LLM conversations."""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.mutation import ProposedBriefMutation
from brif_ai.conversation.elicitation.household import HouseholdComposition
from brif_ai.conversation.elicitation.models import ElicitationContext, ElicitationTopic
from brif_ai.regulatory.models import ComplianceFinding, ProjectRegulatoryContext
from brif_ai.spatial.models import ProposedSpatialRelationship, SpatialRelationshipGraph

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
    visible_entities: list[VisibleEntity] = Field(default_factory=list)
    conversation_summary: str = ""
    current_decisions: list[str] = Field(default_factory=list)
    pending_proposals: list[PendingProposalContext] = Field(default_factory=list)
    brief_snapshot: BriefSnapshot | None = None
    regulatory_context: ProjectRegulatoryContext | None = None
    compliance_findings: list[ComplianceFinding] = Field(default_factory=list)
    elicitation_context: ElicitationContext | None = None

    @model_validator(mode="after")
    def validate_pending_proposals(self) -> ConversationRequest:
        if (
            self.brief_snapshot is not None
            and self.brief_snapshot.project_id != self.active_context.project_id
        ):
            raise ValueError("brief snapshot project_id must match active context project_id")
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
            if proposal.action is not None:
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
    action: ProposedAction | None = None
    brief_mutation: ProposedBriefMutation | None = None
    spatial_relationship: ProposedSpatialRelationship | None = None

    @model_validator(mode="after")
    def validate_proposal_content_xor(self) -> PendingProposalContext:
        proposals = [self.action, self.brief_mutation, self.spatial_relationship]
        non_none_count = sum(1 for p in proposals if p is not None)
        if non_none_count != 1:
            raise ValueError(
                "Exactly one of action, brief_mutation, or spatial_relationship must be populated "
                "in PendingProposalContext"
            )
        return self


class ArchitecturalIntentResult(StrictContract):
    assistant_message: NonEmptyString
    intent: IntentType
    target: EntityTarget
    user_requirements: list[str]
    interpreted_priorities: list[str]
    constraints_to_check: list[str]
    missing_information: list[str]
    proposed_actions: list[ProposedAction]
    proposed_brief_mutations: list[ProposedBriefMutation] = Field(default_factory=list)
    proposed_spatial_relationships: list[ProposedSpatialRelationship] = Field(default_factory=list)
    household_composition: HouseholdComposition | None = None
    answers_current_open_question: bool = False
    needs_follow_up: bool
    follow_up_question: NonEmptyString | None = None
    follow_up_topic: ElicitationTopic | None = None
    needs_user_confirmation: bool
    confidence: float = Field(ge=0, le=1)
    warnings: list[str]

    @model_validator(mode="after")
    def validate_safety_invariants(self) -> ArchitecturalIntentResult:
        if self.needs_follow_up:
            if self.follow_up_question is None:
                raise ValueError("follow_up_question is required when needs_follow_up is true")
            if self.follow_up_topic is None:
                raise ValueError("follow_up_topic is required when needs_follow_up is true")
        else:
            if self.follow_up_topic is not None:
                raise ValueError("follow_up_topic must be None when needs_follow_up is false")
            if self.follow_up_question is not None:
                raise ValueError("follow_up_question must be None when needs_follow_up is false")

        # Invariant: If spatial relationships are present, enforce safety invariants
        if self.proposed_spatial_relationships:
            if not self.needs_user_confirmation:
                raise ValueError("proposed spatial relationships require user confirmation")
            if self.needs_follow_up:
                raise ValueError(
                    "needs_follow_up must be false when spatial relationships are present"
                )
            if self.proposed_actions:
                raise ValueError("cannot mix proposed spatial relationships with proposed actions")
            if self.proposed_brief_mutations:
                raise ValueError(
                    "cannot mix proposed spatial relationships with proposed brief mutations"
                )

        # Enforce single proposal category in V0 (mutations vs actions)
        if self.proposed_brief_mutations and self.proposed_actions:
            raise ValueError("cannot mix proposed brief mutations with proposed actions")

        # Hardening Invariant 4: If result contains proposals, needs_follow_up MUST be False
        if (
            self.proposed_brief_mutations
            or self.proposed_actions
            or self.proposed_spatial_relationships
        ) and self.needs_follow_up:
            raise ValueError("needs_follow_up must be false when proposals are present")

        if self.proposed_actions and not self.needs_user_confirmation:
            raise ValueError("proposed actions require user confirmation")

        if self.proposed_brief_mutations and not self.needs_user_confirmation:
            raise ValueError("proposed brief mutations require user confirmation")

        if self.intent is IntentType.COMPARE_ALTERNATIVES and self.proposed_brief_mutations:
            raise ValueError("compare_alternatives cannot produce brief mutations")

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

        if self.answers_current_open_question:
            if not self.proposed_brief_mutations and not self.proposed_spatial_relationships:
                raise ValueError(
                    "answers_current_open_question requires at least one proposed_brief_mutation "
                    "or proposed_spatial_relationship"
                )
            if self.needs_follow_up:
                raise ValueError(
                    "answers_current_open_question and needs_follow_up cannot both be true"
                )

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
    resulting_brief_snapshot: BriefSnapshot | None = None


class ProposalApprovalRecord(StrictContract):
    proposal_status: str
    approved_at: datetime
    context_fingerprint: NonEmptyString
    proposed_action: ProposedAction


class BriefMutationApprovalRecord(StrictContract):
    proposal_status: Literal["user_approved"] = "user_approved"
    approved_at: datetime
    context_fingerprint: NonEmptyString
    generation_id: int = Field(ge=0)
    mutation_id: NonEmptyString
    proposed_brief_mutation: ProposedBriefMutation
    resulting_brief_version: int = Field(ge=1)


class BriefMutationApprovalRequest(StrictContract):
    brief_snapshot: BriefSnapshot
    proposed_mutation: ProposedBriefMutation
    current_project_id: NonEmptyString
    expected_brief_version: int = Field(ge=1)
    proposal_fingerprint: NonEmptyString
    current_fingerprint: NonEmptyString
    proposal_generation_id: int = Field(ge=0)
    current_generation_id: int = Field(ge=0)
    user_message: str
    source_reference: NonEmptyString
    answers_current_open_question: bool = False

    @model_validator(mode="after")
    def validate_project_context(self) -> BriefMutationApprovalRequest:
        if self.brief_snapshot.project_id != self.current_project_id:
            raise ValueError(
                f"brief_snapshot project_id '{self.brief_snapshot.project_id}' "
                f"does not match current_project_id '{self.current_project_id}'"
            )
        return self


class BriefMutationApprovalResponse(StrictContract):
    success: bool
    resulting_snapshot: BriefSnapshot | None = None
    approval_record: BriefMutationApprovalRecord | None = None
    error: str | None = None


class SpatialRelationshipApprovalRecord(StrictContract):
    proposal_status: Literal["user_approved"] = "user_approved"
    approved_at: datetime
    context_fingerprint: NonEmptyString
    generation_id: int = Field(ge=0)
    proposed_spatial_relationship: ProposedSpatialRelationship
    resulting_brief_version: int = Field(ge=1)
    resulting_evidence_id: NonEmptyString


class SpatialRelationshipApprovalRequest(StrictContract):
    brief_snapshot: BriefSnapshot
    proposed_relationship: ProposedSpatialRelationship
    current_project_id: NonEmptyString
    expected_brief_version: int = Field(ge=1)
    proposal_fingerprint: NonEmptyString
    current_fingerprint: NonEmptyString
    proposal_generation_id: int = Field(ge=0)
    current_generation_id: int = Field(ge=0)
    user_message: str
    source_reference: NonEmptyString
    answers_current_open_question: bool = False

    @model_validator(mode="after")
    def validate_project_context(self) -> SpatialRelationshipApprovalRequest:
        if self.brief_snapshot.project_id != self.current_project_id:
            raise ValueError(
                f"brief_snapshot project_id '{self.brief_snapshot.project_id}' "
                f"does not match current_project_id '{self.current_project_id}'"
            )
        return self


class SpatialRelationshipApprovalResponse(StrictContract):
    success: bool
    resulting_snapshot: BriefSnapshot | None = None
    resulting_spatial_graph: SpatialRelationshipGraph | None = None
    approval_record: SpatialRelationshipApprovalRecord | None = None
    error: str | None = None
