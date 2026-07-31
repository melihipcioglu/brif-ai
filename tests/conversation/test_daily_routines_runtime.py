"""Runtime engine, state persistence, and invariant tests for BRIF.AI Daily Routines v0."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brif_ai.conversation.daily_routines import (
    AnswerValidityState,
    CorrectionTarget,
    DailyRoutinesContentPack,
    DailyRoutinesRuntime,
    DailyRoutinesRuntimeState,
    DayPatternStatus,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
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
# 1. Runtime State Invariant Tests
# -----------------------------------------------------------------------------


def test_runtime_state_in_progress_invariant_rejection() -> None:
    """Verify rejection when IN_PROGRESS runtime state has null current_step_id or non-null terminal_target."""
    with pytest.raises(ValidationError):
        DailyRoutinesRuntimeState(
            status=SessionStatus.IN_PROGRESS,
            current_step_id=None,
            terminal_target=None,
        )

    with pytest.raises(ValidationError):
        DailyRoutinesRuntimeState(
            status=SessionStatus.IN_PROGRESS,
            current_step_id="q_daily_routines_functional_space_day_pattern_status",
            terminal_target="module_complete",
        )


def test_runtime_state_completed_invariant_rejection() -> None:
    """Verify rejection when COMPLETED runtime state has non-null current_step_id or invalid terminal_target."""
    with pytest.raises(ValidationError):
        DailyRoutinesRuntimeState(
            status=SessionStatus.COMPLETED,
            current_step_id="q_daily_routines_functional_space_day_pattern_status",
            terminal_target="module_complete",
        )

    with pytest.raises(ValidationError):
        DailyRoutinesRuntimeState(
            status=SessionStatus.COMPLETED,
            current_step_id=None,
            terminal_target=None,
        )


# -----------------------------------------------------------------------------
# 2. Resumption & Step ID Rejection Tests
# -----------------------------------------------------------------------------


def test_runtime_unknown_current_step_rejection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify resuming runtime with unknown current_step_id raises InvalidSessionStateError."""
    bad_state = DailyRoutinesRuntimeState(
        status=SessionStatus.IN_PROGRESS,
        current_step_id="q_unknown_nonexistent_step",
        terminal_target=None,
    )
    with pytest.raises(InvalidSessionStateError, match="invalid current_step_id"):
        DailyRoutinesRuntime(content_pack, state=bad_state)


# -----------------------------------------------------------------------------
# 3. UI Control & Wording Variant Prompt Generation Tests
# -----------------------------------------------------------------------------


def test_ui_control_prompt_generation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify UI control prompt sets is_ui_control=True, ui_control_definition, and wording_variant=None."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Reject for correction -> reach selector step
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)

    prompt = runtime.get_current_step_prompt()
    assert prompt.step_id == "bp_ui_room_use_correction_selector"
    assert prompt.is_ui_control is True
    assert prompt.ui_control_definition is not None
    assert prompt.question_definition is None
    assert prompt.wording_variant is None
    assert prompt.option_set is not None

    # Answering UI control returns target_closure_effect is None
    res = runtime.process_answer(CorrectionTarget.DAY_PATTERN)
    assert res.target_closure_effect is None


