"""Tests for immutable conversational plan-input approval evidence."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from brif_ai.brief.models.common import EvidenceSource
from brif_ai.spatial.plan_input.approval_evidence import (
    PlanInputApprovalEvidenceRepository,
    generate_plan_input_approval_evidence_id,
)


def test_same_source_content_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    repository = PlanInputApprovalEvidenceRepository(root_dir=tmp_path)
    first_time = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    second_time = first_time + timedelta(hours=1)

    first = repository.save_chat_evidence(
        project_id="proj_metric_revision",
        source_reference="chatmsg_17",
        user_message="Salonu en az 35 m² yap.",
        created_at=first_time,
    )
    replay = repository.save_chat_evidence(
        project_id="proj_metric_revision",
        source_reference="chatmsg_17",
        user_message="Salonu en az 35 m² yap.",
        created_at=second_time,
    )

    assert first == replay
    assert replay.created_at == first_time
    assert replay.source_type == EvidenceSource.CHAT
    assert replay.source_reference == "chatmsg_17"
    assert replay.user_message == "Salonu en az 35 m² yap."
    assert repository.list_evidence("proj_metric_revision") == [first]
    assert first.id == generate_plan_input_approval_evidence_id(
        "proj_metric_revision",
        "chatmsg_17",
        "Salonu en az 35 m² yap.",
    )


def test_changed_source_content_creates_distinct_immutable_evidence(tmp_path: Path) -> None:
    repository = PlanInputApprovalEvidenceRepository(root_dir=tmp_path)
    timestamp = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)

    first = repository.save_chat_evidence(
        project_id="proj_metric_revision",
        source_reference="chatmsg_17",
        user_message="Salonu en az 35 m² yap.",
        created_at=timestamp,
    )
    second = repository.save_chat_evidence(
        project_id="proj_metric_revision",
        source_reference="chatmsg_18",
        user_message="Salon minimum 35 m² olsun.",
        created_at=timestamp,
    )

    assert first.id != second.id
    assert repository.get_evidence("proj_metric_revision", first.id) == first
    assert repository.get_evidence("proj_metric_revision", second.id) == second
    assert len(repository.list_evidence("proj_metric_revision")) == 2


def test_concurrent_same_content_publication_has_one_record(tmp_path: Path) -> None:
    repository = PlanInputApprovalEvidenceRepository(root_dir=tmp_path)
    timestamp = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)

    def publish() -> str:
        return repository.save_chat_evidence(
            project_id="proj_metric_revision",
            source_reference="chatmsg_17",
            user_message="Salonu en az 35 m² yap.",
            created_at=timestamp,
        ).id

    with ThreadPoolExecutor(max_workers=8) as executor:
        evidence_ids = list(executor.map(lambda _: publish(), range(16)))

    assert len(set(evidence_ids)) == 1
    assert len(repository.list_evidence("proj_metric_revision")) == 1
