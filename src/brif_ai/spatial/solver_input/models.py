"""Strict immutable contracts for BRIF.AI Layout Solver Input Set V0.

Scope Note (V0):
This contract represents the SITE-BASED NEW-BUILD SCHEMATIC WORKFLOW where layout
placement is constrained by an authoritative site buildable envelope. Future interior,
renovation, or existing-building workflows may introduce alternative layout containers.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brif_ai.core.models.common import ObjectId
from brif_ai.spatial.layout.models import LayoutSpace
from brif_ai.spatial.metrics.models import MetricRequirement, MetricRequirementType
from brif_ai.spatial.models import RelationshipProvenance, UnconstrainedPair
from brif_ai.spatial.site.models import SiteGeometryRole, SitePolygon
from brif_ai.spatial.solver_policy.models import SolverDirective


class _SolverInputContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolverSpaceMetricRequirements(_SolverInputContract):
    """Authoritative, solver-facing metric requirements for a discrete addressable space.

    Contains exclusively USER_CONFIRMED metric requirements. If a space has no
    authoritative metric requirements, `requirements` is empty (`[]`), explicitly
    denoting an unconstrained/unknown metric state without heuristic defaults.
    """

    space_id: ObjectId
    requirements: list[MetricRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_solver_space_metric_invariants(self) -> SolverSpaceMetricRequirements:
        req_types: set[MetricRequirementType] = set()
        req_ids: set[str] = set()

        for req in self.requirements:
            if req.space_id != self.space_id:
                raise ValueError(
                    f"Requirement {req.id!r} space_id {req.space_id!r} does not match "
                    f"container space_id {self.space_id!r}"
                )
            if req.provenance != RelationshipProvenance.USER_CONFIRMED:
                raise ValueError(
                    f"Requirement {req.id!r} has non-authoritative provenance "
                    f"{req.provenance.value!r}; only USER_CONFIRMED is permitted for solver input."
                )
            if req.id in req_ids:
                raise ValueError(f"Duplicate requirement id {req.id!r} for space {self.space_id!r}")
            req_ids.add(req.id)

            if req.requirement_type in req_types:
                raise ValueError(
                    f"Duplicate requirement_type {req.requirement_type.value!r} for space "
                    f"{self.space_id!r}"
                )
            req_types.add(req.requirement_type)

        return self


class LayoutSolverInputSet(_SolverInputContract):
    """Integrated, solver-facing input contract prepared for downstream layout engines.

    Combines:
    1. Authoritative relational directives (`SolverDirectiveSet V0`)
    2. Authoritative space-level metric requirements (`MetricSpatialRequirements V0`)
    3. Authoritative site buildable envelope (`SiteBuildableEnvelope V0`)

    Crucial Invariants & Scope:
    - Scoped to SITE-BASED NEW-BUILD SCHEMATIC WORKFLOW.
    - `buildable_envelope` defines the site-level allowable building-placement region.
      Downstream solvers must NOT interpret this polygon as an architectural room-layout
      container, building footprint, or floor plate.
    - All exposed directives, metric requirements, and site geometries are strictly
      authoritative (USER_CONFIRMED).
    """

    schema_version: Literal["layout_solver_input_set.v0"] = "layout_solver_input_set.v0"
    project_id: ObjectId
    source_brief_version: int = Field(ge=1)
    source_directive_set_schema_version: Literal["solver_directive_set.v0"] = (
        "solver_directive_set.v0"
    )
    source_metric_requirements_schema_version: Literal["metric_spatial_requirements.v0"] = (
        "metric_spatial_requirements.v0"
    )
    source_site_envelope_schema_version: Literal["site_buildable_envelope.v0"] = (
        "site_buildable_envelope.v0"
    )
    created_at: datetime
    coordinate_system: Literal["LOCAL_CARTESIAN_METRES"] = "LOCAL_CARTESIAN_METRES"
    spaces: list[LayoutSpace] = Field(min_length=1)
    directives: list[SolverDirective] = Field(default_factory=list)
    space_metric_requirements: list[SolverSpaceMetricRequirements] = Field(default_factory=list)
    buildable_envelope: SitePolygon
    unconstrained_pairs: list[UnconstrainedPair] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError("created_at must be timezone-aware")
        if offset != timedelta(0):
            raise ValueError("created_at must use UTC offset")
        return value

    @model_validator(mode="after")
    def validate_solver_input_set_integrity(self) -> LayoutSolverInputSet:
        # 1. Validate unique spaces and identity preservation
        space_ids: set[str] = set()
        for space in self.spaces:
            if space.id in space_ids:
                raise ValueError(f"duplicate space id {space.id!r}")
            space_ids.add(space.id)
            if space.id != space.source_program_space_id:
                raise ValueError(
                    f"LayoutSpace id {space.id!r} does not match "
                    f"source_program_space_id {space.source_program_space_id!r}"
                )

        # 2. Validate space_metric_requirements containers
        metric_space_ids: set[str] = set()
        for smr in self.space_metric_requirements:
            if smr.space_id in metric_space_ids:
                raise ValueError(
                    f"duplicate SolverSpaceMetricRequirements container for "
                    f"space_id {smr.space_id!r}"
                )
            metric_space_ids.add(smr.space_id)

        # Exact set equality
        if metric_space_ids != space_ids:
            missing_in_metrics = space_ids - metric_space_ids
            extra_in_metrics = metric_space_ids - space_ids
            raise ValueError(
                f"space_metric_requirements spaces mismatch solver spaces. "
                f"Missing: {sorted(missing_in_metrics)}, Extra: {sorted(extra_in_metrics)}"
            )

        # 3. Validate directives
        directive_ids: set[str] = set()
        for directive in self.directives:
            if directive.id in directive_ids:
                raise ValueError(f"duplicate directive id {directive.id!r}")
            directive_ids.add(directive.id)
            if directive.source_space_id not in space_ids:
                raise ValueError(
                    f"directive {directive.id!r} references unknown source_space_id "
                    f"{directive.source_space_id!r}"
                )
            if directive.target_space_id not in space_ids:
                raise ValueError(
                    f"directive {directive.id!r} references unknown target_space_id "
                    f"{directive.target_space_id!r}"
                )

        # 4. Validate unconstrained pairs
        seen_pairs: set[tuple[str, str]] = set()
        for pair in self.unconstrained_pairs:
            pair_key = (pair.space_a_id, pair.space_b_id)
            if pair_key in seen_pairs:
                raise ValueError(f"duplicate unconstrained pair {pair_key!r}")
            seen_pairs.add(pair_key)
            if pair.space_a_id not in space_ids:
                raise ValueError(
                    f"unconstrained pair references unknown space_a_id {pair.space_a_id!r}"
                )
            if pair.space_b_id not in space_ids:
                raise ValueError(
                    f"unconstrained pair references unknown space_b_id {pair.space_b_id!r}"
                )

        # 5. Validate buildable_envelope authority and role
        if self.buildable_envelope.role != SiteGeometryRole.BUILDABLE_ENVELOPE:
            raise ValueError(
                f"buildable_envelope must have role BUILDABLE_ENVELOPE, "
                f"got {self.buildable_envelope.role.value!r}"
            )
        if self.buildable_envelope.provenance != RelationshipProvenance.USER_CONFIRMED:
            raise ValueError(
                f"buildable_envelope must have USER_CONFIRMED provenance, "
                f"got {self.buildable_envelope.provenance.value!r}"
            )

        return self