def test_wording_variant_branch_selection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify STABLE branch selects STABLE wording variant and IRREGULAR selects IRREGULAR variant."""
    # 1. STABLE branch
    runtime_stable = DailyRoutinesRuntime(content_pack)
    runtime_stable.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    prompt_st = runtime_stable.get_current_step_prompt()
    assert prompt_st.wording_variant is not None
    assert prompt_st.wording_variant.branch == WordingBranch.STABLE

    # 2. IRREGULAR branch
    runtime_irr = DailyRoutinesRuntime(content_pack)
    runtime_irr.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)
    prompt_irr = runtime_irr.get_current_step_prompt()
    assert prompt_irr.wording_variant is not None
    assert prompt_irr.wording_variant.branch == WordingBranch.IRREGULAR


# -----------------------------------------------------------------------------
# 4. Option Filtering Tests
# -----------------------------------------------------------------------------


def test_option_filtering_sleeping_and_bathroom(content_pack: DailyRoutinesContentPack) -> None:
    """Verify functional domain not relevant option is filtered for sleeping & bathroom."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # living_social
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # kitchen_dining

    prompt_sleeping = runtime.get_current_step_prompt()
    assert prompt_sleeping.step_id == "q_daily_routines_functional_space_sleeping_status"
    assert prompt_sleeping.options is not None
    opt_vals_sleeping = [o.value for o in prompt_sleeping.options]
    assert (
        FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
        not in opt_vals_sleeping
    )

    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # sleeping
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # work_study

    prompt_bathroom = runtime.get_current_step_prompt()
    assert prompt_bathroom.step_id == "q_daily_routines_functional_space_bathroom_status"
    assert prompt_bathroom.options is not None
    opt_vals_bathroom = [o.value for o in prompt_bathroom.options]
    assert (
        FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
        not in opt_vals_bathroom
    )


def test_option_filtering_irregular_correction_selector(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify recurring_day_context option is omitted from correction selector under IRREGULAR branch."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)

    prompt_sel = runtime.get_current_step_prompt()
    assert prompt_sel.step_id == "bp_ui_room_use_correction_selector"
    assert prompt_sel.options is not None
    sel_vals = [o.value for o in prompt_sel.options]
    assert CorrectionTarget.RECURRING_DAY_CONTEXT.value not in sel_vals


# -----------------------------------------------------------------------------
# 5. Answer Prefill & Stale Reconfirmation Tests
# -----------------------------------------------------------------------------


def test_existing_active_answer_prefill(content_pack: DailyRoutinesContentPack) -> None:
    """Verify existing ACTIVE answer is prefilled with stale_reconfirmation=False."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.REVIEW_ALL_ANSWERS)

    prompt = runtime.get_current_step_prompt()
    assert prompt.step_id == "q_daily_routines_functional_space_day_pattern_status"
    assert prompt.existing_answer == DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value
    assert prompt.stale_reconfirmation is False


def test_existing_stale_answer_prefill(content_pack: DailyRoutinesContentPack) -> None:
    """Verify existing STALE answer is prefilled with stale_reconfirmation=True."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
    runtime.process_answer(["evening"])
    for _ in range(4):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Change recurring_day_context (marks downstream status STALE)
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.RECURRING_DAY_CONTEXT)
    runtime.process_answer(RecurringDayContext.WORK_FROM_HOME_DAY)

    prompt_stale = runtime.get_current_step_prompt()
    assert prompt_stale.step_id == "q_daily_routines_functional_space_living_social_status"
    assert prompt_stale.existing_answer == FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE.value
    assert prompt_stale.stale_reconfirmation is True


# -----------------------------------------------------------------------------
# 6. Unknown & Prefer-Not Early Closure Tests
# -----------------------------------------------------------------------------


