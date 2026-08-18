"""Unit tests for PersistentSpatialService."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from brif_ai.brief.models.common import ConfirmationStatus, EvidenceSource, Priority
from brif_ai.brief.models.snapshot import BriefSnapshot, Evidence, SpaceRequest, Stakeholder
from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialRelationshipInput,
    SpatialRelationType,
)
from brif_ai.spatial.persistence import JSONSpatialRelationshipRepository
from brif_ai.spatial.service import PersistentSpatialService


def make_snapshot(version: int = 1) -> BriefSnapshot:
    return BriefSnapshot(
        project_id="proj_service_test",
        schema_version="brief.v0",
        brief_version=version,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        stakeholders=[
            Stakeholder(id="stk_1", display_name="Müşteri", role="CLIENT_OWNER", active=True)
        ],
        evidence=[
            Evidence(
                id="ev_chat_1",
                source_type=EvidenceSource.CHAT,
                source_reference="chat_1",
                excerpt="Mutfak salona bitişik olsun.",
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
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
            SpaceRequest(
                id="sr_kitchen",
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
                minimum_quantity=1,
                mandatory=True,
                stakeholder_ids=["stk_1"],
                evidence_ids=["ev_chat_1"],
                confirmation_status=ConfirmationStatus.CONFIRMED,
            ),
        ],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


def test_persistent_spatial_service_baseline_and_approval(tmp_path: Path) -> None:
    repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    service = PersistentSpatialService(repository=repo)

    snapshot_v1 = make_snapshot(version=1)

    # 1. Baseline creation
    graph_v1 = service.get_or_create_baseline_graph(snapshot_v1)
    assert graph_v1.project_id == "proj_service_test"
    assert graph_v1.source_brief_version == 1
    assert len(graph_v1.nodes) == 2
    assert graph_v1.relationships == []
    assert len(graph_v1.unconstrained_pairs) == 1

    # 2. In-memory updated graph construction
    rel_input = SpatialRelationshipInput(
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.ADJACENT_TO,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        priority=Priority.MUST,
        evidence_ids=["ev_chat_1"],
    )

    snapshot_v2 = snapshot_v1.model_copy(update={"brief_version": 2})
    graph_v2 = service.build_updated_graph_in_memory(
        snapshot=snapshot_v2,
        existing_graph=graph_v1,
        new_relationship=rel_input,
    )

    assert graph_v2.source_brief_version == 2
    assert len(graph_v2.relationships) == 1
    assert graph_v2.relationships[0].provenance == RelationshipProvenance.USER_CONFIRMED
    assert graph_v2.relationships[0].relation_type == SpatialRelationType.ADJACENT_TO

    # 3. Persist graph v2
    saved_v2 = service.save_graph(graph_v2)
    assert saved_v2.source_brief_version == 2

    # Latest should now be v2
    latest = service.get_latest_graph("proj_service_test")
    assert latest is not None
    assert latest.source_brief_version == 2
    assert len(latest.relationships) == 1
