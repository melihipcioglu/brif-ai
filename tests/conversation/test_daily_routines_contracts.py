"""Contract, negative, and end-to-end flow tests for BRIF.AI Daily Routines v0 content pack."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest
from pydantic import ValidationError

from brif_ai.conversation.daily_routines import (
    ContentPackValidationError,
    CorrectionTarget,
    DailyRoutinesContentPack,
    DayPatternStatus,
    DayPeriod,
    FlowResolutionError,
    FlowRule,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidAnswerError,
    InvalidationEngine,
    OptionSet,
    RecurringDayContext,
    RouteMatchType,
    SessionState,
    SummaryConfirmation,
    WordingBranch,
    load_daily_routines_content_pack,
)


@pytest.fixture
def content_pack() -> DailyRoutinesContentPack:
    """Load default Daily Routines v0 content pack."""
    return load_daily_routines_content_pack()


# -----------------------------------------------------------------------------
# 1. Schema, Matcher Breakdown & Cross-File Integrity Tests
# -----------------------------------------------------------------------------


def test_yaml_schema_validation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify default YAML files load into valid DailyRoutinesContentPack."""
    assert content_pack.schema_version == "v0"
    assert len(content_pack.questions) == 16
    assert len(content_pack.ui_state_controls) == 1
    assert len(content_pack.option_sets) == 7
    assert len(content_pack.wording_variants) == 16
    assert len(content_pack.flow_rules) == 56
    assert len(content_pack.conditional_routes) == 9
    assert len(content_pack.invalidation_rules) >= 7


def test_flow_rule_matcher_breakdown(content_pack: DailyRoutinesContentPack) -> None:
    """Verify exact flow rule count and matcher distribution."""
    exact_count = sum(
        1 for r in content_pack.flow_rules if r.match_type == RouteMatchType.EXACT_OPTION
    )
    multi_count = sum(
        1 for r in content_pack.flow_rules if r.match_type == RouteMatchType.ANY_VALID_MULTISELECT
    )
    text_count = sum(
        1 for r in content_pack.flow_rules if r.match_type == RouteMatchType.NON_EMPTY_TEXT
    )
    completed_count = sum(
        1 for r in content_pack.flow_rules if r.match_type == RouteMatchType.QUESTION_COMPLETED
    )

    assert exact_count == 49
    assert multi_count == 5
    assert text_count == 2
    assert completed_count == 0
    assert len(content_pack.flow_rules) == 56


