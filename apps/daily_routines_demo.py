"""BRIF.AI Daily Routines v0 Interactive Streamlit Demo App."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import streamlit as st

from brif_ai.conversation.daily_routines import (
    DailyRoutinesRuntime,
    DailyRoutinesRuntimeState,
    InvalidAnswerError,
    InvalidSessionStateError,
    SessionStatus,
)
from brif_ai.demo.daily_routines_presenter import DailyRoutinesPresenter


def main() -> None:
    """Streamlit application main entry point."""
    st.set_page_config(
        page_title="BRIF.AI - Günlük Yaşam ve Mekân Kullanımı",
        page_icon="🏢",
        layout="centered",
    )

    # Fixed Application Titles
    st.title("BRIF.AI")
    st.subheader("Günlük Yaşam ve Mekân Kullanımı")
    st.caption(
        "Modül kurgusu: Mevcut evinizdeki rutin düzen, mekân kullanımı ve zaman dilimleri "
        "değerlendirmesi."
    )
    st.divider()

    # Session State Keys Initialization
    if "runtime_state_json" not in st.session_state:
        st.session_state["runtime_state_json"] = DailyRoutinesRuntimeState().model_dump_json()

    if "widget_values" not in st.session_state:
        st.session_state["widget_values"] = {}

    if "error_message" not in st.session_state:
        st.session_state["error_message"] = None

    if "last_submission_fingerprint" not in st.session_state:
        st.session_state["last_submission_fingerprint"] = None

    # Reconstruct runtime from JSON state on every rerun
    runtime_state = DailyRoutinesRuntimeState.model_validate_json(
        st.session_state["runtime_state_json"]
    )
    runtime = DailyRoutinesRuntime(state=runtime_state)

    # Sidebar Actions
    with st.sidebar:
        st.header("Oturum Yönetimi")
        if st.button("🔄 Oturumu Sıfırla", use_container_width=True):
            st.session_state["runtime_state_json"] = DailyRoutinesRuntimeState().model_dump_json()
            st.session_state["widget_values"] = {}
            st.session_state["error_message"] = None
            st.session_state["last_submission_fingerprint"] = None
            st.rerun()

    # Display error banner if previous operation failed
    error_msg = st.session_state.get("error_message")
    if error_msg:
        st.error(f"❌ {error_msg}")

    # Check Module Completion Status
    if runtime.state.status == SessionStatus.COMPLETED:
        session_result = runtime.get_result()
        summary_vm = DailyRoutinesPresenter.build_summary_view_model(session_result)

        st.success("✅ Modül Başarıyla Tamamlandı!")
        st.markdown("### Değerlendirme Özeti")

        for line in summary_vm.summary_lines:
            st.info(f"📌 {line}")

        st.divider()
        with st.expander("🔍 Geliştirici Görünümü (Aktif Cevaplar JSON)"):
            st.code(summary_vm.active_answers_json, language="json")

    else:
        # In-Progress Question Flow
        step_prompt = runtime.get_current_step_prompt()
        prompt_vm = DailyRoutinesPresenter.build_prompt_view_model(step_prompt)

        st.markdown(f"### {prompt_vm.prompt_text}")

        if prompt_vm.respondent_instruction:
            st.caption(f"💡 {prompt_vm.respondent_instruction}")

        if prompt_vm.stale_warning_text:
            st.warning(prompt_vm.stale_warning_text)

        # Options mapping strictly uses display_label
        options = prompt_vm.options or []
        label_to_value: dict[str, str] = {}
        value_to_label: dict[str, str] = {}
        label_to_helper: dict[str, str | None] = {}

        for opt in options:
            label_to_value[opt.display_label] = opt.value
            value_to_label[opt.value] = opt.display_label
            label_to_helper[opt.display_label] = opt.helper_text

        option_labels = list(label_to_value.keys())
        step_widget_key = f"widget_{prompt_vm.step_id}"
        stored_widget_value = st.session_state["widget_values"].get(prompt_vm.step_id)

        # Form submission container
        with st.form(key=f"form_{prompt_vm.step_id}"):
            selected_payload: Any = None

            if prompt_vm.input_kind == "multiple_choice":
                # Multi-choice period selection
                prefilled_labels: list[str] = []
                if isinstance(stored_widget_value, list):
                    prefilled_labels = [lbl for lbl in stored_widget_value if lbl in label_to_value]
                elif isinstance(prompt_vm.existing_answer, list):
                    for val in prompt_vm.existing_answer:
                        if val in value_to_label:
                            prefilled_labels.append(value_to_label[val])

                chosen_labels = st.multiselect(
                    "Zaman dilimlerini seçin:",
                    options=option_labels,
                    default=prefilled_labels,
                    key=step_widget_key,
                )
                selected_payload = [
                    label_to_value[lbl] for lbl in chosen_labels if lbl in label_to_value
                ]

                # Display helper_text for selected choices separately
                for lbl in chosen_labels:
                    helper = label_to_helper.get(lbl)
                    if helper:
                        st.caption(f"ℹ️ **{lbl}**: {helper}")

            elif prompt_vm.input_kind == "free_text":
                # Free text input
                initial_text = ""
                if isinstance(stored_widget_value, str):
                    initial_text = stored_widget_value
                elif isinstance(prompt_vm.existing_answer, str):
                    initial_text = prompt_vm.existing_answer

                selected_payload = st.text_area(
                    "Açıklamanızı yazın:",
                    value=initial_text,
                    key=step_widget_key,
                )

            else:
                # Single-choice radio selection: stored_widget_value holds raw option.value
                default_idx: int | None = None
                target_value: str | None = None

                if isinstance(stored_widget_value, str):
                    target_value = stored_widget_value
                elif isinstance(prompt_vm.existing_answer, str):
                    target_value = prompt_vm.existing_answer

                if target_value is not None:
                    for idx, (_lbl, v) in enumerate(label_to_value.items()):
                        if v == target_value:
                            default_idx = idx
                            break

                chosen_label = st.radio(
                    "Lütfen bir seçenek işaretleyin:",
                    options=option_labels,
                    index=default_idx,
                    key=step_widget_key,
                )
                selected_payload = label_to_value.get(chosen_label) if chosen_label else None

                # Display helper_text for single choice selection separately
                if chosen_label:
                    helper = label_to_helper.get(chosen_label)
                    if helper:
                        st.caption(f"ℹ️ {helper}")

            submitted = st.form_submit_button(
                "Cevabı Kaydet ve Devam Et ➔", use_container_width=True
            )

            if submitted:
                # Save raw payload (option.value for single choice) in widget_values
                st.session_state["widget_values"][prompt_vm.step_id] = (
                    chosen_labels if prompt_vm.input_kind == "multiple_choice" else selected_payload
                )

                try:
                    # Validate selection via presenter
                    validated_payload: str | list[str]
                    if prompt_vm.input_kind == "multiple_choice":
                        validated_payload = DailyRoutinesPresenter.convert_ui_multi_choice(
                            prompt_vm, selected_payload
                        )
                    elif prompt_vm.input_kind == "free_text":
                        validated_payload = DailyRoutinesPresenter.convert_ui_free_text(
                            prompt_vm, selected_payload
                        )
                    else:
                        validated_payload = DailyRoutinesPresenter.convert_ui_single_choice(
                            prompt_vm, selected_payload
                        )

                    # Compute double-submission fingerprint
                    raw_state = st.session_state["runtime_state_json"]
                    norm_answer = json.dumps(validated_payload, ensure_ascii=False, sort_keys=True)
                    fingerprint = hashlib.sha256(
                        f"{raw_state}:{prompt_vm.step_id}:{norm_answer}".encode()
                    ).hexdigest()

                    # Prevent duplicate processing
                    if st.session_state.get("last_submission_fingerprint") == fingerprint:
                        st.rerun()

                    # Process answer with runtime
                    runtime.process_answer(validated_payload)

                    # Persist state & fingerprint on success, clean completed widget_values
                    st.session_state["runtime_state_json"] = runtime.state.model_dump_json()
                    st.session_state["last_submission_fingerprint"] = fingerprint
                    st.session_state["widget_values"].pop(prompt_vm.step_id, None)
                    st.session_state["error_message"] = None
                    st.rerun()

                except InvalidAnswerError:
                    st.session_state["error_message"] = (
                        "Geçersiz veya zaman aşımına uğramış bir yanıt tespit edildi. "
                        "Lütfen seçiminizi gözden geçirin."
                    )
                    st.rerun()
                except InvalidSessionStateError:
                    st.session_state["error_message"] = (
                        "Oturum durumunda uyumsuzluk tespit edildi. Lütfen işlemi tekrarlayın."
                    )
                    st.rerun()
                except ValueError as exc:
                    st.session_state["error_message"] = str(exc)
                    st.rerun()
                except Exception:
                    st.session_state["error_message"] = (
                        "Beklenmeyen bir hata oluştu. Oturumunuz değiştirilmedi."
                    )
                    st.rerun()


if __name__ == "__main__":
    main()
