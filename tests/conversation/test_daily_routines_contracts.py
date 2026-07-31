"""Comprehensive test suite for BRIF.AI Daily Routines v0 content pack contracts."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest
from pydantic import ValidationError

from brif_ai.conversation.daily_routines import (
    AnswerValidityState,
    ContentPackValidationError,
    CorrectionTarget,
    DailyRoutinesContentPack,
    DayPatternStatus,
    DayPeriod,
    FunctionalDomain,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidationEngine,
    MultiSelectContract,
    OptionSet,
    RecurringDayContext,
    SessionState,
    WordingBranch,
    is_option_allowed_for_domain,
    load_daily_routines_content_pack,
)


@pytest.fixture
def content_pack() -> DailyRoutinesContentPack:
    """Fixture providing loaded and validated Daily Routines content pack."""
    return load_daily_routines_content_pack()


def test_yaml_schema_validation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify that YAML content pack loads and satisfies Pydantic schema validation."""
    assert content_pack.schema_version == "v0"
    assert len(content_pack.questions) == 16
    assert len(content_pack.ui_state_controls) == 1
    assert len(content_pack.option_sets) == 7
    assert len(content_pack.wording_variants) == 16
    assert len(content_pack.invalidation_rules) >= 7


def test_cross_file_reference_validation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify cross-file integrity of references, option sets, and flow rules."""
    q_ids = {q.id for q in content_pack.questions}
    ui_ids = {ui.id for ui in content_pack.ui_state_controls}
    assert "q_daily_routines_functional_space_day_pattern_status" in q_ids
    assert "bp_ui_room_use_correction_selector" in ui_ids

    ms = content_pack.multi_select_contract
    assert ms.min_selected_items == 1
    assert ms.max_selected_items == 4
    assert ms.unique_items is True
    assert ms.canonical_order == [
        DayPeriod.MORNING,
        DayPeriod.MIDDAY_AFTERNOON,
        DayPeriod.EVENING,
        DayPeriod.NIGHT,
    ]


def test_duplicate_id_rejection() -> None:
    """Verify rejection of duplicate option values within an option set."""
    with pytest.raises(ValidationError, match="duplicate option value"):
        OptionSet.model_validate(
            {
                "id": "os_invalid_dup",
                "options": [
                    {
                        "id": "opt_1",
                        "value": "same_val",
                        "display_label": "Label 1",
                        "helper_text": "Help 1",
                        "display_order": 1,
                    },
                    {
                        "id": "opt_2",
                        "value": "same_val",
                        "display_label": "Label 2",
                        "helper_text": "Help 2",
                        "display_order": 2,
                    },
                ],
            }
        )


def test_extra_field_rejection() -> None:
    """Verify that extra fields are rejected on strict Pydantic models."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MultiSelectContract.model_validate(
            {
                "min_selected_items": 1,
                "max_selected_items": 4,
                "unique_items": True,
                "unsupported_extra_field": "disallowed",
            }
        )


def test_unknown_enum_rejection() -> None:
    """Verify that unknown enum strings are rejected."""
    with pytest.raises((ValueError, ValidationError)):
        DayPatternStatus("invalid_enum_value")


def test_stable_branch_flow(content_pack: DailyRoutinesContentPack) -> None:
    """Verify flow logic and invalidation engine for stable recurring day branch."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    assert session.active_branch == WordingBranch.STABLE

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.WORK_FROM_HOME_DAY,
    )

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_periods",
        [DayPeriod.MORNING.value, DayPeriod.EVENING.value],
    )

    summary_lines = engine.generate_summary(session)
    assert any("belirli" in line for line in summary_lines)
    assert any("Evden çalışılan" in line for line in summary_lines)
    assert any("sabah" in line and "akşam" in line for line in summary_lines)


def test_irregular_branch_flow(content_pack: DailyRoutinesContentPack) -> None:
    """Verify flow logic and summary generation for irregular recurring day branch."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.NO_STABLE_RECURRING_DAY,
    )
    assert session.active_branch == WordingBranch.IRREGULAR

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.VARIABLE,
    )

    summary_lines = engine.generate_summary(session)
    assert any("tekrarlanan sabit bir gün örüntüsü bulunmadığı" in line for line in summary_lines)
    assert any("değişken zamanlarda gerçekleştiği" in line for line in summary_lines)


