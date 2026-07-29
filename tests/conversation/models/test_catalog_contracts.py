from __future__ import annotations

import pytest
from pydantic import ValidationError

from brif_ai.conversation.models import (
    AnswerEqualsCondition,
    AnswerGreaterThanCondition,
    AnswerIncludesCondition,
    AnswerType,
    BriefItemConfirmedCondition,
    ConditionType,
    ContradictionOpenCondition,
    ConversationModule,
    FulfillmentPolicy,
    InformationTargetDefinition,
    QuestionAnsweredCondition,
    QuestionCatalog,
    QuestionDefinition,
    QuestionOption,
    QuestionSkippedCondition,
    QuestionStatus,
    TransitionCondition,
    TransitionRule,
)


def _target(
    target_id: str = "target_1",
    module: ConversationModule = ConversationModule.PROJECT_CONTEXT,
) -> InformationTargetDefinition:
    return InformationTargetDefinition(
        id=target_id,
        module=module,
        purpose="Capture project context.",
        required=True,
        fulfillment_policy=FulfillmentPolicy.VALID_ANSWER,
    )


def _option(
    option_id: str = "option_1",
    value: str = "yes",
    display_order: int = 1,
) -> QuestionOption:
    return QuestionOption(
        id=option_id,
        value=value,
        content_key=f"option.{option_id}",
        display_order=display_order,
    )


def _question(
    question_id: str = "question_1",
    *,
    module: ConversationModule = ConversationModule.PROJECT_CONTEXT,
    answer_type: AnswerType = AnswerType.FREE_TEXT,
    output_target_ids: list[str] | None = None,
    allowed_follow_up_question_ids: list[str] | None = None,
    display_order: int = 1,
    status: QuestionStatus = QuestionStatus.APPROVED,
    options: list[QuestionOption] | None = None,
) -> QuestionDefinition:
    return QuestionDefinition(
        id=question_id,
        module=module,
        purpose="Ask for a controlled catalog input.",
        content_key=f"question.{question_id}",
        answer_type=answer_type,
        required=True,
        output_target_ids=output_target_ids if output_target_ids is not None else ["target_1"],
        allowed_follow_up_question_ids=(
            allowed_follow_up_question_ids if allowed_follow_up_question_ids is not None else []
        ),
        applicable_stakeholder_roles=["owner"],
        display_order=display_order,
        source_metadata="expert-reviewed:v0",
        status=status,
        options=options if options is not None else [],
    )


def _transition_rule(
    rule_id: str = "transition_1",
    *,
    source_question_id: str = "question_1",
    condition: TransitionCondition | None = None,
    target_question_id: str | None = None,
    target_module: ConversationModule | None = ConversationModule.STAKEHOLDERS,
) -> TransitionRule:
    return TransitionRule(
        id=rule_id,
        source_question_id=source_question_id,
        condition=condition
        if condition is not None
        else QuestionAnsweredCondition(question_id=source_question_id),
        target_question_id=target_question_id,
        target_module=target_module,
        priority=1,
    )


def _catalog(
    *,
    modules: list[ConversationModule] | None = None,
    information_targets: list[InformationTargetDefinition] | None = None,
    questions: list[QuestionDefinition] | None = None,
    transition_rules: list[TransitionRule] | None = None,
) -> QuestionCatalog:
    return QuestionCatalog(
        id="catalog_1",
        schema_version="conversation.catalog.v0",
        catalog_version=1,
        modules=modules
        if modules is not None
        else [ConversationModule.PROJECT_CONTEXT, ConversationModule.STAKEHOLDERS],
        information_targets=information_targets if information_targets is not None else [_target()],
        questions=questions if questions is not None else [_question()],
        transition_rules=transition_rules if transition_rules is not None else [],
    )


def test_valid_minimum_question_catalog() -> None:
    catalog = _catalog()

    assert catalog.id == "catalog_1"
    assert catalog.catalog_version == 1
    assert catalog.questions[0].status is QuestionStatus.APPROVED


def test_allows_draft_and_retired_questions() -> None:
    catalog = _catalog(
        questions=[
            _question("question_1", status=QuestionStatus.DRAFT),
            _question("question_2", status=QuestionStatus.RETIRED),
        ]
    )

    assert [question.status for question in catalog.questions] == [
        QuestionStatus.DRAFT,
        QuestionStatus.RETIRED,
    ]
    assert [question.display_order for question in catalog.questions] == [1, 1]


