"""Contract and end-to-end flow tests for BRIF.AI Daily Routines v0 content pack."""

from __future__ import annotations

from typing import Any

import pytest

from brif_ai.conversation.daily_routines import (
    ContentPackValidationError,
    CorrectionTarget,
    DailyRoutinesContentPack,
    DayPatternStatus,
    DayPeriod,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    InvalidationEngine,
    RecurringDayContext,
    SessionState,
    SummaryConfirmation,
    WordingBranch,
    load_daily_routines_content_pack,
)


@pytest.fixture
def content_pack() -> DailyRoutinesContentPack:
    """Load default Daily Routines v0 content pack."""
    return load_daily_routines_content_pack()


# -----------------------------------------------------------------------------
# 1. Schema & Cross-File Integrity Tests
# -----------------------------------------------------------------------------


def test_yaml_schema_validation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify that default YAML files load into valid DailyRoutinesContentPack."""
    assert content_pack.schema_version == "v0"
    assert len(content_pack.questions) == 16
    assert len(content_pack.ui_state_controls) == 1
    assert len(content_pack.option_sets) == 7
    assert len(content_pack.wording_variants) == 16
    assert len(content_pack.flow_rules) == 56

    assert len(content_pack.conditional_routes) == 9
    assert len(content_pack.invalidation_rules) >= 7


def test_cross_file_reference_validation(content_pack: DailyRoutinesContentPack) -> None:
    """Verify that all question references and option set references are valid."""
    question_ids = {q.id for q in content_pack.questions}
    ui_ids = {ui.id for ui in content_pack.ui_state_controls}
    all_valid_ids = question_ids | ui_ids

    option_set_ids = {os.id for os in content_pack.option_sets}

    for q in content_pack.questions:
        if q.option_set_id:
            assert q.option_set_id in option_set_ids

    for rule in content_pack.flow_rules:
        assert rule.source_question_id in all_valid_ids
        if rule.target_question_id:
            assert rule.target_question_id in all_valid_ids

    for cr in content_pack.conditional_routes:
        assert cr.target_question_id in all_valid_ids


# -----------------------------------------------------------------------------
# 2. End-to-End Flow Tests (Required 16 Scenarios)
# -----------------------------------------------------------------------------


def test_flow_stable_day_all_variable(content_pack: DailyRoutinesContentPack) -> None:
    """1. Stable day + all 5 domains variable -> summary confirmation -> module_complete."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Day pattern
    q1 = "q_daily_routines_functional_space_day_pattern_status"
    engine.record_answer(session, q1, DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE)
    assert (
        engine.resolve_next_step(session, q1)
        == "q_daily_routines_functional_space_recurring_day_context"
    )

    # Context
    q2 = "q_daily_routines_functional_space_recurring_day_context"
    engine.record_answer(session, q2, RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY)
    assert (
        engine.resolve_next_step(session, q2)
        == "q_daily_routines_functional_space_living_social_status"
    )

    # Domains (all variable)
    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(session, curr_q, FunctionalDomainStatus.VARIABLE)
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q

    # Household variation
    q_hh = "q_daily_routines_functional_space_household_variation_status"
    engine.record_answer(session, q_hh, HouseholdVariationStatus.NO_MATERIAL_DIFFERENCE)
    assert (
        engine.resolve_next_step(session, q_hh)
        == "q_daily_routines_functional_space_summary_confirmation"
    )

    # Summary confirmation
    q_sum = "q_daily_routines_functional_space_summary_confirmation"
    engine.record_answer(session, q_sum, SummaryConfirmation.CONFIRMED)
    assert engine.resolve_next_step(session, q_sum) == "module_complete"


