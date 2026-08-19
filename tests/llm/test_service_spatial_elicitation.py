"""End-to-end service interpretation tests for conversational spatial relationships
with structured LLM proposals.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from brif_ai.brief.models.common import (
    ConfirmationStatus,
    EvidenceSource,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefSnapshot,
    Evidence,
    OpenQuestion,
    SpaceRequest,
    Stakeholder,
)
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    LocalModelInfo,
    ProviderHealth,
)
from brif_ai.llm.provider import LocalLLMProvider
from brif_ai.llm.service import LocalLLMConversationService
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.models import (
    ProposedSpatialRelationship,
    RelationshipProvenance,
    SpatialRelationType,
)


class MockStructuredSpatialLLMProvider(LocalLLMProvider):
    def __init__(self, proposals: list[ProposedSpatialRelationship]) -> None:
        self.proposals = proposals

    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return []

    async def interpret(
        self,
        request: ConversationRequest,
        output_schema: dict[str, object],
    ) -> ArchitecturalIntentResult:
        return ArchitecturalIntentResult(
            assistant_message="Mekânsal tercihiniz anlaşıldı.",
            intent=IntentType.MODIFY_RELATIONSHIP,
            target=EntityTarget(project_id=request.active_context.project_id),
            user_requirements=[request.message],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=self.proposals,
            needs_follow_up=False,
            follow_up_question=None,
            follow_up_topic=None,
            needs_user_confirmation=True,
            confidence=0.95,
            warnings=[],
        )


@pytest.fixture
def sample_snapshot() -> BriefSnapshot:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    ev = Evidence(
        id="ev_test",
        source_type=EvidenceSource.CHAT,
        excerpt="Test evidence",
        source_reference="msg_1",
    )
    return BriefSnapshot(
        project_id="proj_spatial_service_test",
        schema_version="brief.v0",
        brief_version=1,
        created_at=now,
        stakeholders=[
            Stakeholder(
                id="stk_1",
                display_name="Ev Sahibi",
                role="CLIENT_OWNER",
                active=True,
            )
        ],
        evidence=[ev],
        brief_items=[],
        space_requests=[
            SpaceRequest(
                id="sr_bed",
                display_name="Yatak Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_child",
                display_name="Çocuk Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_living",
                display_name="Salon",
                space_function=SpaceFunction.LIVING,
                minimum_quantity=1,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_kitchen",
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
                minimum_quantity=1,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_guest",
                display_name="Misafir Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=1,
                mandatory=True,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
            SpaceRequest(
                id="sr_garden",
                display_name="Bahçe",
                space_function=SpaceFunction.OTHER,
                minimum_quantity=1,
                mandatory=False,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_test"],
            ),
        ],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def test_service_interpret_bedrooms_near(sample_snapshot: BriefSnapshot) -> None:
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_bed_01",
            target_space_id="sn_bed_02",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    settings = LocalLLMSettings(enabled=True, provider="ollama")
    service = LocalLLMConversationService(
        settings=settings,
        provider=MockStructuredSpatialLLMProvider(proposals),
    )

    req = ConversationRequest(
        message="Yatak odaları birbirine yakın olsun.",
        active_context=ActiveContextSnapshot(
            project_id=sample_snapshot.project_id,
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=sample_snapshot,
    )

    response = asyncio.run(service.interpret(req))
    assert response.success is True
    assert response.result is not None
    res = response.result
    assert res.intent == IntentType.MODIFY_RELATIONSHIP
    assert len(res.proposed_spatial_relationships) == 1
    assert res.proposed_actions == []
    assert res.proposed_brief_mutations == []
    assert res.needs_user_confirmation is True
    assert res.needs_follow_up is False

    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_bed_01"
    assert rel.target_space_id == "sn_bed_02"
    assert rel.relation_type == SpatialRelationType.NEAR
    assert rel.provenance == RelationshipProvenance.USER_STATED
    assert "Yatak Odası 1 ile Yatak Odası 2 birbirine yakın" in res.assistant_message


def test_service_interpret_kitchen_living_near(sample_snapshot: BriefSnapshot) -> None:
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_kitchen_01",
            target_space_id="sn_living_01",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    settings = LocalLLMSettings(enabled=True, provider="ollama")
    service = LocalLLMConversationService(
        settings=settings,
        provider=MockStructuredSpatialLLMProvider(proposals),
    )

    req = ConversationRequest(
        message="Mutfak salona yakın olsun.",
        active_context=ActiveContextSnapshot(
            project_id=sample_snapshot.project_id,
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=sample_snapshot,
    )

    response = asyncio.run(service.interpret(req))
    assert response.success is True
    res = response.result
    assert res is not None
    assert len(res.proposed_spatial_relationships) == 1
    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_kitchen_01"
    assert rel.target_space_id == "sn_living_01"
    assert rel.relation_type == SpatialRelationType.NEAR


def test_service_interpret_guest_child_separated(sample_snapshot: BriefSnapshot) -> None:
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_guest_01",
            target_space_id="sn_child_01",
            relation_type=SpatialRelationType.SEPARATED_FROM,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    settings = LocalLLMSettings(enabled=True, provider="ollama")
    service = LocalLLMConversationService(
        settings=settings,
        provider=MockStructuredSpatialLLMProvider(proposals),
    )

    req = ConversationRequest(
        message="Misafir bölümü çocuk odalarından uzak olsun.",
        active_context=ActiveContextSnapshot(
            project_id=sample_snapshot.project_id,
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=sample_snapshot,
    )

    response = asyncio.run(service.interpret(req))
    assert response.success is True
    res = response.result
    assert res is not None
    assert len(res.proposed_spatial_relationships) == 1
    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_guest_01"
    assert rel.target_space_id == "sn_child_01"
    assert rel.relation_type == SpatialRelationType.SEPARATED_FROM


def test_service_interpret_child_rooms_adjacent(sample_snapshot: BriefSnapshot) -> None:
    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_child_01",
            target_space_id="sn_child_02",
            relation_type=SpatialRelationType.ADJACENT_TO,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    settings = LocalLLMSettings(enabled=True, provider="ollama")
    service = LocalLLMConversationService(
        settings=settings,
        provider=MockStructuredSpatialLLMProvider(proposals),
    )

    req = ConversationRequest(
        message="Çocuk odaları yan yana olsun.",
        active_context=ActiveContextSnapshot(
            project_id=sample_snapshot.project_id,
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=sample_snapshot,
    )

    response = asyncio.run(service.interpret(req))
    assert response.success is True
    res = response.result
    assert res is not None
    assert len(res.proposed_spatial_relationships) == 1
    rel = res.proposed_spatial_relationships[0]
    assert rel.source_space_id == "sn_child_01"
    assert rel.target_space_id == "sn_child_02"
    assert rel.relation_type == SpatialRelationType.ADJACENT_TO


def test_service_interpret_spatial_open_question(sample_snapshot: BriefSnapshot) -> None:
    oq_spatial = OpenQuestion(
        id="oq_spatial_1",
        question="Birbirine özellikle yakın veya ayrı olmasını istediğiniz mekânlar var mı?",
        reason="Mekânsal ilişkiler belirsiz",
        related_brief_item_ids=[],
        status=OpenQuestionStatus.OPEN,
        topic_key="spatial_relationships",
    )
    snap = sample_snapshot.model_copy(update={"open_questions": [oq_spatial]})

    proposals = [
        ProposedSpatialRelationship(
            source_space_id="sn_bed_01",
            target_space_id="sn_bed_02",
            relation_type=SpatialRelationType.NEAR,
            provenance=RelationshipProvenance.USER_STATED,
            priority=Priority.MUST,
            requires_user_confirmation=True,
        )
    ]
    settings = LocalLLMSettings(enabled=True, provider="ollama")
    service = LocalLLMConversationService(
        settings=settings,
        provider=MockStructuredSpatialLLMProvider(proposals),
    )

    req = ConversationRequest(
        message="Yatak odaları birbirine yakın olsun.",
        active_context=ActiveContextSnapshot(
            project_id=snap.project_id,
            context_fingerprint="fp_1",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=snap,
    )

    response = asyncio.run(service.interpret(req))
    assert response.success is True
    res = response.result
    assert res is not None
    assert res.answers_current_open_question is True
    assert len(res.proposed_spatial_relationships) == 1
