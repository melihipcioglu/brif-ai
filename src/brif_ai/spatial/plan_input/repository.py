"""Abstract repository interface for AuthoritativePlanInputState persistence."""

from __future__ import annotations

from typing import Protocol

from brif_ai.spatial.plan_input.models import AuthoritativePlanInputState


class PlanInputStateRepository(Protocol):
    """Storage repository interface for AuthoritativePlanInputState."""

    def get_latest(self, project_id: str) -> AuthoritativePlanInputState | None:
        """Retrieve the latest plan input state for project_id or None if not found."""
        ...

    def get_version(
        self, project_id: str, state_version: int
    ) -> AuthoritativePlanInputState | None:
        """Retrieve a specific state_version plan input state for project_id or None."""
        ...

    def list_versions(self, project_id: str) -> list[int]:
        """List all available state_version numbers for project_id in ascending order."""
        ...

    def save(self, state: AuthoritativePlanInputState) -> AuthoritativePlanInputState:
        """Persist an AuthoritativePlanInputState deterministically."""
        ...
