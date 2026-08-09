"""Project-context safety checks applied after schema validation."""

from __future__ import annotations

import re

from brif_ai.llm.contracts import (
    PLAN_CHANGE_ACTIONS,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    VisibleEntity,
)

_TURKISH_WORD_BOUND_PRE = r"(?<![\wıişğüçÖÇŞİĞÜ])"
_TURKISH_WORD_BOUND_POST = r"(?=[^\wıişğüçÖÇŞİĞÜ]|$)"
_COPULA = r"(?:dır|dir|dur|dür|tır|tir|tur|tür)?"

_INTERNAL_ID_PATTERN = re.compile(
    r"(?<![\w])(?P<identifier>"
    r"(?:space|project|building|block|level|lvl|zone|entity)_"
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
    r")(?![\w])",
    re.IGNORECASE,
)
FORBIDDEN_PUBLIC_TERMS: tuple[str, ...] = (
    "entity_id",
    "entity",
    "target_entity_id",
    "target",
    "enum",
    "öğe bilgisi",
    "ilgili mekân",
    "visible_entities",
    "aktif kapsam kimliği",
)

_PUBLIC_FALLBACKS = {
    "space": "mekân",
    "project": "proje",
    "building": "yapı",
    "block": "yapı",
    "level": "kat",
    "lvl": "kat",
    "zone": "bölge",
    "entity": "öğe",
}
_PUBLIC_TECHNICAL_TERM_REPLACEMENTS = (
    ("pending_user_confirmation", "kullanıcı onayı bekleniyor"),
    ("requires_user_confirmation", "kullanıcı onayı gerekiyor"),
    ("needs_user_confirmation", "kullanıcı onayı gereksinimi"),
    ("needs_follow_up", "ek bilgi gereksinimi"),
    ("follow_up_question", "takip sorusu"),
    ("assistant_message", "asistan yanıtı"),
    ("pending_proposals", "bekleyen öneriler"),
    ("pending_proposal", "bekleyen öneri"),
    ("proposed_actions", "önerilen adımlar"),
    ("proposed_action", "önerilen adım"),
    ("conversation_summary", "konuşma özeti"),
    ("current_decisions", "mevcut kararlar"),
    ("visible_entities", "görünür mekânlar"),
    ("active_context", "aktif bağlam"),
    ("context_fingerprint", "bağlam bilgisi"),
    ("generation_id", "bağlam sürümü"),
    ("target_entity_id", "mekân bilgisi"),
    ("entity_id", "mekân bilgisi"),
    ("project_id", "proje bilgisi"),
    ("building_id", "yapı bilgisi"),
    ("level_id", "kat bilgisi"),
    ("zone_id", "bölge bilgisi"),
    ("action_type", "öneri türü"),
    ("intent_type", "talep türü"),
    ("user_requirements", "kullanıcı gereksinimleri"),
    ("interpreted_priorities", "yorumlanan öncelikler"),
    ("constraints_to_check", "incelenecek kısıtlar"),
    ("missing_information", "eksik bilgiler"),
    ("gather_requirement", "gereksinim toplama"),
    ("modify_relationship", "mekânsal ilişki düzenleme önerisi"),
    ("modify_space", "mekân düzenleme önerisi"),
    ("explain_plan", "plan açıklaması"),
    ("compare_alternatives", "alternatif karşılaştırması"),
    ("inspect_constraint", "kısıt incelemesi"),
    ("request_visual_preference", "görsel tercih talebi"),
    ("highlight_entity", "ilgili öğeyi vurgulama"),
    ("focus_entity", "ilgili öğeye odaklanma"),
    ("request_clarification", "açıklama isteme"),
    ("suggest_space_resize", "mekân boyutu önerisi"),
    ("suggest_relationship_change", "mekânsal ilişki önerisi"),
    ("suggest_orientation_change", "yönlenme önerisi"),
    ("aktif kapsam kimliği", "aktif proje kapsamı"),
    ("aktif kapsam kimligi", "aktif proje kapsamı"),
    ("ilgili mekân", "ilgili alan"),
    ("ilgili mekan", "ilgili alan"),
    ("öğe bilgisi", "mekân bilgisi"),
    ("oge bilgisi", "mekan bilgisi"),
    ("target", "hedef"),
    ("entity", "mekân"),
    ("enum", "seçenek"),
)


