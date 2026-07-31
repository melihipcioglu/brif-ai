"""Presenter adapter, state serialization, and Streamlit demo tests."""

from __future__ import annotations

import importlib
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

pytest.importorskip("streamlit")

from brif_ai.conversation.daily_routines import (
    CorrectionTarget,
    DailyRoutinesContentPack,
    DailyRoutinesRuntime,
    DailyRoutinesRuntimeState,
    DayPatternStatus,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidSessionStateError,
    RecurringDayContext,
    SummaryConfirmation,
    WordingBranch,
    load_daily_routines_content_pack,
)
from brif_ai.conversation.daily_routines.models import (
    DailyRoutinesQuestionDefinition,
)
from brif_ai.conversation.daily_routines.runtime_models import StepPrompt
from brif_ai.conversation.models.common import (
    AnswerType,
    ConversationModule,
    QuestionStatus,
)
from brif_ai.demo.daily_routines_presenter import (
    DailyRoutinesPresenter,
    PromptViewModel,
    UIOption,
)


@pytest.fixture
def content_pack() -> DailyRoutinesContentPack:
    """Load default Daily Routines v0 content pack."""
    return load_daily_routines_content_pack()


# -----------------------------------------------------------------------------
# 1. Single Choice Label / Value Matching & Validation Tests
# -----------------------------------------------------------------------------


