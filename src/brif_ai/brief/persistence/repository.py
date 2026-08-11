"""BRIF.AI — Brief Repository Protocol Definition."""

from __future__ import annotations

from typing import Protocol

from brif_ai.brief.models.snapshot import BriefSnapshot


class BriefRepository(Protocol):
    """Abstract protocol for BriefSnapshot persistence storage."""

    def get_latest(self, project_id: str) -> BriefSnapshot | None:
        """Retrieve the latest persisted BriefSnapshot for a project."""
        ...

    def save(self, snapshot: BriefSnapshot) -> BriefSnapshot:
        """Persist a BriefSnapshot.

        Writes the version file and updates latest pointer. Returns the saved snapshot.
        """
        ...

    def get_version(
        self,
        project_id: str,
        brief_version: int,
    ) -> BriefSnapshot | None:
        """Retrieve a specific historical BriefSnapshot version for a project."""
        ...

    def list_versions(self, project_id: str) -> list[int]:
        """Return a sorted list of all persisted brief version numbers for a project."""
        ...
