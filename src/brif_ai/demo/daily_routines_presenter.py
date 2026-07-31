"""Presenter / adapter layer for BRIF.AI Daily Routines Streamlit Demo v0."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from brif_ai.conversation.daily_routines.enums import InvalidSessionStateError
from brif_ai.conversation.daily_routines.runtime_models import (
    DailyRoutinesSessionResult,
    StepPrompt,
)


@dataclass(frozen=True)
class UIOption:
    """Represents a single selectable option formatted for UI display."""

    value: str
    display_label: str
    helper_text: str | None = None


@dataclass(frozen=True)
class PromptViewModel:
    """Clean view model representation of a step prompt for UI rendering."""

    step_id: str
    is_ui_control: bool
    input_kind: Literal["single_choice", "multiple_choice", "free_text"]
    prompt_text: str
    respondent_instruction: str
    options: list[UIOption]
    existing_answer: str | list[str] | None
    stale_reconfirmation: bool
    stale_warning_text: str | None
    min_selected_items: int | None = None
    max_selected_items: int | None = None
    canonical_value_order: list[str] | None = None


@dataclass(frozen=True)
class SummaryViewModel:
    """Clean view model representation of completed module summary and active answers."""

    summary_lines: list[str]
    active_answers_json: str


class DailyRoutinesPresenter:
    """Pure presenter adapting runtime StepPrompt objects into UI View Models."""

    @staticmethod
    def build_prompt_view_model(prompt: StepPrompt) -> PromptViewModel:
        """Adapt a StepPrompt object into a PromptViewModel for presentation."""
        input_kind: Literal["single_choice", "multiple_choice", "free_text"]
        prompt_text: str
        respondent_instruction: str
        min_selected_items: int | None = None
        max_selected_items: int | None = None
        canonical_value_order: list[str] | None = None

        if prompt.is_ui_control:
            if prompt.ui_control_definition is None:
                raise InvalidSessionStateError("Missing UI control definition for prompt step.")
            input_kind = "single_choice"
            prompt_text = prompt.ui_control_definition.purpose
            respondent_instruction = "Düzeltmek istediğiniz bölümü seçin."
        else:
            if prompt.wording_variant is None:
                raise InvalidSessionStateError(
                    f"Wording variant missing for prompt step '{prompt.step_id}'."
                )

            prompt_text = prompt.wording_variant.prompt_text
            respondent_instruction = prompt.wording_variant.respondent_instruction

            if prompt.question_definition is not None:
                ans_type = str(prompt.question_definition.answer_type)
                if ans_type == "MULTIPLE_CHOICE":
                    input_kind = "multiple_choice"
                    if prompt.multi_select_contract is None:
                        raise InvalidSessionStateError(
                            f"MultiSelectContract missing for prompt step '{prompt.step_id}'."
                        )
                    contract = prompt.multi_select_contract
                    min_selected_items = contract.min_selected_items
                    max_selected_items = contract.max_selected_items
                    canonical_value_order = [
                        str(item.value) if hasattr(item, "value") else str(item)
                        for item in contract.canonical_order
                    ]
                elif ans_type == "FREE_TEXT":
                    input_kind = "free_text"
                else:
                    input_kind = "single_choice"
            else:
                input_kind = "single_choice"

        ui_options: list[UIOption] = []
        if prompt.options:
            for opt in prompt.options:
                ui_options.append(
                    UIOption(
                        value=str(opt.value),
                        display_label=opt.display_label,
                        helper_text=opt.helper_text,
                    )
                )

        stale_warning: str | None = None
        if prompt.stale_reconfirmation:
            stale_warning = (
                "⚠️ Bu cevabı yeniden teyit edin. Önceki seçiminiz "
                "güncellenen bilgiler nedeniyle tekrar onay gerektirmektedir."
            )

        return PromptViewModel(
            step_id=prompt.step_id,
            is_ui_control=prompt.is_ui_control,
            input_kind=input_kind,
            prompt_text=prompt_text,
            respondent_instruction=respondent_instruction,
            options=ui_options,
            existing_answer=prompt.existing_answer,
            stale_reconfirmation=prompt.stale_reconfirmation,
            stale_warning_text=stale_warning,
            min_selected_items=min_selected_items,
            max_selected_items=max_selected_items,
            canonical_value_order=canonical_value_order,
        )

    @staticmethod
    def convert_ui_single_choice(view_model: PromptViewModel, selected_value: str | None) -> str:
        """Validate and convert UI single choice selection into runtime answer payload."""
        if not selected_value or not selected_value.strip():
            raise ValueError("Lütfen devam etmek için bir seçenek belirleyin.")

        valid_values = {opt.value for opt in view_model.options}
        if selected_value not in valid_values:
            raise ValueError(
                f"Geçersiz seçim: {selected_value!r}. Lütfen sunulan seçeneklerden birini seçin."
            )

        return selected_value

    @staticmethod
    def convert_ui_multi_choice(
        view_model: PromptViewModel, selected_values: list[str] | None
    ) -> list[str]:
        """Validate and convert UI multi choice selection into canonical runtime answer payload."""
        if not selected_values:
            raise ValueError("Lütfen devam etmek için en az bir seçenek seçin.")

        # Duplicate check
        if len(selected_values) != len(set(selected_values)):
            raise ValueError("Çoklu seçimde tekrar eden değer seçilemez.")

        valid_values = {opt.value for opt in view_model.options}
        for val in selected_values:
            if val not in valid_values:
                raise ValueError(
                    f"Geçersiz seçim: {val!r}. Lütfen sunulan seçeneklerden tercih yapın."
                )

        min_allowed = view_model.min_selected_items or 1
        max_allowed = view_model.max_selected_items or 4

        if len(selected_values) < min_allowed:
            raise ValueError(f"En az {min_allowed} seçenek seçilmelidir.")
        if len(selected_values) > max_allowed:
            raise ValueError(f"En fazla {max_allowed} seçenek seçilebilir.")

        # Sort into canonical order
        order_reference = view_model.canonical_value_order or [o.value for o in view_model.options]
        order_map = {val: idx for idx, val in enumerate(order_reference)}
        sorted_values = sorted(selected_values, key=lambda v: order_map.get(v, 999))

        return sorted_values

    @staticmethod
    def convert_ui_free_text(view_model: PromptViewModel, text: str | None) -> str:
        """Validate and convert UI free text input into runtime answer payload."""
        if not text or not text.strip():
            raise ValueError("Serbest metin alanı boş bırakılamaz.")

        return text.strip()

    @staticmethod
    def build_summary_view_model(result: DailyRoutinesSessionResult) -> SummaryViewModel:
        """Adapt a completed session result into a SummaryViewModel.

        Preserves Turkish characters via ensure_ascii=False.
        """
        answers_dict: dict[str, Any] = {}
        for q_id, rec in result.active_answers.items():
            answers_dict[q_id] = {
                "question_id": rec.question_id,
                "value": rec.value,
                "validity_state": str(rec.validity_state),
            }

        active_json = json.dumps(answers_dict, ensure_ascii=False, indent=2)

        return SummaryViewModel(
            summary_lines=result.summary_lines,
            active_answers_json=active_json,
        )
