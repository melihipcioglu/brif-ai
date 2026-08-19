"""Deterministic compiler converting SchematicLayoutProblem into SolverDirectiveSet V0."""

from __future__ import annotations

from datetime import datetime

from brif_ai.spatial.layout.models import SchematicLayoutProblem
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.solver_policy.errors import (
    SolverPolicyEndpointError,
    SolverPolicyMissingInputError,
    SolverPolicySchemaVersionMismatchError,
)
from brif_ai.spatial.solver_policy.models import (
    SolverDirective,
    SolverDirectiveSet,
    map_priority_to_enforcement,
    map_relation_type_to_operator,
)


class SolverPolicyCompiler:
    """Deterministic compiler creating SolverDirectiveSet from SchematicLayoutProblem.

    ARCHITECTURAL INVARIANTS:
    1. Deterministic compilation: Given identical SchematicLayoutProblem input,
       produces reproducible, byte-for-byte equivalent serialized output.
       By default, created_at reuses problem.created_at (zero datetime.now() nondeterminism).
    2. Authority segregation: ONLY authoritative_constraints produce SolverDirective records.
       informational_relationships are strictly excluded from the solver-facing directive set.
    3. Total policy mapping:
       - Priority -> ConstraintEnforcement (MUST->REQUIRED, SHOULD->PREFERRED, etc.)
       - SpatialRelationType -> SolverRelationOperator (ADJACENT_TO->ADJACENCY, etc.)
    4. Epistemic preservation: Provenance remains USER_CONFIRMED on all solver directives.
    5. Zero geometry / zero weights: Introduces zero numeric weights, penalty scores,
       distance thresholds, or geometric dimensions.
    """

    def compile(
        self,
        problem: SchematicLayoutProblem,
        *,
        created_at: datetime | None = None,
    ) -> SolverDirectiveSet:
        """Compile a SchematicLayoutProblem into a SolverDirectiveSet deterministically."""
        if problem is None:
            raise SolverPolicyMissingInputError("SchematicLayoutProblem is required.")

        # 1. Strict schema version validation
        if problem.schema_version != "schematic_layout_problem.v0":
            raise SolverPolicySchemaVersionMismatchError(
                expected_schema="schematic_layout_problem.v0",
                actual_schema=str(problem.schema_version),
            )

        # 2. Materialize spaces deterministically
        spaces = sorted(problem.spaces, key=lambda s: s.id)
        space_id_set = {s.id for s in spaces}

        # 3. Transform authoritative constraints to solver directives
        directives: list[SolverDirective] = []
        for constraint in sorted(problem.authoritative_constraints, key=lambda c: c.id):
            if (
                constraint.source_space_id not in space_id_set
                or constraint.target_space_id not in space_id_set
            ):
                raise SolverPolicyEndpointError(
                    f"Constraint {constraint.id!r} references unknown space endpoint "
                    f"(source={constraint.source_space_id!r}, "
                    f"target={constraint.target_space_id!r})."
                )

            directives.append(
                SolverDirective(
                    id=constraint.id,
                    source_constraint_id=constraint.id,
                    source_space_id=constraint.source_space_id,
                    target_space_id=constraint.target_space_id,
                    source_relation_type=constraint.relation_type,
                    operator=map_relation_type_to_operator(constraint.relation_type),
                    enforcement=map_priority_to_enforcement(constraint.priority),
                    priority=constraint.priority,
                    provenance=RelationshipProvenance.USER_CONFIRMED,
                    evidence_ids=sorted(constraint.evidence_ids),
                    rationale=constraint.rationale,
                    bidirectional=constraint.bidirectional,
                )
            )

        # 4. Sort and validate unconstrained pairs
        unconstrained_pairs = sorted(
            problem.unconstrained_pairs,
            key=lambda p: (p.space_a_id, p.space_b_id),
        )
        for pair in unconstrained_pairs:
            if pair.space_a_id not in space_id_set or pair.space_b_id not in space_id_set:
                raise SolverPolicyEndpointError(
                    f"Unconstrained pair references unknown space endpoint "
                    f"(space_a={pair.space_a_id!r}, space_b={pair.space_b_id!r})."
                )

        # 5. Timestamp determinism
        ts = created_at if created_at is not None else problem.created_at

        return SolverDirectiveSet(
            schema_version="solver_directive_set.v0",
            project_id=problem.project_id,
            source_brief_version=problem.source_brief_version,
            source_layout_problem_schema_version="schematic_layout_problem.v0",
            created_at=ts,
            spaces=spaces,
            directives=directives,
            unconstrained_pairs=unconstrained_pairs,
        )
