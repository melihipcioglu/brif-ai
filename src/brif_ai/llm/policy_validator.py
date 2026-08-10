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
FORBIDDEN_LANGUAGE_ARTIFACTS: tuple[str, ...] = (
    "ele alınır ile",
    "kurgulanır ile",
    "yer alır ile",
    "ayrıma ile",
    "kontrollü ayrıma ile",
    "ele alınırla",
    "kurgulanırla",
    "yer alırla",
    "kurgulanır bir",
    "ele alınır bir",
    "yer alır bir",
    "kurgudalığını",
    "kurgu sıralanma",
    "kişisel alanın korunur",
    "ilişkili bir kurgu yer alır",
    "mahremiyeti öncelik verir",
    "kullanım kolaylığını öncelik verir",
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


def is_compare_request(request_or_msg: ConversationRequest | str) -> bool:
    msg = (
        request_or_msg.message
        if isinstance(request_or_msg, ConversationRequest)
        else request_or_msg
    )
    msg_lower = msg.casefold()
    return any(
        kw in msg_lower
        for kw in (
            "alternatif",
            "karşılaştır",
            "seçenek",
            "iki farklı",
            "iki yaklaşım",
            "iki ayrı yaklaşım",
            "iki kullanım yaklaşımı",
            "iki düzenleme yaklaşımı",
            "2 alternatif",
            "2 yaklaşım",
            "düzenleme alternatifi",
        )
    )


_MECHANICAL_PHRASE_PATTERN = re.compile(
    r"ilişkili(?:\s+bir)?\s+kurgu(?:da|yla|yu|su|sunda|ları|dalığını|nun|ya|dan|de|yla|lar)?",
    re.IGNORECASE,
)


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

    # 1b. Language artifact / broken Turkish phrasing check
    for artifact in FORBIDDEN_LANGUAGE_ARTIFACTS:
        if artifact in text_lower:
            raise AlternativeQualityError(
                f"Yanıtta bozuk Türkçe veya dilbilgisel yapay kalıp ('{artifact}') saptandı."
            )

    # 1c. Excessive mechanical phrase repetition check
    mechanical_count = len(_MECHANICAL_PHRASE_PATTERN.findall(text_lower))
    if mechanical_count >= 3:
        raise AlternativeQualityError(
            "Yanıtta mekanik kalıp ('ilişkili kurgu' vb.) aşırı tekrarlandı."
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
        r"(?:Temel\s+fark|Fark)\b[^\n:\-–—]*[:\-–—]?\s*",
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
_NOUN_GENITIVE = (
    r"(?<![\wıişğüçÖÇŞİĞÜ])(?P<noun>[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:ın|in|un|ün|nın|nin|nun|nün))\s+"
)
_COPULA = r"(?:dır|dir|dur|dür|tır|tir|tur|tür)?"

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


RELATIVE_SPATIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "right_left": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:sağ|sol)(?:ında|inde|unda|ünde|ından|inden|undan|ünden|ına|ine|una|üne|"
        + r"ını|ini|unu|ünü|ının|inin|unun|ünün|da|de|ya|ye|tarafında|tarafına|tarafından|"
        + r"tarafta|taraftaki)?"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "front_back": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:ön|arka)(?:ünde|ında|ünden|ından|üne|ına|ünü|ını|tarafında|tarafına|tarafından|"
        + r"tarafta|taraftaki|cephede|cephesinde)?"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "opposite": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"karşı(?:sında|sından|sına|sını|sının|daki|sındaki|tarafında|tarafına|tarafından|"
        + r"tarafta)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "entry_relative": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"giriş(?:ten\s+(?:sonra|önce)|in\s+(?:sağında|solunda|yanında|karşısında|"
        + r"hemen\s+yanında|hemen\s+sağında|hemen\s+solunda))"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "adjacent": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:bitişik|yan\s+yana|doğrudan\s+komşu(?:luk(?:ta|tan|a|u)?)?"
        + r"|fiziksel\s+olarak\s+bitişik)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "shared_edge": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:ortak\s+kenar|kenar\s+ortaklığı)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "shared_wall": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:ortak(?:\s+bir)?\s+duvar(?:la|da|dan|lar|ları)?"
        + r"(?:\s+(?:paylaşır|oluşturur|bulunur|birleşir))?"
        + r"|(?:bir|aynı)\s+duvarı\s+paylaşır"
        + r"|duvar\s+paylaşımı)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "proximity_distance": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:birbirine\s+(?:çok\s+)?yakın|birbirinden\s+uzak"
        + r"|(?:[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:dan|den|tan|ten|a|e|ya|ye)\s+)"
        + r"(?:uzaktır|yakındır|uzak|yakın)"
        + r"|(?:yakın|uzak)\s+konumda|(?:yakın|uzak)\s+bir\s+konumda"
        + r"|yakınında\s+bir\s+konumda|daha\s+uzakta"
        + r"|yakın\s+yerleştirilir|uzak\s+yerleştirilir"
        + r"|(?:yakın|uzak)\s+konumlandır(?:ılır|ılarak|ılacak)"
        + r"|(?:yakın|uzak)\s+konumdadır|uzakta\s+yer\s+alır"
        + r"|yakın\s+kurgulanır|uzak\s+kurgulanır"
        + r"|birbirine\s+yakındır|birbirinden\s+uzaktır"
        + r"|(?:(?:aradaki|fiziksel)\s+)?mesafe(?:nin|yi|si)?\s+"
        + r"(?:artırılır|artırılarak|azaltılır|azaltılarak|açılır|daraltılır|kısaltılır)"
        + r"|(?:fiziksel\s+)?(?:yakınlık|uzaklık)(?:la|le|tan|ten|a|e|ı|i)?)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "immediate_neighbor": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"hemen\s+yan(?:ında|ına|ı\s+başında|ındaki)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "neighbor_relative": re.compile(
        _NOUN_GENITIVE
        + r"(?:hemen\s+)?yan(?:ında|ına|ı\s+başında|ındaki)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "side_relative": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"yan\s+taraf(?:ında|ına|ından|ındaki)"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "containment": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:(?:içine|içinde|dışına|dışında)"
        + r"|(?:oda|alan|mekân|mekan)(?:sında|sinde|sunda|sünde))[^.!?;\n]{0,60}"
        + r"(?:yerleştir(?:ilir|ilerek|mek|me)?|yer\s+al(?:ır|acak)?|bulun(?:ur|acak)?)"
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
    "physical_topology": re.compile(
        _TURKISH_WORD_BOUND_PRE
        + r"(?:fiziksel\s+olarak\s+(?:ayrı|ayrık|birleşik|birleştirilmiş|bağlı)"
        + r"|fiziksel(?:\s+bir)?\s+(?:ayrılık|birleşme|bütünlük|bağlantı|sınır))"
        + _COPULA
        + _TURKISH_WORD_BOUND_POST,
        re.IGNORECASE,
    ),
}

_PAIR_SPATIAL_EVIDENCE_PATTERN = re.compile(
    r"\b(?:yakın|uzak|yakınlık|uzaklık|mesafe)\b|hemen\s+yan(?:ında|ına|ı\s+başında|ındaki)",
    re.IGNORECASE,
)
_PAIR_SPECIFIC_CATEGORIES = frozenset(
    {"proximity_distance", "immediate_neighbor", "neighbor_relative"}
)
_NON_SPATIAL_PROXIMITY_PATTERN = re.compile(
    r"(?:aile\s+üyeleri|kullanıcılar|insanlar|kişiler|çocuklar|öğrenciler)"
    r"[^.!?;\n]{0,50}\bbirbirine\s+(?:daha\s+)?yakın\b"
    r"|\bdiğerlerinden\s+uzak\s+kal",
    re.IGNORECASE,
)
_ENTITY_WORD_PATTERN = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]+")
_GENERIC_SPACE_HEADS = frozenset({"alan", "oda", "mekân", "mekan", "bölüm"})
_ENTITY_ALIAS_STOP_WORDS = frozenset(
    {"ile", "ve", "da", "de", "bir", "iki", "için", "olan", "arasındaki"}
)
_OUTER_CASE_SUFFIXES = (
    "larından",
    "lerinden",
    "larının",
    "lerinin",
    "sından",
    "sinden",
    "sundan",
    "sünden",
    "sının",
    "sinin",
    "sunun",
    "sünün",
    "ndan",
    "nden",
    "nın",
    "nin",
    "nun",
    "nün",
    "yla",
    "yle",
    "na",
    "ne",
)
_ENTITY_ALIAS_SUFFIX = (
    r"(?:larından|lerinden|larının|lerinin|sından|sinden|sundan|sünden|sının|sinin|"
    r"sunun|sünün|ndan|nden|nın|nin|nun|nün|ın|in|un|ün|yla|yle|na|ne|nda|nde|dan|den|ta|te|"
    r"ya|ye|ı|i|u|ü|a|e)?"
)


def _normalize_entity_alias(value: str) -> str:
    return " ".join(_ENTITY_WORD_PATTERN.findall(value.casefold()))


def _strip_outer_case_suffix(word: str) -> str:
    lowered = word.casefold()
    for suffix in _OUTER_CASE_SUFFIXES:
        if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
            return lowered[: -len(suffix)]
    return lowered


def _is_generic_space_head(word: str) -> bool:
    base = _strip_outer_case_suffix(word)
    if base in _GENERIC_SPACE_HEADS:
        return True
    for suffix in ("sı", "si", "su", "sü", "ı", "i", "u", "ü"):
        if base.endswith(suffix) and base[: -len(suffix)] in _GENERIC_SPACE_HEADS:
            return True
    return False


def _message_space_aliases(clause: str) -> set[str]:
    raw_words = _ENTITY_WORD_PATTERN.findall(clause)
    words = [word.casefold() for word in raw_words]
    aliases: set[str] = set()

    for index, word in enumerate(words):
        if not _is_generic_space_head(word):
            continue
        head = _strip_outer_case_suffix(word)
        start = index
        while start > 0 and index - start < 2 and words[start - 1] not in _ENTITY_ALIAS_STOP_WORDS:
            start -= 1
        phrase_words = [*words[start:index], head]
        aliases.add(" ".join(phrase_words))
        if len(phrase_words) > 2:
            aliases.add(" ".join(phrase_words[-2:]))

        if index >= 3 and words[index - 2] == "ve":
            aliases.add(f"{words[index - 3]} {head}")

    for index, word in enumerate(words):
        if word != "ile":
            continue
        if index > 0:
            aliases.add(words[index - 1])
        if index + 1 < len(words):
            aliases.add(words[index + 1])

    if raw_words and raw_words[0][:1].isupper():
        aliases.add(words[0])

    return {alias for alias in aliases if len(alias) > 2}


def _entity_aliases(request: ConversationRequest) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for entity in request.visible_entities:
        normalized = _normalize_entity_alias(entity.name)
        if not normalized:
            continue
        aliases[normalized] = entity.entity_id.casefold()
        words = normalized.split()
        if len(words) > 2:
            aliases[" ".join(words[-2:])] = entity.entity_id.casefold()

    trusted_texts = _trusted_spatial_texts(request)
    for text in trusted_texts:
        for clause in re.split(r"[.!?;\n]", text):
            if not _PAIR_SPATIAL_EVIDENCE_PATTERN.search(clause):
                continue
            for alias in _message_space_aliases(clause):
                aliases.setdefault(alias, f"message:{alias}")

    return aliases


def _extract_entity_keys(text: str, aliases: dict[str, str]) -> set[str]:
    entity_keys: set[str] = set()
    for alias, entity_key in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        words = alias.split()
        alias_pattern = r"\s+".join(re.escape(word) for word in words)
        pattern = re.compile(
            _TURKISH_WORD_BOUND_PRE
            + alias_pattern
            + _ENTITY_ALIAS_SUFFIX
            + _TURKISH_WORD_BOUND_POST,
            re.IGNORECASE,
        )
        if pattern.search(text):
            entity_keys.add(entity_key)
    return entity_keys


def _trusted_spatial_texts(request: ConversationRequest) -> list[str]:
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

    return texts


def extract_trusted_proximity_pairs(request: ConversationRequest) -> set[frozenset[str]]:
    """Extract trusted space entity pairs for proximity/distance claims from request context."""
    combined = " ".join(_trusted_spatial_texts(request))
    clauses = re.split(r"[.!?;\n]", combined)
    trusted_pairs: set[frozenset[str]] = set()
    aliases = _entity_aliases(request)

    for clause in clauses:
        if _PAIR_SPATIAL_EVIDENCE_PATTERN.search(clause):
            entities = _extract_entity_keys(clause, aliases)
            entity_list = list(entities)
            for i in range(len(entity_list)):
                for j in range(i + 1, len(entity_list)):
                    trusted_pairs.add(frozenset([entity_list[i], entity_list[j]]))

    return trusted_pairs


def extract_trusted_relative_spatial_evidence(request: ConversationRequest) -> set[str]:
    """Extract trusted relative spatial claim categories present in request context."""
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
    for category, pattern in RELATIVE_SPATIAL_PATTERNS.items():
        if category in _PAIR_SPECIFIC_CATEGORIES:
            continue
        if pattern.search(combined):
            evidence.add(category)

    return evidence


def validate_relative_spatial_claims(
    result: ArchitecturalIntentResult,
    request: ConversationRequest,
) -> None:
    """Ensure no ungrounded relative spatial claims exist in public model output fields."""
    trusted_evidence = extract_trusted_relative_spatial_evidence(request)
    trusted_prox_pairs = extract_trusted_proximity_pairs(request)
    entity_aliases = _entity_aliases(request)

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
    model_claims: set[str] = set()

    for category, pattern in RELATIVE_SPATIAL_PATTERNS.items():
        if category in _PAIR_SPECIFIC_CATEGORIES:
            for clause in re.split(r"[.!?;\n]", combined):
                if pattern.search(clause):
                    if category == "proximity_distance" and _NON_SPATIAL_PROXIMITY_PATTERN.search(
                        clause
                    ):
                        continue
                    if not trusted_prox_pairs:
                        model_claims.add(category)
                        break
                    entities = _extract_entity_keys(clause, entity_aliases)
                    entity_list = list(entities)
                    if len(entity_list) < 2:
                        model_claims.add(category)
                        break
                    pair_supported = any(
                        frozenset([entity_list[i], entity_list[j]]) in trusted_prox_pairs
                        for i in range(len(entity_list))
                        for j in range(i + 1, len(entity_list))
                    )
                    if not pair_supported:
                        model_claims.add(category)
                        break
        else:
            if pattern.search(combined):
                model_claims.add(category)

    unsupported = model_claims - trusted_evidence
    if unsupported:
        sorted_unsupported = sorted(unsupported)
        unsupported_str = ", ".join(sorted_unsupported)
        raise UnsupportedSpatialClaimError(
            f"Kullanıcı bağlamında bulunmayan göreli mekânsal iddia ({unsupported_str}) kullanıldı."
        )


_RELATIVE_NEUTRALIZATION_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"girişten\s+sonra\s+(?:hemen\s+)?(?:sağ|sol)\s+tarafta(?:\s+yer\s+alır|\s+bulunur)?"
            + _COPULA,
            re.IGNORECASE,
        ),
        "girişle ilişkisi daha açık kurulacak biçimde ele alınır",
    ),
    (
        re.compile(
            r"girişin\s+(?:hemen\s+)?(?:yanında|karşısında|sağında|solunda)(?:\s+yer\s+alır|\s+bulunur)?"
            + _COPULA,
            re.IGNORECASE,
        ),
        "giriş alanıyla ilişkili biçimde ele alınır",
    ),
    (
        re.compile(r"girişten\s+sonra(?:\s+hemen)?", re.IGNORECASE),
        "giriş alanıyla ilişkili olarak",
    ),
    (
        re.compile(
            r"(?:doğrudan\s+)?(?:bir\s+)?kenar\s+ortaklığı(?:\s+oluşturur|\s+sağlar|\s+kurgulanır)?"
            + _COPULA,
            re.IGNORECASE,
        ),
        "daha güçlü fiziksel ilişki kuracak biçimde ele alınır",
    ),
    (
        re.compile(
            r"ortak\s+kenar(?:\s+paylaşır|\s+oluşturur|\s+sağlar)?" + _COPULA,
            re.IGNORECASE,
        ),
        "fiziksel ilişki kuracak biçimde ele alınır",
    ),
    (
        re.compile(
            r"(?:bağlantılı|ilişkili)\s+bir\s+yapıda\s+ele\s+alınır\s+ile\s+(?:birleştirilmiş|bağlanmış)",
            re.IGNORECASE,
        ),
        "bütünleşik bir kurguda ele alınır",
    ),
    (
        re.compile(
            r"ortak(?:\s+bir)?\s+duvarla(?:\s+birleştirilmiş|\s+birleşir|\s+bağlanmış|\s+oluşturulmuş)?",
            re.IGNORECASE,
        ),
        "bütünleşik bir kurguyla",
    ),
    (
        re.compile(
            r"(?:bir|aynı)\s+duvarı\s+paylaşır" + _COPULA,
            re.IGNORECASE,
        ),
        "birbiriyle daha güçlü ilişki kurar",
    ),
    (
        re.compile(
            r"ortak(?:\s+bir)?\s+duvar(?:\s+ile)?(?:\s+paylaşır|\s+bulunur|\s+oluşturur)?",
            re.IGNORECASE,
        ),
        "bütünleşik bir kurgu ile",
    ),
    (
        re.compile(r"duvar\s+paylaşımı", re.IGNORECASE),
        "mekânsal ilişki",
    ),
    (
        re.compile(
            r"(?:doğrudan\s+)?(?:birbirine\s+(?:çok\s+)?)?yakın\s+bir(?:\s+konumda|\s+dizayn|\s+kurgu)?",
            re.IGNORECASE,
        ),
        "ilişkili bir kurgu",
    ),
    (
        re.compile(
            r"(?:doğrudan\s+)?(?:birbirine\s+(?:çok\s+)?)?yakın(?:\s+konumda)?(?:\s+yer\s+alır|\s+bulunur|\s+kurgulanır)?",
            re.IGNORECASE,
        ),
        "ilişkili kurguda",
    ),
    (
        re.compile(
            r"(?:birbirinden\s+)?uzak(?:\s+konumda)?(?:\s+olup|\s+yer\s+alır|\s+bulunur|\s+kurgulanır)?"
            + _COPULA,
            re.IGNORECASE,
        ),
        "kontrollü ayrışma kurgusunda ele alınır",
    ),
    (
        re.compile(
            r"yakınında(?:\s+bir\s+konumda)?(?:\s+yer\s+alır|\s+bulunur|\s+kurgulanır)?" + _COPULA,
            re.IGNORECASE,
        ),
        "ilişkili bir alanda kurgulanır",
    ),
    (
        re.compile(
            r"(?:[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:ın|in|un|ün|nın|nin|nun|nün)?\s+)?"
            r"(?:önün|arkasın)(?:de|da|e|a|den|dan)"
            r"(?:\s+yer\s+alır|\s+bulunur|\s+kurgulanır)?" + _COPULA,
            re.IGNORECASE,
        ),
        "ilişkili alanda kurgulanır",
    ),
    (
        re.compile(
            r"(?:ön|arka)\s+(?:tarafta|tarafında|kısımda|kısmında|cephede|cephesinde)"
            r"(?:\s+yer\s+alır|\s+bulunur|\s+kurgulanır)?" + _COPULA,
            re.IGNORECASE,
        ),
        "ilişkili alanda kurgulanır",
    ),
    (
        re.compile(
            r"(?:fiziksel\s+olarak\s+bitişik|doğrudan\s+komşu)(?:\s+konumdadır|\s+yer\s+alır)?"
            + _COPULA,
            re.IGNORECASE,
        ),
        "ilişkili konumda ele alınır",
    ),
    (
        re.compile(
            r"bitişik(?:tir|tür|tirler)?(?:\s+konumdadır|\s+yer\s+alır|\s+bulunur)?" + _COPULA,
            re.IGNORECASE,
        ),
        "yakın kurgulanır",
    ),
    (
        re.compile(r"yan\s+yana(?:\s+konumlanır|\s+yer\s+alır)?" + _COPULA, re.IGNORECASE),
        "birlikte kurgulanır",
    ),
    (
        re.compile(
            r"(?:sağ|sol)\s+tarafında(?:\s+yer\s+alır|\s+bulunur)?" + _COPULA,
            re.IGNORECASE,
        ),
        "bütünleşik alanda kurgulanır",
    ),
    (
        re.compile(
            r"(?:sağ|sol)\s+tarafta(?:\s+yer\s+alır|\s+bulunur)?" + _COPULA,
            re.IGNORECASE,
        ),
        "bağlantılı alanda kurgulanır",
    ),
    (
        re.compile(
            r"(?:[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:ın|in|un|ün|nın|nin|nun|nün)\s+)?(?:sağında|solunda)"
            + _COPULA
            + r"(?:\s+yer\s+alır|\s+bulunur|\s+kurgulanır)?",
            re.IGNORECASE,
        ),
        "işlevsel yakınlıkta kurgulanır",
    ),
    (
        re.compile(
            r"(?:[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:ın|in|un|ün|nın|nin|nun|nün)\s+)?(?:sağda|solda)"
            + _COPULA
            + r"(?:\s+yer\s+alır|\s+bulunur)?",
            re.IGNORECASE,
        ),
        "yakın konumda kurgulanır",
    ),
    (
        re.compile(
            r"karşı\s+karşıya(?:\s+olur|\s+gelir|\s+konumlanır)?" + _COPULA,
            re.IGNORECASE,
        ),
        "karşılıklı kurguda ele alınır",
    ),
    (
        re.compile(
            r"(?:[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:ın|in|un|ün|nın|nin|nun|nün)\s+)?karşısında"
            + _COPULA
            + r"(?:\s+yer\s+alır|\s+bulunur|\s+konumlanır)?",
            re.IGNORECASE,
        ),
        "karşılıklı ilişkide kurgulanır",
    ),
    (
        re.compile(
            r"karşı\s+tarafında" + _COPULA + r"(?:\s+yer\s+alır|\s+bulunur)?",
            re.IGNORECASE,
        ),
        "karşılıklı konumda kurgulanır",
    ),
    (
        re.compile(
            r"(?:[A-Za-z0-9ıişğüçÖÇŞİĞÜ]+(?:a|e|ya|ye)\s+)?bitişik(?:tir|tür|tirler)?(?:\s+konumdadır|\s+yer\s+alır|\s+bulunur)?"
            + _COPULA,
            re.IGNORECASE,
        ),
        "ilişkili konumdadır",
    ),
    (
        re.compile(
            r"(?:ön|arka)\s+tarafında" + _COPULA + r"(?:\s+yer\s+alır|\s+bulunur)?",
            re.IGNORECASE,
        ),
        "ilişkili alanda kurgulanır",
    ),
    (
        re.compile(
            r"(?:önünde|arkasında)" + _COPULA + r"(?:\s+yer\s+alır|\s+bulunur)?",
            re.IGNORECASE,
        ),
        "ilişkili alanda kurgulanır",
    ),
]


