"""API tests for Spatial Relationship Approval and Persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from apps.api.main import create_app
from fastapi.testclient import TestClient

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
from brif_ai.brief.persistence import JSONBriefRepository
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
from brif_ai.llm.settings import LocalLLMSettings
from brif_ai.spatial.models import (
    ProposedSpatialRelationship,
    RelationshipProvenance,
    SpatialRelationType,
)
from brif_ai.spatial.persistence import JSONSpatialRelationshipRepository


class MockSpatialInterpretationProvider:
    async def health(self) -> ProviderHealth:
        return ProviderHealth(provider="ollama", reachable=True)

    async def list_models(self) -> list[LocalModelInfo]:
        return [LocalModelInfo(name="local-model:latest", size=42)]

    async def interpret(
        self, request: ConversationRequest, output_schema: dict[str, object]
    ) -> ArchitecturalIntentResult:
        return ArchitecturalIntentResult(
            assistant_message="Çocuk odalarını birbirine yakın olacak şekilde planlayabiliriz.",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id=request.active_context.project_id),
            user_requirements=["Çocuk odaları birbirine yakın olsun."],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[],
            proposed_spatial_relationships=[
                ProposedSpatialRelationship(
                    source_space_id="sn_child_room_01",
                    target_space_id="sn_child_room_02",
                    relation_type=SpatialRelationType.NEAR,
                    provenance=RelationshipProvenance.USER_STATED,
                    priority=Priority.MUST,
                    rationale="Çocuk odaları birbirine yakın olmalı",
                    requires_user_confirmation=True,
                )
            ],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=0.95,
            warnings=[],
        )


def initialize_test_brief(repo: JSONBriefRepository) -> BriefSnapshot:
    snapshot = BriefSnapshot(
        project_id="proj_api_test",
        schema_version="brief.v0",
        brief_version=1,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
        ],
        evidence=[
            Evidence(
                id="ev_init_1",
                source_type=EvidenceSource.CHAT,
                source_reference="chat_init",
                excerpt="İlk gereksinimler.",
            )
        ],
        brief_items=[],
        space_requests=[
            SpaceRequest(
                id="sr_living",
                display_name="Salon",
                space_function=SpaceFunction.LIVING,
                minimum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_init_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_child_room",
                display_name="Çocuk Odası",
                space_function=SpaceFunction.SLEEPING,
                minimum_quantity=2,  # Expands to sn_child_room_01 and sn_child_room_02
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_init_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
        ],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[
            OpenQuestion(
                id="oq_spatial_1",
                question="Mekânlar arası yakınlık tercihiniz var mı?",
                reason="Mekânsal ilişkiler konusu",
                status=OpenQuestionStatus.OPEN,
                topic_key="spatial_relationships",
                related_brief_item_ids=[],
            )
        ],
    )
    return repo.save(snapshot)


def test_acceptance_6_and_7_explicit_approval_transaction(tmp_path: Path) -> None:
    """Requirement 6: Explicit approval materializes USER_CONFIRMED edge with real evidence ID.
    Requirement 7: Unapproved proposals do not appear in the persisted graph.
    """
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
    )
    client = TestClient(app)

    # 1. Verify that before approval, no authoritative spatial graph exists (Requirement 7)
    get_res = client.get(f"/api/v1/projects/{snapshot.project_id}/spatial/graph")
    assert get_res.status_code == 404

    # 2. Approve proposed relationship
    proposed_rel = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
        priority=Priority.MUST,
        rationale="Çocuk odaları birbirine yakın olmalı",
        requires_user_confirmation=True,
    )

    approval_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": proposed_rel.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": snapshot.brief_version,
        "proposal_fingerprint": "fingerprint_123",
        "current_fingerprint": "fingerprint_123",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Evet, çocuk odaları yan yana olsun.",
        "source_reference": "chat_msg_42",
        "answers_current_open_question": True,
    }

    response = client.post("/api/v1/spatial/relationships/approve", json=approval_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    resulting_brief = data["resulting_snapshot"]
    resulting_graph = data["resulting_spatial_graph"]
    record = data["approval_record"]

    # Resulting brief version should be 2 (evidence added + question answered)
    assert resulting_brief["brief_version"] == 2
    # Spatial graph source_brief_version MUST match brief_version (Constraint 1)
    assert resulting_graph["source_brief_version"] == 2

    # Open question transitioned to ANSWERED
    oq = next(q for q in resulting_brief["open_questions"] if q["id"] == "oq_spatial_1")
    assert oq["status"] == "ANSWERED"

    # Evidence created
    evidence_ids = [ev["id"] for ev in resulting_brief["evidence"]]
    assert record["resulting_evidence_id"] in evidence_ids

    # Relationships in graph: materialized with USER_CONFIRMED and real evidence ID
    assert len(resulting_graph["relationships"]) == 1
    rel = resulting_graph["relationships"][0]
    assert rel["provenance"] == "USER_CONFIRMED"
    assert rel["relation_type"] == "NEAR"
    assert rel["source_space_id"] == "sn_child_room_01"
    assert rel["target_space_id"] == "sn_child_room_02"
    assert record["resulting_evidence_id"] in rel["evidence_ids"]

    # Now GET spatial graph returns version 2
    get_res2 = client.get(f"/api/v1/projects/{snapshot.project_id}/spatial/graph")
    assert get_res2.status_code == 200
    assert get_res2.json()["source_brief_version"] == 2


def test_acceptance_8_idempotent_approval_replay(tmp_path: Path) -> None:
    """Requirement 8: Approving the same proposal twice does not duplicate evidence or edges."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
    )
    client = TestClient(app)

    proposed_rel = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )

    approval_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": proposed_rel.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 1,
        "proposal_fingerprint": "fingerprint_123",
        "current_fingerprint": "fingerprint_123",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Çocuk odaları yan yana olsun.",
        "source_reference": "chat_msg_42",
        "answers_current_open_question": True,
    }

    # First approval
    res1 = client.post("/api/v1/spatial/relationships/approve", json=approval_payload)
    assert res1.status_code == 200
    data1 = res1.json()
    snapshot_v2 = data1["resulting_snapshot"]
    assert snapshot_v2["brief_version"] == 2

    # Second approval (replaying against resulting brief version 2)
    approval_payload_v2 = {
        **approval_payload,
        "brief_snapshot": snapshot_v2,
        "expected_brief_version": 2,
    }
    res2 = client.post("/api/v1/spatial/relationships/approve", json=approval_payload_v2)
    assert res2.status_code == 200
    data2 = res2.json()

    # Version should not increment further (evidence already exists, question already answered)
    assert data2["resulting_snapshot"]["brief_version"] == 2
    assert len(data2["resulting_snapshot"]["evidence"]) == len(snapshot_v2["evidence"])
    assert len(data2["resulting_spatial_graph"]["relationships"]) == 1