def _internal_term_pattern(term: str) -> re.Pattern[str]:
    words = term.split(" ") if " " in term else term.split("_")
    return re.compile(
        _TURKISH_WORD_BOUND_PRE + r"[_\s-]*".join(map(re.escape, words)) + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    )


_PUBLIC_TECHNICAL_TERM_PATTERNS = tuple(
    (_internal_term_pattern(term), replacement)
    for term, replacement in sorted(
        _PUBLIC_TECHNICAL_TERM_REPLACEMENTS, key=lambda pair: len(pair[0]), reverse=True
    )
)


def _localize_internal_terms(text: str) -> str:
    for pattern, replacement in _PUBLIC_TECHNICAL_TERM_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


_RELATIONSHIP_TERMS = (
    "görünür",
    "görünmesin",
    "mahrem",
    "yakın",
    "uzak",
    "bağlant",
    "geçiş",
    "erişim",
    "ilişki",
    "kopuk",
    "yan yana",
    "ses ilişk",
    "akustik iliş",
    "komşu",
    "arasında",
)


def sanitize_public_text(text: str, visible_entities: list[VisibleEntity]) -> str:
    """Remove machine identifiers from text that can be shown to a user."""

    entity_names = {entity.entity_id.casefold(): entity.name for entity in visible_entities}

    def replacement(match: re.Match[str]) -> str:
        identifier = match.group("identifier")
        entity_name = entity_names.get(identifier.casefold())
        if entity_name is not None:
            return entity_name
        prefix = identifier.split("_", maxsplit=1)[0].casefold()
        return _PUBLIC_FALLBACKS.get(prefix, "öğe")

    sanitized = _localize_internal_terms(text)
    sanitized = _INTERNAL_ID_PATTERN.sub(replacement, sanitized)
    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" +([,.!?;:])", r"\1", sanitized)
    sanitized = "\n".join(line.strip() for line in sanitized.splitlines()).strip()
    return sanitized or "Mekân kapsamı hakkında ek bilgi gerekiyor."


_FORBIDDEN_SYSTEM_PATTERNS = tuple(
    re.compile(
        r"(?<![\w])" + re.escape(term) + r"(?![\w])"
        if re.match(r"^\w+$", term)
        else re.escape(term),
        re.IGNORECASE,
    )
    for term in FORBIDDEN_PUBLIC_TERMS
)


class PolicyValidationError(ValueError):
    """A schema-valid model response violated active project policy."""


class ScopeMismatchError(PolicyValidationError):
    """A schema-valid response referenced a scope that is not currently active."""


class UnsupportedSpatialClaimError(PolicyValidationError):
    """Model output contained spatial/directional claims not supported by request context."""


class AlternativeQualityError(PolicyValidationError):
    """Model-generated architectural alternatives failed quality, distinctness, or format checks."""


FORBIDDEN_FILLER_PHRASES: tuple[str, ...] = (
    "yakınında bir konumda",
    "yakın bir konumda",
    "uygun bir konumda",
    "uygun konumlu",
    "uygun konum doğrultusunda",
)
MAX_FILLER_PHRASE_REPEATS: int = 1
MIN_ALTERNATIVE_WORD_COUNT: int = 6
MAX_ALTERNATIVE_WORD_COUNT: int = 70
MAX_ALTERNATIVE_SIMILARITY_SCORE: float = 0.50
COMMON_TURKISH_STOP_WORDS: set[str] = {
    "ve",
    "ile",
    "de",
    "da",
    "bir",
    "bu",
    "için",
    "olarak",
    "daha",
    "en",
    "veya",
    "gibi",
    "hem",
    "her",
    "göre",
    "ise",
}