def neutralize_unsupported_relative_spatial_claims(
    text: str,
    unsupported_categories: set[str],
) -> str:
    """Neutralize ungrounded relative/topological spatial claims to natural abstract phrases."""
    if not unsupported_categories:
        return text

    sanitized = text
    for pattern, replacement in _RELATIVE_NEUTRALIZATION_RULES:
        sanitized = pattern.sub(replacement, sanitized)

    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" +([,.!?;:])", r"\1", sanitized)
    return sanitized


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
                    _TURKISH_WORD_BOUND_PRE
                    + d
                    + r"(?:doğu|batı)?\s+tarafı(?:nda|na|ndan|nı|nı)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                "ilişkili alanda",
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
                "ilişkili kurgu doğrultusunda",
            ),
            (
                re.compile(
                    _NOUN_GENITIVE + d + r"(?:doğu|batı)?(?:si|sı|su|sü|i|ı|u|ü)?"
                    r"(?:nde|nda|ne|na|nden|ndan|deki|daki|ndaki|ndeki|de|da|ye|ya|e|a)?"
                    + _COPULA
                    + _TURKISH_WORD_BOUND_POST,
                    re.IGNORECASE,
                ),
                r"\g<noun> ilişkili bir konumunda",
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
                "ilişkili bir konumda",
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
                "ilişkili bir konuma",
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
                "ilişkili bir konumdan",
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
                "ilişkili bir konumda",
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
                "ilişkili yapıda",
            ),
        )
        for pattern, replacement in rules:
            sanitized = pattern.sub(replacement, sanitized)

    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" +([,.!?;:])", r"\1", sanitized)
    return sanitized


