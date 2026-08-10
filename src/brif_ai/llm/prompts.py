"""Prompts shared by local model providers."""

from __future__ import annotations

import json

from brif_ai.llm.contracts import ActiveContextSnapshot, ConversationRequest, VisibleEntity

SYSTEM_PROMPT = (
    "Sen BRIF.AI mimari niyet yorumlayıcısısın.\n"
    "Aktif bağlamda olmayan yön (kuzey/güney/doğu/batı), "
    "ölçü ve konum bilgisini kesin uydurma.\n"
    "Plan değişikliği kullanıcı onayı ve "
    "requires_user_confirmation=true gerektirir.\n"
    "Bekleyen öneriler henüz onaylanmış karar değildir; "
    "ilk analizi tekrarlama, onaylama, "
    "ayrıntılandırma veya vazgeçme seçeneklerini doğal Türkçe sun.\n"
    'Makine kimliği, iç alan veya enum adlarını, "entity", "target", '
    '"öğe bilgisi" gösterme; İngilizce terim kullanma.\n'
    "Intent: ilişki modify_relationship; mekân modify_space; "
    "stil request_visual_preference.\n"
    "Alternatif istenirse intent compare_alternatives olsun; "
    "proposed_actions=[] yap.\n"
    "istenen alternatif sayısını assistant_message içinde "
    'gerçekten üret, "Alternatif 1:" ve "Alternatif 2:" yaz.\n'
    "Kesin yön ve konum belirtmeden kavramsal alternatif sun; "
    "zorunluysa tek takip sorusu sor.\n"
    "Alternatif 1 - <ad>: <açıklama>/Alternatif 2 - <ad>: <açıklama>/Temel fark: <fark>\n"
    "İki alternatif farklı mekânsal ilke sunmalı.\n"
    "Belirsizliği 'kesin konum/yön bilgisi henüz verilmedi' "
    "diyerek açıkla.\n"
    "Yanıt yalnız JSON Schema ile uyumlu olsun; "
    "aynı bilgiyi alanlar arasında tekrarlama.\n"
    "Her metin listesinde en fazla bir kısa öğe kullan; "
    "gereksizse boş liste kullan.\n"
    "Önerilen eylemlerde normalde en fazla bir eylem üret; "
    "karşılaştırmada plan eylemi üretme.\n"
)

SCHEMA_REPAIR_PROMPT = f"""{SYSTEM_PROMPT}
Önceki yanıt JSON Schema veya semantik doğrulamasından geçmedi.
Yalnızca çağrının format alanındaki JSON Schema ile tam uyumlu tek bir JSON nesnesi üret.
Markdown, kod bloğu, açıklama veya JSON nesnesi dışında serbest metin üretme.
Aşağıdaki kurallara KESİNLİKLE UY:
- "entity", "entity_id", "target", "enum", "öğe bilgisi", "ilgili mekân", "visible_entities"
  terimlerini kullanma.
- İngilizce kelime kullanma; tüm anlatım öz Türkçe ve doğal olsun.
- Karşılaştırmada intent=compare_alternatives, target tüm alanları null, proposed_actions=[],
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

COMPARE_SYSTEM_PROMPT = (
    "Sen BRIF.AI mimari niyet yorumlayıcısısın.\n"
    "Kullanıcı iki ayrı düzenleme alternatifi istedi.\n"
    "Yanıt yalnız JSON Schema ile tam uyumlu tek bir JSON nesnesi olsun.\n"
    'intent her zaman "compare_alternatives" olsun.\n'
    "assistant_message içinde şu 3 bölümü üret:\n"
    "Alternatif 1 - <Türkçe başlık>: <tek veya iki kısa cümle>\n"
    "Alternatif 2 - <Türkçe başlık>: <tek veya iki kısa cümle>\n"
    "Temel fark: <tek kısa cümle>\n"
    "Yalnız kullanıcının verdiği bilgileri temel al.\n"
    "Fiziksel yerleşim hakkında yeni gerçekler ekleme.\n"
    "Kesin konum, yön, mesafe veya topolojik ilişki tanımlama.\n"
    "İki alternatifi fiziksel koordinatlarla değil, ayrı organizasyon ilkeleriyle açıkla.\n"
    "Birinci alternatif ortak kullanımdaki süreklilik ve etkileşim gibi bir ilkeye; "
    "ikinci alternatif esneklik ve ayrışabilir kullanım gibi ayrı bir ilkeye dayanabilir.\n"
    "Kullanıcı tarafından belirtilen ilişkiyi yeniden yorumlayabilirsin; "
    "fakat yeni mekânsal gerçek üretme.\n"
    "Her cümleyi kullanım amacı, günlük deneyim, sosyal etkileşim, esneklik "
    "veya ayrışabilir kullanım üzerinden kur.\n"
    "Mekân adlarını fiziksel plan konumu belirten yüklemlerle kullanma.\n"
    "Cümle yüklemlerini şu amaç dilinden seç: güçlendirilir, destekler, uyum sağlar, "
    "korunur, öncelik verir, odaklanır.\n"
    "Her alternatifte tam iki kısa cümle, temel ayrımda tek kısa cümle kullan.\n"
    "assistant_message için şu örneğin kavramsal dilini temel al:\n"
    "Alternatif 1 - Etkileşim sürekliliği: Salon ile mutfak arasındaki günlük kullanım "
    "ilişkisi güçlendirilir. Terasın oturma ve sohbet işlevi sosyal deneyimi destekler.\n"
    "Alternatif 2 - Esnek kullanım: Salon ile mutfak değişen kullanım senaryolarına uyum "
    "sağlayacak biçimde ele alınır. Terasın günlük sosyal kullanım rolü korunur.\n"
    "Temel fark: Birinci yaklaşım etkileşim sürekliliğine, ikinci yaklaşım kullanım "
    "esnekliğine odaklanır.\n"
    "Her alternatif için doğal ve özgün bir anlatım kullan.\n"
    "Kısa, doğal ve profesyonel Türkçe kullan.\n"
    "confidence 0 ile 1 arasında bir sayı olsun.\n"
)

COMPARE_REPAIR_PROMPT = f"""{COMPARE_SYSTEM_PROMPT}
İlk yanıt doğrulanamadı.
Yalnız kullanıcının açıkça verdiği mekânsal bilgileri kullan.
Fiziksel yerleşim hakkında yeni gerçek üretme.
İki ayrı organizasyon yaklaşımı sun.
Yanıt şu üç bölümden oluşsun:
Alternatif 1 - <Türkçe başlık>: <tek veya iki kısa cümle>
Alternatif 2 - <Türkçe başlık>: <tek veya iki kısa cümle>
Temel fark: <tek kısa cümle>
Kısa, doğal ve profesyonel Türkçe kullan.
Cümle yüklemlerini şu amaç dilinden seç: güçlendirilir, destekler, uyum sağlar,
korunur, öncelik verir, odaklanır.
Tek bir JSON nesnesi üret.
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
