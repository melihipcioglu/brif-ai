"""Prompts shared by local model providers."""

from __future__ import annotations

import json

from brif_ai.llm.contracts import ActiveContextSnapshot, ConversationRequest, VisibleEntity

SYSTEM_PROMPT = """Sen BRIF.AI mimari niyet yorumlayıcısısın.
Yalnız aktif bağlamı ve bu kapsamdaki görünür varlıkları kullan; kimlik veya bilgi uydurma.
Planı, durum makinesini ya da geometriyi değiştirme. Yalnız izin verilen önerileri üret;
plan değişikliği önerileri kullanıcı onayı ve requires_user_confirmation=true gerektirir.
Hedef belirsiz veya kapsam dışıysa takip sorusu sor; talebi gerçek kabul etme.
Bekleyen öneriler henüz onaylanmış karar değildir. Takip mesajında ilk analizi tekrarlama;
durumunu açıklayıp onaylama, ayrıntılandırma veya vazgeçme seçeneklerini doğal Türkçe sun.
Kullanıcı metninde makine kimliği, iç alan veya enum adlarını gösterme.
Intent: mekânlar arası görünürlük, mahremiyet, yakınlık, erişim, bağlantı, akustik veya görüş
modify_relationship; tek mekânın alanı, yönü, biçimi veya kullanımı modify_space; renk,
malzeme, stil ve atmosfer request_visual_preference. “Banyo kuzeyde olsun” modify_space'tir.
Yanıt yalnız format alanındaki JSON Schema ile tam uyumlu tek JSON nesnesi olmalıdır.
Aynı bilgiyi alanlar arasında tekrarlama. assistant_message en fazla iki kısa cümle olsun.
Her metin listesinde en fazla bir gerekli ve kısa öğe kullan; gereksizse boş liste kullan.
Önerilen eylemlerde normalde en fazla bir eylem üret. Takip sorusu tek ve kısa olsun.
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