_MARKDOWN_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MARKDOWN_ASTERISKS = re.compile(r"\*+")


def sanitize_compare_text(text: str, visible_entities: list[VisibleEntity]) -> str:
    """Minimal cleanup for compare assistant_message: only internal IDs and markdown.

    Unlike sanitize_public_text, this does NOT localize technical terms
    (e.g. 'target' -> 'hedef') to preserve the model's natural Turkish phrasing.
    """
    entity_names = {entity.entity_id.casefold(): entity.name for entity in visible_entities}

    def replacement(match: re.Match[str]) -> str:
        identifier = match.group("identifier")
        entity_name = entity_names.get(identifier.casefold())
        if entity_name is not None:
            return entity_name
        prefix = identifier.split("_", maxsplit=1)[0].casefold()
        return _PUBLIC_FALLBACKS.get(prefix, "öğe")

    sanitized = _INTERNAL_ID_PATTERN.sub(replacement, text)
    # Strip markdown formatting
    sanitized = _MARKDOWN_BOLD.sub(r"\1", sanitized)
    sanitized = _MARKDOWN_HEADER.sub("", sanitized)
    sanitized = _MARKDOWN_ASTERISKS.sub("", sanitized)
    # Whitespace normalization
    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" +([,.!?;:])", r"\1", sanitized)
    sanitized = "\n".join(line.strip() for line in sanitized.splitlines()).strip()
    return sanitized or text


