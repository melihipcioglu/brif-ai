"""Runtime engine and state persistence tests for BRIF.AI Daily Routines v0."""

from __future__ import annotations

import pytest

from brif_ai.conversation.daily_routines import (
    AnswerValidityState,
    CorrectionTarget,
    DailyRoutinesContentPack,
    DailyRoutinesRuntime,
    DailyRoutinesRuntimeState,
    DayPatternStatus,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidAnswerError,
    InvalidSessionStateError,
    RecurringDayContext,
    SessionStatus,
    SummaryConfirmation,
    WordingBranch,
    load_daily_routines_content_pack,
)


@pytest.fixture
def content_pack() -> DailyRoutinesContentPack:
    """Load default Daily Routines v0 content pack."""
    return load_daily_routines_content_pack()


# -----------------------------------------------------------------------------
# 1. Option Filtering Tests
# -----------------------------------------------------------------------------


def test_option_filtering_sleeping_and_bathroom(content_pack: DailyRoutinesContentPack) -> None:
    """Verify functional domain not relevant is filtered for sleeping & bathroom."""
    runtime = DailyRoutinesRuntime(content_pack)

    # Fast forward to sleeping_status
    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # living_social
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # kitchen_dining

    # sleeping_status prompt
    prompt_sleeping = runtime.get_current_step_prompt()
    assert prompt_sleeping.question_id == "q_daily_routines_functional_space_sleeping_status"
    assert prompt_sleeping.options is not None
    opt_values_sleeping = [o.value for o in prompt_sleeping.options]
    assert (
        FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
        not in opt_values_sleeping
    )

    # sleeping_status answer -> bathroom_status
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # sleeping
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # work_study

    prompt_bathroom = runtime.get_current_step_prompt()
    assert prompt_bathroom.question_id == "q_daily_routines_functional_space_bathroom_status"
    assert prompt_bathroom.options is not None
    opt_values_bathroom = [o.value for o in prompt_bathroom.options]
    assert (
        FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
        not in opt_values_bathroom
    )


