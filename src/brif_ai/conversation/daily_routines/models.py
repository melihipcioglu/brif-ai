"""Pydantic data models for BRIF.AI Daily Routines v0 content pack contracts."""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    Field,
    StrictBool,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from brif_ai.conversation.daily_routines.enums import (
    AnswerValidityState,
    CorrectionTarget,
    DayPatternStatus,
    DayPeriod,
    FunctionalDomain,
    HouseholdVariationStatus,
    RecurringDayContext,
    TargetClosureEffect,
    WordingBranch,
)
from brif_ai.conversation.models.common import AnswerType, ConversationModule, QuestionStatus
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)]


class OptionDefinition(ContractModel):
    id: ObjectId
    value: StrictStr
    display_label: NonEmptyString
    helper_text: NonEmptyString
    display_order: int = Field(ge=1)


class OptionSet(ContractModel):
    id: ObjectId
    options: list[OptionDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_options(self) -> OptionSet:
        seen_ids: set[str] = set()
        seen_values: set[str] = set()
        for opt in self.options:
            if opt.id in seen_ids:
                raise ValueError(f"duplicate option id {opt.id!r} in option set {self.id!r}")
            if opt.value in seen_values:
                raise ValueError(f"duplicate option value {opt.value!r} in option set {self.id!r}")
            seen_ids.add(opt.id)
            seen_values.add(opt.value)
        return self


class QuestionWordingVariant(ContractModel):
    branch: WordingBranch
    prompt_text: NonEmptyString
    respondent_instruction: NonEmptyString


class QuestionWording(ContractModel):
    question_id: ObjectId
    variants: list[QuestionWordingVariant] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_branches(self) -> QuestionWording:
        seen_branches: set[WordingBranch] = set()
        for v in self.variants:
            if v.branch in seen_branches:
                raise ValueError(
                    f"duplicate wording branch {v.branch.value!r} for question {self.question_id!r}"
                )
            seen_branches.add(v.branch)
        return self


class DailyRoutinesQuestionDefinition(ContractModel):
    id: ObjectId
    module: ConversationModule
    purpose: NonEmptyString
    content_key: NonEmptyString
    answer_type: AnswerType
    required: bool
    output_target_ids: list[ObjectId] = Field(min_length=1)
    allowed_follow_up_question_ids: list[ObjectId]
    applicable_stakeholder_roles: list[ShortText]
    display_order: int = Field(ge=1)
    source_metadata: ShortText
    status: QuestionStatus
    option_set_id: ObjectId | None = None

    @field_validator("output_target_ids", "allowed_follow_up_question_ids")
    @classmethod
    def reject_duplicate_references(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        for item in value:
            if item in seen:
                raise ValueError(f"duplicate reference id {item!r}")
            seen.add(item)
        return value


QuestionDefinition = DailyRoutinesQuestionDefinition


class UIStateControlDefinition(ContractModel):
    id: ObjectId
    module: ConversationModule
    purpose: NonEmptyString
    content_key: NonEmptyString
    option_set_id: ObjectId


class MultiSelectContract(ContractModel):
    min_selected_items: int = Field(default=1, ge=1)
    max_selected_items: int = Field(default=4, ge=1)
    unique_items: StrictBool = True
    canonical_order: list[DayPeriod] = Field(
        default_factory=lambda: [
            DayPeriod.MORNING,
            DayPeriod.MIDDAY_AFTERNOON,
            DayPeriod.EVENING,
            DayPeriod.NIGHT,
        ]
    )

    @model_validator(mode="after")
    def validate_contract_bounds(self) -> MultiSelectContract:
        if self.min_selected_items > self.max_selected_items:
            raise ValueError("min_selected_items cannot exceed max_selected_items")
        if len(set(self.canonical_order)) != len(self.canonical_order):
            raise ValueError("canonical_order contains duplicate period values")
        return self


class ConditionalRoute(ContractModel):
    selector_value: CorrectionTarget
    target_question_id: ObjectId
    return_step: ObjectId


class FlowRule(ContractModel):
    rule_id: ObjectId
    source_question_id: ObjectId
    expected_value: StrictStr
    target_question_id: ObjectId | None = None
    target_module: NonEmptyString | None = None
    target_closure_effect: TargetClosureEffect
    follow_up_required: StrictBool


class SummaryDomainStatusTemplate(ContractModel):
    reported_periods_available: NonEmptyString
    variable: NonEmptyString
    no_use_reported_in_selected_context: NonEmptyString
    functional_domain_not_available_in_current_home: NonEmptyString
    functional_domain_not_relevant_to_household: NonEmptyString
    unknown: NonEmptyString
    prefer_not_to_answer: NonEmptyString


class SummaryTemplate(ContractModel):
    day_pattern: dict[DayPatternStatus, NonEmptyString]
    recurring_context: dict[RecurringDayContext, NonEmptyString]
    domain_status: dict[WordingBranch, SummaryDomainStatusTemplate]
    periods_label_map: dict[DayPeriod, NonEmptyString]
    household_variation: dict[HouseholdVariationStatus, NonEmptyString]
    domain_names: dict[FunctionalDomain, NonEmptyString]


class ApplicabilityAllowList(ContractModel):
    metadata: NonEmptyString
    description: NonEmptyString
    allowed_domains: dict[FunctionalDomain, StrictBool]


class DomainApplicabilityRule(ContractModel):
    functional_domain_not_relevant_to_household: ApplicabilityAllowList


class AnswerRecord(ContractModel):
    question_id: ObjectId
    value: StrictStr | list[StrictStr]
    validity_state: AnswerValidityState = AnswerValidityState.ACTIVE


class InvalidationRule(ContractModel):
    rule_id: ObjectId
    trigger_event: NonEmptyString
    source_question_id: ObjectId
    trigger_value: StrictStr | None = None
    target_question_ids: list[ObjectId] = Field(min_length=1)
    new_validity_state: AnswerValidityState
    active_branch_effect: WordingBranch | None = None


class DailyRoutinesContentPack(ContractModel):
    schema_version: NonEmptyString
    questions: list[DailyRoutinesQuestionDefinition] = Field(min_length=1)
    ui_state_controls: list[UIStateControlDefinition] = Field(min_length=1)
    option_sets: list[OptionSet] = Field(min_length=1)
    wording_variants: list[QuestionWording] = Field(min_length=1)
    multi_select_contract: MultiSelectContract
    flow_rules: list[FlowRule] = Field(min_length=1)
    conditional_routes: list[ConditionalRoute] = Field(min_length=1)
    summary_templates: SummaryTemplate
    domain_applicability_rules: DomainApplicabilityRule
    invalidation_rules: list[InvalidationRule] = Field(min_length=1)