class ArchitecturalIntentPolicyValidator:
    """Treat model output as untrusted suggestions constrained by active context."""

    def sanitize(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        """Sanitize machine IDs, internal terms, and neutralize unsupported spatial directions."""
        trusted_evidence = extract_trusted_direction_evidence(request)
        trusted_relative = extract_trusted_relative_spatial_evidence(request)

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

        model_relatives: set[str] = set()
        for category, pattern in RELATIVE_SPATIAL_PATTERNS.items():
            if pattern.search(combined):
                model_relatives.add(category)

        unsupported_relatives = model_relatives - trusted_relative

        def _clean(text: str) -> str:
            text = sanitize_public_text(text, request.visible_entities)
            if unsupported_directions:
                text = neutralize_unsupported_spatial_directions(text, unsupported_directions)
            if unsupported_relatives:
                text = neutralize_unsupported_relative_spatial_claims(text, unsupported_relatives)
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

    def sanitize_compare(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        """Minimal sanitization for compare responses: internal IDs and markdown only.

        Does NOT apply spatial direction or relative spatial claim neutralization.
        Unsupported claims will be caught by validate_semantic_integrity and trigger repair.
        """

        def _clean(text: str) -> str:
            return sanitize_compare_text(text, request.visible_entities)

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

        if is_compare_request(request):
            if result.intent != IntentType.COMPARE_ALTERNATIVES:
                raise PolicyValidationError(
                    "Kullanıcı alternatif karşılaştırması istediğinde "
                    "sonuç intent'i COMPARE_ALTERNATIVES olmalıdır."
                )
            validate_alternative_quality(result, request)

            if result.needs_follow_up:
                raise PolicyValidationError(
                    "Kavramsal alternatif talebinde takip sorusu üretilmemelidir "
                    "(needs_follow_up=false olmalı)."
                )

        validate_spatial_direction_claims(result, request)
        validate_relative_spatial_claims(result, request)

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

    def validate(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        result = self._normalize_intent(result, request)
        result = (
            self.sanitize_compare(result, request)
            if is_compare_request(request)
            else self.sanitize(result, request)
        )
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
