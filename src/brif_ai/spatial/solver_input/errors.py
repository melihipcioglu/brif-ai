"""Domain exceptions for BRIF.AI Layout Solver Input Set V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class SolverInputError(SpatialGraphError):
    """Base exception for all layout solver input assembly errors."""


class SolverInputMissingInputError(SolverInputError):
    """Raised when any required source contract is None."""


class SolverInputSchemaVersionMismatchError(SolverInputError):
    """Raised when any source contract schema version is incompatible."""


class SolverInputProjectMismatchError(SolverInputError):
    """Raised when source contracts belong to different project IDs."""


class SolverInputBriefVersionMismatchError(SolverInputError):
    """Raised when source contracts belong to different brief versions."""


class SolverInputSpaceMismatchError(SolverInputError):
    """Raised when space identities differ between source contracts or violate V0 identity.

    Invariants: LayoutSpace.id must equal source_program_space_id.
    """


class SolverInputMissingBuildableEnvelopeError(SolverInputError):
    """Raised when the site envelope does not contain a buildable envelope."""


class SolverInputNonAuthoritativeBuildableEnvelopeError(SolverInputError):
    """Raised when the buildable envelope is not USER_CONFIRMED or authoritative."""


class SolverInputAuthorityMismatchError(SolverInputError):
    """Raised when non-authoritative items are encountered where authoritative data is required."""