def test_option_filtering_correction_selector_in_irregular_branch(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify recurring context option is filtered in IRREGULAR branch."""
    runtime = DailyRoutinesRuntime(content_pack)

    # Start with IRREGULAR branch
    runtime.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)
    assert runtime.state.session_state.active_branch == WordingBranch.IRREGULAR

    # Complete all domain statuses
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)

    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Summary confirmation rejected for correction -> reach selector
    prompt_sum = runtime.get_current_step_prompt()
    assert prompt_sum.question_id == "q_daily_routines_functional_space_summary_confirmation"
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)

    prompt_sel = runtime.get_current_step_prompt()
    assert prompt_sel.question_id == "bp_ui_room_use_correction_selector"
    assert prompt_sel.options is not None
    sel_values = [o.value for o in prompt_sel.options]
    assert CorrectionTarget.RECURRING_DAY_CONTEXT.value not in sel_values


# -----------------------------------------------------------------------------
# 2. Existing Answer Prefill Tests
# -----------------------------------------------------------------------------


def test_existing_answer_prefill(content_pack: DailyRoutinesContentPack) -> None:
    """Verify existing answer is prefilled in step prompt when stepping back or reviewing."""
    runtime = DailyRoutinesRuntime(content_pack)

    # Answer day_pattern_status
    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)

    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)

    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Reject for correction -> select review_all_answers
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.REVIEW_ALL_ANSWERS)

    # Prompt for day_pattern_status should contain existing_answer
    prompt_dp = runtime.get_current_step_prompt()
    assert prompt_dp.question_id == "q_daily_routines_functional_space_day_pattern_status"
    assert prompt_dp.existing_answer == DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value


# -----------------------------------------------------------------------------
# 3. Completed Session Protection Tests
# -----------------------------------------------------------------------------


def test_completed_session_protection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify InvalidSessionStateError on completed session."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    result = runtime.process_answer(SummaryConfirmation.CONFIRMED)
    assert result.terminal_target == "module_complete"
    assert result.next_step_id is None
    assert runtime.state.status == SessionStatus.COMPLETED

    # Protection checks
    with pytest.raises(InvalidSessionStateError, match="completed session"):
        runtime.get_current_step_prompt()

    with pytest.raises(InvalidSessionStateError, match="completed session"):
        runtime.process_answer(SummaryConfirmation.CONFIRMED)


def test_unknown_current_step_id_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify unknown current_step_id is rejected with InvalidAnswerError."""
    runtime = DailyRoutinesRuntime(content_pack)
    runtime.state.current_step_id = "q_unknown_step_id"

    with pytest.raises(InvalidAnswerError, match="Unknown current step ID"):
        runtime.get_current_step_prompt()

    with pytest.raises(InvalidAnswerError, match="Unknown current step ID"):
        runtime.process_answer("some_answer")


# -----------------------------------------------------------------------------
# 4. Unknown & Prefer Not Early Closures
# -----------------------------------------------------------------------------


def test_early_closure_day_pattern_unknown(content_pack: DailyRoutinesContentPack) -> None:
    """Verify early closure flow when day_pattern_status is UNKNOWN."""
    runtime = DailyRoutinesRuntime(content_pack)

    res_dp = runtime.process_answer(DayPatternStatus.UNKNOWN)
    assert res_dp.next_step_id == "q_daily_routines_functional_space_summary_confirmation"

    result = runtime.process_answer(SummaryConfirmation.CONFIRMED)
    assert result.terminal_target == "module_complete"
    assert runtime.state.status == SessionStatus.COMPLETED


def test_early_closure_day_pattern_prefer_not(content_pack: DailyRoutinesContentPack) -> None:
    """Verify early closure flow when day_pattern_status is PREFER_NOT_TO_ANSWER."""
    runtime = DailyRoutinesRuntime(content_pack)

    res_dp = runtime.process_answer(DayPatternStatus.PREFER_NOT_TO_ANSWER)
    assert res_dp.next_step_id == "q_daily_routines_functional_space_summary_confirmation"

    result = runtime.process_answer(SummaryConfirmation.CONFIRMED)
    assert result.terminal_target == "module_complete"
    assert runtime.state.status == SessionStatus.COMPLETED


# -----------------------------------------------------------------------------
# 5. Session Serialization / Restore / Resume Tests
# -----------------------------------------------------------------------------


def test_session_serialization_restore_resume(content_pack: DailyRoutinesContentPack) -> None:
    """Verify state serialization, restoration, and seamless continuation."""
    runtime1 = DailyRoutinesRuntime(content_pack)

    # Execute part of the flow
    res1 = runtime1.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    assert res1.next_step_id == "q_daily_routines_functional_space_recurring_day_context"

    res2 = runtime1.process_answer(RecurringDayContext.WORK_FROM_HOME_DAY)
    assert res2.next_step_id == "q_daily_routines_functional_space_living_social_status"

    # Serialize runtime state to JSON
    json_str = runtime1.state.model_dump_json()

    # Restore state from JSON
    restored_state = DailyRoutinesRuntimeState.model_validate_json(json_str)
    assert (
        restored_state.current_step_id == "q_daily_routines_functional_space_living_social_status"
    )
    assert restored_state.status == SessionStatus.IN_PROGRESS
    assert restored_state.session_state.active_branch == WordingBranch.STABLE

    # Instantiate new runtime with restored state and resume
    runtime2 = DailyRoutinesRuntime(content_pack, state=restored_state)
    prompt = runtime2.get_current_step_prompt()
    assert prompt.question_id == "q_daily_routines_functional_space_living_social_status"

    # Continue session seamlessly to completion
    for _ in range(5):
        runtime2.process_answer(FunctionalDomainStatus.VARIABLE)

    runtime2.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    final_res = runtime2.process_answer(SummaryConfirmation.CONFIRMED)

    assert final_res.terminal_target == "module_complete"
    assert runtime2.state.status == SessionStatus.COMPLETED


# -----------------------------------------------------------------------------
# 6. Branch Change & Stale Reconfirmation Tests
# -----------------------------------------------------------------------------


def test_branch_change_stale_reconfirmation_order(content_pack: DailyRoutinesContentPack) -> None:
    """Verify branch change marks answers stale and reconfirms them in exact flow order."""
    runtime = DailyRoutinesRuntime(content_pack)

    # Initial flow
    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Reject for correction -> select day_pattern correction
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.DAY_PATTERN)

    # Change day_pattern_status to NO_STABLE_RECURRING_DAY (switches branch to IRREGULAR)
    res_dp = runtime.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)
    assert runtime.state.session_state.active_branch == WordingBranch.IRREGULAR

    # First stale question in order is living_social_status
    assert res_dp.next_step_id == "q_daily_routines_functional_space_living_social_status"

    # Reconfirm domain statuses sequentially
    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, _d in enumerate(domains):
        res = runtime.process_answer(FunctionalDomainStatus.VARIABLE)
        expected_next = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert res.next_step_id == expected_next

    # Reconfirm household_variation_status
    res_hh = runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    assert res_hh.next_step_id == "q_daily_routines_functional_space_summary_confirmation"


# -----------------------------------------------------------------------------
# 7. Completed Result Protection (No Stale Answers)
# -----------------------------------------------------------------------------


def test_completed_result_contains_no_stale_answers(content_pack: DailyRoutinesContentPack) -> None:
    """Verify completed session state has no STALE answers remaining."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Trigger context correction & reconfirm
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.RECURRING_DAY_CONTEXT)
    runtime.process_answer(RecurringDayContext.WORK_FROM_HOME_DAY)

    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Complete session
    res = runtime.process_answer(SummaryConfirmation.CONFIRMED)
    assert res.terminal_target == "module_complete"
    assert runtime.state.status == SessionStatus.COMPLETED

    # Check validity state of all recorded answers
    for q_id, record in runtime.state.session_state.answers.items():
        assert record.validity_state != AnswerValidityState.STALE_REQUIRES_RECONFIRMATION, (
            f"Question {q_id} has stale validity state"
        )
