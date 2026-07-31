"""Loader and cross-file validator for BRIF.AI Daily Routines v0 content pack."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from brif_ai.conversation.daily_routines.enums import (
    DayPeriod,
    FunctionalDomain,
    FunctionalDomainStatus,
    HouseholdVariationStatus,
    SummaryConfirmation,
    WordingBranch,
)
from brif_ai.conversation.daily_routines.models import (
    DailyRoutinesContentPack,
    DomainApplicabilityRule,

    FlowRule,

    MultiSelectContract,
    OptionSet,

    QuestionDefinition,
    QuestionWording,
    SummaryTemplate,
    UIStateControlDefinition,
)

DEFAULT_CONTENTPACK_DIR = (
    Path(__file__).parents[4] / "contentpacks" / "tr" / "daily_routines" / "v0"
)


class ContentPackValidationError(ValueError):
    """Raised when cross-file validation of content pack fails."""


def load_daily_routines_content_pack(
    contentpack_dir: Path | str | None = None,
) -> DailyRoutinesContentPack:
    """Load and validate the Daily Routines v0 content pack from YAML files."""
    if contentpack_dir is None:
        contentpack_dir = DEFAULT_CONTENTPACK_DIR
    else:
        contentpack_dir = Path(contentpack_dir)

    if not contentpack_dir.exists():
        raise ContentPackValidationError(f"Content pack directory does not exist: {contentpack_dir}")

    questions_raw = _load_yaml(contentpack_dir / "questions.yaml")
    option_sets_raw = _load_yaml(contentpack_dir / "option_sets.yaml")
    wording_variants_raw = _load_yaml(contentpack_dir / "wording_variants.yaml")
    flow_rules_raw = _load_yaml(contentpack_dir / "flow_rules.yaml")
    summary_templates_raw = _load_yaml(contentpack_dir / "summary_templates.yaml")
    applicability_raw = _load_yaml(contentpack_dir / "applicability.yaml")

    raw_pack = {
        "schema_version": questions_raw.get("schema_version", "v0"),
        "questions": questions_raw.get("questions", []),
        "ui_state_controls": questions_raw.get("ui_state_controls", []),
        "option_sets": option_sets_raw.get("option_sets", []),
        "wording_variants": wording_variants_raw.get("wording_variants", []),
        "multi_select_contract": flow_rules_raw.get("multi_select_contract", {}),
        "flow_rules": flow_rules_raw.get("flow_rules", []),
        "conditional_routes": flow_rules_raw.get("conditional_routes", []),
        "summary_templates": summary_templates_raw.get("summary_templates", {}),
        "domain_applicability_rules": applicability_raw.get("domain_applicability_rules", {}),
    }

    try:
        pack = DailyRoutinesContentPack.model_validate(raw_pack)
    except Exception as err:
        raise ContentPackValidationError(f"Pydantic schema validation failed: {err}") from err

    validate_cross_file_integrity(pack)
    return pack


def validate_cross_file_integrity(pack: DailyRoutinesContentPack) -> None:
    """Perform thorough cross-file validation of DailyRoutinesContentPack."""
    _validate_unique_ids(pack)
    _validate_option_set_references(pack)
    _validate_wording_branch_coverage(pack)
    _validate_multi_select_contract(pack.multi_select_contract)
    _validate_flow_rule_references_and_routing(pack)
    _validate_domain_applicability(pack.domain_applicability_rules)


def _load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise ContentPackValidationError(f"Required YAML file missing: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ContentPackValidationError(f"Invalid YAML content in {file_path}")
    return data


def _validate_unique_ids(pack: DailyRoutinesContentPack) -> None:
    seen_q_ids: set[str] = set()
    for q in pack.questions:
        if q.id in seen_q_ids:
            raise ContentPackValidationError(f"Duplicate question id {q.id!r}")
        seen_q_ids.add(q.id)

    for ui in pack.ui_state_controls:
        if ui.id in seen_q_ids:
            raise ContentPackValidationError(f"UI state control id {ui.id!r} collides with question id")
        seen_q_ids.add(ui.id)

    seen_opt_set_ids: set[str] = set()
    for os_def in pack.option_sets:
        if os_def.id in seen_opt_set_ids:
            raise ContentPackValidationError(f"Duplicate option set id {os_def.id!r}")
        seen_opt_set_ids.add(os_def.id)

    seen_rule_ids: set[str] = set()
    for rule in pack.flow_rules:
        if rule.rule_id in seen_rule_ids:
            raise ContentPackValidationError(f"Duplicate flow rule id {rule.rule_id!r}")
        seen_rule_ids.add(rule.rule_id)


def _validate_option_set_references(pack: DailyRoutinesContentPack) -> None:
    option_set_map = {os.id: os for os in pack.option_sets}
    for q in pack.questions:
        if q.option_set_id is not None and q.option_set_id not in option_set_map:
            raise ContentPackValidationError(
                f"Question {q.id!r} references unknown option_set_id {q.option_set_id!r}"
            )

    for ui in pack.ui_state_controls:
        if ui.option_set_id not in option_set_map:
            raise ContentPackValidationError(
                f"UI control {ui.id!r} references unknown option_set_id {ui.option_set_id!r}"
            )


def _validate_wording_branch_coverage(pack: DailyRoutinesContentPack) -> None:
    wording_map = {w.question_id: w for w in pack.wording_variants}
    for q in pack.questions:
        if q.id not in wording_map:
            raise ContentPackValidationError(f"Question {q.id!r} has no wording variants defined")

        variants = wording_map[q.id].variants
        branches = {v.branch for v in variants}
        if WordingBranch.STABLE not in branches or WordingBranch.IRREGULAR not in branches:
            raise ContentPackValidationError(
                f"Question {q.id!r} must define both STABLE and IRREGULAR wording variants"
            )


def _validate_multi_select_contract(contract: MultiSelectContract) -> None:
    if contract.min_selected_items != 1:
        raise ContentPackValidationError(
            f"MultiSelectContract min_selected_items must be 1, got {contract.min_selected_items}"
        )
    if contract.max_selected_items != 4:
        raise ContentPackValidationError(
            f"MultiSelectContract max_selected_items must be 4, got {contract.max_selected_items}"
        )
    if not contract.unique_items:
        raise ContentPackValidationError("MultiSelectContract unique_items must be True")

    expected_canonical = [
        DayPeriod.MORNING,
        DayPeriod.MIDDAY_AFTERNOON,
        DayPeriod.EVENING,
        DayPeriod.NIGHT,
    ]
    if contract.canonical_order != expected_canonical:
        raise ContentPackValidationError(
            f"MultiSelectContract canonical_order must be {expected_canonical}, got {contract.canonical_order}"
        )


def _validate_flow_rule_references_and_routing(pack: DailyRoutinesContentPack) -> None:
    valid_q_ids = {q.id for q in pack.questions} | {ui.id for ui in pack.ui_state_controls}
    valid_option_values_by_question: dict[str, set[str]] = {}

    option_sets_by_id = {os.id: {opt.value for opt in os.options} for os in pack.option_sets}

    for q in pack.questions:
        if q.option_set_id and q.option_set_id in option_sets_by_id:
            valid_option_values_by_question[q.id] = option_sets_by_id[q.option_set_id]

    for ui in pack.ui_state_controls:
        if ui.option_set_id in option_sets_by_id:
            valid_option_values_by_question[ui.id] = option_sets_by_id[ui.option_set_id]

    # Include placeholder generic templates
    placeholder_source = "DOMAIN_STATUS_QUESTION"
    valid_option_values_by_question[placeholder_source] = {
        opt.value for opt in FunctionalDomainStatus
    }

    for rule in pack.flow_rules:
        if (
            rule.source_question_id not in valid_q_ids
            and rule.source_question_id != placeholder_source
        ):
            raise ContentPackValidationError(
                f"Flow rule {rule.rule_id!r} references unknown source_question_id {rule.source_question_id!r}"
            )

        if (
            rule.target_question_id is not None
            and rule.target_question_id not in valid_q_ids
            and rule.target_question_id != "DOMAIN_PERIODS_QUESTION"
            and rule.target_question_id != "NEXT_DOMAIN_OR_HOUSEHOLD_STATUS"
        ):
            raise ContentPackValidationError(
                f"Flow rule {rule.rule_id!r} references unknown target_question_id {rule.target_question_id!r}"
            )

        if rule.target_module is not None and rule.target_module != "module_complete":
            raise ContentPackValidationError(
                f"Flow rule {rule.rule_id!r} specifies unknown target_module {rule.target_module!r}"
            )

    # Check key specific routing rules
    rule_map = {r.rule_id: r for r in pack.flow_rules}

    if "fr_hh_material_difference" in rule_map:
        r = rule_map["fr_hh_material_difference"]
        if r.target_question_id != "q_daily_routines_functional_space_household_variation_detail":
            raise ContentPackValidationError(
                "material_difference_reported must route to household_variation_detail"
            )

    if "fr_confirm_no" in rule_map:
        r = rule_map["fr_confirm_no"]
        if r.target_question_id != "bp_ui_room_use_correction_selector":
            raise ContentPackValidationError(
                "rejected_for_correction must route to bp_ui_room_use_correction_selector"
            )

    if "fr_confirm_yes" in rule_map:
        r = rule_map["fr_confirm_yes"]
        if r.target_module != "module_complete":
            raise ContentPackValidationError("confirmed must specify target_module module_complete")


def _validate_domain_applicability(rule: DomainApplicabilityRule) -> None:
    allow_list = rule.functional_domain_not_relevant_to_household.allowed_domains
    if allow_list.get(FunctionalDomain.SLEEPING) is not False:
        raise ContentPackValidationError(
            "functional_domain_not_relevant_to_household must be disallowed (false) for SLEEPING"
        )
    if allow_list.get(FunctionalDomain.BATHROOM) is not False:
        raise ContentPackValidationError(
            "functional_domain_not_relevant_to_household must be disallowed (false) for BATHROOM"
        )


def is_option_allowed_for_domain(
    pack: DailyRoutinesContentPack, domain: FunctionalDomain, option_value: str
) -> bool:
    """Check if an option value is allowed for a specific domain based on applicability rules."""
    if option_value == FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value:
        allow_list = (
            pack.domain_applicability_rules.functional_domain_not_relevant_to_household.allowed_domains
        )
        return allow_list.get(domain, True)
    return True
