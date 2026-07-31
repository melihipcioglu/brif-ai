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
from brif_ai.conversation.daily_routines.models import (
    AnswerRecord,
    DailyRoutinesContentPack,
    SummaryTemplate,
)
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
        """Record or update an answer, applying invalidation rules from content pack."""
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

        if old_value != val_str:
            self._apply_yaml_invalidation_rules(session, question_id, val_str)
            self._apply_dynamic_domain_rules(session, question_id, val_str)

        return session

    def _apply_yaml_invalidation_rules(
        self, session: SessionState, question_id: str, new_value: Any
    ) -> None:
        for rule in self.pack.invalidation_rules:
            if rule.source_question_id != question_id:
                continue

            if rule.trigger_value is not None and rule.trigger_value != new_value:
                continue

            if rule.active_branch_effect is not None:
                session.active_branch = rule.active_branch_effect

            for target_id in rule.target_question_ids:
                rec = session.answers.get(target_id)
                if not rec:
                    continue

                if rule.new_validity_state == AnswerValidityState.INACTIVE_BY_BRANCH:
                    rec.validity_state = AnswerValidityState.INACTIVE_BY_BRANCH
                elif (
                    rule.new_validity_state == AnswerValidityState.STALE_REQUIRES_RECONFIRMATION
                    and rec.validity_state == AnswerValidityState.ACTIVE
                ):
                    rec.validity_state = AnswerValidityState.STALE_REQUIRES_RECONFIRMATION

    def _apply_dynamic_domain_rules(
        self, session: SessionState, question_id: str, new_value: Any
    ) -> None:
        if question_id == "q_daily_routines_functional_space_household_variation_status":
            detail_q_id = "q_daily_routines_functional_space_household_variation_detail"
            if new_value == HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED.value:
                rec = session.answers.get(detail_q_id)
                if rec and rec.validity_state == AnswerValidityState.INACTIVE_BY_BRANCH:
                    rec.validity_state = AnswerValidityState.STALE_REQUIRES_RECONFIRMATION
            else:
                rec = session.answers.get(detail_q_id)
                if rec:
                    rec.validity_state = AnswerValidityState.INACTIVE_BY_BRANCH

        elif question_id.endswith("_status") and "functional_space" in question_id:
            domain = self._extract_domain_from_question_id(question_id)
            if domain:
                periods_q_id = f"q_daily_routines_functional_space_{domain}_periods"
                if new_value == FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE.value:
                    rec = session.answers.get(periods_q_id)
                    if rec and rec.validity_state == AnswerValidityState.INACTIVE_BY_BRANCH:
                        rec.validity_state = AnswerValidityState.STALE_REQUIRES_RECONFIRMATION
                else:
                    rec = session.answers.get(periods_q_id)
                    if rec:
                        rec.validity_state = AnswerValidityState.INACTIVE_BY_BRANCH

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
            dp_val = DayPatternStatus(str(dp_rec.value))
            if dp_val in templates.day_pattern:
                lines.append(templates.day_pattern[dp_val])

        # 2. Recurring Context
        if session.active_branch == WordingBranch.STABLE:
            rc_rec = session.answers.get("q_daily_routines_functional_space_recurring_day_context")
            if rc_rec and rc_rec.validity_state == AnswerValidityState.ACTIVE:
                rc_val = RecurringDayContext(str(rc_rec.value))
                if rc_val == RecurringDayContext.OTHER_RECURRING_DAY_CONTEXT:
                    dt_rec = session.answers.get(
                        "q_daily_routines_functional_space_other_day_context_detail"
                    )
                    detail_str = (
                        str(dt_rec.value)
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
            templates.domain_status.get(branch_key) or templates.domain_status[WordingBranch.STABLE]
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

            st_val = FunctionalDomainStatus(str(st_rec.value))
            domain_name = templates.domain_names.get(domain, domain.value)

            if st_val == FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE:
                pr_rec = session.answers.get(periods_id)
                periods_text = ""
                if pr_rec and pr_rec.validity_state == AnswerValidityState.ACTIVE:
                    raw_periods = (
                        pr_rec.value if isinstance(pr_rec.value, list) else [str(pr_rec.value)]
                    )
                    periods_text = self.format_canonical_periods(raw_periods, templates)

                tmpl = domain_templates.reported_periods_available
                lines.append(tmpl.format(domain_name=domain_name, periods_text=periods_text))

            elif st_val == FunctionalDomainStatus.VARIABLE:
                lines.append(domain_templates.variable.format(domain_name=domain_name))

            elif st_val == FunctionalDomainStatus.NO_USE_REPORTED_IN_SELECTED_CONTEXT:
                lines.append(
                    domain_templates.no_use_reported_in_selected_context.format(
                        domain_name=domain_name
                    )
                )

            elif st_val == FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_AVAILABLE_IN_CURRENT_HOME:
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
                lines.append(domain_templates.prefer_not_to_answer.format(domain_name=domain_name))

        # 4. Household Variation
        hh_rec = session.answers.get("q_daily_routines_functional_space_household_variation_status")
        if hh_rec and hh_rec.validity_state == AnswerValidityState.ACTIVE:
            hh_val = HouseholdVariationStatus(str(hh_rec.value))
            if hh_val == HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED:
                dt_rec = session.answers.get(
                    "q_daily_routines_functional_space_household_variation_detail"
                )
                detail_str = (
                    str(dt_rec.value)
                    if dt_rec and dt_rec.validity_state == AnswerValidityState.ACTIVE
                    else ""
                )
                tmpl = templates.household_variation[hh_val]
                lines.append(tmpl.format(detail=detail_str))
            elif hh_val in templates.household_variation:
                lines.append(templates.household_variation[hh_val])

        return lines

    def format_canonical_periods(self, periods: list[str], templates: SummaryTemplate) -> str:
        """Sort period values in canonical chronological order and format multi-period text."""

        order_map = {
            DayPeriod.MORNING.value: 1,
            DayPeriod.MIDDAY_AFTERNOON.value: 2,
            DayPeriod.EVENING.value: 3,
            DayPeriod.NIGHT.value: 4,
        }

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
            joined = ", ".join(f"**{item}**" for item in labels[:-1])

            return f"{joined} ve **{labels[-1]}**"
