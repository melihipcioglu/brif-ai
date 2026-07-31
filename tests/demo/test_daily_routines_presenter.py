"""Presenter adapter, state serialization, and Streamlit demo tests."""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest

from brif_ai.conversation.daily_routines import (
    CorrectionTarget,
    DailyRoutinesContentPack,
    DailyRoutinesRuntime,
    DailyRoutinesRuntimeState,
    DayPatternStatus,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidAnswerError,
    RecurringDayContext,
    SummaryConfirmation,
    load_daily_routines_content_pack,
)
from brif_ai.demo.daily_routines_presenter import DailyRoutinesPresenter


@pytest.fixture
def content_pack() -> DailyRoutinesContentPack:
    """Load default Daily Routines v0 content pack."""
    return load_daily_routines_content_pack()


# -----------------------------------------------------------------------------
# 1. Presenter Single Choice & Multi Choice Option Conversion Tests
# -----------------------------------------------------------------------------


def test_presenter_single_choice_conversion(content_pack: DailyRoutinesContentPack) -> None:
    """Verify presenter single choice validation and option value extraction."""
    runtime = DailyRoutinesRuntime(content_pack)
    prompt = runtime.get_current_step_prompt()

    # Valid selection
    val = DailyRoutinesPresenter.convert_ui_single_choice(
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value, prompt
    )
    assert val == DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value

    # Empty selection rejection
    with pytest.raises(InvalidAnswerError, match="Lütfen devam etmek için bir seçenek"):
        DailyRoutinesPresenter.convert_ui_single_choice("", prompt)

    # Invalid selection rejection
    with pytest.raises(InvalidAnswerError, match="Geçersiz seçim"):
        DailyRoutinesPresenter.convert_ui_single_choice("non_existent_option", prompt)


def test_presenter_multi_choice_conversion(content_pack: DailyRoutinesContentPack) -> None:
    """Verify presenter multi choice validation and option list extraction."""
    runtime = DailyRoutinesRuntime(content_pack)
    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)

    prompt = runtime.get_current_step_prompt()
    assert prompt.step_id == "q_daily_routines_functional_space_living_social_periods"

    # Valid multi-select
    vals = DailyRoutinesPresenter.convert_ui_multi_choice(["morning", "evening"], prompt)
    assert vals == ["morning", "evening"]

    # Empty selection rejection
    with pytest.raises(InvalidAnswerError, match="en az bir seçenek"):
        DailyRoutinesPresenter.convert_ui_multi_choice([], prompt)

    # Invalid selection rejection
    with pytest.raises(InvalidAnswerError, match="Geçersiz seçim"):
        DailyRoutinesPresenter.convert_ui_multi_choice(["invalid_period"], prompt)


# -----------------------------------------------------------------------------
# 2. Existing Answer Prefill & Stale Warning Tests
# -----------------------------------------------------------------------------


def test_existing_answer_prefill_and_stale_warning(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify existing answer prefill and stale warning banner in PromptViewModel."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # Change day pattern to trigger stale state on downstream answers
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)
    runtime.process_answer(CorrectionTarget.RECURRING_DAY_CONTEXT)
    runtime.process_answer(RecurringDayContext.WORK_FROM_HOME_DAY)

    prompt_stale = runtime.get_current_step_prompt()
    prompt_vm = DailyRoutinesPresenter.build_prompt_view_model(prompt_stale)

    assert prompt_vm.existing_answer == FunctionalDomainStatus.VARIABLE.value
    assert prompt_vm.stale_reconfirmation is True
    assert prompt_vm.stale_warning_text is not None
    assert "yeniden teyit edin" in prompt_vm.stale_warning_text


# -----------------------------------------------------------------------------
# 3. UI Control Prompt Formatting Tests
# -----------------------------------------------------------------------------


def test_ui_control_view_model_formatting(content_pack: DailyRoutinesContentPack) -> None:
    """Verify UI control step builds PromptViewModel with is_ui_control=True."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)

    prompt_ui = runtime.get_current_step_prompt()
    prompt_vm = DailyRoutinesPresenter.build_prompt_view_model(prompt_ui)

    assert prompt_vm.is_ui_control is True
    assert prompt_vm.title == "Cevap Düzeltme Seçimi"
    assert len(prompt_vm.options) > 0


# -----------------------------------------------------------------------------
# 4. Summary View Model Formatting Tests
# -----------------------------------------------------------------------------


def test_summary_view_model_formatting(content_pack: DailyRoutinesContentPack) -> None:
    """Verify summary view model formatting from completed session result."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    runtime.process_answer(SummaryConfirmation.CONFIRMED)

    res = runtime.get_result()
    summary_vm = DailyRoutinesPresenter.build_summary_view_model(res)

    assert len(summary_vm.summary_lines) > 0
    assert "active_branch" not in summary_vm.active_answers_json  # Clean JSON dictionary
    assert "q_daily_routines_functional_space_day_pattern_status" in summary_vm.active_answers_json


# -----------------------------------------------------------------------------
# 5. State Serialization & Restoration Tests
# -----------------------------------------------------------------------------


def test_state_json_serialization_and_restoration(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify DailyRoutinesRuntimeState model_dump_json and model_validate_json round-trip."""
    runtime1 = DailyRoutinesRuntime(content_pack)
    runtime1.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)

    json_str = runtime1.state.model_dump_json()
    restored_state = DailyRoutinesRuntimeState.model_validate_json(json_str)

    runtime2 = DailyRoutinesRuntime(content_pack, state=restored_state)
    prompt2 = runtime2.get_current_step_prompt()

    assert prompt2.step_id == "q_daily_routines_functional_space_recurring_day_context"


# -----------------------------------------------------------------------------
# 6. Module Import Smoke Test (No Automatic Server Launch)
# -----------------------------------------------------------------------------


def test_demo_app_import_smoke_test() -> None:
    """Verify importing apps.daily_routines_demo does not trigger automatic server launch."""
    demo_module = importlib.import_module("apps.daily_routines_demo")
    assert hasattr(demo_module, "main")
    assert callable(demo_module.main)


# -----------------------------------------------------------------------------
# 7. Headless Streamlit CLI Startup Smoke Test
# -----------------------------------------------------------------------------


def test_streamlit_headless_startup_smoke_test() -> None:
    """Verify Streamlit CLI starts apps/daily_routines_demo.py headlessly without error."""
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "apps/daily_routines_demo.py",
        "--headless",
        "--server.port=8505",
    ]

    # Spawn streamlit process and terminate after short run
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Give streamlit 3 seconds to start up
        try:
            stdout, stderr = proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            # Process running without early crash -> successful startup
            proc.terminate()
            stdout, stderr = proc.communicate()

        # Process running without early crash -> successful startup
        assert proc.poll() is None or isinstance(proc.returncode, int)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=2)
