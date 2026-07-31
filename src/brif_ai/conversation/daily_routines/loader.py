"""Loader and cross-file validator for BRIF.AI Daily Routines v0 content pack."""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from brif_ai.conversation.daily_routines.enums import (
    CorrectionTarget,
    DayPeriod,
    FunctionalDomain,
    FunctionalDomainStatus,
    RouteMatchType,
    TargetClosureEffect,
    WordingBranch,
)
from brif_ai.conversation.daily_routines.models import (
    DailyRoutinesContentPack,
    DomainApplicabilityRule,
    MultiSelectContract,
)
from brif_ai.conversation.models.common import AnswerType

ALLOWED_TERMINAL_TARGETS: set[str] = {"module_complete"}


class ContentPackValidationError(ValueError):
    """Raised when cross-file validation of content pack fails."""


def get_default_contentpack_dir() -> Path:
    """Resolve default contentpack path using importlib.resources."""
    try:
        ref = importlib.resources.files("brif_ai").joinpath(
            "contentpacks", "tr", "daily_routines", "v0"
        )
        return Path(str(ref))
    except Exception as err:
        fallback = Path(__file__).parents[2] / "contentpacks" / "tr" / "daily_routines" / "v0"
        if fallback.exists():
            return fallback
        raise ContentPackValidationError(
            f"Failed to locate package resources content pack: {err}"
        ) from err


def load_daily_routines_content_pack(
    contentpack_dir: Path | str | None = None,
) -> DailyRoutinesContentPack:
    """Load and validate the Daily Routines v0 content pack from YAML files."""
    if contentpack_dir is None:
        contentpack_dir = get_default_contentpack_dir()
    else:
        contentpack_dir = Path(contentpack_dir)

    if not contentpack_dir.exists():
        raise ContentPackValidationError(
            f"Content pack directory does not exist: {contentpack_dir}"
        )

    questions_raw = _load_yaml(contentpack_dir / "questions.yaml")
    option_sets_raw = _load_yaml(contentpack_dir / "option_sets.yaml")
    wording_variants_raw = _load_yaml(contentpack_dir / "wording_variants.yaml")
    flow_rules_raw = _load_yaml(contentpack_dir / "flow_rules.yaml")
    summary_templates_raw = _load_yaml(contentpack_dir / "summary_templates.yaml")
    applicability_raw = _load_yaml(contentpack_dir / "applicability.yaml")
    invalidation_rules_raw = _load_yaml(contentpack_dir / "invalidation_rules.yaml")

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
        "invalidation_rules": invalidation_rules_raw.get("invalidation_rules", []),
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
    _validate_domain_applicability(pack.domain_applicability_rules)
    _validate_target_closure_effects(pack)
    _validate_flow_rule_references_and_routing(pack)
    _validate_invalidation_rules(pack)


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
            raise ContentPackValidationError(
                f"UI state control id {ui.id!r} collides with question id"
            )
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

    seen_inv_ids: set[str] = set()
    for inv in pack.invalidation_rules:
        if inv.rule_id in seen_inv_ids:
            raise ContentPackValidationError(f"Duplicate invalidation rule id {inv.rule_id!r}")
        seen_inv_ids.add(inv.rule_id)


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
            f"MultiSelectContract canonical_order must be {expected_canonical}, "
            f"got {contract.canonical_order}"
        )


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


def _validate_target_closure_effects(pack: DailyRoutinesContentPack) -> None:
    rules_map = {r.rule_id: r for r in pack.flow_rules}
    expected = {
        "fr_household_variation_no_diff": TargetClosureEffect.VALID_CLOSURE,
        "fr_household_variation_reported": TargetClosureEffect.REQUIRES_FOLLOW_UP,
        "fr_household_variation_unknown": TargetClosureEffect.VALID_BUT_LOW_INFORMATION,
        "fr_household_variation_prefer_not": TargetClosureEffect.VALID_BUT_LOW_INFORMATION,
        "fr_household_variation_single_person": TargetClosureEffect.VALID_CLOSURE,
        "fr_household_variation_detail_complete": TargetClosureEffect.VALID_CLOSURE,
        "fr_summary_confirmation_confirmed": TargetClosureEffect.TARGET_2_FULFILLED,
        "fr_summary_confirmation_rejected": TargetClosureEffect.REQUIRES_CORRECTION,
    }
    for rule_id, exp_effect in expected.items():
        if rule_id in rules_map:
            act_effect = rules_map[rule_id].target_closure_effect
            if act_effect != exp_effect:
                msg = (
                    f"FlowRule {rule_id!r} has incorrect target_closure_effect "
                    f"{act_effect!r}, expected {exp_effect!r}"
                )
                raise ContentPackValidationError(msg)