def compute_alternative_similarity(
    alt1: str,
    alt2: str,
    prompt_text: str = "",
) -> float:
    """Compute n-gram similarity between two alternatives excluding prompt words & stop words."""
    prompt_words = set(re.findall(r"[\wıişğüçÖÇŞİĞÜ]+", prompt_text.casefold()))

    def _tokens(s: str) -> list[str]:
        words = re.findall(r"[\wıişğüçÖÇŞİĞÜ]+", s.casefold())
        return [
            w
            for w in words
            if len(w) > 1 and w not in COMMON_TURKISH_STOP_WORDS and w not in prompt_words
        ]

    tokens1 = _tokens(alt1)
    tokens2 = _tokens(alt2)

    if not tokens1 or not tokens2:
        return 0.0

    set1, set2 = set(tokens1), set(tokens2)
    jaccard_1gram = len(set1 & set2) / max(1, len(set1 | set2))

    def _ngrams(toks: list[str], n: int) -> set[tuple[str, ...]]:
        return {tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)}

    ngrams2_1 = _ngrams(tokens1, 2)
    ngrams2_2 = _ngrams(tokens2, 2)
    min2 = min(len(ngrams2_1), len(ngrams2_2))
    overlap_2gram = len(ngrams2_1 & ngrams2_2) / max(1, min2) if min2 > 0 else 0.0

    ngrams3_1 = _ngrams(tokens1, 3)
    ngrams3_2 = _ngrams(tokens2, 3)
    min3 = min(len(ngrams3_1), len(ngrams3_2))
    overlap_3gram = len(ngrams3_1 & ngrams3_2) / max(1, min3) if min3 > 0 else 0.0

    return max(jaccard_1gram, overlap_2gram, overlap_3gram)


def validate_alternative_quality(
    result: ArchitecturalIntentResult,
    request: ConversationRequest,
) -> None:
    """Validate format, distinctness, word limits, and phrasing for comparison responses."""
    text = result.assistant_message.strip()

    # 1. Filler phrase repetition check
    text_lower = text.casefold()
    total_fillers = sum(text_lower.count(phrase) for phrase in FORBIDDEN_FILLER_PHRASES)
    single_repeated = any(text_lower.count(phrase) >= 2 for phrase in FORBIDDEN_FILLER_PHRASES)
    if single_repeated or total_fillers > MAX_FILLER_PHRASE_REPEATS:
        raise AlternativeQualityError(
            "Yapay dolgu ifadesi ('yakınında bir konumda' vb.) yanıtta tekrarlandı. "
            "Daha doğal Türkçe anlatım kullanılmalıdır."
        )

    # 2. Extract sections: Alternatif 1, Alternatif 2, Temel fark
    section1_match = re.search(
        r"(?:Alternatif\s*1|1\.|Birinci\s+alternatif)[^\n:\-–—]*[:\-–—]?\s*",
        text,
        re.IGNORECASE,
    )
    section2_match = re.search(
        r"(?:Alternatif\s*2|2\.|İkinci\s+alternatif)[^\n:\-–—]*[:\-–—]?\s*",
        text,
        re.IGNORECASE,
    )
    key_diff_match = re.search(
        r"(?:Temel\s+fark|Fark)[^\n:\-–—]*[:\-–—]?\s*",
        text,
        re.IGNORECASE,
    )

    if not (section1_match and section2_match and key_diff_match):
        raise AlternativeQualityError(
            "Karşılaştırma yanıtı 'Alternatif 1', 'Alternatif 2' ve 'Temel fark:' "
            "bölümlerini içermelidir."
        )

    pos1_end = section1_match.end()
    pos2_start = section2_match.start()
    pos2_end = section2_match.end()
    diff_start = key_diff_match.start()
    diff_end = key_diff_match.end()

    if not (pos1_end < pos2_start < diff_start):
        raise AlternativeQualityError(
            "Karşılaştırma yanıtındaki bölümler sırasıyla 'Alternatif 1', 'Alternatif 2' "
            "ve 'Temel fark:' şeklinde dizilmelidir."
        )

    alt1_content = text[pos1_end:pos2_start].strip()
    alt2_content = text[pos2_end:diff_start].strip()
    diff_content = text[diff_end:].strip()

    if not alt1_content or not alt2_content or not diff_content:
        raise AlternativeQualityError(
            "Alternatif başlıkları ve 'Temel fark:' içeriği boş kalmamalıdır."
        )

    # 3. Word count / length check
    words_alt1 = re.findall(r"[\wıişğüçÖÇŞİĞÜ]+", alt1_content)
    words_alt2 = re.findall(r"[\wıişğüçÖÇŞİĞÜ]+", alt2_content)
    words_diff = re.findall(r"[\wıişğüçÖÇŞİĞÜ]+", diff_content)

    if len(words_alt1) < MIN_ALTERNATIVE_WORD_COUNT or len(words_alt2) < MIN_ALTERNATIVE_WORD_COUNT:
        raise AlternativeQualityError(
            "Alternatif açıklamaları çok kısa "
            f"(en az {MIN_ALTERNATIVE_WORD_COUNT} kelime olmalıdır)."
        )

    if len(words_alt1) > MAX_ALTERNATIVE_WORD_COUNT or len(words_alt2) > MAX_ALTERNATIVE_WORD_COUNT:
        raise AlternativeQualityError(
            "Alternatif açıklamaları çok uzun "
            f"(en fazla {MAX_ALTERNATIVE_WORD_COUNT} kelime olmalıdır)."
        )

    if len(words_diff) < 3:
        raise AlternativeQualityError("Temel fark açıklaması yetersiz veya boş.")

    # 4. Distinctness / Similarity check
    similarity = compute_alternative_similarity(alt1_content, alt2_content, request.message)
    if (
        alt1_content.casefold() == alt2_content.casefold()
        or similarity > MAX_ALTERNATIVE_SIMILARITY_SCORE
    ):
        raise AlternativeQualityError(
            "Önerilen iki alternatif birbirinden yeterince farklı değil. "
            "İki ayrı mimari yaklaşım sunulmalıdır."
        )


