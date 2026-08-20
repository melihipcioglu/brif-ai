"""Domain exceptions for Authoritative Plan Input State V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class PlanInputStateError(SpatialGraphError):
    """Base exception for all plan input state and persistence errors."""


class PlanInputStateNotFoundError(PlanInputStateError):
    """Raised when a plan input state for a project is not found."""


class PlanInputStateVersionConflictError(PlanInputStateError):
    """Raised when an expected state version conflicts with the stored state version."""


class PlanInputStateProjectMismatchError(PlanInputStateError):
    """Raised when source artifacts belong to a different project ID."""


class PlanInputStateBriefVersionMismatchError(PlanInputStateError):
    """Raised when source artifacts belong to a different source brief version."""


class PlanInputStateValidationError(PlanInputStateError):
    """Raised when plan input state invariants are violated."""


class PlanInputStatePersistenceError(PlanInputStateError):
    """Raised when a persistence or I/O failure occurs while managing plan input state."""