def test_acceptance_9_conflict_representation(tmp_path: Path) -> None:
    """Requirement 9: NEAR + SEPARATED_FROM builds successfully and contains SpatialConflict."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)

    app = create_app(
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
    )
    client = TestClient(app)

    # 1. Approve NEAR between child room 01 and living room
    rel1 = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )
    payload1 = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": rel1.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 1,
        "proposal_fingerprint": "fp_1",
        "current_fingerprint": "fp_1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Çocuk odası salona yakın olsun.",
        "source_reference": "msg_1",
    }
    res1 = client.post("/api/v1/spatial/relationships/approve", json=payload1)
    assert res1.status_code == 200
    snapshot_v2 = res1.json()["resulting_snapshot"]

    # 2. Approve SEPARATED_FROM on the same pair
    rel2 = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.SEPARATED_FROM,
        provenance=RelationshipProvenance.USER_STATED,
    )
    payload2 = {
        "brief_snapshot": snapshot_v2,
        "proposed_relationship": rel2.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 2,
        "proposal_fingerprint": "fp_2",
        "current_fingerprint": "fp_2",
        "proposal_generation_id": 2,
        "current_generation_id": 2,
        "user_message": "Aslında çocuk odası salondan uzak ve ayrışmış olmalı.",
        "source_reference": "msg_2",
    }
    res2 = client.post("/api/v1/spatial/relationships/approve", json=payload2)
    assert res2.status_code == 200
    graph_v3 = res2.json()["resulting_spatial_graph"]

    assert len(graph_v3["relationships"]) == 2
    assert len(graph_v3["conflicts"]) == 1
    conflict = graph_v3["conflicts"][0]
    assert conflict["space_a_id"] == "sn_child_room_01"
    assert conflict["space_b_id"] == "sn_living_01"
    assert set(conflict["conflicting_relation_types"]) == {"NEAR", "SEPARATED_FROM"}


def test_stale_brief_version_rejection(tmp_path: Path) -> None:
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)

    app = create_app(brief_repository=brief_repo, spatial_repository=spatial_repo)
    client = TestClient(app)

    proposed_rel = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )

    payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": proposed_rel.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 99,  # Stale expected version!
        "proposal_fingerprint": "fp_1",
        "current_fingerprint": "fp_1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Odalar yan yana olsun.",
        "source_reference": "msg_1",
    }
    res = client.post("/api/v1/spatial/relationships/approve", json=payload)
    assert res.status_code == 409
    assert "Stale brief approval" in res.json()["error"]


def test_persistence_failure_before_brief_write(tmp_path: Path) -> None:
    """Validate that graph-construction/validation failure occurs before Brief is mutated."""
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)
    assert snapshot.brief_version == 1
    assert len(snapshot.evidence) == 1

    app = create_app(brief_repository=brief_repo, spatial_repository=spatial_repo)
    client = TestClient(app)

    # Invalid proposal referencing unknown node ID
    invalid_rel = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_nonexistent_room_99",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )

    payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": invalid_rel.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 1,
        "proposal_fingerprint": "fp_1",
        "current_fingerprint": "fp_1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Bilinmeyen oda ile yakın olsun.",
        "source_reference": "msg_invalid",
        "answers_current_open_question": True,
    }

    res = client.post("/api/v1/spatial/relationships/approve", json=payload)
    assert res.status_code == 422
    assert "Unknown target space ID" in res.json()["error"]

    # Verify that Brief on disk was NOT mutated
    persisted_brief = brief_repo.get_latest(snapshot.project_id)
    assert persisted_brief is not None
    assert persisted_brief.brief_version == 1
    assert len(persisted_brief.evidence) == 1
    # Verify open question is still OPEN
    assert persisted_brief.open_questions[0].status == OpenQuestionStatus.OPEN
    # Verify no spatial graph was written
    assert spatial_repo.get_latest(snapshot.project_id) is None


def test_same_brief_version_graph_update_with_different_relationship(
    tmp_path: Path,
) -> None:
    """Test approving a new relationship when evidence exists and question is already resolved.

    BriefSnapshot is unchanged (brief_version remains same), but SpatialRelationshipGraph
    gains a DIFFERENT new relationship while retaining previous relationships.
    """
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)

    app = create_app(brief_repository=brief_repo, spatial_repository=spatial_repo)
    client = TestClient(app)

    # 1. First approval: child_01 NEAR child_02 (adds evidence, resolves open question -> version 2)
    rel1 = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_child_room_02",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )
    payload1 = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": rel1.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 1,
        "proposal_fingerprint": "fp_1",
        "current_fingerprint": "fp_1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Çocuk odaları yan yana olsun.",
        "source_reference": "chat_msg_42",
        "answers_current_open_question": True,
    }
    res1 = client.post("/api/v1/spatial/relationships/approve", json=payload1)
    assert res1.status_code == 200
    data1 = res1.json()
    snapshot_v2 = data1["resulting_snapshot"]
    assert snapshot_v2["brief_version"] == 2
    assert len(data1["resulting_spatial_graph"]["relationships"]) == 1

    # 2. Second approval on SAME brief version:
    # Uses EXACT SAME user_message and source_reference
    # (no new evidence created, question already answered)
    # But proposes a DIFFERENT new relationship: child_01 NEAR living_01
    rel2 = ProposedSpatialRelationship(
        source_space_id="sn_child_room_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_STATED,
    )
    payload2 = {
        "brief_snapshot": snapshot_v2,
        "proposed_relationship": rel2.model_dump(mode="json"),
        "current_project_id": snapshot.project_id,
        "expected_brief_version": 2,
        "proposal_fingerprint": "fp_1",
        "current_fingerprint": "fp_1",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Çocuk odaları yan yana olsun.",  # Existing message & ref
        "source_reference": "chat_msg_42",
        "answers_current_open_question": True,  # Already ANSWERED
    }
    res2 = client.post("/api/v1/spatial/relationships/approve", json=payload2)
    assert res2.status_code == 200
    data2 = res2.json()

    # BriefSnapshot is unchanged and brief_version remains 2
    assert data2["resulting_snapshot"]["brief_version"] == 2
    assert len(data2["resulting_snapshot"]["evidence"]) == len(snapshot_v2["evidence"])

    # SpatialRelationshipGraph gains the DIFFERENT new relationship (now 2 relationships total)
    graph_v2_updated = data2["resulting_spatial_graph"]
    assert graph_v2_updated["source_brief_version"] == 2
    assert len(graph_v2_updated["relationships"]) == 2
    rel_pairs = {
        (r["source_space_id"], r["target_space_id"], r["relation_type"])
        for r in graph_v2_updated["relationships"]
    }
    assert ("sn_child_room_01", "sn_child_room_02", "NEAR") in rel_pairs
    assert ("sn_child_room_01", "sn_living_01", "NEAR") in rel_pairs

    # Verify persisted graph on disk via GET
    get_res = client.get(f"/api/v1/projects/{snapshot.project_id}/spatial/graph")
    assert get_res.status_code == 200
    assert len(get_res.json()["relationships"]) == 2


def test_controlled_e2e_interpret_to_approve_spatial_relationship(
    tmp_path: Path,
) -> None:
    """Requirement 4: Full controlled E2E acceptance from interpret to approve.

    authoritative BriefSnapshot with Çocuk Odası minimum_quantity=2
    -> POST conversation/interpret
    -> proposed_spatial_relationships contains: child_01 NEAR child_02 (USER_STATED)
    -> graph still has NO authoritative edge
    -> POST spatial/relationships/approve
    -> resulting BriefSnapshot contains real CHAT evidence
    -> resulting SpatialRelationshipGraph contains NEAR, USER_CONFIRMED, evidence_id
    -> GET project spatial graph returns the persisted approved relationship
    """
    brief_repo = JSONBriefRepository(root_dir=tmp_path)
    spatial_repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    snapshot = initialize_test_brief(brief_repo)

    mock_provider = MockSpatialInterpretationProvider()
    settings = LocalLLMSettings(enabled=True, model="local-model:latest")
    app = create_app(
        settings=settings,
        provider=mock_provider,
        brief_repository=brief_repo,
        spatial_repository=spatial_repo,
    )
    client = TestClient(app)

    # 1. Interpret conversation turn
    interpret_req = ConversationRequest(
        message="Çocuk odaları birbirine yakın olsun.",
        active_context=ActiveContextSnapshot(
            project_id=snapshot.project_id,
            context_fingerprint="ctx_fp_e2e",
            generation_id=1,
        ),
        visible_entities=[],
        brief_snapshot=snapshot,
    )
    interpret_res = client.post(
        "/api/v1/conversation/interpret",
        json=interpret_req.model_dump(mode="json"),
    )
    assert interpret_res.status_code == 200
    interpret_data = interpret_res.json()
    assert interpret_data["success"] is True
    result = interpret_data["result"]

    # Verify proposed_spatial_relationships structure
    assert len(result["proposed_spatial_relationships"]) == 1
    proposed_rel = result["proposed_spatial_relationships"][0]
    assert proposed_rel["source_space_id"] == "sn_child_room_01"
    assert proposed_rel["target_space_id"] == "sn_child_room_02"
    assert proposed_rel["relation_type"] == "NEAR"
    assert proposed_rel["provenance"] == "USER_STATED"

    # 2. Verify graph still has NO authoritative edge (Requirement 7)
    get_res_before = client.get(f"/api/v1/projects/{snapshot.project_id}/spatial/graph")
    assert get_res_before.status_code == 404

    # 3. Approve proposal
    approval_payload = {
        "brief_snapshot": snapshot.model_dump(mode="json"),
        "proposed_relationship": proposed_rel,
        "current_project_id": snapshot.project_id,
        "expected_brief_version": snapshot.brief_version,
        "proposal_fingerprint": "ctx_fp_e2e",
        "current_fingerprint": "ctx_fp_e2e",
        "proposal_generation_id": 1,
        "current_generation_id": 1,
        "user_message": "Çocuk odaları birbirine yakın olsun.",
        "source_reference": "chat_msg_e2e_1",
        "answers_current_open_question": True,
    }
    approve_res = client.post(
        "/api/v1/spatial/relationships/approve",
        json=approval_payload,
    )
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["success"] is True

    # 4. Resulting brief snapshot contains real CHAT evidence
    resulting_brief = approve_data["resulting_snapshot"]
    assert resulting_brief["brief_version"] == 2
    new_evidence = [
        ev for ev in resulting_brief["evidence"] if ev["source_reference"] == "chat_msg_e2e_1"
    ]
    assert len(new_evidence) == 1
    real_evidence_id = new_evidence[0]["id"]

    # 5. Resulting SpatialRelationshipGraph contains NEAR, USER_CONFIRMED, and real evidence_id
    resulting_graph = approve_data["resulting_spatial_graph"]
    assert resulting_graph["source_brief_version"] == 2
    assert len(resulting_graph["relationships"]) == 1
    rel = resulting_graph["relationships"][0]
    assert rel["source_space_id"] == "sn_child_room_01"
    assert rel["target_space_id"] == "sn_child_room_02"
    assert rel["relation_type"] == "NEAR"
    assert rel["provenance"] == "USER_CONFIRMED"
    assert real_evidence_id in rel["evidence_ids"]

    # 6. GET project spatial graph returns the persisted approved relationship
    get_res_after = client.get(f"/api/v1/projects/{snapshot.project_id}/spatial/graph")
    assert get_res_after.status_code == 200
    persisted_graph = get_res_after.json()
    assert persisted_graph["source_brief_version"] == 2
    assert len(persisted_graph["relationships"]) == 1
    assert persisted_graph["relationships"][0]["relation_type"] == "NEAR"
    assert persisted_graph["relationships"][0]["provenance"] == "USER_CONFIRMED"