_TURKISH_WORD_BOUND_PRE = r"(?<![\wıişğüçÖÇŞİĞÜ])"
_TURKISH_WORD_BOUND_POST = r"(?=[^\wıişğüçÖÇŞİĞÜ]|$)"

DIRECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "kuzey": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"kuzey(?:doğu|batı|e|de|den|in|ine|ini|inde|inden|inin|i|deki|indek[iı]|lü|lük)?"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "güney": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"güney(?:doğu|batı|e|de|den|in|ine|ini|inde|inden|inin|i|deki|indek[iı]|li|lik)?"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "doğu": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"doğu(?:da|dan|ya|su|sunda|sundan|suna|sunu|sunun|daki|sundak[iı]|lu|luk)?"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "batı": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"batı(?:da|dan|ya|sı|sında|sından|sına|sını|sının|daki|sındak[iı]|lı|lık)?"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
}


def extract_trusted_direction_evidence(request: ConversationRequest) -> set[str]:
    """Extract canonical compass directions explicitly present in trusted request context."""
    texts: list[str] = [request.message]

    if request.conversation_summary:
        texts.append(request.conversation_summary)

    for decision in request.current_decisions:
        if isinstance(decision, str):
            texts.append(decision)
        elif hasattr(decision, "description") and decision.description:
            texts.append(str(decision.description))
        elif isinstance(decision, dict) and decision.get("description"):
            texts.append(str(decision["description"]))

    for proposal in request.pending_proposals:
        if hasattr(proposal, "action") and hasattr(proposal.action, "description"):
            if proposal.action.description:
                texts.append(proposal.action.description)
        elif isinstance(proposal, dict):
            action = proposal.get("action", {})
            if isinstance(action, dict) and action.get("description"):
                texts.append(str(action["description"]))

    for entity in request.visible_entities:
        if entity.name:
            texts.append(entity.name)

    evidence: set[str] = set()
    combined = " ".join(texts)
    for canonical, pattern in DIRECTION_PATTERNS.items():
        if pattern.search(combined):
            evidence.add(canonical)

    return evidence


