"""BRIF.AI — Turkish Regulatory Demo & Test Fixture RuleSet.

DISCLAIMER: DEMO / TEST FIXTURE ONLY — NOT BINDING TURKISH LAW.
Real Turkish building regulations will be ingested and legally verified in subsequent PRs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from brif_ai.regulatory.models import (
    ConstraintType,
    FormulaLimitParameters,
    MaxValueParameters,
    RegulatoryRule,
    RegulatoryRuleSet,
    RegulatorySource,
    RegulatoryUnit,
    Severity,
    SourceStatus,
    SourceType,
)

DEMO_PROVENANCE_NOTE = "DEMO / TEST FIXTURE — NOT BINDING TURKISH LAW"

DEMO_REGULATORY_SOURCE = RegulatorySource(
    source_id="src_tr_pa_imar_demo",
    title="Planlı Alanlar İmar Yönetmeliği (Demo Test Fixture)",
    jurisdiction="TR",
    authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı (Demo)",
    official_url="https://resmigazete.gov.tr/demo/pa_imar",
    source_type=SourceType.NATIONAL_REGULATION,
    publication_date=date(2017, 7, 3),
    effective_from=date(2017, 10, 1),
    status=SourceStatus.ACTIVE,
)


def build_demo_ruleset() -> RegulatoryRuleSet:
    """Build a sample regulatory rule set for unit testing and prototype demonstration."""
    rules = [
        RegulatoryRule(
            rule_id="rule_taks_max_01",
            ruleset_id="TR-REG-DEMO-2026",
            source_id=DEMO_REGULATORY_SOURCE.source_id,
            article_reference="Madde 5 / Fıkra 1 (Demo)",
            title="Azami Taban Alanı Kat Sayısı (TAKS) Sınırı",
            scope="zoning",
            constraint_type=ConstraintType.FORMULA_LIMIT,
            parameters=FormulaLimitParameters(
                formula_type="TAKS_FOOTPRINT_LIMIT",
                target_fact_key="proposed_footprint_m2",
                parameters={"taks": Decimal("0.40")},
            ),
            severity=Severity.CRITICAL,
            provenance_note=DEMO_PROVENANCE_NOTE,
        ),
        RegulatoryRule(
            rule_id="rule_height_max_01",
            ruleset_id="TR-REG-DEMO-2026",
            source_id=DEMO_REGULATORY_SOURCE.source_id,
            article_reference="Madde 19 / Fıkra 2 (Demo)",
            title="Azami Yapı Yüksekliği Sınırı",
            scope="building_height",
            constraint_type=ConstraintType.MAX_VALUE,
            parameters=MaxValueParameters(
                fact_key="proposed_height_m",
                limit_value=Decimal("12.50"),
                unit=RegulatoryUnit.METER,
            ),
            severity=Severity.CRITICAL,
            provenance_note=DEMO_PROVENANCE_NOTE,
        ),
    ]

    ruleset = RegulatoryRuleSet(
        ruleset_id="TR-REG-DEMO-2026",
        country="TR",
        jurisdiction="TR-NATIONAL-DEMO",
        effective_from=date(2026, 1, 1),
        source_ids=[DEMO_REGULATORY_SOURCE.source_id],
        rules=rules,
    )

    hash_val = ruleset.compute_canonical_hash()
    return ruleset.model_copy(update={"content_hash": hash_val})