def test_unknown_and_prefer_not_to_answer_closure(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify flow closure when day pattern is unknown or prefer_not_to_answer."""
    engine = InvalidationEngine(content_pack)

    session_a = SessionState()
    engine.record_answer(
        session_a,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.UNKNOWN,
    )
    lines_a = engine.generate_summary(session_a)
    assert any("net bilgi verilemedi" in line for line in lines_a)

    session_b = SessionState()
    engine.record_answer(
        session_b,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.PREFER_NOT_TO_ANSWER,
    )
    lines_b = engine.generate_summary(session_b)
    assert any("paylaşmamayı tercih etti" in line for line in lines_b)


def test_periods_multiselect_bounds() -> None:
    """Verify MultiSelectContract validation bounds."""
    with pytest.raises(
        ValidationError, match="min_selected_items cannot exceed max_selected_items"
    ):
        MultiSelectContract(min_selected_items=5, max_selected_items=4)

    with pytest.raises(ValidationError, match="canonical_order contains duplicate period values"):
        MultiSelectContract(
            canonical_order=[
                DayPeriod.MORNING,
                DayPeriod.MORNING,
                DayPeriod.EVENING,
                DayPeriod.NIGHT,
            ]
        )


def test_canonical_period_ordering(content_pack: DailyRoutinesContentPack) -> None:
    """Verify Turkish multi-period formatting in canonical chronological order."""
    engine = InvalidationEngine(content_pack)

    formatted = engine.format_canonical_periods(
        [DayPeriod.NIGHT.value, DayPeriod.MORNING.value, DayPeriod.MIDDAY_AFTERNOON.value],
        content_pack.summary_templates,
    )
    assert formatted == "**sabah**, **öğle/öğleden sonra** ve **gece**"

    formatted_all = engine.format_canonical_periods(
        [
            DayPeriod.EVENING.value,
            DayPeriod.MORNING.value,
            DayPeriod.NIGHT.value,
            DayPeriod.MIDDAY_AFTERNOON.value,
        ],
        content_pack.summary_templates,
    )
    assert formatted_all == "**sabah**, **öğle/öğleden sonra**, **akşam** ve **gece**"


def test_domain_applicability_filtering(content_pack: DailyRoutinesContentPack) -> None:
    """Verify that sleeping and bathroom domains reject unrelevant household status."""

    val = FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value

    assert is_option_allowed_for_domain(content_pack, FunctionalDomain.LIVING_SOCIAL, val) is True
    assert is_option_allowed_for_domain(content_pack, FunctionalDomain.KITCHEN_DINING, val) is True
    assert is_option_allowed_for_domain(content_pack, FunctionalDomain.WORK_STUDY, val) is True

    assert is_option_allowed_for_domain(content_pack, FunctionalDomain.SLEEPING, val) is False
    assert is_option_allowed_for_domain(content_pack, FunctionalDomain.BATHROOM, val) is False


def test_correction_target_routing(content_pack: DailyRoutinesContentPack) -> None:
    """Verify 9 UI correction target selector routes."""
    routes = {r.selector_value: r for r in content_pack.conditional_routes}
    assert len(routes) == 9

    assert (
        routes[CorrectionTarget.DAY_PATTERN].target_question_id
        == "q_daily_routines_functional_space_day_pattern_status"
    )
    assert (
        routes[CorrectionTarget.SLEEPING].target_question_id
        == "q_daily_routines_functional_space_sleeping_status"
    )
    assert (
        routes[CorrectionTarget.HOUSEHOLD_VARIATION].target_question_id
        == "q_daily_routines_functional_space_household_variation_status"
    )


def test_bidirectional_day_pattern_invalidation(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify answer state transitions when changing day pattern bidirectionally."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.WORK_FROM_HOME_DAY,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.VARIABLE,
    )

    assert session.answers[
        "q_daily_routines_functional_space_living_social_status"
    ].validity_state == (AnswerValidityState.ACTIVE)

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.NO_STABLE_RECURRING_DAY,
    )

    assert (
        session.answers[
            "q_daily_routines_functional_space_recurring_day_context"
        ].validity_state.value
        == AnswerValidityState.INACTIVE_BY_BRANCH.value
    )

    assert (
        session.answers[
            "q_daily_routines_functional_space_living_social_status"
        ].validity_state.value
        == AnswerValidityState.STALE_REQUIRES_RECONFIRMATION.value
    )

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    assert session.active_branch == WordingBranch.STABLE


def test_recurring_context_stale_cascade(content_pack: DailyRoutinesContentPack) -> None:
    """Verify that changing recurring day context marks downstream answers as STALE."""

    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_work_study_status",
        FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE,
    )

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.WORK_FROM_HOME_DAY,
    )

    assert (
        session.answers["q_daily_routines_functional_space_work_study_status"].validity_state.value
        == AnswerValidityState.STALE_REQUIRES_RECONFIRMATION.value
    )


def test_domain_specific_periods_invalidation(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify periods invalidation when domain status changes."""

    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_periods",
        [DayPeriod.EVENING.value],
    )

    assert (
        session.answers[
            "q_daily_routines_functional_space_living_social_periods"
        ].validity_state.value
        == AnswerValidityState.ACTIVE.value
    )

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.VARIABLE,
    )

    assert (
        session.answers[
            "q_daily_routines_functional_space_living_social_periods"
        ].validity_state.value
        == AnswerValidityState.INACTIVE_BY_BRANCH.value
    )


