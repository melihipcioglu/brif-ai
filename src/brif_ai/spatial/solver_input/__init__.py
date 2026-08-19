"""BRIF.AI Layout Solver Input Set Domain Package."""

from __future__ import annotations

from brif_ai.spatial.solver_input.assembler import LayoutSolverInputAssembler
from brif_ai.spatial.solver_input.errors import (
    SolverInputAuthorityMismatchError,
    SolverInputBriefVersionMismatchError,
    SolverInputError,
    SolverInputMissingBuildableEnvelopeError,
    SolverInputMissingInputError,
    SolverInputNonAuthoritativeBuildableEnvelopeError,
    SolverInputProjectMismatchError,
    SolverInputSchemaVersionMismatchError,
    SolverInputSpaceMismatchError,
)
from brif_ai.spatial.solver_input.models import (
    LayoutSolverInputSet,
    SolverSpaceMetricRequirements,
)

__all__ = [
    "LayoutSolverInputAssembler",
    "LayoutSolverInputSet",
    "SolverInputAuthorityMismatchError",
    "SolverInputBriefVersionMismatchError",
    "SolverInputError",
    "SolverInputMissingBuildableEnvelopeError",
    "SolverInputMissingInputError",
    "SolverInputNonAuthoritativeBuildableEnvelopeError",
    "SolverInputProjectMismatchError",
    "SolverInputSchemaVersionMismatchError",
    "SolverInputSpaceMismatchError",
    "SolverSpaceMetricRequirements",
]
