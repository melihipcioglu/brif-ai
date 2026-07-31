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
    QuestionWording,
    QuestionWordingVariant,
    RecurringDayContext,
    SessionStatus,
    SummaryConfirmation,
    TargetClosureEffect,
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
    """Verify rejection when IN_PROGRESS state has null current_step_id or terminal_target."""
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
    """Verify rejection when COMPLETED state has non-null current_step_id or invalid target."""
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
    """Verify UI control prompt sets is_ui_control=True and target_closure_effect is None."""
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
    """Verify STABLE branch selects STABLE wording variant and IRREGULAR selects IRREGULAR."""
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


def test_missing_wording_variant_raises_invalid_session_state_error(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify fail-closed error when active branch wording variant is missing."""
    # Create content pack copy with missing IRREGULAR variant for day_pattern_status
    bad_wordings = []
    for w in content_pack.wording_variants:
        if w.question_id == "q_daily_routines_functional_space_day_pattern_status":
            bad_wordings.append(
                QuestionWording(
                    question_id=w.question_id,
                    variants=[
                        QuestionWordingVariant(
                            branch=WordingBranch.STABLE,
                            prompt_text="Only stable variant",
                            respondent_instruction="Select one",
                        )
                    ],
                )
            )
        else:
            bad_wordings.append(w)

    bad_pack = content_pack.model_copy(update={"wording_variants": bad_wordings})
    runtime = DailyRoutinesRuntime(bad_pack)
    runtime.state.session_state.active_branch = WordingBranch.IRREGULAR

    with pytest.raises(InvalidSessionStateError, match="No wording variant found"):
        runtime.get_current_step_prompt()


# -----------------------------------------------------------------------------
# 4. Option Filtering & Single Source of Truth Tests
# -----------------------------------------------------------------------------


def test_option_filtering_single_source_of_truth(content_pack: DailyRoutinesContentPack) -> None:
    """Verify prompt.options and prompt.option_set.options are identical for filtered steps."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # living_social
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # kitchen_dining

    # 1. Sleeping status
    prompt_sleeping = runtime.get_current_step_prompt()
    assert prompt_sleeping.step_id == "q_daily_routines_functional_space_sleeping_status"
    assert prompt_sleeping.options is not None
    assert prompt_sleeping.option_set is not None
    assert prompt_sleeping.options == prompt_sleeping.option_set.options
    opt_vals_sleeping = [o.value for o in prompt_sleeping.options]
    assert (
        FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
        not in opt_vals_sleeping
    )

    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # sleeping
    runtime.process_answer(FunctionalDomainStatus.VARIABLE)  # work_study

    # 2. Bathroom status
    prompt_bathroom = runtime.get_current_step_prompt()
    assert prompt_bathroom.step_id == "q_daily_routines_functional_space_bathroom_status"
    assert prompt_bathroom.options is not None
    assert prompt_bathroom.option_set is not None
    assert prompt_bathroom.options == prompt_bathroom.option_set.options
    opt_vals_bathroom = [o.value for o in prompt_bathroom.options]
    assert (
        FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
        not in opt_vals_bathroom
    )

    # 3. IRREGULAR correction selector
    runtime_irr = DailyRoutinesRuntime(content_pack)
    runtime_irr.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)
    for _ in range(5):
        runtime_irr.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime_irr.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    runtime_irr.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)

    prompt_sel = runtime_irr.get_current_step_prompt()
    assert prompt_sel.step_id == "bp_ui_room_use_correction_selector"
    assert prompt_sel.options is not None
    assert prompt_sel.option_set is not None
    assert prompt_sel.options == prompt_sel.option_set.options
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