def validate_spatial_direction_claims(
    result: ArchitecturalIntentResult,
    request: ConversationRequest,
) -> None:
    """Ensure no ungrounded compass directions exist in public model output fields."""
    trusted_evidence = extract_trusted_direction_evidence(request)

    public_texts = [
        result.assistant_message,
        *([result.follow_up_question] if result.follow_up_question is not None else []),
        *result.user_requirements,
        *result.interpreted_priorities,
        *result.constraints_to_check,
        *result.missing_information,
        *result.warnings,
        *(action.description for action in result.proposed_actions if action.description),
    ]

    combined = " ".join(public_texts)
    model_directions: set[str] = set()
    for canonical, pattern in DIRECTION_PATTERNS.items():
        if pattern.search(combined):
            model_directions.add(canonical)

    unsupported = model_directions - trusted_evidence
    if unsupported:
        sorted_unsupported = sorted(unsupported)
        unsupported_str = ", ".join(sorted_unsupported)
        raise UnsupportedSpatialClaimError(
            f"Kullanıcı bağlamında bulunmayan yön bilgisi ({unsupported_str}) kullanıldı."
        )


_NOUN_GENITIVE = (
    r"(?<![\wıişğüçÖÇŞİĞÜ])(?P<noun>[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:ın|in|un|ün|nın|nin|nun|nün))\s+"
)
_COPULA = r"(?:dır|dir|dur|dür|tır|tir|tur|tür)?"


def neutralize_unsupported_spatial_directions(
    text: str,
    unsupported_directions: set[str],
) -> str:
    """Neutralize ungrounded compass directions in text to directionless natural Turkish phrases."""
    if not unsupported_directions:
        return text

    sanitized = text
    for d in sorted(unsupported_directions):
        rules = (
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?\s+cephe(?:sindeki|sinden|sine|sinde|si|siyle)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "uygun bir cephe kurgusunda",
            ),
            (
                re.compile(
                    _NOUN_GENITIVE + d + r"(?:doğu|batı)?(?:si|sı|su|sü|i|ı|u|ü)?"
                    r"(?:nde|nda|ne|na|nden|ndan|deki|daki|ndaki|ndeki|de|da|ye|ya|e|a)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                r"\g<noun> yakınında bir konumda",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?\s+tarafı(?:nda|na|ndan|nı|nı)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "yakınındaki alanda",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?\s+yönü(?:nde|ne|nden|nü)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "uygun konum doğrultusunda",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?(?:si|sı|su|sü|i|ı|u|ü)?(?:nde|nda|deki|daki|ndaki|ndeki)"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "yakın bir konumda",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?(?:si|sı|su|sü|i|ı|u|ü)?(?:ne|na|ye|ya|e|a)"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "uygun bir konuma",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?(?:si|sı|su|sü|i|ı|u|ü)?(?:nden|ndan|den|dan)"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "yakın konumundan",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?(?:de|da)"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "uygun bir konumda",
            ),
            (
                re.compile(
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "uygun konumlu",
            ),
        )
        for pattern, replacement in rules:
            sanitized = pattern.sub(replacement, sanitized)

    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" +([,.!?;:])", r"\1", sanitized)
    return sanitized