def test_rejects_invalid_catalog_id() -> None:
    with pytest.raises(ValidationError) as error:
        QuestionCatalog(
            id="Catalog 1",
            schema_version="conversation.catalog.v0",
            catalog_version=1,
            modules=[ConversationModule.PROJECT_CONTEXT],
            information_targets=[_target()],
            questions=[_question()],
            transition_rules=[],
        )

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("id",)
    assert first_error["type"] == "string_pattern_mismatch"


def test_rejects_duplicate_id_across_catalog_object_types() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(information_targets=[_target("question_1")])

    assert "duplicate object id 'question_1'" in str(error.value)


def test_rejects_duplicate_modules() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(modules=[ConversationModule.PROJECT_CONTEXT, ConversationModule.PROJECT_CONTEXT])

    assert "duplicate module" in str(error.value)


def test_rejects_question_with_unknown_module() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(
            modules=[ConversationModule.PROJECT_CONTEXT],
            questions=[_question(module=ConversationModule.STAKEHOLDERS)],
        )

    assert "question 'question_1' references unknown module" in str(error.value)


def test_rejects_information_target_with_unknown_module() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(
            modules=[ConversationModule.PROJECT_CONTEXT],
            information_targets=[_target(module=ConversationModule.STAKEHOLDERS)],
        )

    assert "information target 'target_1' references unknown module" in str(error.value)


def test_rejects_unknown_output_target_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(questions=[_question(output_target_ids=["missing_target"])])

    assert "output_target_id 'missing_target'" in str(error.value)


def test_rejects_unknown_follow_up_question_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(questions=[_question(allowed_follow_up_question_ids=["missing_question"])])

    assert "follow_up_question_id 'missing_question'" in str(error.value)


def test_rejects_unknown_transition_source_question() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(transition_rules=[_transition_rule(source_question_id="missing_question")])

    assert "source_question_id 'missing_question'" in str(error.value)


def test_rejects_unknown_transition_target_question() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(
            questions=[
                _question("question_1"),
                _question("question_2", display_order=2),
            ],
            transition_rules=[
                _transition_rule(target_question_id="missing_question", target_module=None)
            ],
        )

    assert "target_question_id 'missing_question'" in str(error.value)


def test_rejects_unknown_transition_target_module() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(
            modules=[ConversationModule.PROJECT_CONTEXT],
            transition_rules=[_transition_rule(target_module=ConversationModule.STAKEHOLDERS)],
        )

    assert "target_module" in str(error.value)
    assert "STAKEHOLDERS" in str(error.value)


def test_rejects_unknown_transition_condition_question() -> None:
    condition = AnswerEqualsCondition(question_id="missing_question", expected_value="yes")

    with pytest.raises(ValidationError) as error:
        _catalog(transition_rules=[_transition_rule(condition=condition)])

    assert "condition question_id 'missing_question'" in str(error.value)


def test_single_choice_requires_options() -> None:
    with pytest.raises(ValidationError) as error:
        _question(answer_type=AnswerType.SINGLE_CHOICE)

    assert "SINGLE_CHOICE questions require at least one option" in str(error.value)


def test_multiple_choice_requires_options() -> None:
    with pytest.raises(ValidationError) as error:
        _question(answer_type=AnswerType.MULTIPLE_CHOICE)

    assert "MULTIPLE_CHOICE questions require at least one option" in str(error.value)


def test_rejects_options_for_free_text_question() -> None:
    with pytest.raises(ValidationError) as error:
        _question(options=[_option()])

    assert "FREE_TEXT questions cannot define options" in str(error.value)


def test_rejects_duplicate_option_value() -> None:
    with pytest.raises(ValidationError) as error:
        _question(
            answer_type=AnswerType.SINGLE_CHOICE,
            options=[
                _option("option_1", "yes"),
                _option("option_2", "yes", 2),
            ],
        )

    assert "duplicate option value 'yes'" in str(error.value)


def test_rejects_duplicate_option_id() -> None:
    with pytest.raises(ValidationError) as error:
        _question(
            answer_type=AnswerType.SINGLE_CHOICE,
            options=[
                _option("option_1", "yes"),
                _option("option_1", "no", 2),
            ],
        )

    assert "duplicate option id 'option_1'" in str(error.value)


def test_rejects_duplicate_question_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _question(allowed_follow_up_question_ids=["question_2", "question_2"])

    assert "duplicate reference id 'question_2'" in str(error.value)


