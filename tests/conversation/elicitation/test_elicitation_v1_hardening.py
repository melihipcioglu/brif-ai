"""Comprehensive hardening tests for Conversation UX / Brief Elicitation V1."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from apps.api.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError

from brif_ai.brief.models.common import (
    BriefItemKind,
    ConfirmationStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefItem,
    BriefSnapshot,
    Evidence,
    OpenQuestion,
    Stakeholder,
)
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
)
from brif_ai.brief.persistence.json_repository import JSONBriefRepository
from brif_ai.brief.service import PersistentBriefService
from brif_ai.conversation.elicitation.coverage import ElicitationCoverageEngine
from brif_ai.conversation.elicitation.models import ElicitationTopic
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.settings import LocalLLMSettings


def sample_snapshot(project_id: str = "proj_house_2story", version: int = 1) -> BriefSnapshot:
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=version,
        created_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(
                id="stk_owner",
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
        open_questions=[],
    )


class MockAPIProvider:
    def __init__(self, return_result: ArchitecturalIntentResult | None = None) -> None:
        self.return_result = return_result
        self.last_received_request: ConversationRequest | None = None
        self.interpret_call_count = 0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        self.interpret_call_count += 1
        self.last_received_request = request
        if self.return_result is not None:
            return self.return_result
        return ArchitecturalIntentResult(
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(),
            assistant_message="Anladım, devam edelim.",
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            needs_follow_up=False,
            needs_user_confirmation=False,
            confidence=0.9,
            warnings=[],
        )


def conversation_request_payload(
    project_id: str = "proj_house_2story",
    version: int = 1,
    message: str = "Merhaba",
) -> dict[str, Any]:
    return {
        "message": message,
        "active_context": {
            "project_id": project_id,
            "context_fingerprint": "ctx_fp_01",
            "generation_id": 1,
        },
        "brief_snapshot": sample_snapshot(project_id, version).model_dump(mode="json"),
    }


# ============================================================================
# 1. coverage.py: count_active_elicitation_open_questions & legacy filtering
# ============================================================================


def test_coverage_count_active_elicitation_open_questions_ignores_legacy_none() -> None:
    snap = sample_snapshot()
    oq_legacy = OpenQuestion(
        id="oq_legacy",
        question="Genel açıklama soru?",
        reason="Eski soru",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key=None,
    )
    oq_elicitation = OpenQuestion(
        id="oq_elicitation",
        question="Kaç kişisiniz?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap_with_oqs = snap.model_copy(update={"open_questions": [oq_legacy, oq_elicitation]})

    engine = ElicitationCoverageEngine()
    count = engine.count_active_elicitation_open_questions(snap_with_oqs)

    assert count == 1
    open_topics = engine.get_open_question_topics(snap_with_oqs)
    assert open_topics == [ElicitationTopic.HOUSEHOLD]


# ============================================================================
# 2. contracts.py: answers_current_open_question & invariant validations
# ============================================================================


def test_answers_current_open_question_requires_proposed_brief_mutation() -> None:
    # proposed_actions alone cannot answer open question
    with pytest.raises(ValidationError, match="answers_current_open_question requires"):
        ArchitecturalIntentResult(
            intent=IntentType.MODIFY_SPACE,
            target=EntityTarget(),
            assistant_message="Mekân düzenlendi.",
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            answers_current_open_question=True,
            needs_follow_up=False,
            needs_user_confirmation=False,
            confidence=0.9,
            warnings=[],
        )


def test_answers_current_open_question_and_needs_follow_up_cannot_both_be_true() -> None:
    mutation = ProposedBriefMutation(
        mutation_id="mut_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="4 kişilik",
            priority=Priority.MUST,
        ),
    )
    with pytest.raises(ValidationError, match="needs_follow_up must be false"):
        ArchitecturalIntentResult(
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(),
            assistant_message="Gereksinim eklendi.",
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[mutation],
            answers_current_open_question=True,
            needs_follow_up=True,
            follow_up_question="Başka bir konu?",
            follow_up_topic=ElicitationTopic.PRIVACY,
            needs_user_confirmation=True,
            confidence=0.9,
            warnings=[],
        )


# ============================================================================
# 3. API: 404 uninitialized, 409 stale version, client brief replacement
# ============================================================================


def test_interpret_uninitialized_brief_returns_404(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), MockAPIProvider(), brief_repository=repo)
    )

    payload = conversation_request_payload("proj_uninit", 1)
    response = client.post("/api/v1/conversation/interpret", json=payload)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_interpret_stale_client_version_returns_409_without_calling_llm(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    # Persist brief at version 3
    snap = sample_snapshot("proj_house_2story", version=3)
    repo.save(snap)

    mock_provider = MockAPIProvider()
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), mock_provider, brief_repository=repo)
    )

    # Client sends version 2
    payload = conversation_request_payload("proj_house_2story", version=2)
    response = client.post("/api/v1/conversation/interpret", json=payload)

    assert response.status_code == 409
    assert "Stale brief version" in response.json()["detail"]
    assert mock_provider.interpret_call_count == 0  # LLM was NOT called!


def test_interpret_replaces_client_snapshot_with_server_authoritative(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    ev = Evidence(
        id="ev_01",
        source_type=EvidenceSource.CHAT,
        source_reference="ref_1",
        excerpt="4 kişiyiz",
    )
    # Server snapshot has real item
    item = BriefItem(
        id="bi_server",
        kind=BriefItemKind.NEED,
        normalized_statement="Server authoritative item",
        priority=Priority.MUST,
        stakeholder_ids=["stk_owner"],
        evidence_ids=["ev_01"],
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )
    server_snap = sample_snapshot("proj_house_2story", 1).model_copy(
        update={"evidence": [ev], "brief_items": [item]}
    )
    repo.save(server_snap)

    mock_provider = MockAPIProvider()
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), mock_provider, brief_repository=repo)
    )

    # Client sends modified/fake brief_snapshot content
    payload = conversation_request_payload("proj_house_2story", 1)
    # Keep the client snapshot schema-valid so the request reaches the endpoint.
    # The fake brief item below is still intentionally different from server state.
    payload["brief_snapshot"]["evidence"] = [ev.model_dump(mode="json")]
    fake_item = {
        "id": "bi_fake_client",
        "kind": "NEED",
        "normalized_statement": "Fake client item",
        "priority": "MUST",
        "stakeholder_ids": ["stk_owner"],
        "evidence_ids": ["ev_01"],
        "confirmation_status": "CONFIRMED",
    }
    payload["brief_snapshot"]["brief_items"] = [fake_item]

    response = client.post("/api/v1/conversation/interpret", json=payload)
    assert response.status_code == 200

    # Verify provider received the SERVER authoritative snapshot, not the fake client one
    received = mock_provider.last_received_request
    assert received is not None
    assert received.brief_snapshot is not None
    assert len(received.brief_snapshot.brief_items) == 1
    assert received.brief_snapshot.brief_items[0].id == "bi_server"


# ============================================================================
# 4. Pre-LLM Skip Command Handling ("geçelim")
# ============================================================================


def test_pre_llm_skip_command_dismisses_active_open_question_without_llm(
    tmp_path: Path,
) -> None:
    repo = JSONBriefRepository(tmp_path)
    oq = OpenQuestion(
        id="oq_01",
        question="Giyinme odası istiyor musunuz?",
        reason="Depolama alanı belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="storage_service",
    )
    snap = sample_snapshot("proj_house_2story", 1).model_copy(update={"open_questions": [oq]})
    repo.save(snap)

    mock_provider = MockAPIProvider()
    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), mock_provider, brief_repository=repo)
    )

    # User says "geçelim"
    payload = conversation_request_payload("proj_house_2story", 1, message="geçelim")
    response = client.post("/api/v1/conversation/interpret", json=payload)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert mock_provider.interpret_call_count == 0  # LLM skipped!

    # Resulting brief snapshot returned at v2 with DISMISSED question
    resulting = res_data["resulting_brief_snapshot"]
    assert resulting is not None
    assert resulting["brief_version"] == 2
    assert resulting["open_questions"][0]["status"] == "DISMISSED"


# ============================================================================
# 5. Atomic Mutation Approval & OpenQuestion Resolution (1 version increment)
# ============================================================================


def test_atomic_approval_and_open_question_resolution(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)

    oq = OpenQuestion(
        id="oq_01",
        question="Kaç kişisiniz?",
        reason="Nüfus belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="household",
    )
    snap = sample_snapshot("proj_house_2story", 1).model_copy(update={"open_questions": [oq]})
    repo.save(snap)

    mutation = ProposedBriefMutation(
        mutation_id="mut_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Dört kişilik aile",
            priority=Priority.MUST,
        ),
    )

    # Atomically approve mutation and resolve open question
    new_snap = service.record_brief_mutation_approval(
        current_project_id="proj_house_2story",
        expected_brief_version=1,
        proposed_mutation=mutation,
        user_message="4 kişiyiz",
        answers_current_open_question=True,
    )

    # Version should be EXACTLY 2 (single atomic step, NOT 3!)
    assert new_snap.brief_version == 2
    assert len(new_snap.brief_items) == 1
    assert new_snap.open_questions[0].status == OpenQuestionStatus.ANSWERED


def test_atomic_approval_fails_when_no_active_open_question_exists(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    snap = sample_snapshot("proj_house_2story", 1)  # No open questions
    repo.save(snap)

    client = TestClient(
        create_app(LocalLLMSettings(enabled=True), MockAPIProvider(), brief_repository=repo)
    )

    mutation_payload = {
        "mutation_id": "mut_01",
        "mutation_type": "ADD_BRIEF_ITEM",
        "brief_item": {
            "kind": "NEED",
            "normalized_statement": "Dört kişilik aile",
            "priority": "MUST",
        },
    }
    approve_req = {
        "brief_snapshot": snap.model_dump(mode="json"),
        "proposed_mutation": mutation_payload,
        "current_project_id": "proj_house_2story",
        "expected_brief_version": 1,
        "proposal_fingerprint": "fp_01",
        "current_fingerprint": "fp_01",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "4 kişiyiz",
        "source_reference": "ref_01",
        "answers_current_open_question": True,
    }

    response = client.post("/api/v1/brief/mutations/approve", json=approve_req)

    assert response.status_code == 422
    assert "no active OPEN question" in response.json()["error"]
