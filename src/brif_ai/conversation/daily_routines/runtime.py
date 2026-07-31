"""Runtime orchestration engine for BRIF.AI Daily Routines v0."""

from __future__ import annotations

from typing import Any

from brif_ai.conversation.daily_routines.enums import (
    AnswerValidityState,
    CorrectionTarget,
    FunctionalDomainStatus,
    InvalidAnswerError,
    InvalidSessionStateError,
    SessionStatus,
    WordingBranch,
)
from brif_ai.conversation.daily_routines.invalidation import InvalidationEngine
from brif_ai.conversation.daily_routines.loader import load_daily_routines_content_pack
from brif_ai.conversation.daily_routines.models import (
    DailyRoutinesContentPack,
    DailyRoutinesRuntimeState,
    OptionDefinition,
    QuestionWordingVariant,
    SessionStepResult,
    StepPrompt,
)


class DailyRoutinesRuntime:
    """Orchestrates prompts, option filtering, answer processing, and completion state."""

    def __init__(
        self,
        content_pack: DailyRoutinesContentPack | None = None,
        state: DailyRoutinesRuntimeState | None = None,
    ) -> None:
        self.pack = content_pack if content_pack is not None else load_daily_routines_content_pack()
        self.engine = InvalidationEngine(self.pack)
        self.state = state if state is not None else DailyRoutinesRuntimeState()

        self._questions_by_id = {q.id: q for q in self.pack.questions}
        self._ui_controls_by_id = {ui.id: ui for ui in self.pack.ui_state_controls}
        self._option_sets_by_id = {os.id: os for os in self.pack.option_sets}
        self._wordings_by_id = {w.question_id: w for w in self.pack.wording_variants}
        self._rules_by_source_and_value = {
            (r.source_question_id, r.expected_value): r
            for r in self.pack.flow_rules
            if r.expected_value
        }

    def get_current_step_prompt(self) -> StepPrompt:
        """Construct current step prompt with option filtering and existing answer prefill."""
        if self.state.status == SessionStatus.COMPLETED:
            raise InvalidSessionStateError("Cannot get step prompt for a completed session")

        curr_id = self.state.current_step_id
        if not curr_id:
            raise InvalidSessionStateError("Current step ID is not set")

        if curr_id not in self._questions_by_id and curr_id not in self._ui_controls_by_id:
            raise InvalidAnswerError(f"Unknown current step ID: {curr_id!r}")

        content_key: str
        option_set_id: str | None = None
        multi_select_contract = None

        if curr_id in self._questions_by_id:
            q_def = self._questions_by_id[curr_id]
            content_key = q_def.content_key
            option_set_id = q_def.option_set_id
            if str(q_def.answer_type) == "MULTIPLE_CHOICE":
                multi_select_contract = self.pack.multi_select_contract
        else:
            ui_def = self._ui_controls_by_id[curr_id]
            content_key = ui_def.content_key
            option_set_id = ui_def.option_set_id

        wording_variant: QuestionWordingVariant | None = None
        active_branch = self.state.session_state.active_branch
        active_branch_str = str(
            active_branch.value if hasattr(active_branch, "value") else active_branch
        )

        if curr_id in self._questions_by_id:
            wording_obj = self._wordings_by_id.get(curr_id)
            if not wording_obj:
                raise InvalidSessionStateError(
                    f"No wording variants found for question {curr_id!r}"
                )
            wording_variant = next(
                (v for v in wording_obj.variants if v.branch == active_branch),
                wording_obj.variants[0],
            )

        options: list[OptionDefinition] | None = None
        if option_set_id and option_set_id in self._option_sets_by_id:
            raw_options = self._option_sets_by_id[option_set_id].options
            filtered_options: list[OptionDefinition] = []

            for opt in raw_options:
                opt_val_str = str(opt.value)
                if (
                    (curr_id.endswith("_sleeping_status") or curr_id.endswith("_bathroom_status"))
                    and opt_val_str
                    == FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
                ):
                    continue

                if (
                    curr_id == "bp_ui_room_use_correction_selector"
                    and active_branch_str == WordingBranch.IRREGULAR.value
                    and opt_val_str == CorrectionTarget.RECURRING_DAY_CONTEXT.value
                ):
                    continue

                filtered_options.append(opt)

            options = filtered_options

        existing_answer: Any | None = None
        record = self.state.session_state.answers.get(curr_id)
        if record and record.validity_state in (
            AnswerValidityState.ACTIVE,
            AnswerValidityState.STALE_REQUIRES_RECONFIRMATION,
        ):
            existing_answer = record.value

        return StepPrompt(
            question_id=curr_id,
            content_key=content_key,
            wording=wording_variant,
            options=options,
            existing_answer=existing_answer,
            multi_select_contract=multi_select_contract,
        )

    def process_answer(self, answer: Any) -> SessionStepResult:
        """Validate and record answer, resolve next step, and update runtime state."""
        if self.state.status == SessionStatus.COMPLETED:
            raise InvalidSessionStateError("Cannot process answer for a completed session")

        curr_id = self.state.current_step_id
        if not curr_id:
            raise InvalidSessionStateError("Current step ID is not set")

        if curr_id not in self._questions_by_id and curr_id not in self._ui_controls_by_id:
            raise InvalidAnswerError(f"Unknown current step ID: {curr_id!r}")

        self.engine.record_answer(self.state.session_state, curr_id, answer)

        next_step = self.engine.resolve_next_step(self.state.session_state, curr_id)

        target_closure_effect = None
        ans_record = self.state.session_state.answers.get(curr_id)
        if ans_record and isinstance(ans_record.value, str):
            matched_rule = self._rules_by_source_and_value.get((curr_id, ans_record.value))
            if matched_rule:
                target_closure_effect = matched_rule.target_closure_effect

        if next_step == "module_complete":
            self.state.status = SessionStatus.COMPLETED
            self.state.current_step_id = None
            self.state.terminal_target = "module_complete"
            summary_lines = self.engine.generate_summary(self.state.session_state)

            return SessionStepResult(
                answered_step_id=curr_id,
                next_step_id=None,
                terminal_target="module_complete",
                summary=summary_lines,
                target_closure_effect=target_closure_effect,
            )

        else:
            self.state.current_step_id = next_step
            return SessionStepResult(
                answered_step_id=curr_id,
                next_step_id=next_step,
                terminal_target=None,
                summary=None,
                target_closure_effect=target_closure_effect,
            )