class ArchitecturalIntentPolicyValidator:
    """Treat model output as untrusted suggestions constrained by active context."""

    def sanitize(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        """Sanitize machine IDs, internal terms, and neutralize unsupported spatial directions."""
        trusted_evidence = extract_trusted_direction_evidence(request)

        public_texts = [
            result.assistant_message,
            *([result.follow_up_question] if result.follow_up_question is not None else []),
            *result.user_requirements,
            *result.interpreted_priorities,
            *result.constraints_to_check,
            *result.missing_information,
            *result.warnings,
            *(action.description for action in result.proposed_actions if action.description),
        ]
        combined = " ".join(public_texts)
        model_directions: set[str] = set()
        for canonical, pattern in DIRECTION_PATTERNS.items():
            if pattern.search(combined):
                model_directions.add(canonical)

        unsupported_directions = model_directions - trusted_evidence

        def _clean(text: str) -> str:
            text = sanitize_public_text(text, request.visible_entities)
            if unsupported_directions:
                text = neutralize_unsupported_spatial_directions(text, unsupported_directions)
            return text

        actions = [
            action.model_copy(update={"description": _clean(action.description)})
            for action in result.proposed_actions
        ]
        sanitized = result.model_copy(
            update={
                "assistant_message": _clean(result.assistant_message),
                "follow_up_question": (
                    _clean(result.follow_up_question)
                    if result.follow_up_question is not None
                    else None
                ),
                "user_requirements": [_clean(text) for text in result.user_requirements],
                "interpreted_priorities": [_clean(text) for text in result.interpreted_priorities],
                "constraints_to_check": [_clean(text) for text in result.constraints_to_check],
                "missing_information": [_clean(text) for text in result.missing_information],
                "proposed_actions": actions,
                "warnings": [_clean(text) for text in result.warnings],
            }
        )
        if not sanitized.needs_follow_up:
            return sanitized.model_copy(update={"follow_up_question": None})
        return sanitized

    def validate_semantic_integrity(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> None:
        """Validate post-schema semantic rules and forbid internal system jargon."""

        public_texts = [
            result.assistant_message,
            *([result.follow_up_question] if result.follow_up_question is not None else []),
            *result.user_requirements,
            *result.interpreted_priorities,
            *result.constraints_to_check,
            *result.missing_information,
            *result.warnings,
            *(action.description for action in result.proposed_actions),
        ]
        combined = " ".join(public_texts).casefold()
        for pattern in _FORBIDDEN_SYSTEM_PATTERNS:
            match = pattern.search(combined)
            if match:
                raise PolicyValidationError(
                    f"İç sistem dili / yasaklı terim saptandı: {match.group(0)!r}"
                )

        validate_spatial_direction_claims(result, request)

        msg_lower = request.message.casefold()
        is_compare = any(
            kw in msg_lower
            for kw in (
                "alternatif",
                "karşılaştır",
                "seçenek",
                "iki farklı",
                "2 alternatif",
                "düzenleme alternatifi",
            )
        )

        if is_compare:
            if result.intent != IntentType.COMPARE_ALTERNATIVES:
                raise PolicyValidationError(
                    "Alternatif talebi için intent 'compare_alternatives' olmalıdır."
                )

            if result.needs_follow_up:
                raise PolicyValidationError(
                    "Kavramsal alternatif talebinde takip sorusu üretilmemelidir "
                    "(needs_follow_up=false olmalı)."
                )

            validate_alternative_quality(result, request)

    def validate(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        result = self._normalize_intent(result, request)
        result = self.sanitize(result, request)
        self.validate_semantic_integrity(result, request)
        active = request.active_context
        target = result.target

        if result.intent == IntentType.COMPARE_ALTERNATIVES:
            return result.model_copy(
                update={
                    "target": EntityTarget(
                        project_id=None,
                        building_id=None,
                        level_id=None,
                        zone_id=None,
                        entity_id=None,
                    ),
                    "proposed_actions": [],
                    "needs_user_confirmation": False,
                    "needs_follow_up": False,
                    "follow_up_question": None,
                }
            )

        self._match_scope("project_id", target.project_id, active.project_id)
        self._match_scope("building_id", target.building_id, active.building_id)
        self._match_scope("level_id", target.level_id, active.level_id)
        self._match_scope("zone_id", target.zone_id, active.zone_id)

        visible_ids = {
            entity.entity_id
            for entity in request.visible_entities
            if entity.project_id == active.project_id
            and (active.building_id is None or entity.building_id == active.building_id)
            and (active.level_id is None or entity.level_id == active.level_id)
            and (active.zone_id is None or entity.zone_id == active.zone_id)
        }
        referenced_ids = {action.target_entity_id for action in result.proposed_actions}
        if target.entity_id is not None:
            referenced_ids.add(target.entity_id)
        for entity_id in referenced_ids - {None}:
            if entity_id not in visible_ids:
                raise ScopeMismatchError(
                    f"model referenced entity_id {entity_id!r} outside visible_entities"
                )

        is_modification = result.intent in {
            IntentType.MODIFY_SPACE,
            IntentType.MODIFY_RELATIONSHIP,
        } or any(action.action_type in PLAN_CHANGE_ACTIONS for action in result.proposed_actions)

        if (
            is_modification
            and target.entity_id is None
            and not any(action.target_entity_id for action in result.proposed_actions)
        ):
            return result.model_copy(
                update={
                    "needs_follow_up": True,
                    "follow_up_question": result.follow_up_question
                    or (
                        "Hangi görünür mekân veya öğe için değişiklik önerisi "
                        "hazırlamamı istersiniz?"
                    ),
                    "needs_user_confirmation": bool(result.proposed_actions),
                }
            )

        if result.proposed_actions:
            actions = [
                action.model_copy(update={"requires_user_confirmation": True})
                if action.action_type in PLAN_CHANGE_ACTIONS
                else action
                for action in result.proposed_actions
            ]
            return result.model_copy(
                update={"proposed_actions": actions, "needs_user_confirmation": True}
            )

        return result

    def recover_scope_mismatch(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        """Turn a recoverable scope mismatch into a safe clarification result."""

        result = self._normalize_intent(result, request)
        target_entity_id = result.target.entity_id
        entity_name = next(
            (
                entity.name
                for entity in request.visible_entities
                if entity.entity_id == target_entity_id
            ),
            None,
        )
        subject = f"{entity_name} ile ilgili" if entity_name else "Talep ettiğiniz mekânla ilgili"
        question = (
            f"{entity_name} seçildikten sonra bu talebi birlikte inceleyelim mi?"
            if entity_name
            else "Mekânı seçerek bu talebi birlikte inceleyelim mi?"
        )
        active = request.active_context
        recovered = result.model_copy(
            update={
                "assistant_message": (
                    f"{subject} talebinizi anladım. Ancak şu anda farklı bir mekân kapsamındasınız."
                ),
                "target": EntityTarget(
                    project_id=active.project_id,
                    building_id=active.building_id,
                    level_id=active.level_id,
                    zone_id=active.zone_id,
                    entity_id=None,
                ),
                "missing_information": [
                    "Değerlendirilecek mekânın aktif kapsamda seçilmesi gerekiyor."
                ],
                "proposed_actions": [],
                "needs_follow_up": True,
                "follow_up_question": question,
                "needs_user_confirmation": False,
                "warnings": [],
            }
        )
        return self._sanitize_public_fields(recovered, request.visible_entities)

    @staticmethod
    def _normalize_intent(
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        if result.intent not in {
            IntentType.MODIFY_SPACE,
            IntentType.REQUEST_VISUAL_PREFERENCE,
        }:
            return result

        public_model_text = " ".join(
            [
                result.assistant_message,
                *result.user_requirements,
                *result.interpreted_priorities,
                *result.constraints_to_check,
                *result.missing_information,
                *result.warnings,
                *(action.description for action in result.proposed_actions),
            ]
        )
        evidence = f"{request.message} {public_model_text}".casefold()
        if any(term in evidence for term in _RELATIONSHIP_TERMS):
            return result.model_copy(update={"intent": IntentType.MODIFY_RELATIONSHIP})
        return result

    @staticmethod
    def _sanitize_public_fields(
        result: ArchitecturalIntentResult,
        visible_entities: list[VisibleEntity],
    ) -> ArchitecturalIntentResult:
        def sanitize(text: str) -> str:
            return sanitize_public_text(text, visible_entities)

        actions = [
            action.model_copy(update={"description": sanitize(action.description)})
            for action in result.proposed_actions
        ]
        sanitized = result.model_copy(
            update={
                "assistant_message": sanitize(result.assistant_message),
                "follow_up_question": (
                    sanitize(result.follow_up_question)
                    if result.follow_up_question is not None
                    else None
                ),
                "user_requirements": [sanitize(text) for text in result.user_requirements],
                "interpreted_priorities": [
                    sanitize(text) for text in result.interpreted_priorities
                ],
                "constraints_to_check": [sanitize(text) for text in result.constraints_to_check],
                "missing_information": [sanitize(text) for text in result.missing_information],
                "proposed_actions": actions,
                "warnings": [sanitize(text) for text in result.warnings],
            }
        )
        if not sanitized.needs_follow_up:
            return sanitized.model_copy(update={"follow_up_question": None})
        return sanitized

    @staticmethod
    def _match_scope(field: str, proposed: str | None, active: str | None) -> None:
        if proposed is not None and proposed != active:
            raise ScopeMismatchError(
                f"model returned {field} {proposed!r} outside the active context"
            )
