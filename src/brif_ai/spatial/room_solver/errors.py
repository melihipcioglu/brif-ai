"""Typed domain exceptions for BRIF.AI Room Geometry Solver V0."""

from __future__ import annotations

from brif_ai.spatial.errors import SpatialGraphError


class RoomGeometrySolverError(SpatialGraphError):
    """Base class for all Room Geometry Solver V0 domain errors."""


class RoomGeometryInputMismatchError(RoomGeometrySolverError):
    """Raised when cross-contract metadata (project_id, brief_version, etc.) mismatch."""


class RoomGeometryUnsupportedFloorPlateError(RoomGeometrySolverError):
    """Raised when the FloorPlate is non-rectangular or concave (solver capability gate)."""


class RoomGeometryUnsupportedOptionalSpaceError(RoomGeometrySolverError):
    """Raised when an optional space (mandatory=False) is encountered in V0."""


class RoomGeometryUnsupportedMetricError(RoomGeometrySolverError):
    """Raised when unsupported metric semantics (e.g. TARGET_AREA or not MUST) are passed."""


class RoomGeometryUnsupportedDirectiveError(RoomGeometrySolverError):
    """Raised when unsupported directive operators/enforcements (e.g. PROXIMITY) are passed."""


class RoomGeometryUnderconstrainedSpaceError(RoomGeometrySolverError):
    """Raised when a space lacks a mandatory hard MIN_AREA requirement."""


class RoomGeometryGridAlignmentError(RoomGeometrySolverError):
    """Raised when the FloorPlate dimensions are not an exact integer multiple of grid_step_m."""


class RoomGeometryInfeasibleError(RoomGeometrySolverError):
    """Raised when CP-SAT proves that the layout problem is mathematically INFEASIBLE."""


class RoomGeometryEngineError(RoomGeometrySolverError):
    """Raised when CP-SAT returns MODEL_INVALID, search timeout, or an unknown solver state."""
