"""Prompts shared by local model providers."""

from __future__ import annotations

import json

from brif_ai.llm.contracts import ConversationRequest

SYSTEM_PROMPT = """Sen BRIF.AI mimari niyet yorumlayıcısısın.
Yalnız verilen aktif bağlamı ve görünür varlıkları kullan.
Proje, bina, kat, zon veya mekân kimliği uydurma.
Planı, ContextStateMachine durumunu veya SVG geometrisini değiştirme.
Yalnız izin verilen öneri eylemlerini üret; değişiklik önerileri kullanıcı onayı gerektirir.
Hedef belirsizse takip sorusu sor. Aktif kapsam dışındaki talebi kesin gerçek kabul etme.
Yanıtın, çağrının format alanında verilen JSON Schema ile tam uyumlu olmalıdır.
"""


def build_user_prompt(request: ConversationRequest) -> str:
    """Serialize only the minimum validated context needed for interpretation."""

    payload = {
        "message": request.message,
        "active_context": request.active_context.model_dump(mode="json"),
        "visible_entities": [entity.model_dump(mode="json") for entity in request.visible_entities],
        "conversation_summary": request.conversation_summary,
        "current_decisions": request.current_decisions,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