def test_household_detail_invalidation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify household detail invalidation when status changes."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_household_variation_status",
        HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_household_variation_detail",
        "Gece vardiyası çalışması var.",
    )

    assert (
        session.answers[
            "q_daily_routines_functional_space_household_variation_detail"
        ].validity_state.value
        == AnswerValidityState.ACTIVE.value
    )

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_household_variation_status",
        HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE,
    )

    assert (
        session.answers[
            "q_daily_routines_functional_space_household_variation_detail"
        ].validity_state.value
        == AnswerValidityState.INACTIVE_BY_BRANCH.value
    )


def test_confirmation_completion(content_pack: DailyRoutinesContentPack) -> None:
    """Verify confirmation rule routes confirmed to module_complete."""
    rule_map = {r.rule_id: r for r in content_pack.flow_rules}
    assert rule_map["fr_confirm_yes"].target_module == "module_complete"
    assert rule_map["fr_confirm_no"].target_question_id == "bp_ui_room_use_correction_selector"


def test_serialization_round_trip(content_pack: DailyRoutinesContentPack) -> None:
    """Verify serialization round trip (dump to dict/json and re-parse)."""
    dumped_dict = content_pack.model_dump()
    reparsed = DailyRoutinesContentPack.model_validate(dumped_dict)
    assert reparsed.schema_version == content_pack.schema_version
    assert len(reparsed.questions) == len(content_pack.questions)

    dumped_json = content_pack.model_dump_json()
    reparsed_json = DailyRoutinesContentPack.model_validate_json(dumped_json)
    assert reparsed_json.schema_version == content_pack.schema_version


# =============================================================================
# NEGATIVE TEST CASES (Requirement 7)
# =============================================================================


def test_loader_works_when_cwd_changes() -> None:
    """Verify load_daily_routines_content_pack works regardless of working directory."""
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            os.chdir(tmp_dir)
            pack = load_daily_routines_content_pack()
            assert pack.schema_version == "v0"
            assert len(pack.questions) == 16
        finally:
            os.chdir(original_cwd)
            os.chdir(original_cwd)


