"""BRIF.AI Daily Routines v0 Interactive Streamlit Demo App."""

from __future__ import annotations

from typing import Any

import streamlit as st

from brif_ai.conversation.daily_routines import (
    DailyRoutinesRuntime,
    DailyRoutinesRuntimeState,
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

    # Header & Branding
    st.title("BRIF.AI")
    st.subheader("Günlük Yaşam ve Mekân Kullanımı")
    st.caption("Modül kurgusu: Mevcut evinizdeki rutin düzen ve mekân kullanımı değerlendirmesi.")
    st.divider()

    # Session State Initialization
    if "runtime_state_json" not in st.session_state:
        st.session_state["runtime_state_json"] = DailyRoutinesRuntimeState().model_dump_json()

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
            st.session_state.pop("error_message", None)
            st.rerun()

    # Display error banner if previous operation produced an error
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
        with st.expander("🔍 Aktif Cevaplar (Geliştirici JSON Görünümü)"):
            st.code(summary_vm.active_answers_json, language="json")

    else:
        # In-Progress Question Flow
        step_prompt = runtime.get_current_step_prompt()
        prompt_vm = DailyRoutinesPresenter.build_prompt_view_model(step_prompt)

        st.markdown(f"#### {prompt_vm.title}")
        st.markdown(f"### {prompt_vm.prompt_text}")

        if prompt_vm.respondent_instruction:
            st.caption(f"💡 {prompt_vm.respondent_instruction}")

        if prompt_vm.stale_warning_text:
            st.warning(prompt_vm.stale_warning_text)

        # Build options mapping for Streamlit widgets
        options = prompt_vm.options or []
        label_to_value: dict[str, str] = {}
        for opt in options:
            label = opt.display_label
            if opt.helper_text:
                label += f" — {opt.helper_text}"
            label_to_value[label] = opt.value

        option_labels = list(label_to_value.keys())

        # Form submission container
        with st.form(key=f"form_{prompt_vm.step_id}"):
            selected_payload: Any = None

            if prompt_vm.is_multiselect:
                # Multi-choice period selection
                prefilled_labels: list[str] = []
                if isinstance(prompt_vm.existing_answer, list):
                    for val in prompt_vm.existing_answer:
                        for lbl, v in label_to_value.items():
                            if v == val:
                                prefilled_labels.append(lbl)

                chosen_labels = st.multiselect(
                    "Zaman dilimlerini seçin (en az 1, en fazla 4):",
                    options=option_labels,
                    default=prefilled_labels,
                )
                selected_payload = [
                    label_to_value[lbl] for lbl in chosen_labels if lbl in label_to_value
                ]

            else:
                # Single-choice radio selection
                default_idx = 0
                if isinstance(prompt_vm.existing_answer, str):
                    for idx, (_lbl, v) in enumerate(label_to_value.items()):
                        if v == prompt_vm.existing_answer:
                            default_idx = idx
                            break

                chosen_label = st.radio(
                    "Lütfen bir seçenek işaretleyin:",
                    options=option_labels,
                    index=default_idx if option_labels else 0,
                )
                selected_payload = label_to_value.get(chosen_label) if chosen_label else None

            submitted = st.form_submit_button(
                "Cevabı Kaydet ve Devam Et ➔", use_container_width=True
            )

            if submitted:
                try:
                    # Clear error message on attempt
                    st.session_state.pop("error_message", None)

                    # Presenter validation
                    validated_payload: str | list[str]
                    if prompt_vm.is_multiselect:
                        validated_payload = DailyRoutinesPresenter.convert_ui_multi_choice(
                            selected_payload, step_prompt
                        )
                    else:
                        validated_payload = DailyRoutinesPresenter.convert_ui_single_choice(
                            selected_payload, step_prompt
                        )

                    # Runtime execution
                    runtime.process_answer(validated_payload)

                    # State persistence and rerun
                    st.session_state["runtime_state_json"] = runtime.state.model_dump_json()
                    st.rerun()

                except Exception as exc:
                    st.session_state["error_message"] = str(exc)
                    st.rerun()


if __name__ == "__main__":
    main()
