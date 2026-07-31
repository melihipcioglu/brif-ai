"""Runtime execution data models for BRIF.AI Daily Routines v0."""

from __future__ import annotations

from pydantic import Field, model_validator

from brif_ai.conversation.daily_routines.enums import (
    SessionStatus,
    TargetClosureEffect,
    WordingBranch,
)
from brif_ai.conversation.daily_routines.models import (
    AnswerRecord,
    DailyRoutinesQuestionDefinition,
    MultiSelectContract,
    OptionDefinition,
    OptionSet,
    QuestionWordingVariant,
    SessionState,
    UIStateControlDefinition,
)
from brif_ai.core.models.common import ContractModel, NonEmptyString, ObjectId


class DailyRoutinesRuntimeState(ContractModel):
    session_state: SessionState = Field(default_factory=SessionState)
    current_step_id: ObjectId | None = "q_daily_routines_functional_space_day_pattern_status"
    status: SessionStatus = SessionStatus.IN_PROGRESS
    terminal_target: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_state_invariants(self) -> DailyRoutinesRuntimeState:
        if self.status == SessionStatus.IN_PROGRESS:
            if not self.current_step_id:
                raise ValueError("IN_PROGRESS runtime state requires a non-null current_step_id")
            if self.terminal_target is not None:
                raise ValueError("IN_PROGRESS runtime state must have null terminal_target")
        elif self.status == SessionStatus.COMPLETED:
            if self.current_step_id is not None:
                raise ValueError("COMPLETED runtime state must have null current_step_id")
            if self.terminal_target != "module_complete":
                raise ValueError(
                    "COMPLETED runtime state must have terminal_target == 'module_complete'"
                )
        return self


class StepPrompt(ContractModel):
    step_id: ObjectId
    is_ui_control: bool
    question_definition: DailyRoutinesQuestionDefinition | None = None
    ui_control_definition: UIStateControlDefinition | None = None
    content_key: NonEmptyString
    wording_variant: QuestionWordingVariant | None = None
    option_set: OptionSet | None = None
    options: list[OptionDefinition] | None = None
    existing_answer: str | list[str] | None = None
    active_branch: WordingBranch
    stale_reconfirmation: bool = False
    multi_select_contract: MultiSelectContract | None = None


class SessionStepResult(ContractModel):
    answered_step_id: ObjectId
    next_step_id: ObjectId | None
    terminal_target: NonEmptyString | None
    status: SessionStatus
    target_closure_effect: TargetClosureEffect
    summary_lines: list[NonEmptyString] = Field(default_factory=list)


class DailyRoutinesSessionResult(ContractModel):
    status: SessionStatus
    runtime_state: DailyRoutinesRuntimeState
    active_answers: dict[ObjectId, AnswerRecord]
    summary_lines: list[NonEmptyString]
    completed: bool
    terminal_target: NonEmptyString | None
