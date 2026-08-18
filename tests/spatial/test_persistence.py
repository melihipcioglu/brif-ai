"""Unit tests for JSONSpatialRelationshipRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from brif_ai.core.models.common import SpaceFunction
from brif_ai.spatial.models import (
    RelationshipProvenance,
    SpatialNode,
    SpatialRelationship,
    SpatialRelationshipGraph,
    SpatialRelationType,
)
from brif_ai.spatial.persistence import (
    JSONSpatialRelationshipRepository,
    SpatialGraphPersistenceError,
)


def sample_graph(project_id: str = "proj_01", version: int = 1) -> SpatialRelationshipGraph:
    node1 = SpatialNode(
        id="sn_living_01",
        display_name="Salon",
        function=SpaceFunction.LIVING,
        source_space_request_id="sr_living",
        instance_index=1,
    )
    node2 = SpatialNode(
        id="sn_kitchen_01",
        display_name="Mutfak",
        function=SpaceFunction.COOKING,
        source_space_request_id="sr_kitchen",
        instance_index=1,
    )
    rel = SpatialRelationship(
        id="srel_test1",
        source_space_id="sn_kitchen_01",
        target_space_id="sn_living_01",
        relation_type=SpatialRelationType.NEAR,
        provenance=RelationshipProvenance.USER_CONFIRMED,
        evidence_ids=["ev_1"],
    )
    return SpatialRelationshipGraph(
        project_id=project_id,
        source_brief_version=version,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        nodes=[node1, node2],
        relationships=[rel],
        unconstrained_pairs=[],
        conflicts=[],
    )


def test_json_spatial_repository_save_and_retrieve(tmp_path: Path) -> None:
    repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    graph = sample_graph("proj_alpha", 2)

    saved = repo.save(graph)
    assert saved.project_id == "proj_alpha"
    assert saved.source_brief_version == 2

    # Retrieve latest
    latest = repo.get_latest("proj_alpha")
    assert latest is not None
    assert latest.project_id == "proj_alpha"
    assert latest.source_brief_version == 2
    assert len(latest.relationships) == 1

    # Retrieve specific version
    v2 = repo.get_version("proj_alpha", 2)
    assert v2 is not None
    assert v2.source_brief_version == 2

    # Retrieve non-existent
    assert repo.get_version("proj_alpha", 99) is None
    assert repo.get_latest("proj_nonexistent") is None

    # List versions
    assert repo.list_versions("proj_alpha") == [2]


def test_json_spatial_repository_same_version_atomic_update(tmp_path: Path) -> None:
    repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    graph_v1 = sample_graph("proj_beta", 1)
    repo.save(graph_v1)

    # Re-saving identical content is idempotent
    repo.save(graph_v1)
    assert repo.get_latest("proj_beta") is not None
    assert len(repo.get_latest("proj_beta").relationships) == 1  # type: ignore[union-attr]

    # Updating the spatial graph for version 1 with an additional relationship updates atomically
    node1 = SpatialNode(
        id="sn_bed_01",
        display_name="Yatak Odası",
        function=SpaceFunction.SLEEPING,
        source_space_request_id="sr_bed",
        instance_index=1,
    )
    updated_v1 = SpatialRelationshipGraph(
        project_id="proj_beta",
        source_brief_version=1,
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        nodes=[*graph_v1.nodes, node1],
        relationships=graph_v1.relationships,
        unconstrained_pairs=[],
        conflicts=[],
    )
    repo.save(updated_v1)
    latest = repo.get_latest("proj_beta")
    assert latest is not None
    assert len(latest.nodes) == 3


def test_json_spatial_repository_rejects_invalid_project_id(tmp_path: Path) -> None:
    repo = JSONSpatialRelationshipRepository(root_dir=tmp_path)
    with pytest.raises(SpatialGraphPersistenceError):
        repo.get_latest("../malicious_traversal")
