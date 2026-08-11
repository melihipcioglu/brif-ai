"""BRIF.AI — Turkish Regulatory Foundation Package."""

from __future__ import annotations

from brif_ai.regulatory.compliance import DeterministicComplianceEngine
from brif_ai.regulatory.errors import (
    IncompatibleUnitsError,
    InvalidZoningContextError,
    RegulatoryError,
    RuleSetNotFoundError,
)
from brif_ai.regulatory.models import (
    ComplianceFinding,
    ComplianceStatus,
    ConstraintType,
    DesignFacts,
    FormulaLimitParameters,
    GenerationConstraintSet,
    MaxValueParameters,
    MinValueParameters,
    ProjectRegulatoryContext,
    RangeParameters,
    RegulatoryRule,
    RegulatoryRuleSet,
    RegulatorySource,
    RegulatoryUnit,
    RequiredParameters,
    Severity,
    SourceStatus,
    SourceType,
    VerificationStatus,
    ZoningContext,
)
from brif_ai.regulatory.registry import RegulatoryRegistry
from brif_ai.regulatory.update_detection import (
    RegulatoryChangeDetector,
    RegulatorySourceFetcher,
    RegulatorySourceSnapshot,
    RegulatoryUpdateCandidate,
)

__all__ = [
    "ComplianceFinding",
    "ComplianceStatus",
    "ConstraintType",
    "DesignFacts",
    "DeterministicComplianceEngine",
    "FormulaLimitParameters",
    "GenerationConstraintSet",
    "IncompatibleUnitsError",
    "InvalidZoningContextError",
    "MaxValueParameters",
    "MinValueParameters",
    "ProjectRegulatoryContext",
    "RangeParameters",
    "RegulatoryChangeDetector",
    "RegulatoryError",
    "RegulatoryRegistry",
    "RegulatoryRule",
    "RegulatoryRuleSet",
    "RegulatorySource",
    "RegulatorySourceFetcher",
    "RegulatorySourceSnapshot",
    "RegulatoryUnit",
    "RegulatoryUpdateCandidate",
    "RequiredParameters",
    "RuleSetNotFoundError",
    "Severity",
    "SourceStatus",
    "SourceType",
    "VerificationStatus",
    "ZoningContext",
]
