"""Deterministic source binding for conversational metric requirements."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping

from brif_ai.spatial.metrics.models import (
    MetricRequirementType,
    MetricUnit,
    ProposedMetricRequirement,
)


class MetricSourceBindingError(ValueError):
    """Raised when a proposed metric is not fully supported by its user message."""


_APPROXIMATE_METRIC_KEYWORDS: tuple[str, ...] = (
    "yaklaşık",
    "civarında",
    "tahminen",
    "tahmini",
    "dolaylarında",
    "ortalama",
)
_MIN_METRIC_QUALIFIERS: tuple[str, ...] = ("en az", "minimum", "asgari")
_MAX_METRIC_QUALIFIERS: tuple[str, ...] = ("en fazla", "maksimum", "azami")
_CLEAR_WIDTH_KEYWORDS: tuple[str, ...] = (
    "genişlik",
    "genişliği",
    "net genişlik",
    "net genişliği",
)
_AREA_METRIC_UNITS_PATTERN = re.compile(r"(?:\b|\d\s*)(?:m²|m2|metrekare|metre\s+kare|sqm)(?!\w)")
_LENGTH_METRIC_UNITS_PATTERN = re.compile(r"(?:\b|\d\s*)(?:metre|meter|m)(?!\w)")
_METRIC_NUMBER_PATTERN = re.compile(r"(?<![\w])([+-]?[0-9]+(?:[.,][0-9]+)?)(?![\w])")
_WORD_PATTERN = re.compile(r"[0-9]+|[a-zçğıöşü]+", re.IGNORECASE)

# Turkish case suffixes that can be matched without guessing a different lexical root.
_SAFE_SUFFIXES = frozenset(
    {
        "",
        "ı",
        "i",
        "u",
        "ü",
        "a",
        "e",
        "yı",
        "yi",
        "yu",
        "yü",
        "ya",
        "ye",
        "nı",
        "ni",
        "nu",
        "nü",
        "na",
        "ne",
        "ın",
        "in",
        "un",
        "ün",
        "nın",
        "nin",
        "nun",
        "nün",
        "da",
        "de",
        "ta",
        "te",
        "nda",
        "nde",
        "dan",
        "den",
        "tan",
        "ten",
        "ndan",
        "nden",
        "lar",
        "ler",
        "ları",
        "leri",
    }
)
_SOFTENED_FINALS = {"p": "b", "ç": "c", "t": "d", "k": "ğ"}


def normalize_metric_source_text(text: str) -> str:
    """Normalize Turkish case and whitespace while preserving metric symbols."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(normalized.split())


def split_metric_clauses(text: str) -> list[str]:
    """Split clauses without splitting decimal comma/dot values."""
    normalized = normalize_metric_source_text(text)
    clauses: list[str] = []
    start = 0
    for index, char in enumerate(normalized):
        split_here = char in ";:!?\n"
        if char in ".,":
            previous_is_digit = index > 0 and normalized[index - 1].isdigit()
            next_is_digit = index + 1 < len(normalized) and normalized[index + 1].isdigit()
            split_here = not (previous_is_digit and next_is_digit)
        if split_here:
            clause = normalized[start:index].strip(" ,.")
            if clause:
                clauses.append(clause)
            start = index + 1
    final_clause = normalized[start:].strip(" ,.")
    if final_clause:
        clauses.append(final_clause)
    return clauses or [normalized]


def _token_matches_name_token(message_token: str, name_token: str) -> bool:
    if message_token == name_token:
        return True

    stems = {name_token}
    softened = _SOFTENED_FINALS.get(name_token[-1:])
    if softened is not None:
        stems.add(f"{name_token[:-1]}{softened}")

    return any(
        message_token.startswith(stem) and message_token[len(stem) :] in _SAFE_SUFFIXES
        for stem in stems
    )


