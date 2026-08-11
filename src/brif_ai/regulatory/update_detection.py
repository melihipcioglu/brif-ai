"""BRIF.AI — Regulatory Change Detection & Update Candidate Foundation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from pydantic import Field

from brif_ai.regulatory.models import StrictRegulatoryModel, VerificationStatus


class RegulatorySourceSnapshot(StrictRegulatoryModel):
    """Snapshot of a fetched regulatory web or document source."""

    source_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    content_sha256: str = Field(min_length=1)
    retrieved_at: datetime
    version_label: str | None = None


class RegulatoryUpdateCandidate(StrictRegulatoryModel):
    """Informational candidate generated when a regulatory source document changes.

    CRITICAL ARCHITECTURAL RULE:
    An update candidate is strictly informational and NEVER modifies an active
    binding RegulatoryRuleSet until explicit legal/human verification occurs.
    """

    candidate_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    official_url: str = Field(min_length=1)
    old_content_sha256: str | None = None
    new_content_sha256: str = Field(min_length=1)
    detected_at: datetime
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: str | None = None


class RegulatorySourceFetcher(Protocol):
    """Protocol for fetching official regulatory document snapshots."""

    async def fetch_snapshot(self, source_id: str, url: str) -> RegulatorySourceSnapshot:
        """Fetch regulatory source document snapshot."""
        ...


class RegulatoryChangeDetector:
    """Detects changes between official source snapshots and creates audit candidates."""

    def compare_snapshots(
        self,
        source_id: str,
        official_url: str,
        previous_snapshot: RegulatorySourceSnapshot | None,
        current_snapshot: RegulatorySourceSnapshot,
        detected_at: datetime | None = None,
    ) -> RegulatoryUpdateCandidate | None:
        """Compare current and previous snapshots. Returns update candidate if content changed."""
        now = detected_at or datetime.now(timezone.utc)  # noqa: UP017
        if previous_snapshot is None:
            # First ingestion candidate
            return RegulatoryUpdateCandidate(
                candidate_id=f"cand_{source_id}_{current_snapshot.content_sha256[:8]}",
                source_id=source_id,
                official_url=official_url,
                old_content_sha256=None,
                new_content_sha256=current_snapshot.content_sha256,
                detected_at=now,
                verification_status=VerificationStatus.UNVERIFIED,
                notes="Initial document snapshot detected.",
            )

        if previous_snapshot.content_sha256 != current_snapshot.content_sha256:
            return RegulatoryUpdateCandidate(
                candidate_id=f"cand_{source_id}_{current_snapshot.content_sha256[:8]}",
                source_id=source_id,
                official_url=official_url,
                old_content_sha256=previous_snapshot.content_sha256,
                new_content_sha256=current_snapshot.content_sha256,
                detected_at=now,
                verification_status=VerificationStatus.UNVERIFIED,
                notes="Document content SHA256 change detected.",
            )

        return None