def is_option_allowed_for_domain(
    pack: DailyRoutinesContentPack, domain: FunctionalDomain, option_value: str
) -> bool:
    """Check if an option value is allowed for a specific domain based on applicability rules."""
    not_relevant = FunctionalDomainStatus.FUNCTIONAL_DOMAIN_NOT_RELEVANT_TO_HOUSEHOLD.value
    if option_value == not_relevant:
        rules = pack.domain_applicability_rules.functional_domain_not_relevant_to_household
        return rules.allowed_domains.get(domain, True)
    return True


def _validate_flow_rule_references_and_routing(pack: DailyRoutinesContentPack) -> None:
    valid_q_ids = {q.id for q in pack.questions} | {ui.id for ui in pack.ui_state_controls}
    option_sets_by_id = {os.id: {opt.value for opt in os.options} for os in pack.option_sets}
    question_by_id = {q.id: q for q in pack.questions}

    seen_matchers: set[tuple[str, RouteMatchType, str | None]] = set()

    for rule in pack.flow_rules:
        if rule.source_question_id not in valid_q_ids:
            raise ContentPackValidationError(
                f"Flow rule {rule.rule_id!r} references unknown source_question_id "
                f"{rule.source_question_id!r}"
            )

        key = (rule.source_question_id, rule.match_type, rule.expected_value)
        if key in seen_matchers:
            raise ContentPackValidationError(
                f"Duplicate or conflicting flow rule matcher for {rule.source_question_id!r}: "
                f"match_type={rule.match_type.value!r}, expected_value={rule.expected_value!r}"
            )
        seen_matchers.add(key)

        if (
            rule.source_question_id in question_by_id
            and rule.match_type == RouteMatchType.EXACT_OPTION
        ):
            q_def = question_by_id[rule.source_question_id]
            if q_def.option_set_id and q_def.option_set_id in option_sets_by_id:
                allowed_opts = option_sets_by_id[q_def.option_set_id]
                if rule.expected_value not in allowed_opts:
                    raise ContentPackValidationError(
                        f"Flow rule {rule.rule_id!r} expected_value {rule.expected_value!r} "
                        f"not found in OptionSet for question {rule.source_question_id!r}"
                    )

        if rule.target_question_id is not None and rule.target_question_id not in valid_q_ids:
            raise ContentPackValidationError(
                f"Flow rule {rule.rule_id!r} references unknown target_question_id "
                f"{rule.target_question_id!r}"
            )

        if rule.target_module is not None and rule.target_module not in ALLOWED_TERMINAL_TARGETS:
            raise ContentPackValidationError(
                f"Flow rule {rule.rule_id!r} specifies unknown terminal target_module "
                f"{rule.target_module!r}"
            )

    flow_rules_by_source: dict[str, list[Any]] = {}
    for r in pack.flow_rules:
        flow_rules_by_source.setdefault(r.source_question_id, []).append(r)

    for q in pack.questions:
        rules = flow_rules_by_source.get(q.id, [])
        if q.answer_type == AnswerType.SINGLE_CHOICE:
            if not q.option_set_id or q.option_set_id not in option_sets_by_id:
                raise ContentPackValidationError(f"Question {q.id!r} missing option set")
            all_opts = option_sets_by_id[q.option_set_id]

            expected_opts = set(all_opts)
            for domain in [FunctionalDomain.SLEEPING, FunctionalDomain.BATHROOM]:
                if q.id.endswith(f"_{domain.value}_status"):
                    expected_opts = {
                        val
                        for val in expected_opts
                        if is_option_allowed_for_domain(pack, domain, val)
                    }

            exact_rules = [r for r in rules if r.match_type == RouteMatchType.EXACT_OPTION]
            routed_opts = {r.expected_value for r in exact_rules if r.expected_value}

            missing_opts = expected_opts - routed_opts
            if missing_opts:
                opts_str = sorted(missing_opts)
                raise ContentPackValidationError(
                    f"Question {q.id!r} has missing EXACT_OPTION rules: {opts_str}"
                )

        elif q.answer_type == AnswerType.MULTIPLE_CHOICE:
            multi_rules = [r for r in rules if r.match_type == RouteMatchType.ANY_VALID_MULTISELECT]
            if len(multi_rules) != 1:
                cnt = len(multi_rules)
                raise ContentPackValidationError(
                    f"Question {q.id!r} requires 1 ANY_VALID_MULTISELECT rule, got {cnt}"
                )

        elif q.answer_type == AnswerType.FREE_TEXT:
            text_rules = [r for r in rules if r.match_type == RouteMatchType.NON_EMPTY_TEXT]
            if len(text_rules) != 1:
                cnt = len(text_rules)
                raise ContentPackValidationError(
                    f"Question {q.id!r} requires 1 NON_EMPTY_TEXT rule, got {cnt}"
                )

    seen_selectors: set[CorrectionTarget] = set()
    for cr in pack.conditional_routes:
        if cr.selector_value in seen_selectors:
            raise ContentPackValidationError(
                f"Duplicate conditional route for selector_value {cr.selector_value.value!r}"
            )
        seen_selectors.add(cr.selector_value)
        if cr.target_question_id not in valid_q_ids:
            sel_val = cr.selector_value.value
            target_id = cr.target_question_id
            raise ContentPackValidationError(
                f"Conditional route {sel_val!r} unknown target_id {target_id!r}"
            )

    initial_q_id = "q_daily_routines_functional_space_day_pattern_status"
    visited_ids: set[str] = set()
    queue = [initial_q_id]

    for cr in pack.conditional_routes:
        queue.append(cr.target_question_id)

    while queue:
        curr = queue.pop(0)
        if curr in visited_ids:
            continue
        visited_ids.add(curr)

        for r in flow_rules_by_source.get(curr, []):
            if r.target_question_id and r.target_question_id not in visited_ids:
                queue.append(r.target_question_id)

    unreachable_qs = valid_q_ids - visited_ids
    if unreachable_qs:
        raise ContentPackValidationError(
            f"Orphan/unreachable questions or UI controls detected: {sorted(unreachable_qs)}"
        )


def _validate_invalidation_rules(pack: DailyRoutinesContentPack) -> None:
    valid_q_ids = {q.id for q in pack.questions} | {ui.id for ui in pack.ui_state_controls}

    seen_signature_targets: dict[tuple[str, str, str | None, str], str] = {}

    for inv in pack.invalidation_rules:
        if inv.source_question_id not in valid_q_ids:
            raise ContentPackValidationError(
                f"Invalidation rule {inv.rule_id!r} references unknown source_question_id "
                f"{inv.source_question_id!r}"
            )

        for target_id in inv.target_question_ids:
            if target_id not in valid_q_ids:
                raise ContentPackValidationError(
                    f"Invalidation rule {inv.rule_id!r} references unknown target_question_id "
                    f"{target_id!r}"
                )

            key = (inv.trigger_event, inv.source_question_id, inv.trigger_value, target_id)
            if key in seen_signature_targets:
                prev_rule_id = seen_signature_targets[key]
                if prev_rule_id != inv.rule_id:
                    raise ContentPackValidationError(
                        f"Conflicting invalidation rule {inv.rule_id!r} collides with "
                        f"{prev_rule_id!r} for target {target_id!r}"
                    )
            seen_signature_targets[key] = inv.rule_id
