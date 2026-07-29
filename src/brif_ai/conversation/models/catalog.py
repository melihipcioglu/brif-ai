"""Question catalog contracts for BRIF.AI conversation flow v0."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Literal

from pydantic import (
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from brif_ai.conversation.models.common import (
    AnswerType,
    ConditionType,
    ConversationModule,
    FulfillmentPolicy,
    QuestionStatus,
)
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)]
ConditionScalar = StrictStr | StrictBool | StrictInt


def _first_duplicate(values: Iterable[object]) -> object | None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


class InformationTargetDefinition(ContractModel):
    id: ObjectId
    module: ConversationModule
    purpose: NonEmptyString
    required: bool
    fulfillment_policy: FulfillmentPolicy


class QuestionOption(ContractModel):
    id: ObjectId
    value: StrictStr
    content_key: NonEmptyString
    display_order: int = Field(ge=1)


class QuestionDefinition(ContractModel):
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
    options: list[QuestionOption]

    @field_validator("output_target_ids", "allowed_follow_up_question_ids")
    @classmethod
    def reject_duplicate_references(cls, value: list[str]) -> list[str]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate reference id {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_options(self) -> QuestionDefinition:
        choice_types = {AnswerType.SINGLE_CHOICE, AnswerType.MULTIPLE_CHOICE}
        if self.answer_type in choice_types and not self.options:
            raise ValueError(f"{self.answer_type.value} questions require at least one option")
        if self.answer_type not in choice_types and self.options:
            raise ValueError(f"{self.answer_type.value} questions cannot define options")

        duplicate_option_id = _first_duplicate(option.id for option in self.options)
        if duplicate_option_id is not None:
            raise ValueError(f"duplicate option id {duplicate_option_id!r}")

        duplicate_option_value = _first_duplicate(option.value for option in self.options)
        if duplicate_option_value is not None:
            raise ValueError(f"duplicate option value {duplicate_option_value!r}")

        return self


class AnswerEqualsCondition(ContractModel):
    type: Literal[ConditionType.ANSWER_EQUALS] = ConditionType.ANSWER_EQUALS
    question_id: ObjectId
    expected_value: ConditionScalar


class AnswerIncludesCondition(ContractModel):
    type: Literal[ConditionType.ANSWER_INCLUDES] = ConditionType.ANSWER_INCLUDES
    question_id: ObjectId
    expected_value: StrictStr


class AnswerGreaterThanCondition(ContractModel):
    type: Literal[ConditionType.ANSWER_GREATER_THAN] = ConditionType.ANSWER_GREATER_THAN
    question_id: ObjectId
    expected_value: StrictInt


class QuestionAnsweredCondition(ContractModel):
    type: Literal[ConditionType.QUESTION_ANSWERED] = ConditionType.QUESTION_ANSWERED
    question_id: ObjectId


class QuestionSkippedCondition(ContractModel):
    type: Literal[ConditionType.QUESTION_SKIPPED] = ConditionType.QUESTION_SKIPPED
    question_id: ObjectId


class BriefItemConfirmedCondition(ContractModel):
    type: Literal[ConditionType.BRIEF_ITEM_CONFIRMED] = ConditionType.BRIEF_ITEM_CONFIRMED
    brief_item_id: ObjectId


class ContradictionOpenCondition(ContractModel):
    type: Literal[ConditionType.CONTRADICTION_OPEN] = ConditionType.CONTRADICTION_OPEN
    contradiction_id: ObjectId


TransitionCondition = Annotated[
    AnswerEqualsCondition
    | AnswerIncludesCondition
    | AnswerGreaterThanCondition
    | QuestionAnsweredCondition
    | QuestionSkippedCondition
    | BriefItemConfirmedCondition
    | ContradictionOpenCondition,
    Field(discriminator="type"),
]


class TransitionRule(ContractModel):
    id: ObjectId
    source_question_id: ObjectId
    condition: TransitionCondition
    target_question_id: ObjectId | None = None
    target_module: ConversationModule | None = None
    priority: int = Field(ge=1)

    @model_validator(mode="after")
    def require_exactly_one_target(self) -> TransitionRule:
        has_target_question = self.target_question_id is not None
        has_target_module = self.target_module is not None
        if has_target_question == has_target_module:
            raise ValueError("transition rule requires exactly one target")
        return self


CatalogObject = InformationTargetDefinition | QuestionDefinition | QuestionOption | TransitionRule


class QuestionCatalog(ContractModel):
    id: ObjectId
    schema_version: NonEmptyString
    catalog_version: int = Field(ge=1)
    modules: list[ConversationModule]
    information_targets: list[InformationTargetDefinition]
    questions: list[QuestionDefinition]
    transition_rules: list[TransitionRule]

    @field_validator("modules")
    @classmethod
    def reject_duplicate_modules(cls, value: list[ConversationModule]) -> list[ConversationModule]:
        duplicate = _first_duplicate(value)
        if duplicate is not None:
            raise ValueError(f"duplicate module {duplicate!r}")
        return value

    @model_validator(mode="after")
    def validate_catalog_integrity(self) -> QuestionCatalog:
        self._validate_unique_object_ids()

        module_ids = set(self.modules)
        target_ids = {target.id for target in self.information_targets}
        question_ids = {question.id for question in self.questions}

        for target in self.information_targets:
            if target.module not in module_ids:
                raise ValueError(
                    f"information target {target.id!r} references unknown module {target.module!r}"
                )

        for question in self.questions:
            if question.module not in module_ids:
                raise ValueError(
                    f"question {question.id!r} references unknown module {question.module!r}"
                )
            self._validate_target_references(question, target_ids)
            self._validate_follow_up_references(question, question_ids)

        self._validate_transition_references(question_ids, module_ids)
        self._validate_approved_display_orders()
        return self

    def _validate_unique_object_ids(self) -> None:
        seen: dict[str, str] = {}
        collections: list[tuple[str, Iterable[CatalogObject]]] = [
            ("information_target", self.information_targets),
            ("question", self.questions),
            ("transition_rule", self.transition_rules),
        ]
        for question in self.questions:
            collections.append(("question_option", question.options))

        for object_type, objects in collections:
            for item in objects:
                previous_type = seen.get(item.id)
                if previous_type is not None:
                    raise ValueError(
                        f"duplicate object id {item.id!r} used by "
                        f"{previous_type!r} and {object_type!r}"
                    )
                seen[item.id] = object_type

    @staticmethod
    def _validate_target_references(
        question: QuestionDefinition, valid_target_ids: set[str]
    ) -> None:
        for target_id in question.output_target_ids:
            if target_id not in valid_target_ids:
                raise ValueError(
                    f"question {question.id!r} references unknown output_target_id {target_id!r}"
                )

    @staticmethod
    def _validate_follow_up_references(
        question: QuestionDefinition, valid_question_ids: set[str]
    ) -> None:
        for question_id in question.allowed_follow_up_question_ids:
            if question_id not in valid_question_ids:
                raise ValueError(
                    f"question {question.id!r} references unknown follow_up_question_id "
                    f"{question_id!r}"
                )

    def _validate_transition_references(
        self, valid_question_ids: set[str], valid_modules: set[ConversationModule]
    ) -> None:
        for rule in self.transition_rules:
            if rule.source_question_id not in valid_question_ids:
                raise ValueError(
                    f"transition rule {rule.id!r} references unknown source_question_id "
                    f"{rule.source_question_id!r}"
                )
            if (
                rule.target_question_id is not None
                and rule.target_question_id not in valid_question_ids
            ):
                raise ValueError(
                    f"transition rule {rule.id!r} references unknown target_question_id "
                    f"{rule.target_question_id!r}"
                )
            if rule.target_module is not None and rule.target_module not in valid_modules:
                raise ValueError(
                    f"transition rule {rule.id!r} references unknown target_module "
                    f"{rule.target_module!r}"
                )

            condition_question_id = _condition_question_id(rule.condition)
            if (
                condition_question_id is not None
                and condition_question_id not in valid_question_ids
            ):
                raise ValueError(
                    f"transition rule {rule.id!r} references unknown condition question_id "
                    f"{condition_question_id!r}"
                )

    def _validate_approved_display_orders(self) -> None:
        seen: dict[tuple[ConversationModule, int], str] = {}
        for question in self.questions:
            if question.status is not QuestionStatus.APPROVED:
                continue
            key = (question.module, question.display_order)
            previous_question_id = seen.get(key)
            if previous_question_id is not None:
                raise ValueError(
                    f"approved question display_order {question.display_order!r} in "
                    f"module {question.module.value!r} is used by {previous_question_id!r} "
                    f"and {question.id!r}"
                )
            seen[key] = question.id


def _condition_question_id(condition: TransitionCondition) -> str | None:
    if isinstance(
        condition,
        (
            AnswerEqualsCondition,
            AnswerIncludesCondition,
            AnswerGreaterThanCondition,
            QuestionAnsweredCondition,
            QuestionSkippedCondition,
        ),
    ):
        return condition.question_id
    return None
