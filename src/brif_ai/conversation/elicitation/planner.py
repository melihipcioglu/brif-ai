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


_TOPIC_QUESTION_TEXT: dict[ElicitationTopic, str] = {
    ElicitationTopic.HOUSEHOLD: "Evde ka\u00e7 ki\u015fi ya\u015fayacak?",
    ElicitationTopic.SPACE_PROGRAM: (
        "Evde mutlaka bulunmas\u0131n\u0131 istedi\u011finiz mek\u00e2nlar nelerdir?"
    ),
    ElicitationTopic.ACCESSIBILITY: (
        "Eri\u015filebilirlik a\u00e7\u0131s\u0131ndan dikkate almam\u0131z gereken "
        "\u00f6zel bir ihtiya\u00e7 var m\u0131?"
    ),
    ElicitationTopic.SPATIAL_RELATIONSHIPS: (
        "Birbirine \u00f6zellikle yak\u0131n veya ayr\u0131 olmas\u0131n\u0131 "
        "istedi\u011finiz mek\u00e2nlar var m\u0131?"
    ),
    ElicitationTopic.KITCHEN_SERVICE: (
        "Mutfak ve servis alanlar\u0131n\u0131 nas\u0131l kullanmak istersiniz?"
    ),
    ElicitationTopic.PRIVACY: (
        "Ev i\u00e7inde \u00f6zellikle mahrem olmas\u0131n\u0131 istedi\u011finiz "
        "alanlar hangileri?"
    ),
    ElicitationTopic.WORK_STUDY: (
        "Evde d\u00fczenli \u00e7al\u0131\u015fma veya ders \u00e7al\u0131\u015fma "
        "i\u00e7in ayr\u0131 bir alan gerekiyor mu?"
    ),
    ElicitationTopic.STORAGE_SERVICE: (
        "Depolama, \u00e7ama\u015f\u0131r ve kiler gibi servis alanlar\u0131 "
        "i\u00e7in \u00f6zel ihtiya\u00e7lar\u0131n\u0131z var m\u0131?"
    ),
    ElicitationTopic.OUTDOOR_USE: (
        "Bah\u00e7e, teras veya balkon gibi d\u0131\u015f mek\u00e2nlar\u0131 "
        "nas\u0131l kullanmak istersiniz?"
    ),
    ElicitationTopic.DAILY_ROUTINES: (
        "Evde g\u00fcnl\u00fck ya\u015fam\u0131n\u0131zda en s\u0131k "
        "tekrarlanan rutinler nelerdir?"
    ),
    ElicitationTopic.BUDGET_PRIORITY: (
        "B\u00fct\u00e7ede \u00f6ncelik vermek istedi\u011finiz alanlar veya "
        "\u00f6zellikler hangileri?"
    ),
}


def question_for_topic(topic: ElicitationTopic) -> str:
    """Return the server-authoritative V1 question for an elicitation topic."""

    return _TOPIC_QUESTION_TEXT[topic]


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

        # Gate 2: An existing OPEN elicitation question blocks every new
        # follow-up topic until that question is answered or dismissed.
        if open_question_topics:
            return ElicitationContext(
                allowed_follow_up_topic=None,
                reason="An active OPEN question must be resolved before a new follow-up.",
                pending_proposals_exist=False,
                open_question_topics=open_question_topics,
                answered_question_topics=answered_question_topics,
            )

        # Gate 3: Select highest-priority uncovered topic
        excluded_topics = covered_topics

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
