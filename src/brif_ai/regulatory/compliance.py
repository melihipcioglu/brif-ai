"""BRIF.AI — Deterministic Regulatory Compliance Evaluator."""

from __future__ import annotations

from decimal import Decimal

from brif_ai.regulatory.models import (
    ComplianceFinding,
    ComplianceStatus,
    DesignFacts,
    FormulaLimitParameters,
    GenerationConstraintSet,
    MaxValueParameters,
    MinValueParameters,
    ProjectRegulatoryContext,
    RegulatoryRule,
    RegulatoryRuleSet,
    RegulatorySource,
    RegulatoryUnit,
    VerificationStatus,
)


class DeterministicComplianceEngine:
    """100% Python-authoritative deterministic compliance evaluator.

    The LLM is NEVER involved in PASS/FAIL/UNKNOWN calculation.
    """

    def evaluate_rule(
        self,
        rule: RegulatoryRule,
        context: ProjectRegulatoryContext,
        facts: DesignFacts,
        sources_by_id: dict[str, RegulatorySource] | None = None,
    ) -> ComplianceFinding:
        """Evaluate a single regulatory rule against structured facts and context."""
        sources_by_id = sources_by_id or {}
        source = sources_by_id.get(rule.source_id)
        source_id = rule.source_id
        article_ref = rule.article_reference
        provenance = rule.provenance_note or (source.title if source else "UNSPECIFIED_SOURCE")

        # 1. Unverified context protection (Amendment 11)
        if context.verification_status != VerificationStatus.VERIFIED:
            return ComplianceFinding(
                finding_id=f"find_{rule.rule_id}_unverified",
                rule_id=rule.rule_id,
                status=ComplianceStatus.UNKNOWN,
                severity=rule.severity,
                message=(
                    "Mevzuat veya imar durumu henüz doğrulanmadığı için "
                    f"({context.verification_status.value}) {rule.title!r} kuralı "
                    "kesinleştirilemedi."
                ),
                source_id=source_id,
                article_reference=article_ref,
                provenance_note=provenance,
            )

        params = rule.parameters

        if isinstance(params, MaxValueParameters):
            observed = getattr(facts, params.fact_key, None)
            if observed is None and context.zoning_context is not None:
                observed = getattr(context.zoning_context, params.fact_key, None)

            if observed is None:
                return ComplianceFinding(
                    finding_id=f"find_{rule.rule_id}_missing",
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.UNKNOWN,
                    severity=rule.severity,
                    required_value=params.limit_value,
                    required_unit=params.unit,
                    message=(
                        f"Gerekli parametre ('{params.fact_key}') eksik olduğu için "
                        f"{rule.title!r} kontrolü yapılamadı."
                    ),
                    source_id=source_id,
                    article_reference=article_ref,
                    provenance_note=provenance,
                )

            if isinstance(observed, Decimal) and observed <= params.limit_value:
                return ComplianceFinding(
                    finding_id=f"find_{rule.rule_id}_pass",
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.PASS,
                    severity=rule.severity,
                    observed_value=observed,
                    required_value=params.limit_value,
                    observed_unit=params.unit,
                    required_unit=params.unit,
                    message=(
                        f"{rule.title}: Gözlenen değer ({observed} {params.unit.value}), "
                        f"azami sınırı ({params.limit_value} {params.unit.value}) aşmıyor."
                    ),
                    source_id=source_id,
                    article_reference=article_ref,
                    provenance_note=provenance,
                )
            else:
                return ComplianceFinding(
                    finding_id=f"find_{rule.rule_id}_fail",
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.FAIL,
                    severity=rule.severity,
                    observed_value=observed,
                    required_value=params.limit_value,
                    observed_unit=params.unit,
                    required_unit=params.unit,
                    message=(
                        f"{rule.title}: Gözlenen değer ({observed} {params.unit.value}), "
                        f"azami sınırı ({params.limit_value} {params.unit.value}) aşıyor."
                    ),
                    source_id=source_id,
                    article_reference=article_ref,
                    provenance_note=provenance,
                )

        elif isinstance(params, MinValueParameters):
            observed = getattr(facts, params.fact_key, None)
            if observed is None and context.zoning_context is not None:
                observed = getattr(context.zoning_context, params.fact_key, None)

            if observed is None:
                return ComplianceFinding(
                    finding_id=f"find_{rule.rule_id}_missing",
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.UNKNOWN,
                    severity=rule.severity,
                    required_value=params.limit_value,
                    required_unit=params.unit,
                    message=(
                        f"Gerekli parametre ('{params.fact_key}') eksik olduğu için "
                        f"{rule.title!r} kontrolü yapılamadı."
                    ),
                    source_id=source_id,
                    article_reference=article_ref,
                    provenance_note=provenance,
                )

            if isinstance(observed, Decimal) and observed >= params.limit_value:
                return ComplianceFinding(
                    finding_id=f"find_{rule.rule_id}_pass",
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.PASS,
                    severity=rule.severity,
                    observed_value=observed,
                    required_value=params.limit_value,
                    observed_unit=params.unit,
                    required_unit=params.unit,
                    message=(
                        f"{rule.title}: Gözlenen değer ({observed} {params.unit.value}), "
                        f"asgari sınırı ({params.limit_value} {params.unit.value}) sağlıyor."
                    ),
                    source_id=source_id,
                    article_reference=article_ref,
                    provenance_note=provenance,
                )
            else:
                return ComplianceFinding(
                    finding_id=f"find_{rule.rule_id}_fail",
                    rule_id=rule.rule_id,
                    status=ComplianceStatus.FAIL,
                    severity=rule.severity,
                    observed_value=observed,
                    required_value=params.limit_value,
                    observed_unit=params.unit,
                    required_unit=params.unit,
                    message=(
                        f"{rule.title}: Gözlenen değer ({observed} {params.unit.value}), "
                        f"asgari sınırın ({params.limit_value} {params.unit.value}) "
                        "altında kalıyor."
                    ),
                    source_id=source_id,
                    article_reference=article_ref,
                    provenance_note=provenance,
                )

        elif isinstance(params, FormulaLimitParameters):
            if params.formula_type == "TAKS_FOOTPRINT_LIMIT":
                parcel_area = facts.parcel_area_m2 or (
                    context.zoning_context.parcel_area_m2 if context.zoning_context else None
                )
                taks = facts.taks or (
                    context.zoning_context.taks if context.zoning_context else None
                )
                footprint = facts.proposed_footprint_m2

                if parcel_area is None or taks is None or footprint is None:
                    return ComplianceFinding(
                        finding_id=f"find_{rule.rule_id}_unknown",
                        rule_id=rule.rule_id,
                        status=ComplianceStatus.UNKNOWN,
                        severity=rule.severity,
                        message=(
                            "Parsel alanı, TAKS oranı veya önerilen taban alanı eksik "
                            "olduğu için taban alanı sınırı kontrol edilemedi."
                        ),
                        source_id=source_id,
                        article_reference=article_ref,
                        provenance_note=provenance,
                    )

                max_footprint = parcel_area * taks
                if footprint <= max_footprint:
                    return ComplianceFinding(
                        finding_id=f"find_{rule.rule_id}_pass",
                        rule_id=rule.rule_id,
                        status=ComplianceStatus.PASS,
                        severity=rule.severity,
                        observed_value=footprint,
                        required_value=max_footprint,
                        observed_unit=RegulatoryUnit.SQUARE_METER,
                        required_unit=RegulatoryUnit.SQUARE_METER,
                        message=(
                            f"Taban alanı ({footprint} m²), izin verilen azami TAKS sınırını "
                            f"({max_footprint} m²) aşmıyor."
                        ),
                        source_id=source_id,
                        article_reference=article_ref,
                        provenance_note=provenance,
                    )
                else:
                    return ComplianceFinding(
                        finding_id=f"find_{rule.rule_id}_fail",
                        rule_id=rule.rule_id,
                        status=ComplianceStatus.FAIL,
                        severity=rule.severity,
                        observed_value=footprint,
                        required_value=max_footprint,
                        observed_unit=RegulatoryUnit.SQUARE_METER,
                        required_unit=RegulatoryUnit.SQUARE_METER,
                        message=(
                            f"Taban alanı ({footprint} m²), izin verilen azami TAKS sınırını "
                            f"({max_footprint} m²) aşıyor."
                        ),
                        source_id=source_id,
                        article_reference=article_ref,
                        provenance_note=provenance,
                    )

        # Fallback for other parameter types
        return ComplianceFinding(
            finding_id=f"find_{rule.rule_id}_unknown",
            rule_id=rule.rule_id,
            status=ComplianceStatus.UNKNOWN,
            severity=rule.severity,
            message=f"{rule.title!r} kuralı için yeterli veri mevcut değil.",
            source_id=source_id,
            article_reference=article_ref,
            provenance_note=provenance,
        )

    def evaluate_ruleset(
        self,
        ruleset: RegulatoryRuleSet,
        context: ProjectRegulatoryContext,
        facts: DesignFacts,
        sources_by_id: dict[str, RegulatorySource] | None = None,
    ) -> list[ComplianceFinding]:
        """Evaluate an entire RegulatoryRuleSet against facts and context."""
        findings: list[ComplianceFinding] = []
        for rule in ruleset.rules:
            finding = self.evaluate_rule(rule, context, facts, sources_by_id)
            findings.append(finding)
        return findings

    def to_generation_constraints(
        self,
        context: ProjectRegulatoryContext,
        findings: list[ComplianceFinding],
    ) -> GenerationConstraintSet:
        """Export deterministic spatial generation constraints for future plan generators."""
        zoning = context.zoning_context

        max_footprint: Decimal | None = None
        max_total_floor: Decimal | None = None

        if zoning and zoning.parcel_area_m2:
            if zoning.taks:
                max_footprint = zoning.parcel_area_m2 * zoning.taks
            if zoning.kaks_or_emsal:
                max_total_floor = zoning.parcel_area_m2 * zoning.kaks_or_emsal

        return GenerationConstraintSet(
            max_footprint_m2=max_footprint,
            max_total_floor_area_m2=max_total_floor,
            max_height_m=zoning.max_height_m if zoning else None,
            max_floors=zoning.max_floors if zoning else None,
            min_front_setback_m=zoning.front_setback_m if zoning else None,
            min_side_setback_m=zoning.side_setback_m if zoning else None,
            min_rear_setback_m=zoning.rear_setback_m if zoning else None,
            verification_status=context.verification_status,
        )
