"""Deterministic builder for MetricSpatialRequirements V0 from SpatialProgram."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from brif_ai.spatial.metrics.errors import (
    DuplicateMetricRequirementError,
    MetricMissingInputError,
    MetricNonexistentSpaceError,
    MetricRangeConflictError,
    MetricSchemaVersionMismatchError,
)
from brif_ai.spatial.metrics.models import (
    MetricRequirement,
    MetricRequirementInput,
    MetricRequirementType,
    MetricSpatialRequirements,
    SpaceMetricRequirements,
    generate_metric_requirement_id,
)
from brif_ai.spatial.models import RelationshipProvenance
from brif_ai.spatial.program.models import SpatialProgram


class MetricSpatialRequirementsBuilder:
    """Deterministic builder constructing MetricSpatialRequirements bound to a SpatialProgram.

    ARCHITECTURAL INVARIANTS:
    1. Single authoritative space source: Every requirement must resolve against program.spaces.
    2. Explicit absence: Every ProgramSpace is represented; an empty requirement list
       explicitly denotes unknown / unconstrained (zero SpaceFunction defaults).
    3. Deterministic identity: Requirement IDs are generated deterministically based on
       project_id + space_id + requirement_type (independent of value).
    4. Deterministic range & uniqueness: Rejects duplicate types per space and range conflicts.
    5. Authority boundary: Only USER_CONFIRMED requirements enter authoritative_requirement_ids.
       Provenance is required explicitly on all inputs (no implicit defaulting).
    6. Timestamp determinism: Reuses program.created_at by default with strict UTC requirement.
    7. Zero geometry: Contains zero coordinate, dimensional, or rectangular shape assumptions.
    8. Traceability boundary: Presence of evidence_ids is enforced for USER_CONFIRMED requirements
       and preserved deterministically; cross-domain existence validation against BriefSnapshot
       catalog is deferred to a future integration boundary.
    """

    def build(
        self,
        program: SpatialProgram,
        requirements: Sequence[MetricRequirementInput] = (),
        *,
        created_at: datetime | None = None,
    ) -> MetricSpatialRequirements:
        """Build MetricSpatialRequirements deterministically for a valid SpatialProgram."""
        if program is None:
            raise MetricMissingInputError("SpatialProgram is required.")

        # 1. Strict schema version validation
        if program.schema_version != "spatial_program.v0":
            raise MetricSchemaVersionMismatchError(
                expected_schema="spatial_program.v0",
                actual_schema=str(program.schema_version),
            )

        program_spaces = sorted(program.spaces, key=lambda s: s.id)
        program_space_ids = {s.id for s in program_spaces}

        # 2. Group and validate input requirements per space
        grouped_inputs: dict[str, list[MetricRequirementInput]] = defaultdict(list)
        for req_input in requirements:
            if req_input.space_id not in program_space_ids:
                raise MetricNonexistentSpaceError(
                    f"Metric requirement references unknown space_id {req_input.space_id!r} "
                    f"not found in SpatialProgram."
                )
            grouped_inputs[req_input.space_id].append(req_input)

        # 3. Process and materialize requirements for each space
        space_requirements_list: list[SpaceMetricRequirements] = []
        authoritative_ids: list[str] = []

        for p_space in program_spaces:
            space_inputs = grouped_inputs.get(p_space.id, [])
            seen_types: set[MetricRequirementType] = set()
            area_values: dict[MetricRequirementType, float] = {}
            materialized_reqs: list[MetricRequirement] = []

            for inp in space_inputs:
                if inp.requirement_type in seen_types:
                    raise DuplicateMetricRequirementError(
                        f"Duplicate requirement_type {inp.requirement_type.value!r} for space "
                        f"{inp.space_id!r}."
                    )
                seen_types.add(inp.requirement_type)
                area_values[inp.requirement_type] = inp.value

                req_id = generate_metric_requirement_id(
                    project_id=program.project_id,
                    space_id=inp.space_id,
                    requirement_type=inp.requirement_type,
                )

                req = MetricRequirement(
                    id=req_id,
                    space_id=inp.space_id,
                    requirement_type=inp.requirement_type,
                    value=inp.value,
                    unit=inp.unit,
                    priority=inp.priority,
                    provenance=inp.provenance,
                    evidence_ids=sorted(inp.evidence_ids),
                    rationale=inp.rationale,
                )
                materialized_reqs.append(req)

                if req.provenance == RelationshipProvenance.USER_CONFIRMED:
                    authoritative_ids.append(req.id)

            # Area range conflict validation
            min_a = area_values.get(MetricRequirementType.MIN_AREA)
            max_a = area_values.get(MetricRequirementType.MAX_AREA)
            target_a = area_values.get(MetricRequirementType.TARGET_AREA)

            if min_a is not None and max_a is not None and min_a > max_a:
                raise MetricRangeConflictError(
                    f"Space {p_space.id!r} MIN_AREA ({min_a}) exceeds MAX_AREA ({max_a})."
                )
            if target_a is not None:
                if min_a is not None and target_a < min_a:
                    raise MetricRangeConflictError(
                        f"Space {p_space.id!r} TARGET_AREA ({target_a}) is less than "
                        f"MIN_AREA ({min_a})."
                    )
                if max_a is not None and target_a > max_a:
                    raise MetricRangeConflictError(
                        f"Space {p_space.id!r} TARGET_AREA ({target_a}) exceeds MAX_AREA ({max_a})."
                    )

            space_requirements_list.append(
                SpaceMetricRequirements(
                    space_id=p_space.id,
                    requirements=sorted(materialized_reqs, key=lambda r: r.id),
                )
            )

        # 4. Timestamp determinism
        ts = created_at if created_at is not None else program.created_at

        return MetricSpatialRequirements(
            schema_version="metric_spatial_requirements.v0",
            project_id=program.project_id,
            source_brief_version=program.source_brief_version,
            source_program_schema_version="spatial_program.v0",
            created_at=ts,
            space_requirements=space_requirements_list,
            authoritative_requirement_ids=sorted(authoritative_ids),
        )
