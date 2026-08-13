"""Coverage engine for BRIF.AI Elicitation Topics based on BriefSnapshot."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from brif_ai.brief.models.common import OpenQuestionStatus
from brif_ai.conversation.elicitation.models import ElicitationTopic

if TYPE_CHECKING:
    from brif_ai.brief.models.snapshot import BriefSnapshot

_TOPIC_KEYWORDS: dict[ElicitationTopic, tuple[str, ...]] = {
    ElicitationTopic.HOUSEHOLD: (
        "kişi",
        "aile",
        "çocuk",
        "ebeveyn",
        "yaşlı",
        "birey",
        "oğul",
        "kız",
        "nüfus",
    ),
    ElicitationTopic.SPACE_PROGRAM: (
        "oda",
        "salon",
        "mutfak",
        "banyo",
        "yatak odası",
        "çocuk odası",
        "çalışma odası",
        "teras",
        "balkon",
        "kat",
        "tek katlı",
        "iki katlı",
        "dubleks",
    ),
    ElicitationTopic.DAILY_ROUTINES: (
        "sabah",
        "akşam",
        "hafta sonu",
        "rutin",
        "günlük",
        "alışkanlık",
        "kahvaltı",
        "yemek",
    ),
    ElicitationTopic.PRIVACY: (
        "gizlilik",
        "mahremiyet",
        "özel",
        "ortak",
        "kamusal",
        "ayrışabilen",
        "ayrıma",
        "yalıtım",
        "akustik",
        "ses",
    ),
    ElicitationTopic.SPATIAL_RELATIONSHIPS: (
        "yan yana",
        "ilişkili",
        "bağlantılı",
        "komşu",
        "bütünleşik",
        "yakın",
        "doğrudan erişim",
        "geçiş",
    ),
    ElicitationTopic.KITCHEN_SERVICE: (
        "kapanabilen mutfak",
        "açık mutfak",
        "kapalı mutfak",
        "ada mutfak",
        "kiler",
        "servis",
    ),
    ElicitationTopic.WORK_STUDY: (
        "çalışma masası",
        "evden çalışma",
        "ofis",
        "ders",
        "kütüphane",
        "odaklanma",
    ),
    ElicitationTopic.STORAGE_SERVICE: (
        "depo",
        "čamaşır odası",
        "giyinme odası",
        "vestiyer",
        "kiler",
        "garaj",
    ),
    ElicitationTopic.OUTDOOR_USE: (
        "bahçe",
        "veranda",
        "teras",
        "balkon",
        "açık hava",
        "avlu",
    ),
    ElicitationTopic.ACCESSIBILITY: (
        "asansör",
        "merdivensiz",
        "engelsiz",
        "rampa",
        "tek kat",
        "düz ayak",
    ),
    ElicitationTopic.BUDGET_PRIORITY: (
        "bütçe",
        "ekonomik",
        "öncelik",
        "maliyet",
        "kalite",
        "lüks",
    ),
}


_TOPIC_ALLOWED_SOURCES: dict[ElicitationTopic, set[str]] = {
    ElicitationTopic.HOUSEHOLD: {"brief_items"},
    ElicitationTopic.SPACE_PROGRAM: {"space_requests", "brief_items"},
    ElicitationTopic.DAILY_ROUTINES: {"usage_scenarios", "brief_items"},
    ElicitationTopic.PRIVACY: {"brief_items"},
    ElicitationTopic.SPATIAL_RELATIONSHIPS: {"brief_items"},
    ElicitationTopic.KITCHEN_SERVICE: {"space_requests", "brief_items"},
    ElicitationTopic.WORK_STUDY: {"space_requests", "brief_items"},
    ElicitationTopic.STORAGE_SERVICE: {"space_requests", "brief_items"},
    ElicitationTopic.OUTDOOR_USE: {"space_requests", "brief_items"},
    ElicitationTopic.ACCESSIBILITY: {"brief_items"},
    ElicitationTopic.BUDGET_PRIORITY: {"brief_items"},
}


class ElicitationCoverageEngine:
    """Evaluates which elicitation topics are covered in a confirmed BriefSnapshot."""

    def get_open_question_topics(self, snapshot: BriefSnapshot | None) -> list[ElicitationTopic]:
        """Return list of ElicitationTopics currently having an OPEN question."""
        if snapshot is None:
            return []
        topics: set[ElicitationTopic] = set()
        for oq in snapshot.open_questions:
            if oq.status == OpenQuestionStatus.OPEN and oq.topic_key:
                with suppress(ValueError):
                    topics.add(ElicitationTopic(oq.topic_key))
        return sorted(topics, key=lambda t: t.value)

    def get_answered_question_topics(
        self, snapshot: BriefSnapshot | None
    ) -> list[ElicitationTopic]:
        """Return list of ElicitationTopics having an ANSWERED or DISMISSED question."""
        if snapshot is None:
            return []
        topics: set[ElicitationTopic] = set()
        for oq in snapshot.open_questions:
            if (
                oq.status in {OpenQuestionStatus.ANSWERED, OpenQuestionStatus.DISMISSED}
                and oq.topic_key
            ):
                with suppress(ValueError):
                    topics.add(ElicitationTopic(oq.topic_key))
        return sorted(topics, key=lambda t: t.value)

    def count_active_elicitation_open_questions(self, snapshot: BriefSnapshot | None) -> int:
        """Count OPEN questions whose topic_key is a valid ElicitationTopic."""
        if snapshot is None:
            return 0
        count = 0
        for oq in snapshot.open_questions:
            if oq.status == OpenQuestionStatus.OPEN and oq.topic_key:
                with suppress(ValueError):
                    ElicitationTopic(oq.topic_key)
                    count += 1
        return count

    def evaluate_covered_topics(self, snapshot: BriefSnapshot | None) -> set[ElicitationTopic]:
        """Evaluate covered topics based on type-aware source checking."""
        if snapshot is None:
            return set()

        covered: set[ElicitationTopic] = set(self.get_answered_question_topics(snapshot))

        brief_item_texts = [item.normalized_statement.casefold() for item in snapshot.brief_items]
        space_request_texts = [req.display_name.casefold() for req in snapshot.space_requests]
        usage_scenario_texts = [
            f"{us.title} {us.description}".casefold() for us in snapshot.usage_scenarios
        ]

        for topic, keywords in _TOPIC_KEYWORDS.items():
            if topic in covered:
                continue

            allowed = _TOPIC_ALLOWED_SOURCES.get(
                topic, {"brief_items", "space_requests", "usage_scenarios"}
            )
            topic_texts: list[str] = []
            if "brief_items" in allowed:
                topic_texts.extend(brief_item_texts)
            if "space_requests" in allowed:
                topic_texts.extend(space_request_texts)
            if "usage_scenarios" in allowed:
                topic_texts.extend(usage_scenario_texts)

            combined = " ".join(topic_texts)
            for kw in keywords:
                if kw in combined:
                    covered.add(topic)
                    break

        return covered