def _name_match_spans(clause: str, display_name: str) -> list[tuple[int, int, int]]:
    clause_tokens = _WORD_PATTERN.findall(clause)
    name_tokens = _WORD_PATTERN.findall(normalize_metric_source_text(display_name))
    if not name_tokens or len(name_tokens) > len(clause_tokens):
        return []

    width = len(name_tokens)
    matches: list[tuple[int, int, int]] = []
    for start in range(len(clause_tokens) - width + 1):
        candidate = clause_tokens[start : start + width]
        if candidate[:-1] != name_tokens[:-1]:
            continue
        if _token_matches_name_token(candidate[-1], name_tokens[-1]):
            score = width * 1000 + sum(len(token) for token in name_tokens)
            matches.append((start, start + width, score))
    return matches


def _bound_space_ids(clause: str, available_spaces: Mapping[str, str]) -> set[str]:
    matches: list[tuple[str, int, int, int]] = []
    for space_id, display_name in available_spaces.items():
        for start, end, score in _name_match_spans(clause, display_name):
            matches.append((space_id, start, end, score))
    if not matches:
        return set()

    # Suppress only a shorter lexical match inside the same longer mention. Thus
    # "Çocuk Odası" does not also bind a generic "Oda", while separately written
    # targets ("Oda ve Büyük Mutfağı") remain correctly ambiguous.
    unshadowed: set[str] = set()
    for space_id, start, end, score in matches:
        shadowed = any(
            other_start <= start
            and end <= other_end
            and (other_start < start or end < other_end)
            and other_score > score
            for _, other_start, other_end, other_score in matches
        )
        if not shadowed:
            unshadowed.add(space_id)
    return unshadowed


def _numbers_in_clause(clause: str) -> list[float]:
    numbers: list[float] = []
    for match in _METRIC_NUMBER_PATTERN.finditer(clause):
        try:
            numbers.append(float(match.group(1).replace(",", ".")))
        except ValueError:  # pragma: no cover - regex already constrains the token
            continue
    return numbers


def _validate_metric_clause(
    clause: str,
    proposed_requirement: ProposedMetricRequirement,
) -> None:
    for approximate_word in _APPROXIMATE_METRIC_KEYWORDS:
        if approximate_word in clause:
            raise MetricSourceBindingError(
                f"Kullanıcı mesajındaki yaklaşık/belirsiz ifade ({approximate_word!r}) "
                "kesin metrik gereksinimi olarak önerilemez."
            )

    numbers = _numbers_in_clause(clause)
    if not numbers:
        raise MetricSourceBindingError("Kullanıcı mesajında açık bir sayısal değer bulunamadı.")
    if not any(
        math.isclose(number, proposed_requirement.value, abs_tol=1e-4) for number in numbers
    ):
        raise MetricSourceBindingError(
            f"Önerilen metrik değeri ({proposed_requirement.value}) kullanıcı mesajında belirtilen "
            f"sayısal değerler ({numbers}) ile eşleşmiyor."
        )

    has_minimum = any(qualifier in clause for qualifier in _MIN_METRIC_QUALIFIERS)
    has_maximum = any(qualifier in clause for qualifier in _MAX_METRIC_QUALIFIERS)

    if proposed_requirement.requirement_type == MetricRequirementType.MIN_AREA:
        if not has_minimum or has_maximum:
            raise MetricSourceBindingError(
                "MIN_AREA önerisi için kullanıcı mesajında açık asgari niteleyici "
                "('en az', 'minimum', 'asgari') bulunmalıdır."
            )
        if proposed_requirement.unit != MetricUnit.SQUARE_METRE:
            raise MetricSourceBindingError("MIN_AREA önerisi SQUARE_METRE birimini kullanmalıdır.")
        if not _AREA_METRIC_UNITS_PATTERN.search(clause):
            raise MetricSourceBindingError(
                "MIN_AREA önerisi için kullanıcı mesajında alan birimi "
                "('m²', 'm2', 'metrekare') bulunmalıdır."
            )
    elif proposed_requirement.requirement_type == MetricRequirementType.MAX_AREA:
        if not has_maximum or has_minimum:
            raise MetricSourceBindingError(
                "MAX_AREA önerisi için kullanıcı mesajında açık azami niteleyici "
                "('en fazla', 'maksimum', 'azami') bulunmalıdır."
            )
        if proposed_requirement.unit != MetricUnit.SQUARE_METRE:
            raise MetricSourceBindingError("MAX_AREA önerisi SQUARE_METRE birimini kullanmalıdır.")
        if not _AREA_METRIC_UNITS_PATTERN.search(clause):
            raise MetricSourceBindingError(
                "MAX_AREA önerisi için kullanıcı mesajında alan birimi "
                "('m²', 'm2', 'metrekare') bulunmalıdır."
            )
    elif proposed_requirement.requirement_type == MetricRequirementType.MIN_CLEAR_WIDTH:
        if not has_minimum or has_maximum:
            raise MetricSourceBindingError(
                "MIN_CLEAR_WIDTH önerisi için kullanıcı mesajında açık asgari niteleyici "
                "('en az', 'minimum', 'asgari') bulunmalıdır."
            )
        if proposed_requirement.unit != MetricUnit.METRE:
            raise MetricSourceBindingError("MIN_CLEAR_WIDTH önerisi METRE birimini kullanmalıdır.")
        if not any(keyword in clause for keyword in _CLEAR_WIDTH_KEYWORDS):
            raise MetricSourceBindingError(
                "MIN_CLEAR_WIDTH önerisi için kullanıcı mesajında net genişlik ifadesi "
                "('genişlik', 'net genişlik') bulunmalıdır."
            )
        if not _LENGTH_METRIC_UNITS_PATTERN.search(clause):
            raise MetricSourceBindingError(
                "MIN_CLEAR_WIDTH önerisi için kullanıcı mesajında uzunluk birimi "
                "('metre', 'm') bulunmalıdır."
            )
    else:
        raise MetricSourceBindingError(
            f"{proposed_requirement.requirement_type.value} konuşma tabanlı metrik "
            "önerilerinde desteklenmemektedir."
        )


