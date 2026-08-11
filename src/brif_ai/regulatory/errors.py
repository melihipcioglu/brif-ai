"""BRIF.AI — Regulatory Domain Exceptions."""

from __future__ import annotations


class RegulatoryError(Exception):
    """Base exception for regulatory domain errors."""


class RuleSetNotFoundError(RegulatoryError):
    """Raised when a requested RegulatoryRuleSet is missing or invalid."""


class InvalidZoningContextError(RegulatoryError):
    """Raised when zoning inputs are invalid or inconsistent."""


class IncompatibleUnitsError(RegulatoryError):
    """Raised when comparing regulatory constraints with incompatible units."""
