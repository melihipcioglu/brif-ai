"""BRIF.AI — Regulatory RuleSet and Source Registry."""

from __future__ import annotations

from brif_ai.regulatory.models import RegulatoryRuleSet, RegulatorySource


class RegulatoryRegistry:
    """Registry for verified RegulatorySource and RegulatoryRuleSet models."""

    def __init__(self) -> None:
        self._sources: dict[str, RegulatorySource] = {}
        self._rulesets: dict[str, RegulatoryRuleSet] = {}

    def register_source(self, source: RegulatorySource) -> None:
        """Register an official regulatory source."""
        self._sources[source.source_id] = source

    def get_source(self, source_id: str) -> RegulatorySource | None:
        """Retrieve a registered regulatory source by ID."""
        return self._sources.get(source_id)

    def register_ruleset(self, ruleset: RegulatoryRuleSet) -> None:
        """Register a versioned RegulatoryRuleSet."""
        # Ensure content_hash is computed if missing
        if not ruleset.content_hash:
            computed = ruleset.compute_canonical_hash()
            ruleset = ruleset.model_copy(update={"content_hash": computed})
        self._rulesets[ruleset.ruleset_id] = ruleset

    def get_ruleset(self, ruleset_id: str) -> RegulatoryRuleSet | None:
        """Retrieve a registered RegulatoryRuleSet by ID."""
        return self._rulesets.get(ruleset_id)

    def list_rulesets(self) -> list[str]:
        """Return a sorted list of registered ruleset IDs."""
        return sorted(self._rulesets.keys())
