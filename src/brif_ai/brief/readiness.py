"""Deterministic readiness evaluation for BRIF.AI brief snapshots."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from brif_ai.brief.models.common import (
    ConfirmationStatus,
    ContradictionStatus,
    OpenQuestionStatus,
)
from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.conversation.elicitation.coverage import ElicitationCoverageEngine
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.conversation.elicitation.planner import elicitation_topic_priority_order


class ReadinessBlockerCode(StrEnum):
    """Stable machine-readable reasons why a brief cannot advance."""

    SNAPSHOT_MISSING = "SNAPSHOT_MISSING"
    PENDING_CONFIRMATIONS = "PENDING_CONFIRMATIONS"
    OPEN_CONTRADICTIONS = "OPEN_CONTRADICTIONS"
    OPEN_QUESTIONS = "OPEN_QUESTIONS"
    UNCOVERED_REQUIRED_TOPICS = "UNCOVERED_REQUIRED_TOPICS"


class _ReadinessContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadinessBlocker(_ReadinessContract):
    """One deterministic condition blocking progression to the next stage."""

    code: ReadinessBlockerCode
    message: str
    related_ids: list[str] = Field(default_factory=list)


class BriefReadinessResult(_ReadinessContract):
    """Complete deterministic readiness result for one brief snapshot."""

    ready_for_next_stage: bool
    covered_topics: list[ElicitationTopic]
    uncovered_topics: list[ElicitationTopic]
    blockers: list[ReadinessBlocker]


_BLOCKER_MESSAGES: dict[ReadinessBlockerCode, str] = {
    ReadinessBlockerCode.SNAPSHOT_MISSING: "Brief snapshot bulunamadı.",
    ReadinessBlockerCode.PENDING_CONFIRMATIONS: "Onay bekleyen brief kayıtları var.",
    ReadinessBlockerCode.OPEN_CONTRADICTIONS: "Çözülmemiş brief çelişkileri var.",
    ReadinessBlockerCode.OPEN_QUESTIONS: "Yanıtlanmamış açık brief soruları var.",
    ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS: (
        "Gerekli elicitation konularının tamamı kapsanmıyor."
    ),
}


def _blocker(
    code: ReadinessBlockerCode,
    related_ids: list[str] | None = None,
) -> ReadinessBlocker:
    return ReadinessBlocker(
        code=code,
        message=_BLOCKER_MESSAGES[code],
        related_ids=related_ids or [],
    )


class BriefReadinessEvaluator:
    """Evaluate brief readiness without inference or free-text parsing."""

    def __init__(self, coverage_engine: ElicitationCoverageEngine | None = None) -> None:
        self.coverage_engine = coverage_engine or ElicitationCoverageEngine()

    def evaluate(self, snapshot: BriefSnapshot | None) -> BriefReadinessResult:
        required_topics = elicitation_topic_priority_order()

        if snapshot is None:
            missing_snapshot_blockers = [
                _blocker(ReadinessBlockerCode.SNAPSHOT_MISSING),
                _blocker(ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS),
            ]
            return BriefReadinessResult(
                ready_for_next_stage=False,
                covered_topics=[],
                uncovered_topics=list(required_topics),
                blockers=missing_snapshot_blockers,
            )

        covered_set = self.coverage_engine.evaluate_covered_topics(snapshot)
        covered_topics = [topic for topic in required_topics if topic in covered_set]
        uncovered_topics = [topic for topic in required_topics if topic not in covered_set]
        blockers: list[ReadinessBlocker] = []

        pending_ids = [
            *(
                item.id
                for item in snapshot.brief_items
                if item.confirmation_status is ConfirmationStatus.PROPOSED
            ),
            *(
                request.id
                for request in snapshot.space_requests
                if request.confirmation_status is ConfirmationStatus.PROPOSED
            ),
            *(
                scenario.id
                for scenario in snapshot.usage_scenarios
                if scenario.confirmation_status is ConfirmationStatus.PROPOSED
            ),
        ]
        if pending_ids:
            blockers.append(
                _blocker(
                    ReadinessBlockerCode.PENDING_CONFIRMATIONS,
                    sorted(pending_ids),
                )
            )

        open_contradiction_ids = sorted(
            contradiction.id
            for contradiction in snapshot.contradictions
            if contradiction.status is ContradictionStatus.OPEN
        )
        if open_contradiction_ids:
            blockers.append(
                _blocker(
                    ReadinessBlockerCode.OPEN_CONTRADICTIONS,
                    open_contradiction_ids,
                )
            )

        open_question_ids = sorted(
            question.id
            for question in snapshot.open_questions
            if question.status is OpenQuestionStatus.OPEN
        )
        if open_question_ids:
            blockers.append(
                _blocker(
                    ReadinessBlockerCode.OPEN_QUESTIONS,
                    open_question_ids,
                )
            )

        if uncovered_topics:
            blockers.append(_blocker(ReadinessBlockerCode.UNCOVERED_REQUIRED_TOPICS))

        return BriefReadinessResult(
            ready_for_next_stage=not blockers,
            covered_topics=covered_topics,
            uncovered_topics=uncovered_topics,
            blockers=blockers,
        )