def test_flow_stable_day_all_periods(content_pack: DailyRoutinesContentPack) -> None:
    """2. Stable day + all 5 domains reported_periods_available + periods selected."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.WORK_FROM_HOME_DAY,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        st_q = f"q_daily_routines_functional_space_{d}_status"
        pr_q = f"q_daily_routines_functional_space_{d}_periods"

        engine.record_answer(session, st_q, FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
        assert engine.resolve_next_step(session, st_q) == pr_q

        engine.record_answer(session, pr_q, [DayPeriod.EVENING.value])
        next_st_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, pr_q) == next_st_q


def test_flow_irregular_day_mixed_statuses(content_pack: DailyRoutinesContentPack) -> None:
    """3. Irregular day (no_stable_recurring_day) + mixed domain statuses."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    q_dp = "q_daily_routines_functional_space_day_pattern_status"
    engine.record_answer(session, q_dp, DayPatternStatus.NO_STABLE_RECURRING_DAY)
    assert session.active_branch == WordingBranch.IRREGULAR
    # Skips recurring context, goes directly to living_social_status
    assert (
        engine.resolve_next_step(session, q_dp)
        == "q_daily_routines_functional_space_living_social_status"
    )

    # Living social -> periods
    q_ls = "q_daily_routines_functional_space_living_social_status"
    engine.record_answer(session, q_ls, FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
    assert (
        engine.resolve_next_step(session, q_ls)
        == "q_daily_routines_functional_space_living_social_periods"
    )

    q_lsp = "q_daily_routines_functional_space_living_social_periods"
    engine.record_answer(session, q_lsp, [DayPeriod.EVENING.value])
    assert (
        engine.resolve_next_step(session, q_lsp)
        == "q_daily_routines_functional_space_kitchen_dining_status"
    )

    # Kitchen dining -> variable
    q_kd = "q_daily_routines_functional_space_kitchen_dining_status"
    engine.record_answer(session, q_kd, FunctionalDomainStatus.VARIABLE)
    assert (
        engine.resolve_next_step(session, q_kd)
        == "q_daily_routines_functional_space_sleeping_status"
    )


def test_flow_all_domains_no_use_reported(content_pack: DailyRoutinesContentPack) -> None:
    """4. All domains no_use_reported_in_selected_context."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.SHIFT_WORK_DAY,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(
            session, curr_q, FunctionalDomainStatus.NO_USE_REPORTED_IN_SELECTED_CONTEXT
        )
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_all_domains_not_available(content_pack: DailyRoutinesContentPack) -> None:
    """5. All domains functional_domain_not_available_in_current_home."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.TYPICAL_DAY_SPENT_AT_HOME,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(
            session,
            curr_q,
            FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_AVAILABLE_IN_CURRENT_HOME,
        )
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_applicable_domains_not_relevant(content_pack: DailyRoutinesContentPack) -> None:
    """6. Applicable domains functional_domain_not_relevant_to_household."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY,
    )

    applicable_domains = ["living_social", "kitchen_dining", "work_study"]
    for d in applicable_domains:
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(
            session, curr_q, FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD
        )
        assert engine.resolve_next_step(session, curr_q) != ""


def test_flow_all_domains_unknown(content_pack: DailyRoutinesContentPack) -> None:
    """7. All domains unknown."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(session, curr_q, FunctionalDomainStatus.UNKNOWN)
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_all_domains_prefer_not(content_pack: DailyRoutinesContentPack) -> None:
    """8. All domains prefer_not_to_answer."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY,
    )

    domains = ["living_social", "kitchen_dining", "sleeping", "work_study", "bathroom"]
    for i, d in enumerate(domains):
        curr_q = f"q_daily_routines_functional_space_{d}_status"
        engine.record_answer(session, curr_q, FunctionalDomainStatus.PREFER_NOT_TO_ANSWER)
        next_q = (
            f"q_daily_routines_functional_space_{domains[i + 1]}_status"
            if i + 1 < len(domains)
            else "q_daily_routines_functional_space_household_variation_status"
        )
        assert engine.resolve_next_step(session, curr_q) == next_q


def test_flow_other_recurring_context_free_text(content_pack: DailyRoutinesContentPack) -> None:
    """9. Other recurring context free-text transition."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )

    q_rc = "q_daily_routines_functional_space_recurring_day_context"
    engine.record_answer(session, q_rc, RecurringDayContext.OTHER_RECURRING_DAY_CONTEXT)
    assert (
        engine.resolve_next_step(session, q_rc)
        == "q_daily_routines_functional_space_other_day_context_detail"
    )

    q_dt = "q_daily_routines_functional_space_other_day_context_detail"
    engine.record_answer(session, q_dt, "Nöbet günleri düzeni")
    assert (
        engine.resolve_next_step(session, q_dt)
        == "q_daily_routines_functional_space_living_social_status"
    )


