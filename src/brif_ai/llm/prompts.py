"""Prompts shared by local model providers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from brif_ai.llm.compare_engine import CompareFailureCategory, CompareRequestAnalysis
from brif_ai.llm.contracts import (
    ActiveContextSnapshot,
    ConversationRequest,
    PendingProposalContext,
    VisibleEntity,
)

if TYPE_CHECKING:
    from brif_ai.brief.models.snapshot import BriefSnapshot

SYSTEM_PROMPT = (
    "Sen BRIF.AI mimari niyet ve mevzuat yorumlayıcısısın.\n"
    "Mevzuat uydurma; PASS/FAIL/UNKNOWN değiştirme; tercih/mevzuatı ayırt et.\n"
    "Aktif bağlamda olmayan yön, ölçü/konum uydurma.\n"
    "Plan önerisi proposed_actions, brief önerisi proposed_brief_mutations ile verilir.\n"
    "Bağımsız isteklerde proposed_brief_mutations en fazla 3 öneri üretebilir.\n"
    "Plan değişikliği requires_user_confirmation=true gerektirir.\n"
    "Bekleyen öneri henüz onaylanmış karar değildir; ilk analizi tekrarlama, "
    "onaylama, ayrıntılandırma veya vazgeçme seçeneklerini doğal Türkçe sun.\n"
    'Makine kimliği, iç alan veya enum adlarını, "entity", "target", "öğe bilgisi" gösterme.\n'
    "Intent: modify_relationship/modify_space/request_visual_preference.\n"
    "Alternatif istenirse intent compare_alternatives olsun; "
    "proposed_actions=[], proposed_brief_mutations=[] yap.\n"
    "istenen alternatif sayısını gerçekten üret.\n"
    "Kesin yön ve konum belirtmeden kavramsal alternatif sun; tek takip sorusu sor.\n"
    "Alternatif 1 - <ad>: <özet>/Alternatif 2 - <ad>: <özet>/Temel fark: <fark>\n"
    "'kesin konum/yön bilgisi henüz verilmedi' de.\n"
    "Yanıt JSON Schema ile uyumlu olsun; aynı bilgiyi alanlar arasında tekrarlama.\n"
    "Her metin listesinde en fazla bir öğe kullan; gereksizse boş liste kullan.\n"
    "Önerilen eylemlerde normalde en fazla bir eylem üret.\n"
)

SCHEMA_REPAIR_PROMPT = f"""{SYSTEM_PROMPT}
Önceki yanıt JSON Schema veya semantik doğrulamasından geçmedi.
Yalnızca çağrının format alanındaki JSON Schema ile tam uyumlu tek bir JSON nesnesi üret.
Markdown, kod bloğu, açıklama veya JSON nesnesi dışında serbest metin üretme.
Aşağıdaki kurallara KESİNLİKLE UY:
- "entity", "entity_id", "target", "enum", "öğe bilgisi", "ilgili mekân", "visible_entities"
  terimlerini kullanma.
- İngilizce kelime kullanma; tüm anlatım öz Türkçe ve doğal olsun.
- Karşılaştırmada intent=compare_alternatives, target tüm alanları null,
  proposed_actions=[], proposed_brief_mutations=[],
  needs_user_confirmation=false, needs_follow_up=false, follow_up_question=null yap.
- assistant_message içinde kesin yön ve konum belirtmeden şu 3 bölümü eksiksiz üret:
  Alternatif 1 - <Türkçe kısa ad>: <tek veya iki kısa cümle>
  Alternatif 2 - <Türkçe kısa ad>: <tek veya iki kısa cümle>
  Temel fark: <tek kısa cümle>
- İki alternatif farklı mekânsal organizasyon ilkeleri
  (ör. açık/bütünleşik vs. esnek/ayrışabilen) sunmalı.
- Kuzey, güney, doğu, batı yönlerini ve 'yakın bir konumda' gibi
  yapay dolguları KESİNLİKLE kullanma.
- Verilmeyen yön (kuzey/güney/doğu/batı), cephe, ölçü veya konum bilgisini uydurma.
- target her zaman bir JSON nesnesi olsun; bilinmeyen alt alanlarda null kullan.
- user_requirements, interpreted_priorities, constraints_to_check,
  missing_information, proposed_actions, proposed_brief_mutations ve warnings
  her zaman JSON dizisi olsun; null veya metin kullanma.
