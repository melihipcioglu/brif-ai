"""Deterministic analysis, validation, and realization for compare decisions."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from enum import Enum

from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    CompareApproach,
    CompareDecisionPlan,
    CompareGoalFamily,
    CompareMode,
    CompareOutcome,
    ConversationRequest,
    EntityTarget,
    IntentType,
)
from brif_ai.llm.policy_validator import (
    AlternativeQualityError,
    validate_alternative_quality,
    validate_relative_spatial_claims,
    validate_spatial_direction_claims,
)

_WORD_PATTERN = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+")
_SELECTION_EVIDENCE = re.compile(
    r"\b(?:hangisi|hangisini|birini\s+seç|arasında\s+seçim|öne\s+çıkarmalıyım)\b"
    r"|\b[^?.!\n]{1,80}?\s+m[ıiuü]\s+[^?.!\n]{1,80}?\s+m[ıiuü](?=\s|[?.!]|$)",
    re.IGNORECASE,
)
_MI_PAIR = re.compile(
    r"(?P<first>[^?.!\n]{1,80}?)\s+m[ıiuü]\s+"
    r"(?P<second>[^?.!\n]{1,80}?)\s+m[ıiuü](?=\s|[?.!]|$)",
    re.IGNORECASE,
)
_AXIS_PATTERNS = (
    re.compile(
        r"\bbirinde\s+(?P<first>[^,;.!?\n]{2,100}?)\s*,?\s+diğerinde\s+"
        r"(?P<second>[^;.!?\n]{2,100}?)(?=\s+(?:(?:daha\s+)?(?:baskın|önemli)"
        r"|ön\s+planda)\s+olsun\b|[;.!?\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbiri\s+(?P<first>[^,;.!?\n]{2,100}?)\s*,?\s+diğeri\s+"
        r"(?P<second>[^;.!?\n]{2,100}?)(?=[;.!?\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbirincide\s+(?P<first>[^,;.!?\n]{2,100}?)\s*,?\s+ikincide\s+"
        r"(?P<second>[^;.!?\n]{2,100}?)(?=[;.!?\n]|$)",
        re.IGNORECASE,
    ),
)
_AXIS_TAIL = re.compile(
    r"\s+(?:(?:daha\s+)?(?:baskın|önemli)|ön\s+planda)(?:\s+olsun)?\s*$",
    re.IGNORECASE,
)
_CASE_SUFFIX = (
    r"(?:larından|lerinden|larının|lerinin|sından|sinden|sunun|sünün|nın|nin|nun|nün|"
    r"ndan|nden|nda|nde|na|ne|ın|in|un|ün|yla|yle|da|de|dan|den|ta|te|"
    r"ya|ye|ı|i|u|ü|a|e)?"
)
_CONTENT_STOP_WORDS = frozenset(
    {
        "ve",
        "ile",
        "bir",
        "bu",
        "için",
        "olarak",
        "daha",
        "ilk",
        "ikinci",
        "birinci",
        "seçenek",
        "yaklaşım",
        "alternatif",
        "aynı",
        "farklı",
    }
)
_GENERIC_GENITIVE_SUFFIX = re.compile(
    r"(?P<stem>.{3,}?)(?:nın|nin|nun|nün|ın|in|un|ün)$",
    re.IGNORECASE,
)


class CompareFailureCategory(str, Enum):  # noqa: UP042 - Python 3.10 compatibility
    SCHEMA_INVALID = "SCHEMA_INVALID"
    MODE_MISMATCH = "MODE_MISMATCH"
    SEMANTIC_SUBJECT_SPLIT = "SEMANTIC_SUBJECT_SPLIT"
    AXIS_MISMATCH = "AXIS_MISMATCH"
    ENTITY_CHOICE_MISMATCH = "ENTITY_CHOICE_MISMATCH"
    UNSUPPORTED_SPATIAL_CLAIM = "UNSUPPORTED_SPATIAL_CLAIM"
    LANGUAGE_QUALITY = "LANGUAGE_QUALITY"
    ALTERNATIVES_TOO_SIMILAR = "ALTERNATIVES_TOO_SIMILAR"
    KEY_DIFFERENCE_INVALID = "KEY_DIFFERENCE_INVALID"
    UNSUPPORTED_QUANTITATIVE_CLAIM = "UNSUPPORTED_QUANTITATIVE_CLAIM"
    CONTEXT_FIDELITY = "CONTEXT_FIDELITY"


class ComparePlanValidationError(ValueError):
    """A structured compare plan failed a deterministic semantic rule."""

    def __init__(self, category: CompareFailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True, slots=True)
class CompareRequestAnalysis:
    mode: CompareMode
    subject_labels: tuple[str, ...]
    axes: tuple[str, str] | None
    choice_labels: tuple[str, str] | None
    goal_family: CompareGoalFamily
    open_approaches: tuple[CompareApproach, CompareApproach] | None

    def prompt_payload(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "subject_labels": list(self.subject_labels),
            "axis_1": self.axes[0] if self.axes else None,
            "axis_2": self.axes[1] if self.axes else None,
            "choice_1": self.choice_labels[0] if self.choice_labels else None,
            "choice_2": self.choice_labels[1] if self.choice_labels else None,
            "goal_family": self.goal_family.value,
            "outcome_hint_1": (
                _axis_outcome(self.axes[0]).value if self.axes is not None else None
            ),
            "outcome_hint_2": (
                _axis_outcome(self.axes[1]).value if self.axes is not None else None
            ),
            "recommended_approach_1": (
                self.open_approaches[0].value if self.open_approaches is not None else None
            ),
            "recommended_approach_2": (
                self.open_approaches[1].value if self.open_approaches is not None else None
            ),
        }


def _normalize(value: str) -> str:
    return " ".join(_WORD_PATTERN.findall(value.casefold()))


def _unique(values: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(value.split()).strip(" ,:;-–—.?!\"'")
        normalized = _normalize(cleaned)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        result.append(cleaned)
    return tuple(result)


def _label_pattern(label: str) -> re.Pattern[str] | None:
    words = _WORD_PATTERN.findall(label)
    if not words:
        return None
    body = r"\s+".join(re.escape(word) for word in words[:-1])
    if body:
        body += r"\s+"
    body += re.escape(words[-1]) + _CASE_SUFFIX
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def _label_in_text(label: str, text: str) -> bool:
    pattern = _label_pattern(label)
    return pattern.search(text) is not None if pattern is not None else False


def extract_explicit_axes(message: str) -> tuple[str, str] | None:
    """Extract only high-confidence paired Turkish preference axes."""

    for pattern in _AXIS_PATTERNS:
        match = pattern.search(message)
        if match is None:
            continue
        first = _AXIS_TAIL.sub("", match.group("first")).strip(" ,:;-–—")
        second = _AXIS_TAIL.sub("", match.group("second")).strip(" ,:;-–—")
        if (
            1 <= len(_WORD_PATTERN.findall(first)) <= 8
            and 1 <= len(_WORD_PATTERN.findall(second)) <= 8
        ):
            return first, second
    return None


def _visible_subjects(request: ConversationRequest) -> tuple[str, ...]:
    active = request.active_context
    found: list[tuple[int, str]] = []
    for entity in request.visible_entities:
        if entity.project_id != active.project_id:
            continue
        if active.building_id is not None and entity.building_id != active.building_id:
            continue
        if active.level_id is not None and entity.level_id != active.level_id:
            continue
        pattern = _label_pattern(entity.name)
        match = pattern.search(request.message) if pattern is not None else None
        if match is not None:
            found.append((match.start(), entity.name))
    return _unique([name for _, name in sorted(found)])


def _generic_pair_subjects(message: str) -> tuple[str, ...]:
    """Small fallback for named phrases around ``ile`` when entities are unavailable."""

    found: list[str] = []
    for match in re.finditer(r"\bile\b", message, re.IGNORECASE):
        left_words = _WORD_PATTERN.findall(message[max(0, match.start() - 50) : match.start()])
        right_words = _WORD_PATTERN.findall(message[match.end() : match.end() + 50])
        if left_words:
            found.append(" ".join(left_words[-3:]))
        if right_words:
            genitive_boundaries = {
                "arasındaki",
                "birlikte",
                "ilişkisi",
                "ilişkiyi",
                "kullanım",
            }
            boundary_words = genitive_boundaries | {"için"}
            selected: list[str] = []
            boundary: str | None = None
            for word in right_words[:4]:
                if word.casefold() in boundary_words:
                    boundary = word.casefold()
                    break
                selected.append(word)
            if selected and boundary in genitive_boundaries:
                suffix_match = _GENERIC_GENITIVE_SUFFIX.fullmatch(selected[-1])
                if suffix_match is not None:
                    selected[-1] = suffix_match.group("stem")
            if selected:
                found.append(" ".join(selected))
    return _unique(found)


def _choice_labels(
    request: ConversationRequest,
    subjects: tuple[str, ...],
) -> tuple[str, str] | None:
    match = _MI_PAIR.search(request.message)
    if match is not None:
        ordered_subjects = [label for label in subjects if _label_in_text(label, match.group(0))]
        if len(ordered_subjects) >= 2:
            return ordered_subjects[0], ordered_subjects[1]
        raw = _unique([match.group("first"), match.group("second")])
        if len(raw) == 2:
            return raw[0], raw[1]

    if len(subjects) == 2:
        return subjects[0], subjects[1]

    if re.search(r"\b(?:hangisi|hangisini|birini\s+seç)\b", request.message, re.IGNORECASE):
        active = request.active_context
        visible = [
            entity.name
            for entity in request.visible_entities
            if entity.project_id == active.project_id
            and (active.building_id is None or entity.building_id == active.building_id)
            and (active.level_id is None or entity.level_id == active.level_id)
        ]
        unique_visible = _unique(visible)
        if len(unique_visible) == 2:
            return unique_visible[0], unique_visible[1]
    return None


def analyze_compare_request(request: ConversationRequest) -> CompareRequestAnalysis:
    subjects = _visible_subjects(request)
    if not subjects:
        subjects = _generic_pair_subjects(request.message)
    axes = extract_explicit_axes(request.message)
    has_selection = _SELECTION_EVIDENCE.search(request.message) is not None
    choices = _choice_labels(request, subjects) if has_selection else None
    goal_family = _infer_goal_family(request.message)

    if has_selection:
        mode = CompareMode.ENTITY_CHOICE
    elif axes is not None:
        mode = CompareMode.EXPLICIT_AXES
    else:
        mode = CompareMode.OPEN_ALTERNATIVES

    return CompareRequestAnalysis(
        mode=mode,
        subject_labels=subjects,
        axes=axes,
        choice_labels=choices,
        goal_family=goal_family,
        open_approaches=(
            _recommend_open_approaches(goal_family)
            if mode is CompareMode.OPEN_ALTERNATIVES
            else None
        ),
    )


def _semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in _WORD_PATTERN.findall(value.casefold())
        if len(token) > 2 and token not in _CONTENT_STOP_WORDS
    }


def _tokens_related(left: str, right: str) -> bool:
    if left == right:
        return True
    if (
        len(left) >= 4
        and len(right) >= 4
        and (left.startswith(right[:4]) or right.startswith(left[:4]))
    ):
        return True
    families = (
        frozenset({"mahremiyet", "mahrem", "kişisel", "özel"}),
        frozenset({"kolaylık", "kolay", "akıcı", "erişim", "kullanım"}),
        frozenset({"sessizlik", "sessiz", "odaklanma", "odak"}),
        frozenset({"etkileşim", "birlikte", "sosyal", "paylaşım", "paylaşımı"}),
        frozenset({"esneklik", "esnek", "serbest", "uyarlanabilir"}),
        frozenset({"düzen", "kontrol", "denetim"}),
        frozenset({"gösteriş", "temsil", "etkileyici"}),
        frozenset({"sadelik", "sade", "yalın"}),
        frozenset({"bireysel", "tek", "kişisel"}),
        frozenset({"ortak", "birlikte", "işbirliği", "paylaşım", "paylaşımı"}),
    )
    return any(left in family and right in family for family in families)


def semantic_match(text: str, expected: str) -> bool:
    actual_tokens = _semantic_tokens(text)
    expected_tokens = _semantic_tokens(expected)
    return bool(expected_tokens) and any(
        _tokens_related(actual, target) for actual in actual_tokens for target in expected_tokens
    )


def _axis_outcome(axis: str) -> CompareOutcome:
    normalized = _normalize(axis)
    candidates = (
        (("iki kişi", "birlikte çalışma", "işbirliği"), CompareOutcome.COLLABORATIVE_PRODUCTIVITY),
        (("bireysel", "tek kişi"), CompareOutcome.INDIVIDUAL_PRODUCTIVITY),
        (("mahrem", "kişisel alan", "özel kullanım"), CompareOutcome.CONTROLLED_PERSONAL_USE),
        (("sessiz", "odak"), CompareOutcome.FOCUSED_ACTIVITY),
        (("aile", "etkileşim", "paylaşım"), CompareOutcome.SHARED_INTERACTION),
        (("düzen", "kontrol", "denetim"), CompareOutcome.ORDER_AND_OVERSIGHT),
        (("esnek", "serbest", "uyarlanabilir"), CompareOutcome.FLEXIBLE_SELF_DIRECTED_USE),
        (("gösteriş", "temsil", "etkileyici"), CompareOutcome.EXPRESSIVE_CHARACTER),
        (("sade", "yalın"), CompareOutcome.CALM_SIMPLICITY),
        (("kolay", "akıcı", "erişim"), CompareOutcome.EASY_DAILY_USE),
    )
    for fragments, outcome in candidates:
        if any(fragment in normalized for fragment in fragments):
            return outcome
    return CompareOutcome.CONTEXTUAL_PRIORITY


def _infer_goal_family(message: str) -> CompareGoalFamily:
    """Classify explicit behavior goals without inferring a building or room type."""

    normalized = _normalize(message)

    def contains(*fragments: str) -> bool:
        return any(fragment in normalized for fragment in fragments)

    if contains("mahrem", "kişisel alan", "özel kullanım"):
        return CompareGoalFamily.PRIVACY
    has_focus = contains("odak", "sessiz", "bireysel çalışma")
    has_collaboration = contains(
        "birlikte çalış",
        "ortak çalış",
        "işbirliği",
        "fikir paylaş",
    )
    if has_focus and has_collaboration:
        return CompareGoalFamily.FOCUS_COLLABORATION
    if contains("sohbet", "aileyle etkileşim", "birlikte geçirilen zaman"):
        return CompareGoalFamily.SOCIAL_INTERACTION
    if contains(
        "birlikte çalış",
        "koordin",
        "işlevsel ilişki",
        "birlikte işleyiş",
        "üretim akışı",
    ):
        return CompareGoalFamily.FUNCTIONAL_COORDINATION
    if contains("çok amaçlı", "esnek", "değişen", "dönüş"):
        return CompareGoalFamily.FLEXIBILITY
    if has_focus:
        return CompareGoalFamily.FOCUS
    if contains("sıra", "işleyiş", "rutin", "kontrol", "akış"):
        return CompareGoalFamily.ORDERED_FLOW
    return CompareGoalFamily.GENERAL_USE


def _recommend_open_approaches(
    goal_family: CompareGoalFamily,
) -> tuple[CompareApproach, CompareApproach]:
    """Map behavior goals, never building types, to safe decision families."""

    if goal_family is CompareGoalFamily.PRIVACY:
        return CompareApproach.PRIVACY_BALANCE, CompareApproach.INTEGRATED_FLOW
    if goal_family is CompareGoalFamily.FLEXIBILITY:
        return CompareApproach.ADAPTABLE_USE, CompareApproach.ORDERED_USE
    if goal_family is CompareGoalFamily.FOCUS_COLLABORATION:
        return CompareApproach.INDIVIDUAL_BALANCE, CompareApproach.SHARED_ACTIVITY
    if goal_family is CompareGoalFamily.SOCIAL_INTERACTION:
        return CompareApproach.SHARED_ACTIVITY, CompareApproach.PARALLEL_RHYTHMS
    if goal_family is CompareGoalFamily.FUNCTIONAL_COORDINATION:
        return CompareApproach.INTEGRATED_FLOW, CompareApproach.PARALLEL_RHYTHMS
    if goal_family is CompareGoalFamily.FOCUS:
        return CompareApproach.INDIVIDUAL_BALANCE, CompareApproach.ORDERED_USE
    if goal_family is CompareGoalFamily.ORDERED_FLOW:
        return CompareApproach.INTEGRATED_FLOW, CompareApproach.ORDERED_USE
    return CompareApproach.INTEGRATED_FLOW, CompareApproach.PARALLEL_RHYTHMS


_OPEN_OUTCOMES = {
    CompareApproach.INTEGRATED_FLOW: CompareOutcome.CONTINUOUS_INTERACTION,
    CompareApproach.PARALLEL_RHYTHMS: CompareOutcome.INDEPENDENT_SIMULTANEOUS_USE,
    CompareApproach.ADAPTABLE_USE: CompareOutcome.ADAPTABLE_DAILY_USE,
    CompareApproach.ORDERED_USE: CompareOutcome.PREDICTABLE_ROUTINE,
    CompareApproach.SHARED_ACTIVITY: CompareOutcome.SHARED_INTERACTION,
    CompareApproach.INDIVIDUAL_BALANCE: CompareOutcome.CONTROLLED_PERSONAL_USE,
    CompareApproach.PRIVACY_BALANCE: CompareOutcome.CONTROLLED_PERSONAL_USE,
}
_OPEN_APPROACHES = frozenset(_OPEN_OUTCOMES)


def sanitize_compare_plan(
    plan: CompareDecisionPlan,
    request: ConversationRequest,
) -> CompareDecisionPlan:
    """The enum-only plan has no untrusted public text to rewrite."""

    del request
    return plan


def build_compare_plan_schema(analysis: CompareRequestAnalysis) -> dict[str, object]:
    """Constrain enum branches with deterministic request analysis before inference."""

    schema = copy.deepcopy(CompareDecisionPlan.model_json_schema())
    properties = schema["properties"]
    if not isinstance(properties, dict):  # pragma: no cover - Pydantic contract invariant
        raise TypeError("compare plan schema properties must be an object")

    def constrain(field: str, values: tuple[str, ...]) -> None:
        properties[field] = {"type": "string", "enum": list(values)}

    constrain("mode", (analysis.mode.value,))
    if analysis.mode is CompareMode.OPEN_ALTERNATIVES:
        if analysis.open_approaches is None:  # pragma: no cover - analysis invariant
            raise ValueError("open mode requires recommended approaches")
        approach_1, approach_2 = analysis.open_approaches
        constrain("approach_1", (approach_1.value,))
        constrain("approach_2", (approach_2.value,))
        constrain("outcome_1", (_OPEN_OUTCOMES[approach_1].value,))
        constrain("outcome_2", (_OPEN_OUTCOMES[approach_2].value,))
    elif analysis.mode is CompareMode.EXPLICIT_AXES and analysis.axes is not None:
        constrain("approach_1", (CompareApproach.AXIS_1.value,))
        constrain("approach_2", (CompareApproach.AXIS_2.value,))
        constrain("outcome_1", (_axis_outcome(analysis.axes[0]).value,))
        constrain("outcome_2", (_axis_outcome(analysis.axes[1]).value,))
    elif analysis.mode is CompareMode.ENTITY_CHOICE:
        constrain("approach_1", (CompareApproach.CHOICE_1.value,))
        constrain("approach_2", (CompareApproach.CHOICE_2.value,))
        if analysis.choice_labels is not None:
            first, second = (_normalize(label) for label in analysis.choice_labels)
            if "açık" in first and "kapalı" in second:
                constrain("outcome_1", (CompareOutcome.OPEN_SHARED_USE.value,))
                constrain("outcome_2", (CompareOutcome.SEPARATED_CONTROLLED_USE.value,))
            else:
                entity_outcomes = (
                    CompareOutcome.INDOOR_CONTINUITY,
                    CompareOutcome.OUTDOOR_EXPERIENCE,
                    CompareOutcome.OPEN_SHARED_USE,
                    CompareOutcome.SEPARATED_CONTROLLED_USE,
                    CompareOutcome.FOCUSED_ACTIVITY,
                    CompareOutcome.SHARED_INTERACTION,
                    CompareOutcome.ADAPTABLE_DAILY_USE,
                    CompareOutcome.CONTROLLED_PERSONAL_USE,
                )
                constrain("outcome_1", tuple(outcome.value for outcome in entity_outcomes))
                constrain("outcome_2", tuple(outcome.value for outcome in entity_outcomes))
    return schema


def validate_compare_plan(
    plan: CompareDecisionPlan,
    request: ConversationRequest,
    analysis: CompareRequestAnalysis,
) -> None:
    """Enforce mode-specific semantic invariants before any public text exists."""

    del request
    if plan.mode is not analysis.mode:
        raise ComparePlanValidationError(
            CompareFailureCategory.MODE_MISMATCH,
            "Plan modu deterministik istek analiziyle eşleşmiyor.",
        )

    if analysis.mode is CompareMode.OPEN_ALTERNATIVES:
        if plan.approach_1 not in _OPEN_APPROACHES or plan.approach_2 not in _OPEN_APPROACHES:
            raise ComparePlanValidationError(
                CompareFailureCategory.MODE_MISMATCH,
                "Açık karşılaştırma yalnız organizasyon yaklaşımları kullanabilir.",
            )
        if plan.approach_1 is plan.approach_2:
            raise ComparePlanValidationError(
                CompareFailureCategory.ALTERNATIVES_TOO_SIMILAR,
                "İki yaklaşım aynı karar ilkesini kullanamaz.",
            )
        if (
            analysis.open_approaches is None
            or (
                plan.approach_1,
                plan.approach_2,
            )
            != analysis.open_approaches
        ):
            raise ComparePlanValidationError(
                CompareFailureCategory.MODE_MISMATCH,
                "Plan gereksinimlerden seçilen iki organizasyon ailesini korumuyor.",
            )
        if (
            plan.outcome_1 is not _OPEN_OUTCOMES[plan.approach_1]
            or plan.outcome_2 is not _OPEN_OUTCOMES[plan.approach_2]
        ):
            raise ComparePlanValidationError(
                CompareFailureCategory.KEY_DIFFERENCE_INVALID,
                "Yaklaşım ve kullanım sonucu semantik olarak eşleşmiyor.",
            )
        return

    if analysis.mode is CompareMode.EXPLICIT_AXES:
        if analysis.axes is None:
            raise ComparePlanValidationError(
                CompareFailureCategory.AXIS_MISMATCH,
                "Açık tercih eksenleri doğrulanamadı.",
            )
        if (
            plan.approach_1 is not CompareApproach.AXIS_1
            or plan.approach_2 is not CompareApproach.AXIS_2
            or plan.outcome_1 is not _axis_outcome(analysis.axes[0])
            or plan.outcome_2 is not _axis_outcome(analysis.axes[1])
        ):
            raise ComparePlanValidationError(
                CompareFailureCategory.AXIS_MISMATCH,
                "Plan iki güvenilir tercih eksenini doğru sırada korumuyor.",
            )
        return

    if analysis.choice_labels is None:
        raise ComparePlanValidationError(
            CompareFailureCategory.ENTITY_CHOICE_MISMATCH,
            "Açık seçim kanıtı iki seçenek üretmedi.",
        )
    if (
        plan.approach_1 is not CompareApproach.CHOICE_1
        or plan.approach_2 is not CompareApproach.CHOICE_2
        or plan.outcome_1 is plan.outcome_2
    ):
        raise ComparePlanValidationError(
            CompareFailureCategory.ENTITY_CHOICE_MISMATCH,
            "Plan iki açık seçeneği doğru sırada ve farklı sonuçlarla değerlendirmiyor.",
        )


@dataclass(frozen=True, slots=True)
class _ApproachLanguage:
    title: str
    decision: str
    effect: str
    difference: str


_APPROACH_LANGUAGE = {
    CompareApproach.INTEGRATED_FLOW: _ApproachLanguage(
        title="Bütünleşik işleyiş",
        decision=(
            "işlevsel ilişkiyi tek bir kullanım akışı içinde destekleyecek biçimde değerlendirilir"
        ),
        effect="etkinlikler arasındaki koordinasyon ve kullanım sürekliliği güçlenir",
        difference="işlevsel koordinasyonu ve kullanım sürekliliğini güçlendirir",
    ),
    CompareApproach.PARALLEL_RHYTHMS: _ApproachLanguage(
        title="Dengeli kullanım ritimleri",
        decision="farklı kullanım ritimlerini koruyan bir düzen içinde değerlendirilir",
        effect="eşzamanlı etkinlikler birbirini daha az etkileyerek sürdürülebilir",
        difference="eşzamanlı kullanımların bağımsızlığını korur",
    ),
    CompareApproach.ADAPTABLE_USE: _ApproachLanguage(
        title="Dönüşebilir kullanım",
        decision="değişen etkinliklere uyum veren esnek bir düzen içinde değerlendirilir",
        effect="farklı etkinlikler arasında kullanım değişikliği daha kolay gerçekleşir",
        difference="değişen etkinliklere uyum yeteneğini artırır",
    ),
    CompareApproach.ORDERED_USE: _ApproachLanguage(
        title="Belirgin işleyiş sırası",
        decision=(
            "işleyiş adımlarını belirgin bir sıra içinde destekleyecek biçimde değerlendirilir"
        ),
        effect="kullanım süreci daha öngörülebilir ve kolay izlenebilir ilerler",
        difference="işleyiş sürecinin öngörülebilirliğini artırır",
    ),
    CompareApproach.SHARED_ACTIVITY: _ApproachLanguage(
        title="Koordineli ortak kullanım",
        decision=(
            "ortak kullanılan etkinlikleri aynı işleyiş düzeninde destekleyecek biçimde "
            "değerlendirilir"
        ),
        effect="işlevlerin birbirini desteklemesi ve ortak kullanımın yönetilmesi kolaylaşır",
        difference="ortak kullanım içindeki işlevsel koordinasyonu güçlendirir",
    ),
    CompareApproach.INDIVIDUAL_BALANCE: _ApproachLanguage(
        title="Odaklı kullanım dengesi",
        decision="ortak ve bireysel etkinlikleri dengeleyen bir düzen içinde değerlendirilir",
        effect="odak gerektiren çalışmalar eşzamanlı ortak kullanımdan daha az etkilenir",
        difference="odak gerektiren kullanımın bağımsızlığını daha güçlü korur",
    ),
    CompareApproach.PRIVACY_BALANCE: _ApproachLanguage(
        title="Mahremiyet dengesi",
        decision="kişisel kullanımı koruyan kontrollü bir düzen içinde değerlendirilir",
        effect="mahremiyet deneyimi kullanım süreci boyunca daha güçlü korunur",
        difference="mahremiyet deneyimini daha güçlü korur",
    ),
}

_GOAL_LANGUAGE_OVERRIDES = {
    (
        CompareGoalFamily.SOCIAL_INTERACTION,
        CompareApproach.SHARED_ACTIVITY,
    ): _ApproachLanguage(
        title="Ortak kullanım ve sohbet",
        decision="oturma ve ortak etkinlikleri destekleyen bir kullanım düzeninde değerlendirilir",
        effect="sohbet ve ortak kullanım arasındaki etkileşim güçlenir",
        difference="sohbeti ve ortak kullanım etkileşimini güçlendirir",
    ),
    (
        CompareGoalFamily.FOCUS_COLLABORATION,
        CompareApproach.SHARED_ACTIVITY,
    ): _ApproachLanguage(
        title="Birlikte çalışma odağı",
        decision="ortak çalışmayı destekleyen bir kullanım düzeni içinde değerlendirilir",
        effect="birlikte çalışma ve bilgi paylaşımı daha belirgin biçimde desteklenir",
        difference="birlikte çalışma ve bilgi paylaşımını güçlendirir",
    ),
    (
        CompareGoalFamily.PRIVACY,
        CompareApproach.INTEGRATED_FLOW,
    ): _ApproachLanguage(
        title="Akıcı işleyiş",
        decision=(
            "kullanım adımlarını kesintisiz bir işleyiş içinde destekleyecek biçimde "
            "değerlendirilir"
        ),
        effect="işlemler arasındaki kullanım akışı daha akıcı ilerler",
        difference="kullanım adımları arasındaki işleyişi hızlandırır",
    ),
}

_UNGROUNDED_SOCIAL_LANGUAGE = (
    "yaşam düzeni",
    "gündelik yaşam",
    "aile birliği",
    "birlikte geçirilen zaman",
    "sohbet",
    "oturma ve ortak etkinlik",
)
_GOAL_SIGNAL_GROUPS: dict[
    CompareGoalFamily,
    tuple[tuple[str, ...], ...],
] = {
    CompareGoalFamily.SOCIAL_INTERACTION: (("sohbet", "etkileşim", "ortak kullanım"),),
    CompareGoalFamily.FUNCTIONAL_COORDINATION: (
        ("koordinasyon", "işlevsel", "işleyiş", "birbirini destek"),
    ),
    CompareGoalFamily.PRIVACY: (("mahrem",),),
    CompareGoalFamily.FOCUS_COLLABORATION: (
        ("odak", "dikkat"),
        ("birlikte çalışma", "ortak çalışma", "bilgi paylaş", "fikir paylaş"),
    ),
    CompareGoalFamily.FOCUS: (("odak", "dikkat"),),
    CompareGoalFamily.FLEXIBILITY: (("esnek", "değişen", "dönüş"),),
    CompareGoalFamily.ORDERED_FLOW: (("sıra", "işleyiş", "öngörülebilir", "akış"),),
}

_OUTCOME_LANGUAGE = {
    CompareOutcome.CONTINUOUS_INTERACTION: (
        "etkinlikler arasındaki koordinasyon ve kullanım sürekliliği güçlenir"
    ),
    CompareOutcome.INDEPENDENT_SIMULTANEOUS_USE: (
        "eşzamanlı etkinlikler birbirini daha az etkileyerek sürdürülebilir"
    ),
    CompareOutcome.ADAPTABLE_DAILY_USE: (
        "farklı etkinlikler arasında kullanım değişikliği daha kolay gerçekleşir"
    ),
    CompareOutcome.PREDICTABLE_ROUTINE: (
        "kullanım süreci daha öngörülebilir ve kolay izlenebilir ilerler"
    ),
    CompareOutcome.CONTROLLED_PERSONAL_USE: (
        "kişisel etkinlikler daha kontrollü ve kesintisiz sürdürülebilir"
    ),
    CompareOutcome.EASY_DAILY_USE: "hazırlık ve kullanım süreci daha akıcı ilerler",
    CompareOutcome.FOCUSED_ACTIVITY: "dikkat gerektiren etkinlikler daha az bölünerek sürer",
    CompareOutcome.SHARED_INTERACTION: (
        "ortak etkinlikler ve karşılıklı etkileşim daha güçlü desteklenir"
    ),
    CompareOutcome.ORDER_AND_OVERSIGHT: (
        "etkinliklerin düzeni ve izlenebilirliği daha öngörülebilir olur"
    ),
    CompareOutcome.FLEXIBLE_SELF_DIRECTED_USE: (
        "değişen etkinliklere kişisel uyum sağlamak kolaylaşır"
    ),
    CompareOutcome.EXPRESSIVE_CHARACTER: "mekânın temsil gücü daha belirgin hale gelir",
    CompareOutcome.CALM_SIMPLICITY: "kullanım deneyiminde görsel yük ve dikkat dağılımı azalır",
    CompareOutcome.INDIVIDUAL_PRODUCTIVITY: "tek kişinin odaklı çalışma düzeni güçlenir",
    CompareOutcome.COLLABORATIVE_PRODUCTIVITY: (
        "eşzamanlı üretim ve fikir paylaşımı daha güçlü desteklenir"
    ),
    CompareOutcome.INDOOR_CONTINUITY: "iç mekândaki ortak kullanım daha tutarlı sürer",
    CompareOutcome.OUTDOOR_EXPERIENCE: "açık hava deneyimi kullanım kararında ağırlık kazanır",
    CompareOutcome.OPEN_SHARED_USE: "ortak etkinlikler ve karşılıklı iletişim güçlenir",
    CompareOutcome.SEPARATED_CONTROLLED_USE: (
        "farklı etkinliklerin kontrolü ve bağımsızlığı artar"
    ),
}


def _subject_phrase(labels: tuple[str, ...]) -> str:
    if not labels:
        return "İstenen kullanım konuları"
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} ve {labels[-1]}"


def _title(value: str) -> str:
    first = {"i": "İ", "ı": "I"}.get(value[:1], value[:1].upper())
    return f"{first}{value[1:]}"


def _trusted_pair_relation(
    request: ConversationRequest,
    labels: tuple[str, ...],
) -> str | None:
    if len(labels) < 2:
        return None
    for clause in re.split(r"[.!?;\n]", request.message):
        if not all(_label_in_text(label, clause) for label in labels[:2]):
            continue
        match = re.search(
            r"(?P<relation>[^.!?;\n]{1,160}?\b(?:hemen\s+yanında|yakın(?:ında)?))\s+olsun\b",
            clause,
            re.IGNORECASE,
        )
        if match is not None:
            return " ".join(match.group("relation").split())
    return None


def _outcome_text(outcome: CompareOutcome, axis: str | None = None) -> str:
    if outcome is CompareOutcome.CONTEXTUAL_PRIORITY:
        priority = axis or "seçilen öncelik"
        return f"{priority} kullanım kararlarında daha tutarlı karşılık bulur"
    return _OUTCOME_LANGUAGE[outcome]


def _approach_language(
    approach: CompareApproach,
    goal_family: CompareGoalFamily,
) -> _ApproachLanguage:
    return _GOAL_LANGUAGE_OVERRIDES.get(
        (goal_family, approach),
        _APPROACH_LANGUAGE[approach],
    )


def _as_result(message: str, confidence: float) -> ArchitecturalIntentResult:
    return ArchitecturalIntentResult(
        assistant_message=message,
        intent=IntentType.COMPARE_ALTERNATIVES,
        target=EntityTarget(),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        needs_follow_up=False,
        follow_up_question=None,
        needs_user_confirmation=False,
        confidence=confidence,
        warnings=[],
    )


def render_compare_plan(
    plan: CompareDecisionPlan,
    request: ConversationRequest,
    analysis: CompareRequestAnalysis,
) -> ArchitecturalIntentResult:
    """Realize an enum-only semantic plan with grammar-safe Turkish sentence families."""

    subjects = _subject_phrase(analysis.subject_labels)
    if analysis.mode is CompareMode.OPEN_ALTERNATIVES:
        first = _approach_language(plan.approach_1, analysis.goal_family)
        second = _approach_language(plan.approach_2, analysis.goal_family)
        trusted_relation = _trusted_pair_relation(request, analysis.subject_labels)

        def summary(language: _ApproachLanguage) -> str:
            decision = f"{subjects} {language.decision}; {language.effect}."
            if trusted_relation is not None:
                return f"{trusted_relation} kalır. {decision}"
            return decision

        title_1 = first.title
        title_2 = second.title
        summary_1 = summary(first)
        summary_2 = summary(second)
        difference = f"İlk yaklaşım {first.difference}; ikinci yaklaşım {second.difference}."
    elif analysis.mode is CompareMode.EXPLICIT_AXES and analysis.axes is not None:
        axis_1, axis_2 = analysis.axes
        title_1 = _title(axis_1)
        title_2 = _title(axis_2)
        summary_1 = (
            f"{subjects} {axis_1} odağında değerlendirilir; "
            f"{_outcome_text(plan.outcome_1, axis_1)}."
        )
        summary_2 = (
            f"{subjects} {axis_2} odağında değerlendirilir; "
            f"{_outcome_text(plan.outcome_2, axis_2)}."
        )
        difference = (
            f"İlk yaklaşımda belirleyici ölçüt {axis_1}; "
            f"ikinci yaklaşımda belirleyici ölçüt {axis_2}."
        )
    elif analysis.choice_labels is not None:
        choice_1, choice_2 = analysis.choice_labels
        title_1 = choice_1
        title_2 = choice_2
        summary_1 = (
            f"{choice_1} ana kullanım tercihi olarak değerlendirilir; "
            f"{_outcome_text(plan.outcome_1)}."
        )
        summary_2 = (
            f"{choice_2} ana kullanım tercihi olarak değerlendirilir; "
            f"{_outcome_text(plan.outcome_2)}."
        )
        difference = (
            f"İlk tercihte {_outcome_text(plan.outcome_1)}; "
            f"ikinci tercihte {_outcome_text(plan.outcome_2)}."
        )
    else:  # pragma: no cover - validated before rendering
        raise ComparePlanValidationError(
            CompareFailureCategory.ENTITY_CHOICE_MISMATCH,
            "Karşılaştırılacak seçenekler bulunamadı.",
        )

    message = (
        f"Alternatif 1 - {title_1}: {summary_1}\n\n"
        f"Alternatif 2 - {title_2}: {summary_2}\n\n"
        f"Temel fark: {difference}"
    )
    return _as_result(message, plan.confidence)


def validate_context_fidelity(
    result: ArchitecturalIntentResult,
    request: ConversationRequest,
    analysis: CompareRequestAnalysis | None = None,
) -> None:
    """Reject open-mode language that is ungrounded or loses the compared subjects."""

    resolved_analysis = analysis or analyze_compare_request(request)
    if resolved_analysis.mode is not CompareMode.OPEN_ALTERNATIVES:
        return

    message = result.assistant_message
    normalized_message = message.casefold()
    if resolved_analysis.goal_family is not CompareGoalFamily.SOCIAL_INTERACTION:
        leaked = next(
            (phrase for phrase in _UNGROUNDED_SOCIAL_LANGUAGE if phrase in normalized_message),
            None,
        )
        if leaked is not None:
            raise ComparePlanValidationError(
                CompareFailureCategory.CONTEXT_FIDELITY,
                f"Açık karşılaştırma talepte bulunmayan sosyal bağlamı içeriyor: {leaked}.",
            )

    if resolved_analysis.subject_labels:
        expected_subject = _subject_phrase(resolved_analysis.subject_labels)
        subject_pattern = re.compile(
            rf"(?<!\w){re.escape(expected_subject)}(?=\s)",
            re.IGNORECASE,
        )
        if len(subject_pattern.findall(message)) < 2:
            raise ComparePlanValidationError(
                CompareFailureCategory.CONTEXT_FIDELITY,
                "Karşılaştırılan konular iki alternatifte de dilbilgisel olarak korunmuyor.",
            )

    for signal_group in _GOAL_SIGNAL_GROUPS.get(resolved_analysis.goal_family, ()):
        if not any(signal in normalized_message for signal in signal_group):
            raise ComparePlanValidationError(
                CompareFailureCategory.CONTEXT_FIDELITY,
                "Açık karşılaştırma talepteki kullanım hedefini sonuç diline yansıtmıyor.",
            )


def validate_rendered_compare(
    result: ArchitecturalIntentResult,
    request: ConversationRequest,
    analysis: CompareRequestAnalysis | None = None,
) -> None:
    """Defense-in-depth checks after deterministic language realization."""

    validate_context_fidelity(result, request, analysis)
    validate_alternative_quality(result, request)
    validate_spatial_direction_claims(result, request)
    validate_relative_spatial_claims(result, request)
    if re.search(
        r"\b(?:entity|target|enum|visible_entities|proposed_actions)\b",
        result.assistant_message,
        re.IGNORECASE,
    ):
        raise AlternativeQualityError("Son kullanıcı metni iç sistem dili içeriyor.")
