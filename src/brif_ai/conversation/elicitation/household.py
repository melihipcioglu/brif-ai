"""Structured extraction and deterministic normalization for household elicitation."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ConfigDict, Field

from brif_ai.core.models.common import ContractModel

_TURKISH_NUMBER_WORDS: dict[str, int] = {
    "bir": 1,
    "tek": 1,
    "iki": 2,
    "üç": 3,
    "dört": 4,
    "beş": 5,
    "alti": 6,
    "altı": 6,
    "yedi": 7,
    "sekiz": 8,
    "dokuz": 9,
    "on": 10,
}

_NUMBER_TOKEN = r"\d+|bir|iki|üç|dört|beş|altı|alti|yedi|sekiz|dokuz|on"
_TOTAL_COUNT_PATTERN = re.compile(
    rf"\b(?P<count>{_NUMBER_TOKEN})\s*kişi(?:lik|yiz|yizdir|dir|den|deniz|ler)?\b"
)
_ADULT_COUNT_PATTERN = re.compile(
    rf"\b(?P<count>{_NUMBER_TOKEN})\s*yetişkin\w*\b"
)
_CHILD_COUNT_PATTERN = re.compile(
    rf"\b(?P<count>{_NUMBER_TOKEN})\s*"
    r"(?:ve\s*\d+\s*yaşlarında\s*)?"
    r"(?:çocuk(?!\s+oda)\w*|çocuğ\w*|oğl\w*|kız\w*|evlat\w*)\b"
)
_SELF_PATTERN = re.compile(r"\b(?:ben|kendim)\b")
_SPOUSE_PATTERN = re.compile(r"\b(?:eşim\w*|karım\w*|kocam\w*|partnerim\w*)\b")
_HOUSEHOLD_CONTEXT_PATTERN = re.compile(
    r"\b(?:evde|hanede|aile\w*|yaşa\w*|otur\w*|kal\w*)\b"
)
_CHILD_REFERENCE_PATTERN = re.compile(
    r"\b(?:çocuk(?!\s+oda)\w*|çocuğ\w*|oğl\w*|kız\w*|evlat\w*)\b"
)
_AGE_LIST_PATTERN = re.compile(
    rf"\b(?P<ages>(?:{_NUMBER_TOKEN})"
    rf"(?:\s*(?:,|ve)\s*(?:{_NUMBER_TOKEN}))*)\s*yaş(?:ında|larında)\b"
)


def _parse_int(token: str) -> int | None:
    token_clean = token.strip().casefold()
    if token_clean.isdigit():
        return int(token_clean)
    return _TURKISH_NUMBER_WORDS.get(token_clean)


def _matched_count(pattern: re.Pattern[str], text: str) -> int | None:
    match = pattern.search(text)
    if match is None:
        return None
    return _parse_int(match.group("count"))


def _explicit_child_ages(text: str) -> list[int]:
    """Return ages explicitly linked to children in the current message."""
    for age_match in _AGE_LIST_PATTERN.finditer(text):
        before = text[max(0, age_match.start() - 40) : age_match.start()]
        after = text[age_match.end() : age_match.end() + 40]
        child_before = re.search(
            rf"{_CHILD_REFERENCE_PATTERN.pattern}\s*$",
            before,
        )
        child_after = re.match(
            rf"\s*(?:olan\s+)?(?:(?:{_NUMBER_TOKEN})\s+)?"
            rf"{_CHILD_REFERENCE_PATTERN.pattern}",
            after,
        )
        if child_before is None and child_after is None:
            continue

        ages = [
            _parse_int(token)
            for token in re.split(r"\s*(?:,|ve)\s*", age_match.group("ages"))
        ]
        return [age for age in ages if age is not None]

    return []


def has_defensible_household_evidence(text: str) -> bool:
    """Return whether the message itself grounds a household-count interpretation.

    This is a narrow hallucination guard around the LLM's structured semantic
    extraction, not a general natural-language parser. It recognizes only
    explicit counts or an occupant enumeration in household context.
    """
    text_clean = text.casefold()
    if any(
        pattern.search(text_clean) is not None
        for pattern in (
            _TOTAL_COUNT_PATTERN,
            _ADULT_COUNT_PATTERN,
            _CHILD_COUNT_PATTERN,
        )
    ):
        return True

    return (
        _SELF_PATTERN.search(text_clean) is not None
        and _SPOUSE_PATTERN.search(text_clean) is not None
        and _HOUSEHOLD_CONTEXT_PATTERN.search(text_clean) is not None
    )


class HouseholdComposition(ContractModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int | None = Field(default=None, ge=0)
    adult_count: int | None = Field(default=None, ge=0)
    child_count: int | None = Field(default=None, ge=0)
    child_ages: list[int] = Field(default_factory=list)
    notes: str | None = None


def reconcile_household_composition(comp: HouseholdComposition) -> HouseholdComposition:
    """Reconcile household counts with deterministic arithmetic only."""
    adults = comp.adult_count
    children = comp.child_count
    total = comp.total_count

    if adults is not None and children is not None:
        total = adults + children
    elif total is not None and adults is not None and children is None:
        if total >= adults:
            children = total - adults
    elif total is not None and children is not None and adults is None and total >= children:
        adults = total - children

    if total is None and adults is None and children is None:
        raise ValueError("Metinde hane halkı sayısı veya bileşimi saptanamadı.")

    return comp.model_copy(
        update={
            "total_count": total,
            "adult_count": adults,
            "child_count": children,
        }
    )


def _sanitize_llm_composition_against_explicit_evidence(
    text: str,
    comp: HouseholdComposition,
) -> HouseholdComposition:
    """Validate structured counts against narrow, explicit message constraints.

    The LLM remains the primary semantic extractor. This guard only honors
    directly stated counts, child ages, and the unambiguous self-plus-spouse
    enumeration, then removes details unsupported by the current message.
    """
    text_clean = text.casefold()
    explicit_total = _matched_count(_TOTAL_COUNT_PATTERN, text_clean)
    explicit_adults = _matched_count(_ADULT_COUNT_PATTERN, text_clean)
    explicit_children = _matched_count(_CHILD_COUNT_PATTERN, text_clean)
    explicit_child_ages = _explicit_child_ages(text_clean)
    enumerates_self = _SELF_PATTERN.search(text_clean) is not None
    enumerates_spouse = _SPOUSE_PATTERN.search(text_clean) is not None

    updates: dict[str, int | list[int] | None] = {
        "child_ages": explicit_child_ages,
    }
    if explicit_total is not None:
        updates["total_count"] = explicit_total

        # When the user states a total plus only one subgroup, the other
        # subgroup must be derived from that grounded pair rather than copied
        # from a possibly stale model aggregate. With total-only evidence,
        # neither subgroup is semantically known.
        if explicit_adults is None and not (enumerates_self and enumerates_spouse):
            updates["adult_count"] = None
        if explicit_children is None:
            updates["child_count"] = None
            updates["child_ages"] = []

    if explicit_adults is not None:
        updates["adult_count"] = explicit_adults
    elif enumerates_self and enumerates_spouse:
        updates["adult_count"] = max(comp.adult_count or 0, 2)

    if explicit_children is not None:
        updates["child_count"] = explicit_children

    return comp.model_copy(update=updates)


def extract_household_composition(
    text: str,
    llm_composition: HouseholdComposition | dict[str, Any] | None = None,
) -> HouseholdComposition:
    """Extract structured household facts and validate arithmetic consistency.

    LLM structured extraction is primary.
    Python acts as arithmetic and domain consistency authority.
    Raw text parsing is used only as a defensive fallback when structured LLM
    extraction is completely absent.
    """
    if isinstance(llm_composition, HouseholdComposition) and (
        llm_composition.total_count is not None
        or llm_composition.adult_count is not None
        or llm_composition.child_count is not None
    ):
        sanitized = _sanitize_llm_composition_against_explicit_evidence(
            text,
            llm_composition,
        )
        return reconcile_household_composition(sanitized)

    if isinstance(llm_composition, dict):
        try:
            parsed = HouseholdComposition.model_validate(llm_composition)
            if (
                parsed.total_count is not None
                or parsed.adult_count is not None
                or parsed.child_count is not None
            ):
                sanitized = _sanitize_llm_composition_against_explicit_evidence(
                    text,
                    parsed,
                )
                return reconcile_household_composition(sanitized)
        except Exception:
            pass

    # Defensive fallback parser from explicit raw-text facts only.
    text_clean = text.casefold()

    python_adults: int | None = None
    has_self = bool(re.search(r"\b(ben|kendim)\b", text_clean))
    has_spouse = bool(re.search(r"\b(eşim|eşimle|karım|kocam|partnerim)\b", text_clean))

    adult_match = re.search(r"(\d+|bir|iki|üç|dört|beş)\s*yetişkin", text_clean)
    if adult_match:
        python_adults = _parse_int(adult_match.group(1))
    elif has_self and has_spouse:
        python_adults = 2
    elif has_self or has_spouse:
        python_adults = 1

    python_children: int | None = None
    child_match = re.search(
        r"(\d+|bir|iki|üç|dört|beş)\s*(?:ve\s*\d+\s*yaşlarında\s*)?"
        r"(?:çocuk|çocuğum|çocuğumuz|oğlum|kızım|evlat)",
        text_clean,
    )
    if child_match:
        python_children = _parse_int(child_match.group(1))

    python_ages: list[int] = []
    age_match = re.search(r"(\d+)(?:\s*ve\s*(\d+))?\s*yaşlarında", text_clean)
    if age_match:
        python_ages.append(int(age_match.group(1)))
        if age_match.group(2):
            python_ages.append(int(age_match.group(2)))

    python_total: int | None = None
    total_match = re.search(
        r"(\d+|bir|iki|üç|dört|beş)\s*kişi(?:lik|yiz|ler)?",
        text_clean,
    )
    if total_match:
        python_total = _parse_int(total_match.group(1))

    fallback_comp = HouseholdComposition(
        total_count=python_total,
        adult_count=python_adults,
        child_count=python_children,
        child_ages=python_ages,
    )
    return reconcile_household_composition(fallback_comp)


def format_household_statement(comp: HouseholdComposition) -> str:
    """Construct deterministic Turkish brief statement for household composition."""
    if comp.adult_count is not None and comp.child_count is not None:
        details = f"{comp.adult_count} yetişkin, {comp.child_count} çocuk"
        if comp.child_ages:
            ages_str = ", ".join(str(age) for age in comp.child_ages)
            details += f": {ages_str} yaşlarında"
        return f"Evde {comp.total_count} kişi yaşayacak ({details})."

    if comp.total_count is not None:
        return f"Evde {comp.total_count} kişi yaşayacak."

    raise ValueError("Hane halkı sayısı tanımlanamadı.")