def test_cross_file_reference_validation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify that all question references and option set references are valid."""
    question_ids = {q.id for q in content_pack.questions}
    ui_ids = {ui.id for ui in content_pack.ui_state_controls}
    all_valid_ids = question_ids | ui_ids

    option_set_ids = {os.id for os in content_pack.option_sets}

    for q in content_pack.questions:
        if q.option_set_id:
            assert q.option_set_id in option_set_ids

    for rule in content_pack.flow_rules:
        assert rule.source_question_id in all_valid_ids
        if rule.target_question_id:
            assert rule.target_question_id in all_valid_ids

    for cr in content_pack.conditional_routes:
        assert cr.target_question_id in all_valid_ids


# -----------------------------------------------------------------------------
# 2. Historical & Strict Contract Negative Tests
# -----------------------------------------------------------------------------


def test_negative_extra_field_rejection() -> None:
    """Verify that models forbid extra unknown fields."""
    with pytest.raises(ValidationError):
        FlowRule.model_validate(
            {
                "rule_id": "fr_test_extra",
                "source_question_id": "q_test",
                "match_type": "EXACT_OPTION",
                "expected_value": "val",
                "target_question_id": "q_target",
                "target_closure_effect": "REQUIRES_FOLLOW_UP",
                "follow_up_required": True,
                "unexpected_extra_field": "disallowed",
            }
        )


def test_negative_unknown_enum_rejection() -> None:
    """Verify rejection when an unknown enum value is passed to a model."""
    with pytest.raises(ValidationError):
        FlowRule.model_validate(
            {
                "rule_id": "fr_test_invalid_enum",
                "source_question_id": "q_test",
                "match_type": "INVALID_MATCH_TYPE_STRING",
                "expected_value": "val",
                "target_question_id": "q_target",
                "target_closure_effect": "REQUIRES_FOLLOW_UP",
                "follow_up_required": True,
            }
        )


def test_negative_duplicate_option_id_rejection() -> None:
    """Verify rejection when an option set has duplicate option IDs."""
    with pytest.raises(ValidationError):
        OptionSet.model_validate(
            {
                "id": "os_test_dup",
                "options": [
                    {
                        "id": "opt_dup",
                        "value": "v1",
                        "display_label": "Label 1",
                        "helper_text": "Help 1",
                        "display_order": 1,
                    },
                    {
                        "id": "opt_dup",
                        "value": "v2",
                        "display_label": "Label 2",
                        "helper_text": "Help 2",
                        "display_order": 2,
                    },
                ],
            }
        )


def test_loader_works_when_cwd_changes(content_pack: DailyRoutinesContentPack) -> None:
    """Verify loader resolves package resources independent of current working directory."""
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            os.chdir(tmpdir)
            pack = load_daily_routines_content_pack()
            assert pack.schema_version == "v0"
            assert len(pack.questions) == 16
        finally:
            os.chdir(original_cwd)


def test_negative_invalid_invalidation_state(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an invalidation rule has an invalid new_validity_state."""
    raw_pack = content_pack.model_dump()
    raw_pack["invalidation_rules"][0]["new_validity_state"] = "INVALID_STATE_STRING"
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_duplicate_invalidation_rule(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an invalidation rule ID is duplicated."""
    raw_pack = content_pack.model_dump()
    dup_rule = dict(raw_pack["invalidation_rules"][0])
    raw_pack["invalidation_rules"].append(dup_rule)
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_conflicting_invalidation_rule(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when two invalidation rules collide on trigger & target."""
    raw_pack = content_pack.model_dump()
    conflicting_rule = {
        "rule_id": "inv_rule_conflict_id",
        "trigger_event": raw_pack["invalidation_rules"][0]["trigger_event"],
        "source_question_id": raw_pack["invalidation_rules"][0]["source_question_id"],
        "trigger_value": raw_pack["invalidation_rules"][0]["trigger_value"],
        "target_question_ids": raw_pack["invalidation_rules"][0]["target_question_ids"],
        "new_validity_state": "STALE_REQUIRES_RECONFIRMATION",
        "active_branch_effect": None,
    }
    raw_pack["invalidation_rules"].append(conflicting_rule)
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_model_enum_vs_yaml_mismatch(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an option set value does not match defined enum options."""
    raw_pack = content_pack.model_dump()
    raw_pack["flow_rules"][0]["expected_value"] = "unsupported_option_value"
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


# -----------------------------------------------------------------------------
# 3. Runtime Validator & Fail-Closed Resolver Negative Tests
# -----------------------------------------------------------------------------


def test_runtime_unknown_question_id_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when attempting to record an answer for an unknown question ID."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    with pytest.raises(InvalidAnswerError, match="Unknown question or UI control id"):
        engine.record_answer(session, "q_unknown_nonexistent_question", "some_value")
    assert "q_unknown_nonexistent_question" not in session.answers


def test_runtime_unknown_option_value_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when recording an option value not present in the OptionSet."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_day_pattern_status"

    with pytest.raises(InvalidAnswerError, match="not found in OptionSet"):
        engine.record_answer(session, q_id, "invalid_unsupported_pattern")
    assert q_id not in session.answers


def test_runtime_sleeping_disallowed_not_relevant_rejection(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify rejection of functional_domain_not_relevant_to_household for Sleeping domain."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_sleeping_status"

    with pytest.raises(InvalidAnswerError, match="disallowed for domain 'sleeping'"):
        engine.record_answer(
            session, q_id, FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD
        )
    assert q_id not in session.answers


def test_runtime_bathroom_disallowed_not_relevant_rejection(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify rejection of functional_domain_not_relevant_to_household for Bathroom domain."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_bathroom_status"

    with pytest.raises(InvalidAnswerError, match="disallowed for domain 'bathroom'"):
        engine.record_answer(
            session, q_id, FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD
        )
    assert q_id not in session.answers


def test_runtime_empty_multiselect_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an empty list is recorded for MULTIPLE_CHOICE question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_living_social_periods"

    with pytest.raises(InvalidAnswerError, match="requires 1 to 4 items"):
        engine.record_answer(session, q_id, [])
    assert q_id not in session.answers


def test_runtime_five_periods_multiselect_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when a list of 5 items is recorded for MULTIPLE_CHOICE question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_living_social_periods"

    with pytest.raises(InvalidAnswerError, match="requires 1 to 4 items"):
        engine.record_answer(
            session, q_id, ["morning", "midday_afternoon", "evening", "night", "extra"]
        )
    assert q_id not in session.answers


def test_runtime_duplicate_period_multiselect_rejection(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify rejection when duplicate period items are recorded for MULTIPLE_CHOICE question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_living_social_periods"

    with pytest.raises(InvalidAnswerError, match="contains duplicate items"):
        engine.record_answer(session, q_id, ["morning", "morning"])
    assert q_id not in session.answers


def test_runtime_unknown_period_value_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when an unknown period value is recorded for MULTIPLE_CHOICE question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_living_social_periods"

    with pytest.raises(InvalidAnswerError, match="Invalid period value"):
        engine.record_answer(session, q_id, ["morning", "invalid_period_name"])
    assert q_id not in session.answers


def test_runtime_empty_whitespace_freetext_rejection(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify rejection when empty or whitespace-only text is recorded for FREE_TEXT question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_other_day_context_detail"

    with pytest.raises(InvalidAnswerError, match="cannot be empty or whitespace"):
        engine.record_answer(session, q_id, "   ")
    assert q_id not in session.answers


def test_runtime_answer_type_mismatch_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify rejection when a list is recorded for a SINGLE_CHOICE question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_day_pattern_status"

    with pytest.raises(InvalidAnswerError, match="expects string value"):
        engine.record_answer(session, q_id, ["stable_recurring_day_available"])
    assert q_id not in session.answers


def test_runtime_resolver_fail_closed_missing_answer(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify FlowResolutionError when resolving next step for a question with no active answer."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()
    q_id = "q_daily_routines_functional_space_day_pattern_status"

    with pytest.raises(FlowResolutionError, match="No active answer"):
        engine.resolve_next_step(session, q_id)


def test_runtime_resolver_fail_closed_unknown_question(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify FlowResolutionError when resolving next step for an unknown question ID."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    with pytest.raises(FlowResolutionError, match="Unknown current_question_id"):
        engine.resolve_next_step(session, "q_nonexistent_question")


def test_runtime_irregular_branch_recurring_context_correction_rejection(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify rejection when attempting recurring_day_context correction in IRREGULAR branch."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.NO_STABLE_RECURRING_DAY,
    )
    assert session.active_branch == WordingBranch.IRREGULAR

    q_sel = "bp_ui_room_use_correction_selector"
    with pytest.raises(InvalidAnswerError, match="only available in STABLE branch"):
        engine.record_answer(session, q_sel, CorrectionTarget.RECURRING_DAY_CONTEXT)


# -----------------------------------------------------------------------------
# 4. End-to-End Flow Tests (16 Scenarios)
# -----------------------------------------------------------------------------


def test_flow_stable_day_all_variable(content_pack: DailyRoutinesContentPack) -> None:
    """1. Stable day + all 5 domains variable -> summary confirmation -> module_complete."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Day pattern
    q1 = "q_daily_routines_functional_space_day_pattern_status"
    engine.record_answer(session, q1, DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    assert (
        engine.resolve_next_step(session, q1)
        == "q_daily_routines_functional_space_recurring_day_context"
    )

    # Context
    q2 = "q_daily_routines_functional_space_recurring_day_context"
    engine.record_answer(session, q2, RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    assert (
        engine.resolve_next_step(session, q2)
        == "q_daily_routines_functional_space_living_social_status"
    )

    # Domains (all variable)
    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(session, curr_q, FunctionalDomainStatus.VARIABLE)
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q

    # Household variation
    q_hh = "q_daily_routines_functional_space_household_variation_status"
    engine.record_answer(session, q_hh, HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    assert (
        engine.resolve_next_step(session, q_hh)
        == "q_daily_routines_functional_space_summary_confirmation"
    )

    # Summary confirmation
    q_sum = "q_daily_routines_functional_space_summary_confirmation"
    engine.record_answer(session, q_sum, SummaryConfirmation.CONFIRMED)
    assert engine.resolve_next_step(session, q_sum) == "module_complete"


def test_flow_stable_day_all_periods(content_pack: DailyRoutinesContentPack) -> None:
    """2. Stable day + all 5 domains reported_periods_available + periods selected."""
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

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        st_q = f"q_daily_routines_functional_space_{d}_status"
        pr_q = f"q_daily_routines_functional_space_{d}_periods"

        engine.record_answer(session, st_q, FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
        assert engine.resolve_next_step(session, st_q) == pr_q

        engine.record_answer(session, pr_q, [DayPeriod.EVENING.value])
        next_st_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, pr_q) == next_st_q


def test_flow_irregular_day_mixed_statuses(content_pack: DailyRoutinesContentPack) -> None:
    """3. Irregular day (no_stable_recurring_day) + mixed domain statuses."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    q_dp = "q_daily_routines_functional_space_day_pattern_status"
    engine.record_answer(session, q_dp, DayPatternStatus.NO_STABLE_RECURRING_DAY)
    assert session.active_branch == WordingBranch.IRREGULAR
    assert (
        engine.resolve_next_step(session, q_dp)
        == "q_daily_routines_functional_space_living_social_status"
    )

    q_ls = "q_daily_routines_functional_space_living_social_status"
    engine.record_answer(session, q_ls, FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
    assert (
        engine.resolve_next_step(session, q_ls)
        == "q_daily_routines_functional_space_living_social_periods"
    )

    q_lsp = "q_daily_routines_functional_space_living_social_periods"
    engine.record_answer(session, q_lsp, [DayPeriod.EVENING.value])
    assert (
        engine.resolve_next_step(session, q_lsp)
        == "q_daily_routines_functional_space_kitchen_dining_status"
    )

    q_kd = "q_daily_routines_functional_space_kitchen_dining_status"
    engine.record_answer(session, q_kd, FunctionalDomainStatus.VARIABLE)
    assert (
        engine.resolve_next_step(session, q_kd)
        == "q_daily_routines_functional_space_sleeping_status"
    )


def test_flow_all_domains_no_use_reported(content_pack: DailyRoutinesContentPack) -> None:
    """4. All domains no_use_reported_in_selected_context."""
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
        RecurringDayContext.SHIFT_WORK_DAY,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(
            session, curr_q, FunctionalDomainStatus.NO_USE_REPORTED_IN_SELECTED_CONTEXT
        )
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_all_domains_not_available(content_pack: DailyRoutinesContentPack) -> None:
    """5. All domains functional_domain_not_available_in_current_home."""
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
        RecurringDayContext.TYPICAL_DAY_SPENT_AT_HOME,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(
            session,
            curr_q,
            FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_AVAILABLE_IN_CURRENT_HOME,
        )
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_applicable_domains_not_relevant(content_pack: DailyRoutinesContentPack) -> None:
    """6. Applicable domains functional_domain_not_relevant_to_household."""
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

    applicable_domains = ["living_social", "kitchen_dining", "work_study"]
    for d in applicable_domains:
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(
            session, curr_q, FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD
        )
        assert engine.resolve_next_step(session, curr_q) != ""


def test_flow_all_domains_unknown(content_pack: DailyRoutinesContentPack) -> None:
    """7. All domains unknown."""
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

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(session, curr_q, FunctionalDomainStatus.UNKNOWN)
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_all_domains_prefer_not(content_pack: DailyRoutinesContentPack) -> None:
    """8. All domains prefer_not_to_answer."""
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

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(session, curr_q, FunctionalDomainStatus.PREFER_NOT_TO_ANSWER)
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_other_recurring_context_free_text(content_pack: DailyRoutinesContentPack) -> None:
    """9. Other recurring context free-text transition."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )

    q_rc = "q_daily_routines_functional_space_recurring_day_context"
    engine.record_answer(session, q_rc, RecurringDayContext.OTHER_RECURRING_DAY_CONTEXT)
    assert (
        engine.resolve_next_step(session, q_rc)
        == "q_daily_routines_functional_space_other_day_context_detail"
    )

    q_dt = "q_daily_routines_functional_space_other_day_context_detail"
    engine.record_answer(session, q_dt, "Nöbet günleri düzeni")
    assert (
        engine.resolve_next_step(session, q_dt)
        == "q_daily_routines_functional_space_living_social_status"
    )


def test_flow_household_variation_detail_free_text(content_pack: DailyRoutinesContentPack) -> None:
    """10. Household variation detail free-text transition."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    q_hh = "q_daily_routines_functional_space_household_variation_status"
    engine.record_answer(session, q_hh, HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED)
    assert (
        engine.resolve_next_step(session, q_hh)
        == "q_daily_routines_functional_space_household_variation_detail"
    )

    q_dt = "q_daily_routines_functional_space_household_variation_detail"
    engine.record_answer(session, q_dt, "Gece çalışması yapan hane üyesi var.")
    assert (
        engine.resolve_next_step(session, q_dt)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_domain_correction_to_periods(content_pack: DailyRoutinesContentPack) -> None:
    """11. Domain correction -> reported_periods_available -> periods question (self-contained)."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Complete initial flow self-contained
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
    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for d in domains:
        engine.record_answer(
            session,
            f"q_daily_routines_functional_space_{d}_status",
            FunctionalDomainStatus.VARIABLE,
        )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_household_variation_status",
        HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE,
    )

    # Reach summary & trigger correction for living_social
    q_sum = "q_daily_routines_functional_space_summary_confirmation"
    engine.record_answer(session, q_sum, SummaryConfirmation.REJECTED_FOR_CORRECTION)
    assert engine.resolve_next_step(session, q_sum) == "bp_ui_room_use_correction_selector"

    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.LIVING_SOCIAL)
    assert (
        engine.resolve_next_step(session, q_sel)
        == "q_daily_routines_functional_space_living_social_status"
    )

    # Change living_social status to reported_periods_available
    q_ls = "q_daily_routines_functional_space_living_social_status"
    engine.record_answer(session, q_ls, FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
    assert (
        engine.resolve_next_step(session, q_ls)
        == "q_daily_routines_functional_space_living_social_periods"
    )

    # Answer periods and return to summary
    q_lsp = "q_daily_routines_functional_space_living_social_periods"
    engine.record_answer(session, q_lsp, [DayPeriod.EVENING.value])
    assert (
        engine.resolve_next_step(session, q_lsp)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_domain_correction_direct_summary(content_pack: DailyRoutinesContentPack) -> None:
    """12. Domain correction -> variable -> directly to summary."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.KITCHEN_DINING)
    assert (
        engine.resolve_next_step(session, q_sel)
        == "q_daily_routines_functional_space_kitchen_dining_status"
    )

    q_kd = "q_daily_routines_functional_space_kitchen_dining_status"
    engine.record_answer(session, q_kd, FunctionalDomainStatus.VARIABLE)
    assert (
        engine.resolve_next_step(session, q_kd)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_context_correction_stale_reconfirmation(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """13. Context correction -> stale reconfirmation -> exact step sequence -> summary."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Step 1: Initial stable day + context + domain answers
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
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_periods",
        [DayPeriod.EVENING.value],
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_kitchen_dining_status",
        FunctionalDomainStatus.VARIABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_sleeping_status",
        FunctionalDomainStatus.VARIABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_work_study_status",
        FunctionalDomainStatus.VARIABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_bathroom_status",
        FunctionalDomainStatus.VARIABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_household_variation_status",
        HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE,
    )

    # Step 2: Change recurring context (triggers invalidation cascade marking answers STALE)

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.WORK_FROM_HOME_DAY,
    )

    # Step 3: Trigger correction for recurring_day_context
    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.RECURRING_DAY_CONTEXT)

    # Exact step 1: Resolves to first stale question: living_social_status
    step1 = engine.resolve_next_step(session, q_sel)
    assert step1 == "q_daily_routines_functional_space_living_social_status"

    # Reconfirm living_social_status & living_social_periods
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

    # Exact step 2: Resolves to kitchen_dining_status
    step2 = engine.resolve_next_step(
        session, "q_daily_routines_functional_space_living_social_periods"
    )
    assert step2 == "q_daily_routines_functional_space_kitchen_dining_status"

    # Reconfirm remaining domain statuses & household variation status
    for d in ["kitchen_dining", "sleeping", "work_study", "bathroom"]:
        engine.record_answer(
            session,
            f"q_daily_routines_functional_space_{d}_status",
            FunctionalDomainStatus.VARIABLE,
        )

    q_hh = "q_daily_routines_functional_space_household_variation_status"
    assert (
        engine.resolve_next_step(session, "q_daily_routines_functional_space_bathroom_status")
        == q_hh
    )

    engine.record_answer(session, q_hh, HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    assert (
        engine.resolve_next_step(session, q_hh)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_review_all_to_summary(content_pack: DailyRoutinesContentPack) -> None:
    """14. Review all -> step through all questions -> summary confirmation."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Initial flow
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
    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for d in domains:
        engine.record_answer(
            session,
            f"q_daily_routines_functional_space_{d}_status",
            FunctionalDomainStatus.VARIABLE,
        )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_household_variation_status",
        HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE,
    )

    # Trigger review_all_answers correction
    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.REVIEW_ALL_ANSWERS)
    assert (
        engine.resolve_next_step(session, q_sel)
        == "q_daily_routines_functional_space_day_pattern_status"
    )

    # Step through all questions without deleting existing answers
    q_dp = "q_daily_routines_functional_space_day_pattern_status"
    assert (
        engine.resolve_next_step(session, q_dp)
        == "q_daily_routines_functional_space_recurring_day_context"
    )

    q_rc = "q_daily_routines_functional_space_recurring_day_context"
    assert (
        engine.resolve_next_step(session, q_rc)
        == "q_daily_routines_functional_space_living_social_status"
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q

    q_hh = "q_daily_routines_functional_space_household_variation_status"
    assert (
        engine.resolve_next_step(session, q_hh)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_negative_missing_route_rejected(content_pack: DailyRoutinesContentPack) -> None:
    """15. Rejection of contentpack with a missing route."""
    raw_pack = content_pack.model_dump()
    raw_pack["flow_rules"].pop(0)
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_duplicate_matching_route_rejected(content_pack: DailyRoutinesContentPack) -> None:
    """16. Rejection of contentpack with duplicate matching flow rule."""
    raw_pack = content_pack.model_dump()
    dup_rule = dict(raw_pack["flow_rules"][0])
    dup_rule["rule_id"] = "fr_duplicate_rule_id"
    raw_pack["flow_rules"].append(dup_rule)
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


# -----------------------------------------------------------------------------
# Helper for Dict Validation
# -----------------------------------------------------------------------------


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
