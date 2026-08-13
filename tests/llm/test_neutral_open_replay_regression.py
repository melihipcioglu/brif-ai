from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from brif_ai.brief.models.common import OpenQuestionStatus
from brif_ai.brief.models.snapshot import BriefSnapshot, OpenQuestion, Stakeholder
from brif_ai.conversation.elicitation.planner import ElicitationPlanner
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings


class NeverCallProvider:
    async def health(self) -> ProviderHealth:
        raise AssertionError("Neutral start with existing OPEN must not check provider health.")

    async def list_models(self) -> list[LocalModelInfo]:
        raise AssertionError("Neutral start with existing OPEN must not list provider models.")

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
    ) -> ArchitecturalIntentResult:
        raise AssertionError("Neutral start with existing OPEN must not call the LLM.")


def test_neutral_start_replays_existing_open_question_without_llm() -> None:
    snapshot = BriefSnapshot(
        project_id="p1",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="s1",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[
            OpenQuestion(
                id="oq_household_1",
                question="Evde kaç kişi yaşayacak?",
                reason="Hane yapısı henüz bilinmiyor.",
                related_brief_item_ids=[],
                status=OpenQuestionStatus.OPEN,
                topic_key="household",
            )
        ],
    )
    request = ConversationRequest(
        message="Başlayalım.",
        active_context=ActiveContextSnapshot(
            project_id="p1",
            context_fingerprint="fp1",
            generation_id=1,
        ),
        visible_entities=[],
        conversation_summary="",
        current_decisions=[],
        pending_proposals=[],
        brief_snapshot=snapshot,
        elicitation_context=ElicitationPlanner().plan_context(snapshot),
    )
    service = LocalLLMConversationService(
        LocalLLMSettings(enabled=True, model="local-model:latest"),
        NeverCallProvider(),
    )

    response = asyncio.run(service.interpret(request))

    assert response.success is True
    assert response.result is not None
    assert response.result.assistant_message == "Evde kaç kişi yaşayacak?"
    assert response.result.proposed_actions == []
    assert response.result.proposed_brief_mutations == []
    assert response.result.answers_current_open_question is False
    assert response.result.needs_follow_up is False
    assert response.result.follow_up_question is None
    assert response.result.follow_up_topic is None
    assert response.result.needs_user_confirmation is False