def test_rejects_transition_with_both_targets() -> None:
    with pytest.raises(ValidationError) as error:
        _transition_rule(
            target_question_id="question_2", target_module=ConversationModule.STAKEHOLDERS
        )

    assert "transition rule requires exactly one target" in str(error.value)


def test_rejects_transition_without_target() -> None:
    with pytest.raises(ValidationError) as error:
        _transition_rule(target_question_id=None, target_module=None)

    assert "transition rule requires exactly one target" in str(error.value)


def test_answer_equals_condition_accepts_only_its_fields() -> None:
    condition = AnswerEqualsCondition(question_id="question_1", expected_value=True)

    assert condition.type is ConditionType.ANSWER_EQUALS
    assert condition.expected_value is True

    with pytest.raises(ValidationError) as error:
        AnswerEqualsCondition.model_validate(
            {
                "type": "ANSWER_EQUALS",
                "question_id": "question_1",
                "expected_value": "yes",
                "unexpected": "field",
            }
        )

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("unexpected",)
    assert first_error["type"] == "extra_forbidden"


def test_question_skipped_condition_rejects_expected_value() -> None:
    with pytest.raises(ValidationError) as error:
        QuestionSkippedCondition.model_validate(
            {
                "type": "QUESTION_SKIPPED",
                "question_id": "question_1",
                "expected_value": "yes",
            }
        )

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("expected_value",)
    assert first_error["type"] == "extra_forbidden"


def test_rejects_duplicate_approved_display_order_in_module() -> None:
    with pytest.raises(ValidationError) as error:
        _catalog(
            questions=[
                _question("question_1", display_order=1),
                _question("question_2", display_order=1),
            ]
        )

    assert "approved question display_order 1" in str(error.value)
    assert "question_1" in str(error.value)
    assert "question_2" in str(error.value)


def test_allows_duplicate_display_order_for_nonapproved_questions() -> None:
    catalog = _catalog(
        questions=[
            _question("question_1", display_order=1, status=QuestionStatus.DRAFT),
            _question("question_2", display_order=1, status=QuestionStatus.RETIRED),
        ]
    )

    assert [question.id for question in catalog.questions] == ["question_1", "question_2"]


def test_serializes_catalog_and_discriminated_conditions() -> None:
    condition = AnswerIncludesCondition(question_id="question_1", expected_value="quiet")
    rule = _transition_rule(
        condition=condition,
        target_question_id="question_2",
        target_module=None,
    )
    catalog = _catalog(
        questions=[
            _question("question_1"),
            _question("question_2", display_order=2),
        ],
        transition_rules=[rule],
    )

    dumped = catalog.model_dump(mode="json")
    json_output = catalog.model_dump_json()
    round_trip = QuestionCatalog.model_validate(dumped)

    assert dumped["transition_rules"][0]["condition"]["type"] == "ANSWER_INCLUDES"
    assert dumped["transition_rules"][0]["condition"]["expected_value"] == "quiet"
    assert '"type":"ANSWER_INCLUDES"' in json_output
    assert round_trip.transition_rules[0].condition.type is ConditionType.ANSWER_INCLUDES


def test_other_condition_models_serialize_expected_type_values() -> None:
    greater_than = AnswerGreaterThanCondition(question_id="question_1", expected_value=2)
    answered = QuestionAnsweredCondition(question_id="question_1")

    assert greater_than.model_dump(mode="json")["type"] == "ANSWER_GREATER_THAN"
    assert answered.model_dump(mode="json")["type"] == "QUESTION_ANSWERED"


def test_catalog_accepts_conditions_without_question_references() -> None:
    rules = [
        _transition_rule(
            rule_id="rule_1",
            condition=BriefItemConfirmedCondition(brief_item_id="brief_item_1"),
        ),
        _transition_rule(
            rule_id="rule_2",
            condition=ContradictionOpenCondition(contradiction_id="contradiction_1"),
            target_question_id="question_2",
            target_module=None,
        ),
    ]

    catalog = _catalog(
        questions=[
            _question("question_1"),
            _question("question_2", display_order=2),
        ],
        transition_rules=rules,
    )

    assert catalog.transition_rules[0].condition.type is ConditionType.BRIEF_ITEM_CONFIRMED
    assert catalog.transition_rules[1].condition.type is ConditionType.CONTRADICTION_OPEN