def test_stale_reconfirmation_step_by_step_order(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify exact step-by-step reconfirmation sequence when branch changes to IRREGULAR."""
    runtime = DailyRoutinesRuntime(content_pack)

    # Complete initial STABLE flow with living_social reported_periods_available
    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
    runtime.process_answer(["evening"])
    for _ in range(4):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Change day_pattern_status to NO_STABLE_RECURRING_DAY (switches branch to IRREGULAR)
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.DAY_PATTERN)
    runtime.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)

    # Verify exact step-by-step reconfirmation sequence with periods insertion
    expected_sequence = [
        "q_daily_routines_functional_space_living_social_status",
        "q_daily_routines_functional_space_living_social_periods",
        "q_daily_routines_functional_space_kitchen_dining_status",
        "q_daily_routines_functional_space_sleeping_status",
        "q_daily_routines_functional_space_work_study_status",
        "q_daily_routines_functional_space_bathroom_status",
        "q_daily_routines_functional_space_household_variation_status",
        "q_daily_routines_functional_space_summary_confirmation",
    ]

    for expected_step in expected_sequence:
        assert runtime.state.current_step_id == expected_step, (
            f"Expected step {expected_step!r}, got {runtime.state.current_step_id!r}"
        )

        # Submit answer to proceed
        if expected_step == "q_daily_routines_functional_space_living_social_status":
            runtime.process_answer(FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
        elif expected_step == "q_daily_routines_functional_space_living_social_periods":
            runtime.process_answer(["evening"])
        elif expected_step == "q_daily_routines_functional_space_household_variation_status":
            runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
        elif expected_step == "q_daily_routines_functional_space_summary_confirmation":
            res = runtime.process_answer(SummaryConfirmation.CONFIRMED)
            assert res.status == SessionStatus.COMPLETED
        else:
            runtime.process_answer(FunctionalDomainStatus.VARIABLE)


# -----------------------------------------------------------------------------
# 6. Target Closure Effect Tests
# -----------------------------------------------------------------------------


def test_target_closure_effect_outcomes(content_pack: DailyRoutinesContentPack) -> None:
    """Verify target_closure_effect values across standard rules, household, and summary."""
    runtime = DailyRoutinesRuntime(content_pack)

    # 1. Normal status transition -> REQUIRES_FOLLOW_UP
    res1 = runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    assert res1.target_closure_effect == TargetClosureEffect.REQUIRES_FOLLOW_UP

    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)

    # 2. Household variation no_material_difference -> VALID_CLOSURE
    res_hh_valid = runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    assert res_hh_valid.target_closure_effect == TargetClosureEffect.VALID_CLOSURE

    # 3. Summary rejected_for_correction -> REQUIRES_CORRECTION
    res_rej = runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    assert res_rej.target_closure_effect == TargetClosureEffect.REQUIRES_CORRECTION

    # 4. Household variation unknown -> VALID_BUT_LOW_INFORMATION
    runtime.process_answer(CorrectionTarget.HOUSEHOLD_VARIATION)
    res_hh_low = runtime.process_answer(HouseholdVariationStatus.UNKNOWN)
    assert res_hh_low.target_closure_effect == TargetClosureEffect.VALID_BUT_LOW_INFORMATION

    # 5. Summary confirmed -> TARGET_2_FULFILLED
    res_conf = runtime.process_answer(SummaryConfirmation.CONFIRMED)
    assert res_conf.target_closure_effect == TargetClosureEffect.TARGET_2_FULFILLED


# -----------------------------------------------------------------------------
# 7. Atomic Rollback & Stale Completion Protection Tests
# -----------------------------------------------------------------------------


def test_process_answer_atomic_rollback(content_pack: DailyRoutinesContentPack) -> None:
    """Verify atomic state rollback when process_answer fails due to stale completion error."""
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

    # Capture snapshot before attempting completion
    runtime.state.current_step_id = "q_daily_routines_functional_space_summary_confirmation"

    with pytest.raises(InvalidSessionStateError, match="stale answer"):
        runtime.process_answer(SummaryConfirmation.CONFIRMED)

    # Assert state was fully rolled back to pre-attempt snapshot
    assert (
        "q_daily_routines_functional_space_summary_confirmation"
        not in runtime.state.session_state.answers
    )
    assert runtime.state.status == SessionStatus.IN_PROGRESS
    assert runtime.state.current_step_id == "q_daily_routines_functional_space_summary_confirmation"
    assert runtime.state.terminal_target is None


# -----------------------------------------------------------------------------
# 8. Serialization, Restore, Resume & Active Answer Filtering Tests
# -----------------------------------------------------------------------------


def test_serialization_restore_resume_deterministic_next_step(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify DailyRoutinesRuntimeState serialization, restoration, and identical next step."""
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

    # Change day_pattern_status to NO_STABLE_RECURRING_DAY (marks context INACTIVE, domains STALE)
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.DAY_PATTERN)
    runtime.process_answer(DayPatternStatus.NO_STABLE_RECURRING_DAY)

    # Inspect session result prior to reconfirming
    mid_result = runtime.get_result()
    for _q_id, rec in mid_result.active_answers.items():
        assert rec.validity_state == AnswerValidityState.ACTIVE

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