def test_early_closure_unknown_and_prefer_not_paths(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify unknown and prefer_not_to_answer flow to summary_confirmation and complete on confirmed."""
    # 1. UNKNOWN
    runtime_unk = DailyRoutinesRuntime(content_pack)
    res_unk = runtime_unk.process_answer(DayPatternStatus.UNKNOWN)
    assert res_unk.next_step_id == "q_daily_routines_functional_space_summary_confirmation"
    res_unk_fin = runtime_unk.process_answer(SummaryConfirmation.CONFIRMED)
    assert res_unk_fin.terminal_target == "module_complete"
    assert runtime_unk.state.status == SessionStatus.COMPLETED

    # 2. PREFER_NOT_TO_ANSWER
    runtime_pref = DailyRoutinesRuntime(content_pack)
    res_pref = runtime_pref.process_answer(DayPatternStatus.PREFER_NOT_TO_ANSWER)
    assert res_pref.next_step_id == "q_daily_routines_functional_space_summary_confirmation"
    res_pref_fin = runtime_pref.process_answer(SummaryConfirmation.CONFIRMED)
    assert res_pref_fin.terminal_target == "module_complete"
    assert runtime_pref.state.status == SessionStatus.COMPLETED


# -----------------------------------------------------------------------------
# 7. Completed Protection & Stale Answer Rejection Tests
# -----------------------------------------------------------------------------


def test_completed_session_protection(content_pack: DailyRoutinesContentPack) -> None:
    """Verify process_answer and get_current_step_prompt raise InvalidSessionStateError on completed session."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    runtime.process_answer(SummaryConfirmation.CONFIRMED)

    assert runtime.state.status == SessionStatus.COMPLETED
    assert runtime.state.current_step_id is None
    assert runtime.state.terminal_target == "module_complete"

    with pytest.raises(InvalidSessionStateError, match="completed session"):
        runtime.get_current_step_prompt()

    with pytest.raises(InvalidSessionStateError, match="completed session"):
        runtime.process_answer(SummaryConfirmation.CONFIRMED)

    # get_result() works cleanly on completed session
    session_result = runtime.get_result()
    assert session_result.completed is True
    assert session_result.terminal_target == "module_complete"
    assert len(session_result.summary_lines) > 0


def test_completion_rejected_when_stale_answers_exist(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify session completion is rejected if any answer is STALE_REQUIRES_RECONFIRMATION."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Manually mark living_social_status answer STALE
    rec = runtime.state.session_state.answers[
        "q_daily_routines_functional_space_living_social_status"
    ]
    rec.validity_state = AnswerValidityState.STALE_REQUIRES_RECONFIRMATION

    # Attempt to process summary confirmation answer -> must raise InvalidSessionStateError
    runtime.state.current_step_id = "q_daily_routines_functional_space_summary_confirmation"
    with pytest.raises(InvalidSessionStateError, match="stale answer"):
        runtime.process_answer(SummaryConfirmation.CONFIRMED)


# -----------------------------------------------------------------------------
# 8. Serialization, Restore, Resume & Active Answer Filtering Tests
# -----------------------------------------------------------------------------


def test_serialization_restore_resume_deterministic_next_step(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify DailyRoutinesRuntimeState serialization, restoration, and identical next step resolution."""
    runtime1 = DailyRoutinesRuntime(content_pack)

    runtime1.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    res1 = runtime1.process_answer(RecurringDayContext.WORK_FROM_HOME_DAY)
    step1_next = res1.next_step_id

    # Serialize & restore
    json_str = runtime1.state.model_dump_json()
    restored_state = DailyRoutinesRuntimeState.model_validate_json(json_str)

    runtime2 = DailyRoutinesRuntime(content_pack, state=restored_state)
    prompt2 = runtime2.get_current_step_prompt()
    assert prompt2.step_id == step1_next

    # Resume and verify next step is identical
    res2 = runtime2.process_answer(FunctionalDomainStatus.VARIABLE)
    assert res2.next_step_id == "q_daily_routines_functional_space_kitchen_dining_status"


def test_session_result_contains_only_active_answers(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify DailyRoutinesSessionResult.active_answers filters out INACTIVE and STALE answers."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Change day_pattern_status to NO_STABLE_RECURRING_DAY (marks context INACTIVE and domains STALE)
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.DAY_PATTERN)
    runtime.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)

    # Inspect session result prior to reconfirming
    mid_result = runtime.get_result()
    for q_id, rec in mid_result.active_answers.items():
        assert rec.validity_state == AnswerValidityState.ACTIVE, (
            f"Answer {q_id} in active_answers has state {rec.validity_state}"
        )

    # Complete flow
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    final_step_res = runtime.process_answer(SummaryConfirmation.CONFIRMED)

    assert final_step_res.status == SessionStatus.COMPLETED
    final_result = runtime.get_result()
    assert final_result.completed is True
    assert final_result.runtime_state.current_step_id is None
    assert final_result.runtime_state.terminal_target == "module_complete"
    for _q_id, rec in final_result.active_answers.items():
        assert rec.validity_state == AnswerValidityState.ACTIVE
