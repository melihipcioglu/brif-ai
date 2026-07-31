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
    TargetClosureEffect,
    WordingBranch,
)
from brif_ai.conversation.daily_routines.invalidation import InvalidationEngine
from brif_ai.conversation.daily_routines.loader import load_daily_routines_content_pack
from brif_ai.conversation.daily_routines.models import (
    DailyRoutinesContentPack,
    DailyRoutinesQuestionDefinition,
    OptionDefinition,
    OptionSet,
    QuestionWordingVariant,
    UIStateControlDefinition,
)
from brif_ai.conversation.daily_routines.runtime_models import (
    DailyRoutinesRuntimeState,
    DailyRoutinesSessionResult,
    SessionStepResult,
    StepPrompt,
)


class DailyRoutinesRuntime:
    """Orchestrates prompts, option filtering, answer processing, state persistence, and completion state."""

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
        self._rules_by_source_any = {
            r.source_question_id: r for r in self.pack.flow_rules if r.expected_value is None
        }

        # Validate restored IN_PROGRESS state current_step_id
        if self.state.status == SessionStatus.IN_PROGRESS:
            curr_id = self.state.current_step_id
            if (
                not curr_id
                or curr_id not in self._questions_by_id
                and curr_id not in self._ui_controls_by_id
            ):
                raise InvalidSessionStateError(
                    f"Restored IN_PROGRESS state has invalid current_step_id: {curr_id!r}"
                )

    def get_current_step_prompt(self) -> StepPrompt:
        """Construct current step prompt with detailed metadata, option filtering, and prefill."""
        if self.state.status == SessionStatus.COMPLETED:
            raise InvalidSessionStateError("Cannot get step prompt for a completed session")

        curr_id = self.state.current_step_id
        if not curr_id:
            raise InvalidSessionStateError("Current step ID is not set")

        if curr_id not in self._questions_by_id and curr_id not in self._ui_controls_by_id:
            raise InvalidAnswerError(f"Unknown current step ID: {curr_id!r}")

        is_ui_control = curr_id in self._ui_controls_by_id
        q_def: DailyRoutinesQuestionDefinition | None = None
        ui_def: UIStateControlDefinition | None = None
        content_key: str
        option_set_id: str | None = None
        multi_select_contract = None

        if not is_ui_control:
            q_def = self._questions_by_id[curr_id]
            content_key = q_def.content_key
            option_set_id = q_def.option_set_id
            if str(q_def.answer_type) == "MULTIPLE_CHOICE":
                multi_select_contract = self.pack.multi_select_contract
        else:
            ui_def = self._ui_controls_by_id[curr_id]
            content_key = ui_def.content_key
            option_set_id = ui_def.option_set_id

        active_branch = self.state.session_state.active_branch
        active_branch_str = str(
            active_branch.value if hasattr(active_branch, "value") else active_branch
        )

        wording_variant: QuestionWordingVariant | None = None
        if not is_ui_control:
            wording_obj = self._wordings_by_id.get(curr_id)
            if not wording_obj:
                raise InvalidSessionStateError(
                    f"No wording variants found for question {curr_id!r}"
                )
            wording_variant = next(
                (v for v in wording_obj.variants if v.branch == active_branch),
                wording_obj.variants[0],
            )

        option_set_obj: OptionSet | None = None
        options: list[OptionDefinition] | None = None
        if option_set_id and option_set_id in self._option_sets_by_id:
            option_set_obj = self._option_sets_by_id[option_set_id]
            raw_options = option_set_obj.options
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

        existing_answer: str | list[str] | None = None
        stale_reconfirmation = False
        record = self.state.session_state.answers.get(curr_id)
        if record:
            if record.validity_state == AnswerValidityState.ACTIVE:
                existing_answer = record.value
                stale_reconfirmation = False
            elif record.validity_state == AnswerValidityState.STALE_REQUIRES_RECONFIRMATION:
                existing_answer = record.value
                stale_reconfirmation = True

        return StepPrompt(
            step_id=curr_id,
            is_ui_control=is_ui_control,
            question_definition=q_def,
            ui_control_definition=ui_def,
            content_key=content_key,
            wording_variant=wording_variant,
            option_set=option_set_obj,
            options=options,
            existing_answer=existing_answer,
            active_branch=active_branch,
            stale_reconfirmation=stale_reconfirmation,
            multi_select_contract=multi_select_contract,
        )

    def process_answer(self, answer: Any) -> SessionStepResult:
        """Validate and record answer, resolve next step, check stale completion, and return result."""
        if self.state.status == SessionStatus.COMPLETED:
            raise InvalidSessionStateError("Cannot process answer for a completed session")

        curr_id = self.state.current_step_id
        if not curr_id:
            raise InvalidSessionStateError("Current step ID is not set")

        if curr_id not in self._questions_by_id and curr_id not in self._ui_controls_by_id:
            raise InvalidAnswerError(f"Unknown current step ID: {curr_id!r}")

        self.engine.record_answer(self.state.session_state, curr_id, answer)

        next_step = self.engine.resolve_next_step(self.state.session_state, curr_id)

        # Lookup exact matched FlowRule for target_closure_effect
        matched_rule = None
        ans_record = self.state.session_state.answers.get(curr_id)
        if ans_record:
            if isinstance(ans_record.value, str):
                matched_rule = self._rules_by_source_and_value.get((curr_id, ans_record.value))
            if not matched_rule:
                matched_rule = self._rules_by_source_any.get(curr_id)

        target_closure_effect: TargetClosureEffect | None = (
            matched_rule.target_closure_effect if matched_rule else None
        )

        if next_step == "module_complete":
            # Check stale answer protection before completing session
            for q_id, rec in self.state.session_state.answers.items():
                if rec.validity_state == AnswerValidityState.STALE_REQUIRES_RECONFIRMATION:
                    raise InvalidSessionStateError(
                        f"Cannot complete session with stale answer for question {q_id!r}"
                    )

            self.state.status = SessionStatus.COMPLETED
            self.state.current_step_id = None
            self.state.terminal_target = "module_complete"
            summary_lines = self.engine.generate_summary(self.state.session_state)

            return SessionStepResult(
                answered_step_id=curr_id,
                next_step_id=None,
                terminal_target="module_complete",
                status=SessionStatus.COMPLETED,
                target_closure_effect=target_closure_effect,
                summary_lines=summary_lines,
            )

        else:
            self.state.current_step_id = next_step
            return SessionStepResult(
                answered_step_id=curr_id,
                next_step_id=next_step,
                terminal_target=None,
                status=SessionStatus.IN_PROGRESS,
                target_closure_effect=target_closure_effect,
                summary_lines=[],
            )

    def get_result(self) -> DailyRoutinesSessionResult:
        """Return structured session result summary for both in-progress and completed sessions."""
        active_answers = {
            q_id: rec
            for q_id, rec in self.state.session_state.answers.items()
            if rec.validity_state == AnswerValidityState.ACTIVE
        }
        summary_lines = (
            self.engine.generate_summary(self.state.session_state)
            if self.state.status == SessionStatus.COMPLETED
            else []
        )

        return DailyRoutinesSessionResult(
            status=self.state.status,
            runtime_state=self.state,
            active_answers=active_answers,
            summary_lines=summary_lines,
            completed=self.state.status == SessionStatus.COMPLETED,
            terminal_target=self.state.terminal_target,
        )
