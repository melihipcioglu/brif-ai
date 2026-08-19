"""Deterministic Layout Solver Input Assembler for BRIF.AI."""

from __future__ import annotations

from datetime import datetime, timedelta

from brif_ai.spatial.metrics.models import MetricSpatialRequirements
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.site.models import SiteBuildableEnvelope, SiteGeometryRole
from brif_ai.spatial.solver_input.errors import (
    SolverInputBriefVersionMismatchError,
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
from brif_ai.spatial.solver_policy.models import SolverDirectiveSet


class LayoutSolverInputAssembler:
    """Deterministic assembler that integrates three authoritative spatial contracts.

    Combines:
    1. SolverDirectiveSet V0 (authoritative relational directives)
    2. MetricSpatialRequirements V0 (authoritative space metric requirements)
    3. SiteBuildableEnvelope V0 (authoritative site buildable envelope)

    Ensures strict cross-source consistency, authority filtering, and deterministic
    canonical ordering without running a solver or creating layout geometry.
    """

    @classmethod
    def assemble(
        cls,
        directive_set: SolverDirectiveSet,
        metric_requirements: MetricSpatialRequirements,
        site_envelope: SiteBuildableEnvelope,
        *,
        created_at: datetime | None = None,
    ) -> LayoutSolverInputSet:
        # 1. Check missing inputs
        if directive_set is None:
            raise SolverInputMissingInputError("directive_set must not be None.")
        if metric_requirements is None:
            raise SolverInputMissingInputError("metric_requirements must not be None.")
        if site_envelope is None:
            raise SolverInputMissingInputError("site_envelope must not be None.")

        # 2. Strict schema version checks
        if directive_set.schema_version != "solver_directive_set.v0":
            raise SolverInputSchemaVersionMismatchError(
                f"Unsupported directive_set schema_version: {directive_set.schema_version!r} "
                f"(expected 'solver_directive_set.v0')."
            )
        if metric_requirements.schema_version != "metric_spatial_requirements.v0":
            raise SolverInputSchemaVersionMismatchError(
                f"Unsupported metric_requirements schema_version: "
                f"{metric_requirements.schema_version!r} "
                f"(expected 'metric_spatial_requirements.v0')."
            )
        if site_envelope.schema_version != "site_buildable_envelope.v0":
            raise SolverInputSchemaVersionMismatchError(
                f"Unsupported site_envelope schema_version: {site_envelope.schema_version!r} "
                f"(expected 'site_buildable_envelope.v0')."
            )

        # 3. Project ID consistency
        if (
            directive_set.project_id != metric_requirements.project_id
            or directive_set.project_id != site_envelope.project_id
        ):
            raise SolverInputProjectMismatchError(
                f"Project ID mismatch across source contracts: "
                f"directive_set={directive_set.project_id!r}, "
                f"metric_requirements={metric_requirements.project_id!r}, "
                f"site_envelope={site_envelope.project_id!r}."
            )

        # 4. Brief version consistency
        if (
            directive_set.source_brief_version != metric_requirements.source_brief_version
            or directive_set.source_brief_version != site_envelope.source_brief_version
        ):
            raise SolverInputBriefVersionMismatchError(
                f"Source brief version mismatch across source contracts: "
                f"directive_set={directive_set.source_brief_version}, "
                f"metric_requirements={metric_requirements.source_brief_version}, "
                f"site_envelope={site_envelope.source_brief_version}."
            )

        # 5. Space identity consistency
        solver_spaces = directive_set.spaces
        solver_space_ids = {s.id for s in solver_spaces}
        metric_space_ids = {smr.space_id for smr in metric_requirements.space_requirements}

        for space in solver_spaces:
            if space.id != space.source_program_space_id:
                raise SolverInputSpaceMismatchError(
                    f"LayoutSpace id {space.id!r} does not match "
                    f"source_program_space_id {space.source_program_space_id!r}."
                )

        if solver_space_ids != metric_space_ids:
            missing_in_metrics = solver_space_ids - metric_space_ids
            extra_in_metrics = metric_space_ids - solver_space_ids
            raise SolverInputSpaceMismatchError(
                f"Space mismatch between solver directives and metric requirements. "
                f"Missing in metrics: {sorted(missing_in_metrics)}, "
                f"Extra in metrics: {sorted(extra_in_metrics)}."
            )

        # 6. Buildable envelope validation
        if site_envelope.buildable_envelope is None:
            raise SolverInputMissingBuildableEnvelopeError(
                "Site envelope does not contain a buildable envelope. "
                "A confirmed buildable envelope is required for solver input."
            )

        env = site_envelope.buildable_envelope
        if env.role != SiteGeometryRole.BUILDABLE_ENVELOPE:
            raise SolverInputNonAuthoritativeBuildableEnvelopeError(
                f"Site polygon has role {env.role.value!r}; BUILDABLE_ENVELOPE is required."
            )
        if env.provenance != RelationshipProvenance.USER_CONFIRMED:
            raise SolverInputNonAuthoritativeBuildableEnvelopeError(
                f"Buildable envelope has non-authoritative provenance {env.provenance.value!r}; "
                f"USER_CONFIRMED is required for solver input."
            )
        if env.id not in site_envelope.authoritative_geometry_ids:
            raise SolverInputNonAuthoritativeBuildableEnvelopeError(
                f"Buildable envelope {env.id!r} is not listed in authoritative_geometry_ids."
            )

        # 7. Authoritative metrics filtering
        authoritative_metric_ids = set(metric_requirements.authoritative_requirement_ids)
        metric_lookup = {smr.space_id: smr for smr in metric_requirements.space_requirements}

        assembled_space_metrics: list[SolverSpaceMetricRequirements] = []
        for space_id in sorted(solver_space_ids):
            space_metrics = metric_lookup[space_id]
            filtered_reqs = [
                req
                for req in space_metrics.requirements
                if (
                    req.id in authoritative_metric_ids
                    and req.provenance == RelationshipProvenance.USER_CONFIRMED
                )
            ]
            sorted_reqs = sorted(filtered_reqs, key=lambda r: r.id)
            assembled_space_metrics.append(
                SolverSpaceMetricRequirements(
                    space_id=space_id,
                    requirements=sorted_reqs,
                )
            )

        # 8. Deterministic timestamp
        if created_at is not None:
            offset = created_at.utcoffset()
            if created_at.tzinfo is None or offset is None:
                raise ValueError("created_at must be timezone-aware")
            if offset != timedelta(0):
                raise ValueError("created_at must use UTC offset")
            assembled_created_at = created_at
        else:
            assembled_created_at = max(
                directive_set.created_at,
                metric_requirements.created_at,
                site_envelope.created_at,
            )

        # 9. Canonical sorting of output collections
        sorted_spaces = sorted(solver_spaces, key=lambda s: s.id)
        sorted_directives = sorted(directive_set.directives, key=lambda d: d.id)
        sorted_unconstrained = sorted(
            directive_set.unconstrained_pairs,
            key=lambda p: (p.space_a_id, p.space_b_id),
        )

        return LayoutSolverInputSet(
            project_id=directive_set.project_id,
            source_brief_version=directive_set.source_brief_version,
            source_directive_set_schema_version=directive_set.schema_version,
            source_metric_requirements_schema_version=metric_requirements.schema_version,
            source_site_envelope_schema_version=site_envelope.schema_version,
            created_at=assembled_created_at,
            coordinate_system=site_envelope.coordinate_system,
            spaces=sorted_spaces,
            directives=sorted_directives,
            space_metric_requirements=assembled_space_metrics,
            buildable_envelope=env,
            unconstrained_pairs=sorted_unconstrained,
        )
