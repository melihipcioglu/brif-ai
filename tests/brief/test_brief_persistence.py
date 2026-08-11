"""BRIF.AI — Comprehensive Tests for Brief Persistence V0."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from brif_ai.brief.models.common import BriefItemKind, Priority
from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
)
from brif_ai.brief.persistence.errors import (
    BriefNotFoundError,
    BriefPersistenceError,
    BriefVersionConflictError,
    InvalidProjectIdError,
)
from brif_ai.brief.persistence.json_repository import JSONBriefRepository
from brif_ai.brief.service import PersistentBriefService


def sample_snapshot(project_id: str = "proj_house_2story", version: int = 1) -> BriefSnapshot:
    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=version,
        created_at=datetime.now(timezone.utc),  # noqa: UP017
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


def test_initialize_and_load_brief(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)
    snap = sample_snapshot("proj_house_2story", 1)

    initialized = service.initialize_brief("proj_house_2story", snap)
    assert initialized.brief_version == 1

    loaded = service.get_latest_brief("proj_house_2story")
    assert loaded is not None
    assert loaded.project_id == "proj_house_2story"
    assert loaded.brief_version == 1


def test_uninitialized_project_approval_returns_404(tmp_path: Path) -> None:
    """Regression test: Approval on uninitialized project raises BriefNotFoundError."""
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)

    mutation = ProposedBriefMutation(
        mutation_id="mut_uninit",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test statement",
            priority=Priority.MUST,
        ),
    )

    with pytest.raises(BriefNotFoundError, match="is not initialized"):
        service.record_brief_mutation_approval(
            current_project_id="proj_house_2story",
            expected_brief_version=1,
            proposed_mutation=mutation,
            user_message="Test message",
        )

    # Repository remains empty
    assert repo.get_latest("proj_house_2story") is None
    assert repo.list_versions("proj_house_2story") == []


def test_approve_mutation_persists_version_n_plus_1(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)
    snap = sample_snapshot("proj_house_2story", 1)
    service.initialize_brief("proj_house_2story", snap)

    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Teras ve salon doğrudan bağlantılı olsun.",
            priority=Priority.MUST,
        ),
    )

    new_snap = service.record_brief_mutation_approval(
        current_project_id="proj_house_2story",
        expected_brief_version=1,
        proposed_mutation=mutation,
        user_message="Teras salona bağlansın.",
        source_reference="chatmsg_01",
    )

    assert new_snap.brief_version == 2
    assert len(new_snap.brief_items) == 1

    # Reload from separate repository instance backed by same directory
    repo2 = JSONBriefRepository(tmp_path)
    service2 = PersistentBriefService(repo2)
    loaded = service2.get_latest_brief("proj_house_2story")
    assert loaded is not None
    assert loaded.brief_version == 2
    assert len(loaded.brief_items) == 1


def test_version_history_retained(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)
    service.initialize_brief("proj_house_2story", sample_snapshot("proj_house_2story", 1))

    for i in range(1, 4):
        mutation = ProposedBriefMutation(
            mutation_id=f"mut_{i}",
            mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
            brief_item=BriefItemProposalPayload(
                kind=BriefItemKind.NEED,
                normalized_statement=f"Gereksinim {i}",
                priority=Priority.MUST,
            ),
        )
        service.record_brief_mutation_approval(
            current_project_id="proj_house_2story",
            expected_brief_version=i,
            proposed_mutation=mutation,
            user_message=f"Gereksinim {i}",
            source_reference=f"ref_{i}",
        )

    versions = service.list_brief_versions("proj_house_2story")
    assert versions == [1, 2, 3, 4]

    v2 = service.get_brief_version("proj_house_2story", 2)
    assert v2 is not None
    assert v2.brief_version == 2
    assert len(v2.brief_items) == 1


def test_project_isolation(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)

    service.initialize_brief("proj_house", sample_snapshot("proj_house", 1))
    service.initialize_brief("proj_tower", sample_snapshot("proj_tower", 1))

    house_snap = service.get_latest_brief("proj_house")
    tower_snap = service.get_latest_brief("proj_tower")

    assert house_snap is not None and house_snap.project_id == "proj_house"
    assert tower_snap is not None and tower_snap.project_id == "proj_tower"


def test_stale_expected_version_rejected(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    service = PersistentBriefService(repo)
    service.initialize_brief("proj_house_2story", sample_snapshot("proj_house_2story", 1))

    mutation = ProposedBriefMutation(
        mutation_id="mut_stale",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test",
            priority=Priority.MUST,
        ),
    )

    with pytest.raises(BriefVersionConflictError, match="Stale brief approval"):
        service.record_brief_mutation_approval(
            current_project_id="proj_house_2story",
            expected_brief_version=99,  # Mismatched expected version!
            proposed_mutation=mutation,
            user_message="Test",
        )


def test_path_traversal_rejected(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)

    bad_ids = ["../foo", "../../foo", "foo/bar", "foo\\bar", "/etc/passwd", "C:\\Windows"]
    for bad_id in bad_ids:
        with pytest.raises(InvalidProjectIdError):
            repo.get_latest(bad_id)

        bad_snap = BriefSnapshot.model_construct(
            project_id=bad_id,
            schema_version="brief.v0",
            brief_version=1,
            created_at=datetime.now(timezone.utc),  # noqa: UP017
            stakeholders=[],
            evidence=[],
            brief_items=[],
            space_requests=[],
            usage_scenarios=[],
            contradictions=[],
            open_questions=[],
        )
        with pytest.raises(InvalidProjectIdError):
            repo.save(bad_snap)


def test_same_version_different_content_rejected(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    snap1 = sample_snapshot("proj_house_2story", 1)
    repo.save(snap1)

    # Different snapshot for same version
    snap2 = snap1.model_copy(update={"schema_version": "brief.v1_different"})
    with pytest.raises(BriefVersionConflictError):
        repo.save(snap2)


def test_latest_and_version_inconsistency_fails_safely(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    snap = sample_snapshot("proj_house_2story", 1)
    repo.save(snap)

    # Corrupt latest.json by modifying its version content
    latest_file = tmp_path / "projects" / "proj_house_2story" / "brief" / "latest.json"
    with open(latest_file, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["schema_version"] = "corrupted_version"
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    with pytest.raises(BriefPersistenceError, match="Inconsistency detected"):
        repo.get_latest("proj_house_2story")


def test_caller_owned_snapshot_is_not_mutated(tmp_path: Path) -> None:
    repo = JSONBriefRepository(tmp_path)
    snap = sample_snapshot("proj_house_2story", 1)
    orig_dict = snap.model_dump(mode="python")

    saved = repo.save(snap)
    assert snap.model_dump(mode="python") == orig_dict
    assert saved is not snap


def test_brief_domain_has_zero_llm_imports() -> None:
    """Architectural boundary test: src/brif_ai/brief package contains zero imports from llm."""
    brief_dir = Path(__file__).parents[2] / "src" / "brif_ai" / "brief"
    assert brief_dir.exists()

    for py_file in brief_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        assert "brif_ai.llm" not in text, f"Illegal import from brif_ai.llm in {py_file}"