def validate_metric_source_binding(
    *,
    user_message: str,
    proposed_requirement: ProposedMetricRequirement,
    available_spaces: Mapping[str, str],
) -> None:
    """Validate one proposal against one unambiguous, target-bound message clause."""
    if not user_message or not user_message.strip():
        raise MetricSourceBindingError("Kullanıcı mesajı metrik onayı için zorunludur.")
    if proposed_requirement.requirement_type not in {
        MetricRequirementType.MIN_AREA,
        MetricRequirementType.MAX_AREA,
        MetricRequirementType.MIN_CLEAR_WIDTH,
    }:
        raise MetricSourceBindingError(
            f"{proposed_requirement.requirement_type.value} konuşma tabanlı metrik "
            "önerilerinde desteklenmemektedir."
        )
    if proposed_requirement.space_id not in available_spaces:
        raise MetricSourceBindingError(
            f"Bilinmeyen mekân kimliği {proposed_requirement.space_id!r} "
            "metrik kaynağına bağlanamaz."
        )

    target_clauses: list[str] = []
    for clause in split_metric_clauses(user_message):
        bound_ids = _bound_space_ids(clause, available_spaces)
        if proposed_requirement.space_id in bound_ids:
            if len(bound_ids) != 1:
                raise MetricSourceBindingError(
                    "Kullanıcı mesajındaki metrik hedefi birden fazla mekâna bağlanabildiği için "
                    "belirsizdir."
                )
            target_clauses.append(clause)

    if not target_clauses:
        raise MetricSourceBindingError(
            f"Kullanıcı mesajı önerilen hedef mekâna "
            f"({available_spaces[proposed_requirement.space_id]!r}) açıkça bağlanmıyor."
        )
    if len(target_clauses) != 1:
        raise MetricSourceBindingError(
            "Kullanıcı mesajındaki metrik hedefi birden fazla ifadeye bağlandığı için belirsizdir."
        )

    _validate_metric_clause(target_clauses[0], proposed_requirement)


__all__ = [
    "MetricSourceBindingError",
    "normalize_metric_source_text",
    "split_metric_clauses",
    "validate_metric_source_binding",
]
