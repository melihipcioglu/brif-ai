"""Deterministic Elicitation Planner for BRIF.AI Conversation UX V1."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brif_ai.conversation.elicitation.coverage import ElicitationCoverageEngine
from brif_ai.conversation.elicitation.models import ElicitationContext, ElicitationTopic

if TYPE_CHECKING:
    from brif_ai.brief.models.snapshot import BriefSnapshot

_TOPIC_PRIORITY_ORDER: tuple[ElicitationTopic, ...] = (
    ElicitationTopic.HOUSEHOLD,
    ElicitationTopic.SPACE_PROGRAM,
    ElicitationTopic.ACCESSIBILITY,
    ElicitationTopic.SPATIAL_RELATIONSHIPS,
    ElicitationTopic.KITCHEN_SERVICE,
    ElicitationTopic.PRIVACY,
    ElicitationTopic.WORK_STUDY,
    ElicitationTopic.STORAGE_SERVICE,
    ElicitationTopic.OUTDOOR_USE,
    ElicitationTopic.DAILY_ROUTINES,
    ElicitationTopic.BUDGET_PRIORITY,
)


class ElicitationPlanner:
    """Plans allowed follow-up topics deterministically without LLM provider dependencies."""

    def __init__(self, coverage_engine: ElicitationCoverageEngine | None = None) -> None:
        self.coverage_engine = coverage_engine or ElicitationCoverageEngine()

    def plan_context(
        self,
        snapshot: BriefSnapshot | None,
        *,
        pending_proposals_exist: bool = False,
        user_message: str = "",
    ) -> ElicitationContext:
        """Evaluate snapshot and turn state to produce server-authoritative ElicitationContext."""
        open_question_topics = self.coverage_engine.get_open_question_topics(snapshot)
        answered_question_topics = self.coverage_engine.get_answered_question_topics(snapshot)
        covered_topics = self.coverage_engine.evaluate_covered_topics(snapshot)

        # Gate 1: If pending proposals exist, suppress follow-up questions
        if pending_proposals_exist:
            return ElicitationContext(
                allowed_follow_up_topic=None,
                reason="Bekleyen öneriler varken takip sorusu sorulamaz.",
                pending_proposals_exist=True,
                open_question_topics=open_question_topics,
                answered_question_topics=answered_question_topics,
            )

        # Gate 2: Exclude covered topics and topics that ALREADY have an OPEN question
        open_set = set(open_question_topics)
        excluded_topics = covered_topics | open_set

        # Select highest-priority uncovered topic
        selected_topic: ElicitationTopic | None = None
        for topic in _TOPIC_PRIORITY_ORDER:
            if topic not in excluded_topics:
                selected_topic = topic
                break

        reason = (
            f"Seçilen mimari konu: '{selected_topic.value}'"
            if selected_topic is not None
            else "Tüm temel mimari konular kapsandı."
        )

        return ElicitationContext(
            allowed_follow_up_topic=selected_topic,
            reason=reason,
            pending_proposals_exist=False,
            open_question_topics=open_question_topics,
            answered_question_topics=answered_question_topics,
        )
