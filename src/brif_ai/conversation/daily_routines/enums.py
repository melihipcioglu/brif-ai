"""Enums and custom exception types for BRIF.AI Daily Routines v0 content pack contracts."""

from __future__ import annotations

import sys
from enum import Enum

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class InvalidAnswerError(ValueError):
    """Raised when an answer violates runtime validation rules."""


class FlowResolutionError(RuntimeError):
    """Raised when deterministic flow resolution fails."""


class InvalidSessionStateError(RuntimeError):
    """Raised when an operation is performed on a completed or invalid session state."""


class SessionStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class DayPatternStatus(StrEnum):
    STABLE_RECURRING_DAY_AVAILABLE = "stable_recurring_day_available"
    NO_STABLE_RECURRING_DAY = "no_stable_recurring_day"
    UNKNOWN = "unknown"
    PREFER_NOT_TO_ANSWER = "prefer_not_to_answer"


class RecurringDayContext(StrEnum):
    TYPICAL_WORK_OR_SCHOOL_DAY = "typical_work_or_school_day"
    WORK_FROM_HOME_DAY = "work_from_home_day"
    SHIFT_WORK_DAY = "shift_work_day"
    TYPICAL_DAY_SPENT_AT_HOME = "typical_day_spent_at_home"
    OTHER_RECURRING_DAY_CONTEXT = "other_recurring_day_context"


class FunctionalDomain(StrEnum):
    LIVING_SOCIAL = "living_social"
    KITCHEN_DINING = "kitchen_dining"
    SLEEPING = "sleeping"
    WORK_STUDY = "work_study"
    BATHROOM = "bathroom"


class FunctionalDomainStatus(StrEnum):
    REPORTED_PERIODS_AVAILABLE = "reported_periods_available"
    VARIABLE = "variable"
    NO_USE_REPORTED_IN_SELECTED_CONTEXT = "no_use_reported_in_selected_context"
    FUNCTIONAL_DOMAIN_NOT_AVAILABLE_IN_CURRENT_HOME = (
        "functional_domain_not_available_in_current_home"
    )
    FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD = "functional_domain_not_relevant_to_household"
    UNKNOWN = "unknown"
    PREFER_NOT_TO_ANSWER = "prefer_not_to_answer"


class DayPeriod(StrEnum):
    MORNING = "morning"
    MIDDAY_AFTERNOON = "midday_afternoon"
    EVENING = "evening"
    NIGHT = "night"


class HouseholdVariationStatus(StrEnum):
    NO_MATERIAL_DIFFERENCE = "no_material_difference"
    MATERIAL_DIFFERENCE_REPORTED = "material_difference_reported"
    UNKNOWN = "unknown"
    PREFER_NOT_TO_ANSWER = "prefer_not_to_answer"
    NOT_APPLICABLE_SINGLE_PERSON_HOUSEHOLD = "not_applicable_single_person_household"


class SummaryConfirmation(StrEnum):
    CONFIRMED = "confirmed"
    REJECTED_FOR_CORRECTION = "rejected_for_correction"


class CorrectionTarget(StrEnum):
    DAY_PATTERN = "day_pattern"
    RECURRING_DAY_CONTEXT = "recurring_day_context"
    LIVING_SOCIAL = "living_social"
    KITCHEN_DINING = "kitchen_dining"
    SLEEPING = "sleeping"
    WORK_STUDY = "work_study"
    BATHROOM = "bathroom"
    HOUSEHOLD_VARIATION = "household_variation"
    REVIEW_ALL_ANSWERS = "review_all_answers"


class AnswerValidityState(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE_BY_BRANCH = "INACTIVE_BY_BRANCH"
    STALE_REQUIRES_RECONFIRMATION = "STALE_REQUIRES_RECONFIRMATION"


class WordingBranch(StrEnum):
    STABLE = "STABLE"
    IRREGULAR = "IRREGULAR"


class TargetClosureEffect(StrEnum):
    REQUIRES_FOLLOW_UP = "REQUIRES_FOLLOW_UP"
    VALID_CLOSURE = "VALID_CLOSURE"
    VALID_BUT_LOW_INFORMATION = "VALID_BUT_LOW_INFORMATION"
    REQUIRES_CORRECTION = "REQUIRES_CORRECTION"
    TARGET_2_FULFILLED = "TARGET_2_FULFILLED"


class RouteMatchType(StrEnum):
    EXACT_OPTION = "EXACT_OPTION"
    ANY_VALID_MULTISELECT = "ANY_VALID_MULTISELECT"
    NON_EMPTY_TEXT = "NON_EMPTY_TEXT"
    QUESTION_COMPLETED = "QUESTION_COMPLETED"


class CorrectionReturnPolicy(StrEnum):
    RESOLVE_BY_FLOW = "RESOLVE_BY_FLOW"
    RECONFIRM_STALE_THEN_SUMMARY = "RECONFIRM_STALE_THEN_SUMMARY"
    REVIEW_ALL_THEN_SUMMARY = "REVIEW_ALL_THEN_SUMMARY"
