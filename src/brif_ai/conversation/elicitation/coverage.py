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
        """Evaluate covered topics based on snapshot items, room requests, and scenarios."""
        if snapshot is None:
            return set()

        covered: set[ElicitationTopic] = set(self.get_answered_question_topics(snapshot))

        # Inspect brief items, space requests, and usage scenarios
        texts: list[str] = []
        for item in snapshot.brief_items:
            texts.append(item.normalized_statement.casefold())
        for req in snapshot.space_requests:
            texts.append(req.display_name.casefold())
        for us in snapshot.usage_scenarios:
            texts.append(f"{us.title} {us.description}".casefold())

        combined = " ".join(texts)

        for topic, keywords in _TOPIC_KEYWORDS.items():
            if topic in covered:
                continue
            for kw in keywords:
                if kw in combined:
                    covered.add(topic)
                    break

        return covered
