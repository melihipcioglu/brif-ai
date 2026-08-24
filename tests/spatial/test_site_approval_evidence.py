"""Tests for persistent site approval evidence repository."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from brif_ai.brief.models.common import EvidenceSource
from brif_ai.spatial.site.approval_evidence import (
    SiteApprovalEvidenceRepository,
    SiteEvidencePersistenceError,
    _generate_site_evidence_id,
)


def test_generate_site_evidence_id_deterministic() -> None:
    id1 = _generate_site_evidence_id("proj_1", "ref_1", "user message text")
    id2 = _generate_site_evidence_id("proj_1", "ref_1", "user message text")
    id3 = _generate_site_evidence_id("proj_1", "ref_2", "user message text")

    assert id1 == id2
    assert id1.startswith("ev_")
    assert id1 != id3


def test_site_approval_evidence_persistence_and_reload(tmp_path: Path) -> None:
    repo1 = SiteApprovalEvidenceRepository(root_dir=tmp_path)
    ev1 = repo1.save_site_evidence(
        project_id="proj_1",
        source_reference="user_msg_01",
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
    )

    assert ev1.id.startswith("ev_")
    assert ev1.source_type == EvidenceSource.CHAT
    assert ev1.source_reference == "user_msg_01"
    assert ev1.excerpt == "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)"

    # Create fresh repository instance from same root_dir (simulating process restart)
    repo2 = SiteApprovalEvidenceRepository(root_dir=tmp_path)
    reloaded = repo2.get_evidence("proj_1", ev1.id)
    assert reloaded is not None
    assert reloaded.id == ev1.id
    assert reloaded.excerpt == ev1.excerpt

    # Re-saving identical content reuses existing record
    ev2 = repo2.save_site_evidence(
        project_id="proj_1",
        source_reference="user_msg_01",
        user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
    )
    assert ev2.id == ev1.id
    assert len(repo2.list_evidence("proj_1")) == 1


@pytest.mark.parametrize(
    "invalid_pid",
    [
        "",
        "   ",
        "../other",
        "..\\other",
        "project/other",
        "project\\other",
        "proj/../traversal",
        "proj\\..\\traversal",
        "project:name",
        "project*name",
        "project?name",
        "project<name",
        "project>name",
        "project|name",
        "project name",
    ],
)
def test_site_approval_evidence_rejects_path_traversal_and_invalid_project_ids(
    tmp_path: Path, invalid_pid: str
) -> None:
    repo = SiteApprovalEvidenceRepository(root_dir=tmp_path)
    with pytest.raises(SiteEvidencePersistenceError):
        repo.save_site_evidence(
            project_id=invalid_pid,
            source_reference="msg_01",
            user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        )

    with pytest.raises(SiteEvidencePersistenceError):
        repo.list_evidence(invalid_pid)

    with pytest.raises(SiteEvidencePersistenceError):
        repo.get_evidence(invalid_pid, "ev_test")

    # Assert no file or directory was created outside tmp_path / "projects"
    projects_dir = tmp_path / "projects"
    if projects_dir.exists():
        for item in projects_dir.rglob("*"):
            # All items must be within projects_dir
            assert str(item.resolve()).startswith(str(projects_dir.resolve()))


def test_atomic_write_does_not_leave_temp_files_on_failure(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo = SiteApprovalEvidenceRepository(root_dir=tmp_path)

    # Monkeypatch os.replace to simulate sudden failure
    def _mock_replace(
        src: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        dst: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> None:
        raise OSError("Simulated disk error during atomic replace")

    monkeypatch.setattr("os.replace", _mock_replace)

    with pytest.raises(SiteEvidencePersistenceError, match="Simulated disk error"):
        repo.save_site_evidence(
            project_id="proj_atomic_test",
            source_reference="msg_01",
            user_message="Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
        )

    # Verify no dangling tmp files left behind in site dir
    site_dir = tmp_path / "projects" / "proj_atomic_test" / "site"
    if site_dir.exists():
        tmp_files = list(site_dir.glob("tmp_site_ev_*"))
        assert len(tmp_files) == 0