- needs_follow_up=true ise follow_up_question dolu bir metin olsun ve follow_up_topic
  girdideki elicitation.allowed_follow_up_topic ile birebir aynı olsun.
- needs_follow_up=false ise follow_up_question=null ve follow_up_topic=null olsun.
- elicitation.allowed_follow_up_topic=null ise needs_follow_up=false olsun.
- proposed_actions veya proposed_brief_mutations boş değilse needs_follow_up=false olsun.
- proposed_actions boş değilse needs_user_confirmation=true olsun ve her eylemde
  requires_user_confirmation=true kullan.
- Plan değişikliği eyleminde yalnız görünür kapsamdaki gerçek target_entity_id değerini kullan;
  hedef bilinmiyorsa eylem üretme, takip sorusu sor.
- confidence 0 ile 1 arasında bir sayı olsun; şema dışı hiçbir alan ekleme.
Yanıtı kısa tut, ancak şemanın zorunlu alanlarının tamamını üret.
"""

COMPARE_SYSTEM_PROMPT = """Sen BRIF.AI için yalnız enum değerlerinden oluşan küçük bir
mimari karar planı seçersin. Son kullanıcı metni yazma. Yanıt yalnız çağrının JSON Schema
alanıyla tam uyumlu tek bir JSON nesnesi olsun. mode compare_context içindeki mode ile aynı olsun.

open_alternatives için yalnız şu yaklaşım-sonuç eşleşmelerini kullan:
- integrated_flow -> continuous_interaction
- parallel_rhythms -> independent_simultaneous_use
- adaptable_use -> adaptable_daily_use
- ordered_use -> predictable_routine
- shared_activity -> shared_interaction
- individual_balance -> controlled_personal_use
- privacy_balance -> controlled_personal_use
İki yaklaşım farklı olsun ve her outcome kendi approach değeriyle yukarıdaki gibi eşleşsin.
approach_1 ve approach_2 değerlerini compare_context içindeki recommended_approach_1 ve
recommended_approach_2 değerleriyle aynen eşleştir.

explicit_axes için approach_1=axis_1 ve approach_2=axis_2 kullan.
outcome_1 ve outcome_2 değerlerini compare_context içindeki outcome_hint_1 ve outcome_hint_2
değerleriyle aynen eşleştir.

entity_choice için approach_1=choice_1 ve approach_2=choice_2 kullan. İki outcome farklı olsun.
Seçeneklerin kullanım karakterine en uygun iki sonucu seç; fiziksel yerleşim çıkarımı yapma.
indoor_continuity iç kullanım sürekliliğini, outdoor_experience açık hava deneyimini,
open_shared_use açık ve ortak kullanımı, separated_controlled_use ayrışmış kontrollü kullanımı,
focused_activity odaklanmayı, shared_interaction sosyal etkileşimi anlatır.

