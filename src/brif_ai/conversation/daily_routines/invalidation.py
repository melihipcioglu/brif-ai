"""Invalidation rules engine, flow resolver, and summary generator for BRIF.AI Daily Routines v0."""

from __future__ import annotations

from typing import Any

from brif_ai.conversation.daily_routines.enums import (
    AnswerValidityState,
    CorrectionReturnPolicy,
    CorrectionTarget,
    DayPatternStatus,
    DayPeriod,
    FlowResolutionError,
    FunctionalDomain,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidAnswerError,
    RecurringDayContext,
    RouteMatchType,
    WordingBranch,
)
from brif_ai.conversation.daily_routines.models import (
    AnswerRecord,
    DailyRoutinesContentPack,
    SessionState,
    SummaryTemplate,
)
from brif_ai.conversation.models.common import AnswerType
from brif_ai.core.models.common import ObjectId


class InvalidationEngine:
    """Manages answer state transitions, rules, flow resolution, and summary generation."""

    def __init__(self, content_pack: DailyRoutinesContentPack) -> None:
        self.pack = content_pack
        self.questions_by_id = {q.id: q for q in content_pack.questions}
        self.ui_controls_by_id = {ui.id: ui for ui in content_pack.ui_state_controls}
        self.option_sets_by_id = {
            os.id: {opt.value for opt in os.options} for os in content_pack.option_sets
        }

    def validate_answer(self, session: SessionState, question_id: str, value: Any) -> None:
        """Validate answer against schema, option sets, answer types, and applicability rules."""
        if question_id not in self.questions_by_id and question_id not in self.ui_controls_by_id:
            raise InvalidAnswerError(f"Unknown question or UI control id: {question_id!r}")

        # 1. UI Control Validation
        if question_id in self.ui_controls_by_id:
            ui = self.ui_controls_by_id[question_id]
            val_str = str(value.value if hasattr(value, "value") else value)
            allowed_opts = self.option_sets_by_id.get(ui.option_set_id, set())
            if val_str not in allowed_opts:
                raise InvalidAnswerError(
                    f"Value {val_str!r} not allowed for UI control {question_id!r}"
                )

            # Specific check for recurring_day_context in IRREGULAR branch
            if (
                val_str == CorrectionTarget.RECURRING_DAY_CONTEXT.value
                and session.active_branch == WordingBranch.IRREGULAR
            ):
                raise InvalidAnswerError(
                    "recurring_day_context correction is only available in STABLE branch"
                )
            return

        # 2. Question Definition Validation
        q_def = self.questions_by_id[question_id]
        if q_def.answer_type == AnswerType.SINGLE_CHOICE:
            if isinstance(value, list):
                raise InvalidAnswerError(
                    f"SINGLE_CHOICE question {question_id!r} expects string value, got list"
                )
            val_str = str(value.value if hasattr(value, "value") else value)
            if not q_def.option_set_id or q_def.option_set_id not in self.option_sets_by_id:
                raise InvalidAnswerError(f"Missing option set for question {question_id!r}")
            allowed_opts = self.option_sets_by_id[q_def.option_set_id]
            if val_str not in allowed_opts:
                raise InvalidAnswerError(
                    f"Value {val_str!r} not found in OptionSet for question {question_id!r}"
                )

            # Domain Applicability Rule Validation
            not_relevant = FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
            if val_str == not_relevant:
                for domain in [FunctionalDomain.SLEEPING, FunctionalDomain.BATHROOM]:
                    if question_id.endswith(f"_{domain.value}_status"):
                        msg = (
                            "functional_domain_not_relevant_to_household is disallowed "
                            f"for domain {domain.value!r}"
                        )
                        raise InvalidAnswerError(msg)

        elif q_def.answer_type == AnswerType.MULTIPLE_CHOICE:
            if not isinstance(value, list):
                raise InvalidAnswerError(f"MULTIPLE_CHOICE question {question_id!r} expects a list")
            if not (1 <= len(value) <= 4):
                msg = f"MULTIPLE_CHOICE question {question_id!r} requires 1 to 4 items"
                raise InvalidAnswerError(msg)

            str_items = [str(v.value if hasattr(v, "value") else v) for v in value]
            if len(set(str_items)) != len(str_items):
                raise InvalidAnswerError(
                    f"MULTIPLE_CHOICE question {question_id!r} contains duplicate items"
                )
            valid_periods = {p.value for p in DayPeriod}
            for item in str_items:
                if item not in valid_periods:
                    raise InvalidAnswerError(
                        f"Invalid period value {item!r} for question {question_id!r}"
                    )

        elif q_def.answer_type == AnswerType.FREE_TEXT:
            if not isinstance(value, str):
                raise InvalidAnswerError(f"FREE_TEXT question {question_id!r} expects string value")
            if not value.strip():
                raise InvalidAnswerError(
                    f"FREE_TEXT question {question_id!r} cannot be empty or whitespace"
                )

    def record_answer(
        self, session: SessionState, question_id: ObjectId, value: Any
    ) -> SessionState:
        """Record or update an answer, applying strict validation and invalidation rules."""
        self.validate_answer(session, question_id, value)

        val_str: str | list[str]
        if isinstance(value, list):
            val_str = [str(v.value if hasattr(v, "value") else v) for v in value]
        else:
            val_str = str(value.value if hasattr(value, "value") else value)

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

    def resolve_next_step(self, session: SessionState, current_question_id: str) -> str:
        """Deterministically resolve next question ID or terminal module target (fail-closed)."""
        if (
            current_question_id not in self.questions_by_id
            and current_question_id not in self.ui_controls_by_id
        ):
            raise FlowResolutionError(f"Unknown current_question_id: {current_question_id!r}")

        # 1. UI Correction Selector Step
        if current_question_id == "bp_ui_room_use_correction_selector":
            ans = session.answers.get("bp_ui_room_use_correction_selector")
            if not ans or ans.validity_state != AnswerValidityState.ACTIVE:
                raise FlowResolutionError("No active answer for UI correction selector")
            sel_val = str(ans.value)
            for cr in self.pack.conditional_routes:
                if cr.selector_value.value == sel_val:
                    session.correction_target = cr.selector_value
                    target_id = cr.target_question_id
                    if cr.return_policy == CorrectionReturnPolicy.RECONFIRM_STALE_THEN_SUMMARY:
                        stale_q = self._find_first_stale_question(session)
                        if stale_q:
                            return stale_q
                    return target_id
            raise FlowResolutionError(f"No conditional route found for selector value {sel_val!r}")

        # 2. Correction Mode Resolution
        if session.correction_target is not None:
            cond_route = next(
                (
                    cr
                    for cr in self.pack.conditional_routes
                    if cr.selector_value == session.correction_target
                ),
                None,
            )
            if cond_route:
                if cond_route.return_policy == CorrectionReturnPolicy.RESOLVE_BY_FLOW:
                    ans = session.answers.get(current_question_id)
                    if ans and ans.validity_state == AnswerValidityState.ACTIVE:
                        if (
                            str(ans.value)
                            == FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE.value
                        ):
                            domain = self._extract_domain_from_question_id(current_question_id)
                            if domain:
                                return f"q_daily_routines_functional_space_{domain}_periods"
                        elif (
                            str(ans.value)
                            == HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED.value
                        ):
                            return "q_daily_routines_functional_space_household_variation_detail"

                    session.correction_target = None
                    return "q_daily_routines_functional_space_summary_confirmation"

                elif (
                    cond_route.return_policy == CorrectionReturnPolicy.RECONFIRM_STALE_THEN_SUMMARY
                ):
                    stale_q = self._find_first_stale_question(session)
                    if stale_q:
                        return stale_q
                    session.correction_target = None
                    return "q_daily_routines_functional_space_summary_confirmation"

                elif cond_route.return_policy == CorrectionReturnPolicy.REVIEW_ALL_THEN_SUMMARY:
                    if (
                        current_question_id
                        == "q_daily_routines_functional_space_summary_confirmation"
                    ):
                        session.correction_target = None

        # 3. Standard Flow Resolution via FlowRules
        ans = session.answers.get(current_question_id)
        if not ans or ans.validity_state != AnswerValidityState.ACTIVE:
            raise FlowResolutionError(f"No active answer for question {current_question_id!r}")

        rules_for_q = [
            r for r in self.pack.flow_rules if r.source_question_id == current_question_id
        ]
        matching_rules = []
        for rule in rules_for_q:
            if rule.match_type == RouteMatchType.EXACT_OPTION:
                if str(ans.value) == rule.expected_value:
                    matching_rules.append(rule)

            elif rule.match_type == RouteMatchType.ANY_VALID_MULTISELECT:
                if isinstance(ans.value, list) and 1 <= len(ans.value) <= 4:
                    matching_rules.append(rule)

            elif (
                rule.match_type == RouteMatchType.NON_EMPTY_TEXT
                and isinstance(ans.value, str)
                and len(ans.value.strip()) > 0
            ):
                matching_rules.append(rule)

        if not matching_rules:
            raise FlowResolutionError(
                f"No matching flow rule found for question {current_question_id!r}"
            )
        if len(matching_rules) > 1:
            cnt = len(matching_rules)
            raise FlowResolutionError(
                f"Multiple matching flow rules ({cnt}) for question {current_question_id!r}"
            )

        matched_rule = matching_rules[0]
        return matched_rule.target_question_id or matched_rule.target_module or ""

    def _find_first_stale_question(self, session: SessionState) -> str | None:
        """Find the first question in canonical flow order marked STALE_REQUIRES_RECONFIRMATION."""
        canonical_order = [
            "q_daily_routines_functional_space_day_pattern_status",
            "q_daily_routines_functional_space_recurring_day_context",
            "q_daily_routines_functional_space_other_day_context_detail",
            "q_daily_routines_functional_space_living_social_status",
            "q_daily_routines_functional_space_living_social_periods",
            "q_daily_routines_functional_space_kitchen_dining_status",
            "q_daily_routines_functional_space_kitchen_dining_periods",
            "q_daily_routines_functional_space_sleeping_status",
            "q_daily_routines_functional_space_sleeping_periods",
            "q_daily_routines_functional_space_work_study_status",
            "q_daily_routines_functional_space_work_study_periods",
            "q_daily_routines_functional_space_bathroom_status",
            "q_daily_routines_functional_space_bathroom_periods",
            "q_daily_routines_functional_space_household_variation_status",
            "q_daily_routines_functional_space_household_variation_detail",
        ]
        for q_id in canonical_order:
            rec = session.answers.get(q_id)
            if rec and rec.validity_state == AnswerValidityState.STALE_REQUIRES_RECONFIRMATION:
                return q_id
        return None

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