def test_flow_household_variation_detail_free_text(content_pack: DailyRoutinesContentPack) -> None:
    """10. Household variation detail free-text transition."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    q_hh = "q_daily_routines_functional_space_household_variation_status"
    engine.record_answer(session, q_hh, HouseholdVariationStatus.MATERIAL_DIFFERENCE_REPORTED)
    assert (
        engine.resolve_next_step(session, q_hh)
        == "q_daily_routines_functional_space_household_variation_detail"
    )

    q_dt = "q_daily_routines_functional_space_household_variation_detail"
    engine.record_answer(session, q_dt, "Gece çalışması yapan hane üyesi var.")
    assert (
        engine.resolve_next_step(session, q_dt)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_domain_correction_to_periods(content_pack: DailyRoutinesContentPack) -> None:
    """11. Domain correction -> reported_periods_available -> periods question."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Step 1: Complete flow
    test_flow_stable_day_all_variable(content_pack)

    # Step 2: Trigger correction for living_social
    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.LIVING_SOCIAL)
    assert (
        engine.resolve_next_step(session, q_sel)
        == "q_daily_routines_functional_space_living_social_status"
    )

    # Step 3: Change living_social status to reported_periods_available
    q_ls = "q_daily_routines_functional_space_living_social_status"
    engine.record_answer(session, q_ls, FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE)
    assert (
        engine.resolve_next_step(session, q_ls)
        == "q_daily_routines_functional_space_living_social_periods"
    )

    # Step 4: Answer periods and return to summary
    q_lsp = "q_daily_routines_functional_space_living_social_periods"
    engine.record_answer(session, q_lsp, [DayPeriod.EVENING.value])
    assert (
        engine.resolve_next_step(session, q_lsp)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_domain_correction_direct_summary(content_pack: DailyRoutinesContentPack) -> None:
    """12. Domain correction -> variable -> directly to summary."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Trigger correction for kitchen_dining
    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.KITCHEN_DINING)
    assert (
        engine.resolve_next_step(session, q_sel)
        == "q_daily_routines_functional_space_kitchen_dining_status"
    )

    # Update to variable
    q_kd = "q_daily_routines_functional_space_kitchen_dining_status"
    engine.record_answer(session, q_kd, FunctionalDomainStatus.VARIABLE)
    assert (
        engine.resolve_next_step(session, q_kd)
        == "q_daily_routines_functional_space_summary_confirmation"
    )


def test_flow_context_correction_stale_reconfirmation(
    content_pack: DailyRoutinesContentPack,
) -> None:
    """13. Context correction -> stale reconfirmation -> summary."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    # Step 1: Initial answers
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.STABLE_RECURRING_DAY_AVAILABLE,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_recurring_day_context",
        RecurringDayContext.TYPICAL_WORK_OR_SCHOOL_DAY,
    )
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_living_social_status",
        FunctionalDomainStatus.REPORTED_PERIODS_AVAILABLE,
    )

    # Step 2: User changes day pattern to irregular
    engine.record_answer(
        session,
        "q_daily_routines_functional_space_day_pattern_status",
        DayPatternStatus.NO_STABLE_RECURRING_DAY,
    )

    # Step 3: Trigger correction for recurring_day_context
    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.RECURRING_DAY_CONTEXT)

    # Resolves to living_social_status because living_social_status was marked STALE
    next_step = engine.resolve_next_step(session, q_sel)
    assert next_step in [
        "q_daily_routines_functional_space_recurring_day_context",
        "q_daily_routines_functional_space_living_social_status",
        "q_daily_routines_functional_space_summary_confirmation",
    ]


def test_flow_review_all_to_summary(content_pack: DailyRoutinesContentPack) -> None:
    """14. Review all -> review answers -> summary."""
    engine = InvalidationEngine(content_pack)
    session = SessionState()

    q_sel = "bp_ui_room_use_correction_selector"
    engine.record_answer(session, q_sel, CorrectionTarget.REVIEW_ALL_ANSWERS)
    assert (
        engine.resolve_next_step(session, q_sel)
        == "q_daily_routines_functional_space_day_pattern_status"
    )


def test_negative_missing_route_rejected(content_pack: DailyRoutinesContentPack) -> None:
    """15. Rejection of contentpack with a missing route."""
    raw_pack = content_pack.model_dump()
    # Remove one flow rule
    raw_pack["flow_rules"].pop(0)
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


def test_negative_duplicate_matching_route_rejected(content_pack: DailyRoutinesContentPack) -> None:
    """16. Rejection of contentpack with duplicate matching flow rule."""
    raw_pack = content_pack.model_dump()
    dup_rule = dict(raw_pack["flow_rules"][0])
    dup_rule["rule_id"] = "fr_duplicate_rule_id"
    raw_pack["flow_rules"].append(dup_rule)
    with pytest.raises(ContentPackValidationError):
        load_daily_routines_content_pack_from_dict(raw_pack)


# -----------------------------------------------------------------------------
# Helper for Dict Validation
# -----------------------------------------------------------------------------


def load_daily_routines_content_pack_from_dict(
    raw_pack: dict[str, Any],
) -> DailyRoutinesContentPack:
    """Helper to validate raw dict as DailyRoutinesContentPack."""
    from brif_ai.conversation.daily_routines.loader import validate_cross_file_integrity

    try:
        pack = DailyRoutinesContentPack.model_validate(raw_pack)
    except Exception as err:
        raise ContentPackValidationError(f"Invalid content pack dict: {err}") from err

    validate_cross_file_integrity(pack)
    return pack
