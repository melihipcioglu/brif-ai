"""Elicitation topics and context contracts for BRIF.AI Conversation UX V1."""

from __future__ import annotations

import sys
from enum import Enum

from pydantic import BaseModel, ConfigDict

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class ElicitationTopic(StrEnum):
    HOUSEHOLD = "household"
    SPACE_PROGRAM = "space_program"
    DAILY_ROUTINES = "daily_routines"
    PRIVACY = "privacy"
    SPATIAL_RELATIONSHIPS = "spatial_relationships"
    KITCHEN_SERVICE = "kitchen_service"
    WORK_STUDY = "work_study"
    STORAGE_SERVICE = "storage_service"
    OUTDOOR_USE = "outdoor_use"
    ACCESSIBILITY = "accessibility"
    BUDGET_PRIORITY = "budget_priority"


class ElicitationContext(BaseModel):
    """Server-authoritative elicitation state evaluated for the current turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed_follow_up_topic: ElicitationTopic | None = None
    reason: str = ""
    pending_proposals_exist: bool = False
    open_question_topics: list[ElicitationTopic] = []
    answered_question_topics: list[ElicitationTopic] = []