def test_single_choice_label_value_matching_and_validation(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify single choice option matching and invalid choice rejection."""
    runtime = DailyRoutinesRuntime(content_pack)
    prompt = runtime.get_current_step_prompt()
    vm = DailyRoutinesPresenter.build_prompt_view_model(prompt)

    assert vm.input_kind == "single_choice"
    val = DailyRoutinesPresenter.convert_ui_single_choice(
        vm, DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value
    )
    assert val == DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value

    # Empty choice rejection
    with pytest.raises(ValueError, match="Lütfen devam etmek için bir seçenek"):
        DailyRoutinesPresenter.convert_ui_single_choice(vm, "")

    # Invalid choice rejection
    with pytest.raises(ValueError, match="Geçersiz seçim"):
        DailyRoutinesPresenter.convert_ui_single_choice(vm, "invalid_option")


# -----------------------------------------------------------------------------
# 2. Multiple Choice Canonical Ordering, Duplicate, and Min/Max Limit Tests
# -----------------------------------------------------------------------------


def test_multiple_choice_canonical_ordering_and_limits(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify canonical ordering, duplicate rejection, and min/max item bounds."""
    runtime = DailyRoutinesRuntime(content_pack)
    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    runtime.process_answer(FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)

    prompt = runtime.get_current_step_prompt()
    vm = DailyRoutinesPresenter.build_prompt_view_model(prompt)

    assert vm.input_kind == "multiple_choice"

    # Out of order selection returned in canonical order
    vals = DailyRoutinesPresenter.convert_ui_multi_choice(vm, ["night", "morning"])
    assert vals == ["morning", "night"]

    # Duplicate selection rejection
    with pytest.raises(ValueError, match="tekrar eden değer"):
        DailyRoutinesPresenter.convert_ui_multi_choice(vm, ["morning", "morning"])

    # Invalid option rejection
    with pytest.raises(ValueError, match="Geçersiz seçim"):
        DailyRoutinesPresenter.convert_ui_multi_choice(vm, ["unknown_period"])

    # Custom VM for min/max limit tests
    vm_limits = PromptViewModel(
        step_id="test_limits",
        is_ui_control=False,
        input_kind="multiple_choice",
        prompt_text="Test",
        respondent_instruction="",
        options=[
            UIOption("a", "A"),
            UIOption("b", "B"),
            UIOption("c", "C"),
            UIOption("d", "D"),
        ],
        existing_answer=None,
        stale_reconfirmation=False,
        stale_warning_text=None,
        min_selected_items=2,
        max_selected_items=3,
        canonical_value_order=["a", "b", "c", "d"],
    )

    with pytest.raises(ValueError, match="En az 2 seçenek"):
        DailyRoutinesPresenter.convert_ui_multi_choice(vm_limits, ["a"])

    with pytest.raises(ValueError, match="En fazla 3 seçenek"):
        DailyRoutinesPresenter.convert_ui_multi_choice(vm_limits, ["a", "b", "c", "d"])


# -----------------------------------------------------------------------------
# 3. Free Text Conversion & Empty Rejection Tests
# -----------------------------------------------------------------------------


def test_free_text_conversion_and_rejection() -> None:
    """Verify free text validation and blank text rejection."""
    vm_free = PromptViewModel(
        step_id="test_free",
        is_ui_control=False,
        input_kind="free_text",
        prompt_text="Free text prompt",
        respondent_instruction="",
        options=[],
        existing_answer=None,
        stale_reconfirmation=False,
        stale_warning_text=None,
    )

    valid_text = DailyRoutinesPresenter.convert_ui_free_text(vm_free, "  Hello world  ")
    assert valid_text == "Hello world"

    with pytest.raises(ValueError, match="boş bırakılamaz"):
        DailyRoutinesPresenter.convert_ui_free_text(vm_free, "   ")


# -----------------------------------------------------------------------------
# 4. ACTIVE Answer Prefill, STALE Warning & UI Control Presentation Tests
# -----------------------------------------------------------------------------


def test_active_and_stale_prefill_and_ui_control(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify ACTIVE prefill, STALE warning, and UI control purpose rendering."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)

    # ACTIVE answer prefill on Summary step
    prompt_active = runtime.get_current_step_prompt()
    vm_active = DailyRoutinesPresenter.build_prompt_view_model(prompt_active)
    assert vm_active.stale_reconfirmation is False
    assert vm_active.stale_warning_text is None

    # Reject summary to get UI control selector
    runtime.process_answer(SummaryConfirmation.REJECTED_FOR_CORRECTION)

    # UI Control Step Presentation
    prompt_ui = runtime.get_current_step_prompt()
    vm_ui = DailyRoutinesPresenter.build_prompt_view_model(prompt_ui)

    assert vm_ui.is_ui_control is True
    assert prompt_ui.ui_control_definition is not None
    assert vm_ui.prompt_text == prompt_ui.ui_control_definition.purpose
    assert vm_ui.respondent_instruction == "Düzeltmek istediğiniz bölümü seçin."

    # Perform correction target change to trigger STALE state
    runtime.process_answer(CorrectionTarget.RECURRING_DAY_CONTEXT)
    runtime.process_answer(RecurringDayContext.WORK_FROM_HOME_DAY)

    prompt_stale = runtime.get_current_step_prompt()
    vm_stale = DailyRoutinesPresenter.build_prompt_view_model(prompt_stale)

    assert vm_stale.existing_answer == FunctionalDomainStatus.VARIABLE.value
    assert vm_stale.stale_reconfirmation is True
    assert vm_stale.stale_warning_text is not None
    assert "yeniden teyit edin" in vm_stale.stale_warning_text


# -----------------------------------------------------------------------------
# 5. Normal Question Wording Usage & Missing Wording Rejection Tests
# -----------------------------------------------------------------------------


def test_normal_question_wording_usage_and_missing_wording_rejection(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify prompt wording extraction and missing wording error handling."""
    runtime = DailyRoutinesRuntime(content_pack)
    prompt = runtime.get_current_step_prompt()
    vm = DailyRoutinesPresenter.build_prompt_view_model(prompt)

    assert prompt.wording_variant is not None
    assert vm.prompt_text == prompt.wording_variant.prompt_text
    assert vm.respondent_instruction == prompt.wording_variant.respondent_instruction

    # Create dummy StepPrompt missing wording_variant
    bad_prompt = StepPrompt(
        step_id="q_test",
        is_ui_control=False,
        active_branch=WordingBranch.STABLE,
        content_key="key",
        question_definition=DailyRoutinesQuestionDefinition(
            id="q_test",
            module=ConversationModule.DAILY_ROUTINES,
            purpose="Test purpose",
            content_key="key",
            answer_type=AnswerType.SINGLE_CHOICE,
            required=True,
            output_target_ids=["target_1"],
            allowed_follow_up_question_ids=[],
            applicable_stakeholder_roles=["resident"],
            display_order=1,
            source_metadata="test",
            status=QuestionStatus.APPROVED,
            option_set_id="day_pattern_status",
        ),
        ui_control_definition=None,
        wording_variant=None,  # Missing!
        option_set=None,
        options=[],
        existing_answer=None,
        stale_reconfirmation=False,
    )

    with pytest.raises(InvalidSessionStateError, match="Wording variant missing"):
        DailyRoutinesPresenter.build_prompt_view_model(bad_prompt)


# -----------------------------------------------------------------------------
# 6. Summary JSON Turkish Character Preservation Tests
# -----------------------------------------------------------------------------


def test_summary_json_turkish_character_preservation(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """Verify active_answers_json preserves Turkish characters with ensure_ascii=False."""
    runtime = DailyRoutinesRuntime(content_pack)

    runtime.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    runtime.process_answer(RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    for _ in range(5):
        runtime.process_answer(FunctionalDomainStatus.VARIABLE)
    runtime.process_answer(HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    runtime.process_answer(SummaryConfirmation.CONFIRMED)

    res = runtime.get_result()
    vm_sum = DailyRoutinesPresenter.build_summary_view_model(res)

    assert (
        "\\u" not in vm_sum.active_answers_json
    )  # Turkish characters are raw, not escaped unicode
    assert "stable_recurring_day_available" in vm_sum.active_answers_json


# -----------------------------------------------------------------------------
# 7. State JSON Serialize & Restore Tests
# -----------------------------------------------------------------------------


def test_state_json_serialize_and_restore(content_pack: DailyRoutinesContentPack) -> None:
    """Verify DailyRoutinesRuntimeState JSON serialization and runtime restoration."""
    runtime1 = DailyRoutinesRuntime(content_pack)
    runtime1.process_answer(DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)

    state_json = runtime1.state.model_dump_json()
    restored_state = DailyRoutinesRuntimeState.model_validate_json(state_json)

    runtime2 = DailyRoutinesRuntime(content_pack, state=restored_state)
    prompt2 = runtime2.get_current_step_prompt()

    assert prompt2.step_id == "q_daily_routines_functional_space_recurring_day_context"


# -----------------------------------------------------------------------------
# 8. Module Import Smoke Test (No Automatic Main Launch)
# -----------------------------------------------------------------------------


def test_demo_app_import_smoke_test() -> None:
    """Verify importing apps.daily_routines_demo does not trigger automatic server launch."""
    demo_module = importlib.import_module("apps.daily_routines_demo")
    assert hasattr(demo_module, "main")
    assert callable(demo_module.main)


# -----------------------------------------------------------------------------
# 9. Headless Streamlit Startup & Health Check Test
# -----------------------------------------------------------------------------


def _find_free_port() -> int:
    """Find a free local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_streamlit_headless_startup_and_health_check() -> None:
    """Verify Streamlit app starts headlessly and responds on health endpoint."""
    port = _find_free_port()
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "apps/daily_routines_demo.py",
        "--server.headless=true",
        f"--server.port={port}",
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    health_ok = False
    start_time = time.time()

    try:
        # Poll health endpoint for up to 6 seconds
        while time.time() - start_time < 6.0:
            if proc.poll() is not None:
                # Process crashed early
                break

            try:
                with urllib.request.urlopen(health_url, timeout=1) as resp:
                    if resp.status == 200:
                        health_ok = True
                        break
            except Exception:
                time.sleep(0.3)

    finally:
        # Guarantee process cleanup
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        stdout, stderr = proc.communicate()

    # Assert Streamlit server started cleanly and responded to health check
    assert health_ok, f"Streamlit failed health check on port {port}. Stderr:\n{stderr}"
