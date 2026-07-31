"""Invalidation rules engine and summary generator for BRIF.AI Daily Routines v0."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from brif_ai.conversation.daily_routines.enums import (
    AnswerValidityState,
    DayPatternStatus,

    DayPeriod,

    FunctionalDomain,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    RecurringDayContext,

    WordingBranch,
)
from brif_ai.conversation.daily_routines.loader import DailyRoutinesContentPack
from brif_ai.conversation.daily_routines.models import AnswerRecord
from brif_ai.core.models.common import ContractModel, ObjectId


class SessionState(ContractModel):
    answers: dict[ObjectId, AnswerRecord] = Field(default_factory=dict)
    active_branch: WordingBranch = WordingBranch.STABLE


class InvalidationEngine:
    """Manages answer state transitions, invalidation rules, and summary generation."""

    def __init__(self, content_pack: DailyRoutinesContentPack) -> None:
        self.pack = content_pack

    def record_answer(
        self, session: SessionState, question_id: ObjectId, value: Any
    ) -> SessionState:
        """Record or update an answer, applying invalidation rules to downstream data."""
        # Convert value if needed
        val_str = (
            [str(v) for v in value]
            if isinstance(value, list)
            else str(value.value if hasattr(value, "value") else value)
        )

        old_record = session.answers.get(question_id)
        old_value = old_record.value if old_record else None

        new_record = AnswerRecord(
            question_id=question_id, value=val_str, validity_state=AnswerValidityState.ACTIVE
        )
        session.answers[question_id] = new_record

        # Apply specific invalidation rules based on what changed
        if question_id == "q_daily_routines_functional_space_day_pattern_status":
            self._handle_day_pattern_change(session, old_value, val_str)

        elif question_id == "q_daily_routines_functional_space_recurring_day_context":
            self._handle_recurring_context_change(session, old_value, val_str)

        elif question_id == "q_daily_routines_functional_space_household_variation_status":
            self._handle_household_variation_change(session, old_value, val_str)

        elif question_id.endswith("_status") and "functional_space" in question_id:
            domain = self._extract_domain_from_question_id(question_id)
            if domain:
                self._handle_domain_status_change(session, domain, old_value, val_str)


        return session

    def _handle_day_pattern_change(
        self, session: SessionState, old_value: Any, new_value: Any
    ) -> None:
        if old_value == new_value:
            return

        if new_value == DayPatternStatus.NO_STABLE_RECURRING_DAY.value:
            session.active_branch = WordingBranch.IRREGULAR
            # Invalidate recurring context answers
            self._set_state(
                session,
                "q_daily_routines_functional_space_recurring_day_context",
                AnswerValidityState.INACTIVE_BY_BRANCH,
            )
            self._set_state(
                session,
                "q_daily_routines_functional_space_other_day_context_detail",
                AnswerValidityState.INACTIVE_BY_BRANCH,
            )

            # Mark downstream space & household answers as STALE_REQUIRES_RECONFIRMATION
            self._mark_downstream_stale(session)

        elif new_value == DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE.value:
            session.active_branch = WordingBranch.STABLE

            # If moving from irregular/unknown to stable, mark downstream space answers as STALE_REQUIRES_RECONFIRMATION
            if old_value in (
                DayPatternStatus.NO_STABLE_RECURRING_DAY.value,
                DayPatternStatus.UNKNOWN.value,
                DayPatternStatus.PREFER_NOT_TO_ANSWER.value,
            ):
                self._mark_downstream_stale(session)

        elif new_value in (
            DayPatternStatus.UNKNOWN.value,
            DayPatternStatus.PREFER_NOT_TO_ANSWER.value,
        ):
            # Invalidate all downstream answers
            self._set_all_downstream_inactive(session)

    def _handle_recurring_context_change(
        self, session: SessionState, old_value: Any, new_value: Any
    ) -> None:
        if old_value == new_value:
            return

        if new_value != RecurringDayContext.OTHER_RECURRING_DAY_CONTEXT.value:
            self._set_state(
                session,
                "q_daily_routines_functional_space_other_day_context_detail",
                AnswerValidityState.INACTIVE_BY_BRANCH,
            )

        # Context shift requires reconfirming all domain status & household answers
        self._mark_downstream_stale(session)

    def _handle_domain_status_change(
        self, session: SessionState, domain: str, old_value: Any, new_value: Any
    ) -> None:
        if old_value == new_value:
            return

        periods_q_id = f"q_daily_routines_functional_space_{domain}_periods"

        if new_value == FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE.value:
            # Periods answer needs to be active/answered
            rec = session.answers.get(periods_q_id)
            if rec and rec.validity_state == AnswerValidityState.INACTIVE_BY_BRANCH:
                rec.validity_state = AnswerValidityState.STALE_REQUIRES_RECONFIRMATION
        else:
            # Non-reported status makes periods answer INACTIVE_BY_BRANCH
            self._set_state(session, periods_q_id, AnswerValidityState.INACTIVE_BY_BRANCH)

    def _handle_household_variation_change(
        self, session: SessionState, old_value: Any, new_value: Any
    ) -> None:
        if old_value == new_value:
            return

        detail_q_id = "q_daily_routines_functional_space_household_variation_detail"
        if new_value == HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED.value:
            rec = session.answers.get(detail_q_id)
            if rec and rec.validity_state == AnswerValidityState.INACTIVE_BY_BRANCH:
                rec.validity_state = AnswerValidityState.STALE_REQUIRES_RECONFIRMATION
        else:
            self._set_state(session, detail_q_id, AnswerValidityState.INACTIVE_BY_BRANCH)

    def _set_state(
        self, session: SessionState, question_id: str, state: AnswerValidityState
    ) -> None:
        rec = session.answers.get(question_id)
        if rec:
            rec.validity_state = state

    def _mark_downstream_stale(self, session: SessionState) -> None:
        domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
        for domain in domains:
            status_id = f"q_daily_routines_functional_space_{domain}_status"
            periods_id = f"q_daily_routines_functional_space_{domain}_periods"
            self._set_state_if_active(session, status_id, AnswerValidityState.STALE_REQUIRES_RECONFIRMATION)
            self._set_state_if_active(session, periods_id, AnswerValidityState.STALE_REQUIRES_RECONFIRMATION)

        self._set_state_if_active(
            session,
            "q_daily_routines_functional_space_household_variation_status",
            AnswerValidityState.STALE_REQUIRES_RECONFIRMATION,
        )
        self._set_state_if_active(
            session,
            "q_daily_routines_functional_space_household_variation_detail",
            AnswerValidityState.STALE_REQUIRES_RECONFIRMATION,
        )

    def _set_all_downstream_inactive(self, session: SessionState) -> None:
        for q_id in session.answers:
            if q_id != "q_daily_routines_functional_space_day_pattern_status":
                session.answers[q_id].validity_state = AnswerValidityState.INACTIVE_BY_BRANCH

    def _set_state_if_active(
        self, session: SessionState, question_id: str, state: AnswerValidityState
    ) -> None:
        rec = session.answers.get(question_id)
        if rec and rec.validity_state == AnswerValidityState.ACTIVE:
            rec.validity_state = state

    def _extract_domain_from_question_id(self, question_id: str) -> str | None:
        for d in ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]:
            if f"_{d}_" in question_id:
                return d
        return None

    def generate_summary(self, session: SessionState) -> list[str]:
        """Generate factual summary statements for ACTIVE answers in session."""
        templates = self.pack.summary_templates
        lines: list[str] = []

        # 1. Day Pattern
        dp_rec = session.answers.get("q_daily_routines_functional_space_day_pattern_status")
        if dp_rec and dp_rec.validity_state == AnswerValidityState.ACTIVE:
            dp_val = DayPatternStatus(dp_rec.value)
            if dp_val in templates.day_pattern:
                lines.append(templates.day_pattern[dp_val])

        # 2. Recurring Context
        if session.active_branch == WordingBranch.STABLE:
            rc_rec = session.answers.get(
                "q_daily_routines_functional_space_recurring_day_context"
            )
            if rc_rec and rc_rec.validity_state == AnswerValidityState.ACTIVE:
                rc_val = RecurringDayContext(rc_rec.value)
                if rc_val == RecurringDayContext.OTHER_RECURRING_DAY_CONTEXT:
                    dt_rec = session.answers.get(
                        "q_daily_routines_functional_space_other_day_context_detail"
                    )
                    detail_str = (
                        dt_rec.value
                        if dt_rec and dt_rec.validity_state == AnswerValidityState.ACTIVE
                        else ""
                    )
                    tmpl = templates.recurring_context[rc_val]
                    lines.append(tmpl.format(detail=detail_str))
                elif rc_val in templates.recurring_context:
                    lines.append(templates.recurring_context[rc_val])

        # 3. Domain Status & Periods
        branch_key = session.active_branch
        domain_templates = (
            templates.domain_status.get(branch_key)
            or templates.domain_status[WordingBranch.STABLE]
        )

        domains = [
            FunctionalDomain.LIVING_SOCIAL,
            FunctionalDomain.KITCHEN_DINING,
            FunctionalDomain.SLEEPING,
            FunctionalDomain.WORK_STUDY,
            FunctionalDomain.BATHROOM,
        ]

        for domain in domains:
            status_id = f"q_daily_routines_functional_space_{domain.value}_status"
            periods_id = f"q_daily_routines_functional_space_{domain.value}_periods"

            st_rec = session.answers.get(status_id)
            if not st_rec or st_rec.validity_state != AnswerValidityState.ACTIVE:
                continue

            st_val = FunctionalDomainStatus(st_rec.value)
            domain_name = templates.domain_names.get(domain, domain.value)

            if st_val == FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE:
                pr_rec = session.answers.get(periods_id)
                periods_text = ""
                if pr_rec and pr_rec.validity_state == AnswerValidityState.ACTIVE:
                    raw_periods = (
                        pr_rec.value if isinstance(pr_rec.value, list) else [pr_rec.value]
                    )
                    periods_text = self.format_canonical_periods(raw_periods, templates)

                tmpl = domain_templates.reported_periods_available
                lines.append(
                    tmpl.format(domain_name=domain_name, periods_text=periods_text)
                )

            elif st_val == FunctionalDomainStatus.VARIABLE:
                lines.append(domain_templates.variable.format(domain_name=domain_name))

            elif st_val == FunctionalDomainStatus.NO_USE_REPORTED_IN_SELECTED_CONTEXT:
                lines.append(
                    domain_templates.no_use_reported_in_selected_context.format(
                        domain_name=domain_name
                    )
                )

            elif (
                st_val
                == FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_AVAILABLE_IN_CURRENT_HOME
            ):
                lines.append(
                    domain_templates.functional_domain_not_available_in_current_home.format(
                        domain_name=domain_name
                    )
                )

            elif st_val == FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD:
                lines.append(
                    domain_templates.functional_domain_not_relevant_to_household.format(
                        domain_name=domain_name
                    )
                )

            elif st_val == FunctionalDomainStatus.UNKNOWN:
                lines.append(domain_templates.unknown.format(domain_name=domain_name))

            elif st_val == FunctionalDomainStatus.PREFER_NOT_TO_ANSWER:
                lines.append(
                    domain_templates.prefer_not_to_answer.format(domain_name=domain_name)
                )

        # 4. Household Variation
        hh_rec = session.answers.get(
            "q_daily_routines_functional_space_household_variation_status"
        )
        if hh_rec and hh_rec.validity_state == AnswerValidityState.ACTIVE:
            hh_val = HouseholdVariationStatus(hh_rec.value)
            if hh_val == HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED:
                dt_rec = session.answers.get(
                    "q_daily_routines_functional_space_household_variation_detail"
                )
                detail_str = (
                    dt_rec.value
                    if dt_rec and dt_rec.validity_state == AnswerValidityState.ACTIVE
                    else ""
                )
                tmpl = templates.household_variation[hh_val]
                lines.append(tmpl.format(detail=detail_str))
            elif hh_val in templates.household_variation:
                lines.append(templates.household_variation[hh_val])

        return lines

    def format_canonical_periods(
        self, periods: list[str], templates: SummaryTemplate
    ) -> str:
        """Sort period values in canonical chronological order and format multi-period Turkish text."""
        order_map = {
            DayPeriod.MORNING.value: 1,
            DayPeriod.MIDDAY_AFTERNOON.value: 2,
            DayPeriod.EVENING.value: 3,
            DayPeriod.NIGHT.value: 4,
        }

        # Filter and sort
        valid_periods = [p for p in periods if p in order_map]
        valid_periods.sort(key=lambda p: order_map[p])

        if not valid_periods:
            return ""

        label_map = templates.periods_label_map
        labels = [label_map.get(DayPeriod(p), p) for p in valid_periods]

        if len(labels) == 1:
            return f"**{labels[0]}**"
        elif len(labels) == 2:
            return f"**{labels[0]}** ve **{labels[1]}**"
        elif len(labels) == 3:
            return f"**{labels[0]}**, **{labels[1]}** ve **{labels[2]}**"
        else:
            joined = ", ".join(f"**{l}**" for l in labels[:-1])
            return f"{joined} ve **{labels[-1]}**"