confidence 0 ile 1 arasında bir sayı olsun. Şema dışı alan, açıklama, Markdown veya serbest metin
ekleme. subject_labels, axis ve choice değerlerini çıktı alanlarına kopyalama.
"""

COMPARE_REPAIR_PROMPT = f"""{COMPARE_SYSTEM_PROMPT}
İlk plan şema veya semantik doğrulamadan geçmedi.
Ham ilk yanıtı görmeden, aynı compare_context için yeni ve bağımsız bir plan üret.
Yalnız bildirilen hata sınıfını düzelt; güvenlik kurallarını gevşetme.
"""


def build_compare_repair_prompt(category: CompareFailureCategory) -> str:
    """Add only a safe failure category, never raw model or user text."""

    guidance = {
        CompareFailureCategory.SCHEMA_INVALID: "Zorunlu alanların tamamını doğru türlerle üret.",
        CompareFailureCategory.MODE_MISMATCH: "mode değerini compare_context ile aynı yap.",
        CompareFailureCategory.SEMANTIC_SUBJECT_SPLIT: (
            "Subject adlarını çıktı alanına yazma; yalnız izin verilen enum değerlerini kullan."
        ),
        CompareFailureCategory.AXIS_MISMATCH: (
            "approach değerlerini axis_1 ve axis_2, outcome değerlerini iki outcome_hint yap."
        ),
        CompareFailureCategory.ENTITY_CHOICE_MISMATCH: (
            "approach_1=choice_1 ve approach_2=choice_2 yap; iki outcome farklı olsun."
        ),
        CompareFailureCategory.UNSUPPORTED_SPATIAL_CLAIM: (
            "Kullanıcının vermediği hiçbir fiziksel olguyu plan alanlarına ekleme."
        ),
        CompareFailureCategory.LANGUAGE_QUALITY: (
            "Serbest metin üretme; yalnız şemadaki enum ve confidence değerlerini yaz."
        ),
        CompareFailureCategory.ALTERNATIVES_TOO_SIMILAR: (
            "İki yaklaşımın karar ilkesi ve kullanıcı sonucu belirgin biçimde ayrı olsun."
        ),
        CompareFailureCategory.KEY_DIFFERENCE_INVALID: (
            "open modunda her outcome değerini seçilen approach ile verilen eşleme listesine uydur."
        ),
        CompareFailureCategory.UNSUPPORTED_QUANTITATIVE_CLAIM: (
            "Metin alanlarına sayı, yüzde, skor veya güven değeri ekleme."
        ),
    }[category]
    return f"{COMPARE_REPAIR_PROMPT}\nHata sınıfı: {category.value}\nDüzeltme: {guidance}\n"


def _is_in_active_scope(request: ConversationRequest, entity: VisibleEntity) -> bool:
    active = request.active_context
    return (
        entity.project_id == active.project_id
        and (active.building_id is None or entity.building_id == active.building_id)
        and (active.level_id is None or entity.level_id == active.level_id)
    )


def _visible_entity_payload(
    entity: VisibleEntity,
    active: ActiveContextSnapshot,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type,
        "name": entity.name,
        "zone_id": entity.zone_id,
    }
    if active.building_id is None:
        payload["building_id"] = entity.building_id
    if active.level_id is None:
        payload["level_id"] = entity.level_id
    return payload


def _proposal_payload(proposal: PendingProposalContext) -> dict[str, object]:
    payload: dict[str, object] = {"status": proposal.status}
    if proposal.action is not None:
        payload["action"] = proposal.action.model_dump(mode="json")
    if proposal.brief_mutation is not None:
        payload["brief_mutation"] = proposal.brief_mutation.model_dump(mode="json")
    return payload


def _compact_brief_payload(snapshot: BriefSnapshot) -> dict[str, object]:
    return {
        "brief_version": snapshot.brief_version,
        "brief_items": [
            {
                "kind": item.kind.value if hasattr(item.kind, "value") else str(item.kind),
                "statement": item.normalized_statement,
                "priority": (
                    item.priority.value if hasattr(item.priority, "value") else str(item.priority)
                ),
            }
            for item in snapshot.brief_items
        ],
        "space_requests": [
            {
                "display_name": req.display_name,
                "space_function": (
                    req.space_function.value
                    if hasattr(req.space_function, "value")
                    else str(req.space_function)
                ),
                "minimum_quantity": req.minimum_quantity,
                "maximum_quantity": req.maximum_quantity,
                "mandatory": req.mandatory,
            }
            for req in snapshot.space_requests
        ],
        "usage_scenarios": [
            {
                "title": us.title,
                "description": us.description,
            }
            for us in snapshot.usage_scenarios
        ],
    }


def build_user_prompt(request: ConversationRequest) -> str:
    """Serialize validated context once, without repeating inherited scope."""

    active = request.active_context
    payload: dict[str, object] = {
        "message": request.message,
        "active_context": active.model_dump(mode="json"),
        "visible_entities": [
            _visible_entity_payload(entity, active)
            for entity in request.visible_entities
            if _is_in_active_scope(request, entity)
        ],
        "conversation_summary": request.conversation_summary,
        "current_decisions": request.current_decisions,
        "pending_proposals": [
            _proposal_payload(proposal) for proposal in request.pending_proposals
        ],
    }
    if request.brief_snapshot is not None:
        payload["active_brief"] = _compact_brief_payload(request.brief_snapshot)
    if request.regulatory_context is not None:
        payload["regulatory_context"] = {
            "ruleset_id": request.regulatory_context.ruleset_id,
            "verification_status": (
                request.regulatory_context.verification_status.value
                if hasattr(request.regulatory_context.verification_status, "value")
                else str(request.regulatory_context.verification_status)
            ),
        }
    if request.compliance_findings:
        payload["compliance_findings"] = [
            {
                "rule_id": f.rule_id,
                "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "message": f.message,
                "article_reference": f.article_reference,
            }
            for f in request.compliance_findings
        ]
    if request.elicitation_context is not None:
        el = request.elicitation_context
        payload["elicitation"] = {
            "allowed_follow_up_topic": (
                el.allowed_follow_up_topic.value if el.allowed_follow_up_topic is not None else None
            ),
            "reason": el.reason,
            "pending_proposals_exist": el.pending_proposals_exist,
            "open_question_topics": [t.value for t in el.open_question_topics],
            "answered_question_topics": [t.value for t in el.answered_question_topics],
        }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_compare_user_prompt(
    request: ConversationRequest,
    analysis: CompareRequestAnalysis,
) -> str:
    """Serialize only trusted compare context; mutation scope identifiers are unnecessary."""

    requested_count = getattr(
        analysis, "requested_count", getattr(analysis, "alternative_count", None)
    )
    message = request.message
    if requested_count is not None:
        message = (
            f"Kullanıcı talebi: {request.message} (İstenen alternatif sayısı: {requested_count})"
        )

    payload: dict[str, object] = {
        "intent": "compare_alternatives",
        "message": message,
        "active_context": request.active_context.model_dump(mode="json"),
        "visible_entities": [
            _visible_entity_payload(entity, request.active_context)
            for entity in request.visible_entities
            if _is_in_active_scope(request, entity)
        ],
        "conversation_summary": request.conversation_summary,
        "current_decisions": request.current_decisions,
    }
    if request.brief_snapshot is not None:
        payload["active_brief"] = _compact_brief_payload(request.brief_snapshot)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


ELICITATION_ANSWER_SYSTEM_PROMPT = (
    "Sen BRIF.AI mimari brief yorumlayıcısısın.\n"
    "Aktif bir elicitation sorusu var; yalnız kullanıcının brief bilgisini yorumla.\n"
    "Aktif soru yanıtlanıyorsa answers_current_open_question=true yap.\n"
    "Yanıtsa izinli türde tam 1 proposed_brief_mutations üret.\n"
    "Plan/geometri eylemi veya alternatif üretme; proposed_actions=[] olsun.\n"
    "Yeni takip sorusu üretme; needs_follow_up=false ve follow-up alanları null olsun.\n"
    "Household sorusunda household_composition alanını yapılandırılmış doldur.\n"
    "Örnek: ben + eş + iki çocuk => total=4, adult=2, child=2.\n"
    "Yalnız toplam biliniyorsa adult_count ve child_count null olsun; bilgi uydurma.\n"
    "Toplam ile tek alt grup biliniyorsa diğer alt grup aritmetik olarak çıkarılabilir.\n"
    "Household yanıtı değilse sayımlar null, child_ages=[] ve notes=null olsun.\n"
    "Household brief maddesinde kind=CONTEXT kullan.\n"
    "Başka bir brief ihtiyacıysa answers_current_open_question=false yap ve en fazla "
    "1 brief mutasyonu üret.\n"
    "Mesaj ilgisizse answers_current_open_question=false ve proposed_brief_mutations=[] yap.\n"
)


def build_elicitation_user_prompt(
    active_question_id: str,
    active_topic_key: str,
    active_question_text: str,
    user_message: str,
    snapshot: BriefSnapshot | None = None,
) -> str:
    """Build compact user prompt for dedicated elicitation answer interpretation."""
    payload: dict[str, object] = {
        "active_open_question": {
            "id": active_question_id,
            "topic_key": active_topic_key,
            "question": active_question_text,
        },
        "user_message": user_message,
    }
    if snapshot is not None:
        payload["active_brief"] = _compact_brief_payload(snapshot)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
