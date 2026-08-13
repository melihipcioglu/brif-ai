"""Elicitation topics and context contracts for BRIF.AI Conversation UX V1."""

from __future__ import annotations

import sys
from contextlib import suppress
from enum import Enum

from pydantic import BaseModel, ConfigDict

from brif_ai.brief.mutation import BriefMutationType

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


_TOPIC_PERMITTED_MUTATIONS: dict[ElicitationTopic, set[BriefMutationType]] = {
    ElicitationTopic.HOUSEHOLD: {BriefMutationType.ADD_BRIEF_ITEM},
    ElicitationTopic.SPACE_PROGRAM: {
        BriefMutationType.ADD_SPACE_REQUEST,
        BriefMutationType.ADD_BRIEF_ITEM,
    },
    ElicitationTopic.DAILY_ROUTINES: {
        BriefMutationType.ADD_USAGE_SCENARIO,
        BriefMutationType.ADD_BRIEF_ITEM,
    },
    ElicitationTopic.PRIVACY: {BriefMutationType.ADD_BRIEF_ITEM},
    ElicitationTopic.SPATIAL_RELATIONSHIPS: {
        BriefMutationType.ADD_BRIEF_ITEM,
        BriefMutationType.ADD_SPACE_REQUEST,
    },
    ElicitationTopic.KITCHEN_SERVICE: {
        BriefMutationType.ADD_SPACE_REQUEST,
        BriefMutationType.ADD_BRIEF_ITEM,
    },
    ElicitationTopic.WORK_STUDY: {
        BriefMutationType.ADD_BRIEF_ITEM,
        BriefMutationType.ADD_SPACE_REQUEST,
    },
    ElicitationTopic.STORAGE_SERVICE: {
        BriefMutationType.ADD_SPACE_REQUEST,
        BriefMutationType.ADD_BRIEF_ITEM,
    },
    ElicitationTopic.OUTDOOR_USE: {
        BriefMutationType.ADD_SPACE_REQUEST,
        BriefMutationType.ADD_BRIEF_ITEM,
    },
    ElicitationTopic.ACCESSIBILITY: {BriefMutationType.ADD_BRIEF_ITEM},
    ElicitationTopic.BUDGET_PRIORITY: {BriefMutationType.ADD_BRIEF_ITEM},
}


def get_permitted_mutations_for_topic(topic: ElicitationTopic | str) -> set[BriefMutationType]:
    """Return the set of server-authoritative allowed BriefMutationTypes for a topic."""
    if isinstance(topic, str):
        with suppress(ValueError):
            topic = ElicitationTopic(topic)
    if not isinstance(topic, ElicitationTopic):
        return {BriefMutationType.ADD_BRIEF_ITEM}
    return _TOPIC_PERMITTED_MUTATIONS.get(topic, {BriefMutationType.ADD_BRIEF_ITEM})


class ElicitationContext(BaseModel):
    """Server-authoritative elicitation state evaluated for the current turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed_follow_up_topic: ElicitationTopic | None = None
    reason: str = ""
    pending_proposals_exist: bool = False
    open_question_topics: list[ElicitationTopic] = []
    answered_question_topics: list[ElicitationTopic] = []
