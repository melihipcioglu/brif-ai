"""Presenter / adapter layer for BRIF.AI Daily Routines Streamlit Demo v0."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from brif_ai.conversation.daily_routines.enums import InvalidAnswerError
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
    title: str
    prompt_text: str
    respondent_instruction: str
    is_multiselect: bool
    options: list[UIOption]
    existing_answer: str | list[str] | None
    stale_reconfirmation: bool
    stale_warning_text: str | None


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
        is_multiselect = (
            prompt.question_definition is not None
            and str(prompt.question_definition.answer_type) == "MULTIPLE_CHOICE"
        )

        title: str
        prompt_text: str
        respondent_instruction: str

        if not prompt.is_ui_control:
            title = f"Soru ID: {prompt.step_id}"
            if prompt.wording_variant:
                prompt_text = prompt.wording_variant.prompt_text
                respondent_instruction = prompt.wording_variant.respondent_instruction
            else:
                prompt_text = prompt.content_key
                respondent_instruction = ""
        else:
            title = "Cevap Düzeltme Seçimi"
            prompt_text = "Lütfen düzeltmek veya incelemek istediğiniz bölümü seçin:"
            respondent_instruction = "Aşağıdaki seçeneklerden birini işaretleyerek devam edin."

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
            title=title,
            prompt_text=prompt_text,
            respondent_instruction=respondent_instruction,
            is_multiselect=is_multiselect,
            options=ui_options,
            existing_answer=prompt.existing_answer,
            stale_reconfirmation=prompt.stale_reconfirmation,
            stale_warning_text=stale_warning,
        )

    @staticmethod
    def convert_ui_single_choice(selected_value: str | None, prompt: StepPrompt) -> str:
        """Validate and convert UI single choice selection into runtime answer payload."""
        if not selected_value or not selected_value.strip():
            raise InvalidAnswerError("Lütfen devam etmek için bir seçenek belirleyin.")

        valid_values = {str(opt.value) for opt in (prompt.options or [])}
        if selected_value not in valid_values:
            raise InvalidAnswerError(
                f"Geçersiz seçim: {selected_value!r}. Lütfen sunulan seçeneklerden birini seçin."
            )

        return selected_value

    @staticmethod
    def convert_ui_multi_choice(selected_values: list[str] | None, prompt: StepPrompt) -> list[str]:
        """Validate and convert UI multi choice selection into runtime answer payload."""
        if not selected_values:
            raise InvalidAnswerError("Lütfen devam etmek için en az bir seçenek seçin.")

        valid_values = {str(opt.value) for opt in (prompt.options or [])}
        for val in selected_values:
            if val not in valid_values:
                raise InvalidAnswerError(
                    f"Geçersiz seçim: {val!r}. Lütfen sunulan seçeneklerden tercih yapın."
                )

        return selected_values

    @staticmethod
    def build_summary_view_model(result: DailyRoutinesSessionResult) -> SummaryViewModel:
        """Adapt a completed session result into a SummaryViewModel."""
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