def test_negative_unknown_flow_source(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when a flow rule references an unknown source_question_id."""
    raw_pack = content_pack.model_dump()
    raw_pack["flow_rules"].append(
        {
            "rule_id": "fr_invalid_source",
            "source_question_id": "q_non_existent_source_id",
            "expected_value": "some_value",
            "target_question_id": "q_daily_routines_functional_space_day_pattern_status",
            "target_module": None,
            "target_closure_effect": "REQUIRES_FOLLOW_UP",
            "follow_up_required": True,
        }
    )
    with pytest.raises(ContentPackValidationError, match="unknown source_question_id"):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_unknown_flow_target(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when a flow rule references an unknown target_question_id."""
    raw_pack = content_pack.model_dump()
    raw_pack["flow_rules"].append(
        {
            "rule_id": "fr_invalid_target",
            "source_question_id": "q_daily_routines_functional_space_day_pattern_status",
            "expected_value": "stable_recurring_day_available",
            "target_question_id": "q_non_existent_target_id",
            "target_module": None,
            "target_closure_effect": "REQUIRES_FOLLOW_UP",
            "follow_up_required": True,
        }
    )
    with pytest.raises(ContentPackValidationError, match="unknown target_question_id"):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_unknown_terminal_target(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when a flow rule specifies an unallowed terminal target_module."""
    raw_pack = content_pack.model_dump()
    raw_pack["flow_rules"].append(
        {
            "rule_id": "fr_invalid_terminal",
            "source_question_id": "q_daily_routines_functional_space_day_pattern_status",
            "expected_value": "stable_recurring_day_available",
            "target_question_id": None,
            "target_module": "unallowed_terminal_module",
            "target_closure_effect": "TARGET_2_FULFILLED",
            "follow_up_required": False,
        }
    )
    with pytest.raises(ContentPackValidationError, match="unknown terminal target_module"):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_invalid_invalidation_state(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an invalidation rule has an invalid new_validity_state."""
    raw_pack = content_pack.model_dump()
    raw_pack["invalidation_rules"][0]["new_validity_state"] = "INVALID_STATE_STRING"
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_duplicate_invalidation_rule(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection of duplicate invalidation rule IDs."""
    raw_pack = content_pack.model_dump()
    dup_rule = dict(raw_pack["invalidation_rules"][0])
    raw_pack["invalidation_rules"].append(dup_rule)
    with pytest.raises(ContentPackValidationError, match="Duplicate invalidation rule id"):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_conflicting_invalidation_rule(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection of conflicting invalidation rules with different validity states."""
    raw_pack = content_pack.model_dump()
    conflicting_rule = {
        "rule_id": "ir_conflicting_rule",
        "trigger_event": raw_pack["invalidation_rules"][0]["trigger_event"],
        "source_question_id": raw_pack["invalidation_rules"][0]["source_question_id"],
        "trigger_value": raw_pack["invalidation_rules"][0]["trigger_value"],
        "target_question_ids": [raw_pack["invalidation_rules"][0]["target_question_ids"][0]],
        "new_validity_state": "STALE_REQUIRES_RECONFIRMATION",
        "active_branch_effect": None,
    }
    raw_pack["invalidation_rules"].append(conflicting_rule)
    with pytest.raises(ContentPackValidationError, match="Conflicting invalidation rule"):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_model_enum_vs_yaml_mismatch(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an option set value does not match defined enum options."""
    raw_pack = content_pack.model_dump()
    raw_pack["flow_rules"][0]["expected_value"] = "unsupported_option_value"
    with pytest.raises(ContentPackValidationError, match="not found in OptionSet"):
        load_daily_routines_content_pack_from_dict(raw_pack)


def load_daily_routines_content_pack_from_dict(
    raw_pack: dict[str, Any],
) -> DailyRoutinesContentPack:
    """Helper to validate raw dict as DailyRoutinesContentPack."""
    from brif_ai.conversation.daily_routines.loader import validate_cross_file_integrity

    try:
        pack = DailyRoutinesContentPack.model_validate(raw_pack)
    except Exception as err:
        raise ContentPackValidationError(f"Invalid content pack dict: {err}") from err

    validate_cross_file_integrity(pack)
    return pack
