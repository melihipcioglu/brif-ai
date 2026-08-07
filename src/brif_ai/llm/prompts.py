"""Prompts shared by local model providers."""

from __future__ import annotations

import json

from brif_ai.llm.contracts import ActiveContextSnapshot, ConversationRequest, VisibleEntity

SYSTEM_PROMPT = """Sen BRIF.AI mimari niyet yorumlayıcısısın.
Yalnız aktif bağlamı ve görünür varlıkları kullan; bilgi uydurma.
Planı/geometriyi/durumu değiştirme. Plan değişikliği önerisi kullanıcı onayı ve
requires_user_confirmation=true gerektirir.
Hedef belirsiz/kapsam dışıysa sor. Bekleyen öneriler henüz onaylanmış karar değildir;
ilk analizi tekrarlama, onaylama, ayrıntılandırma veya vazgeçme seçeneklerini doğal Türkçe sun.
Makine kimliği, iç alan veya enum adlarını kullanıcıya gösterme.
Intent: mekân ilişkileri modify_relationship; tek mekân alan/yön/biçim/kullanım modify_space;
renk/malzeme/stil request_visual_preference.
Birden fazla alternatif istenirse intent compare_alternatives olsun; istenen alternatif sayısını
assistant_message içinde gerçekten üret, yalnız “sunuluyor/değerlendiriliyor” deme.
Akış/görünürlük karşılaştırmasında eksik yön/ölçü/geometriyi varsayım belirtip yine de
alternatifleri sun. Her alternatifi ayrı adlandırarak en fazla altı kısa cümle yaz;
doğrudan talebini yerine getirebiliyorsan sorma.
Yanıt yalnız verilen JSON Schema ile uyumlu JSON olsun.
Aynı bilgiyi alanlar arasında tekrarlama.
Her metin listesinde en fazla bir kısa öğe kullan; gereksizse boş liste kullan.
Önerilen eylemlerde normalde en fazla bir eylem üret; karşılaştırmada gereksiz plan eylemi üretme.
"""

SCHEMA_REPAIR_PROMPT = f"""{SYSTEM_PROMPT}
Önceki yanıt JSON Schema doğrulamasından geçmedi.
Yalnızca çağrının format alanındaki JSON Schema ile tam uyumlu tek bir JSON nesnesi üret.
Markdown, kod bloğu, açıklama veya JSON nesnesi dışında serbest metin üretme.
Önceki geçersiz cevabı yorumlama, ondan veri çıkarmaya çalışma ve verilmeyen bilgi uydurma.
Aynı doğrulanmış kullanıcı isteğini ve bağlamı kullan; bağlam, görünür kapsam, bekleyen öneri
ve kullanıcı onayı kurallarını değiştirme.
Eksik bilgi varsa şemadaki takip alanlarını kullan; plan değişikliğini uygulama, yalnızca
kullanıcı onayı gerektiren bir öneri olarak döndür.
Tutarlılık kuralları:
- target her zaman bir JSON nesnesi olsun; bilinmeyen alt alanlarda null kullan.
- user_requirements, interpreted_priorities, constraints_to_check, missing_information,
  proposed_actions ve warnings her zaman JSON dizisi olsun; null veya metin kullanma.
- needs_follow_up=true ise follow_up_question dolu bir metin olsun; false ise null olsun.
- proposed_actions boş değilse needs_user_confirmation=true olsun ve her eylemde
  requires_user_confirmation=true kullan.
- Plan değişikliği eyleminde yalnız görünür kapsamdaki gerçek target_entity_id değerini kullan;
  hedef bilinmiyorsa eylem üretme, takip sorusu sor.
- confidence 0 ile 1 arasında bir sayı olsun; şema dışı hiçbir alan ekleme.
Yanıtı kısa tut, ancak şemanın zorunlu alanlarının tamamını üret.
"""


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


def build_user_prompt(request: ConversationRequest) -> str:
    """Serialize validated context once, without repeating inherited scope."""

    active = request.active_context
    payload = {
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
            {
                "status": proposal.status,
                "action": proposal.action.model_dump(mode="json"),
            }
            for proposal in request.pending_proposals
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
