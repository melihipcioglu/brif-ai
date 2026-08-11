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
    "Sen BRIF.AI mimari niyet yorumlayıcısısın.\n"
    "Aktif bağlamda olmayan yön (kuzey/güney/doğu/batı), ölçü/konum uydurma.\n"
    "Plan önerisi proposed_actions, brief önerisi proposed_brief_mutations dizisinde verilir.\n"
    "Plan değişikliği requires_user_confirmation=true gerektirir.\n"
    "Bekleyen öneri henüz onaylanmış karar değildir; ilk analizi tekrarlama, "
    "onaylama, ayrıntılandırma veya vazgeçme seçeneklerini doğal Türkçe sun.\n"
    'Makine kimliği, iç alan veya enum adlarını, "entity", "target", "öğe bilgisi" gösterme.\n'
    "Intent: modify_relationship, modify_space, request_visual_preference.\n"
    "Alternatif istenirse intent compare_alternatives olsun; "
    "proposed_actions=[], proposed_brief_mutations=[] yap.\n"
    "istenen alternatif sayısını assistant_message içinde gerçekten üret.\n"
    "Kesin yön ve konum belirtmeden kavramsal alternatif sun; tek takip sorusu sor.\n"
    "Alternatif 1 - <ad>: <açıklama>/Alternatif 2 - <ad>: <açıklama>/Temel fark: <fark>\n"
    "İki alternatif farklı ilke sunmalı; 'kesin konum/yön bilgisi henüz verilmedi' de.\n"
    "Yanıt JSON Schema ile uyumlu olsun; aynı bilgiyi alanlar arasında tekrarlama.\n"
    "Her metin listesinde en fazla bir öğe kullan; gereksizse boş liste kullan.\n"
    "Önerilen eylemlerde normalde en fazla bir eylem üret; karşılaştırmada plan eylemi üretme.\n"
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
- needs_follow_up=true ise follow_up_question dolu bir metin olsun; false ise null olsun.
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
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_compare_user_prompt(
    request: ConversationRequest,
    analysis: CompareRequestAnalysis,
) -> str:
    """Serialize only trusted compare context; mutation scope identifiers are unnecessary."""

    active = request.active_context
    payload: dict[str, object] = {
        "message": request.message,
        "visible_entity_names": [
            entity.name
            for entity in request.visible_entities
            if _is_in_active_scope(request, entity)
        ],
        "conversation_summary": request.conversation_summary,
        "current_decisions": request.current_decisions,
        "pending_decision_descriptions": [
            proposal.action.description
            for proposal in request.pending_proposals
            if proposal.action is not None
        ],
        "compare_context": analysis.prompt_payload(),
        "context_generation": active.generation_id,
    }
    if request.brief_snapshot is not None:
        payload["active_brief"] = _compact_brief_payload(request.brief_snapshot)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
