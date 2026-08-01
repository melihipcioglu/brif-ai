/**
 * BRIF.AI — Contextual Assistant Core Engine (v4 Demo)
 *
 * Provides a single, stage-aware assistant instance across all 4 stages
 * and Architect View. Manages conversation memory (last 8 turns), context badges,
 * action proposal cards, and rule evaluation synthesis.
 */

class ContextualAssistant {
  constructor(options = {}) {
    this.historyMemory = []; // Keeps last 8 turns
    this.currentContext = {
      stage: 1,
      prefRound: 1,
      alternative: 'a',
      floor: 'ground',
      spaceId: 'study',
      spaceName: 'Çalışma Odası',
      isArchitectView: false
    };

    this.intentParser = new DemoIntentParser();
    this.ruleEvaluator = new RuleEvaluator();

    this.onActionProposed = options.onActionProposed || (() => {});
    this.onActionExecuted = options.onActionExecuted || (() => {});
  }

  setContext(newCtx) {
    this.currentContext = { ...this.currentContext, ...newCtx };
    this.updateContextBadge();
  }

  updateContextBadge() {
    const badgeEl = document.getElementById('assistantContextBadge');
    const headerInfo = document.getElementById('chatHeaderRoomInfo');
    if (!badgeEl) return;

    const ctx = this.currentContext;
    let badgeText = '';

    if (ctx.isArchitectView) {
      badgeText = 'Mimar Önizlemesi — Teyit Gereken Kararlar';
    } else if (ctx.stage === 1) {
      badgeText = 'Yaşamınızı Anlama — Sohbet Diyaloğu';
    } else if (ctx.stage === 2) {
      badgeText = `Görsel Tercihler — Tur ${ctx.prefRound}`;
    } else if (ctx.stage === 3) {
      badgeText = `Mekân Programı — ${ctx.spaceName || 'Tüm Mekânlar'} Seçili`;
    } else if (ctx.stage === 4) {
      const altText = ctx.alternative === 'a' ? 'Alternatif A' : 'Alternatif B';
      const floorText = ctx.floor === 'ground' ? 'Zemin Kat' : 'Üst Kat';
      badgeText = `Taslak Plan — ${altText} / ${floorText} — ${ctx.spaceName || 'Çalışma Odası'} Seçili`;
    }

    badgeEl.textContent = badgeText;

    if (headerInfo) {
      if (ctx.stage === 4 && ctx.spaceName) {
        headerInfo.innerHTML = `📌 <strong>${escapeHtml(ctx.spaceName)}</strong> hakkında konuşuyorsunuz.`;
        headerInfo.classList.remove('hidden');
      } else {
        headerInfo.classList.add('hidden');
      }
    }
  }

  processUserMessage(messageText) {
    // Record turn in memory (last 8 turns)
    this.historyMemory.push({ role: 'user', text: messageText });
    if (this.historyMemory.length > 16) {
      this.historyMemory = this.historyMemory.slice(-16);
    }

    // Parse Intent into Structured Payload
    const actionPayload = this.intentParser.parseMessage(messageText, this.currentContext);

    // Evaluate Rules
    const dummySpace = { id: actionPayload.target.space_id, use_type: 'work' };
    const evaluationResults = this.ruleEvaluator.evaluateSpaceOperation(dummySpace, actionPayload.operation.type, {
      narrow_edge: actionPayload.operation.narrow_edge,
      is_misleading_rename: actionPayload.special_case === 'misleading_bypass',
      rename_text: actionPayload.operation.rename_text
    });

    // Response Generation with Natural Variations (Requirement 17)
    let aiResponseText = '';
    const intent = actionPayload.intent;

    if (actionPayload.special_case === 'two_meter_bedroom') {
      aiResponseText = evaluationResults[0].user_message;
    } else if (actionPayload.special_case === 'misleading_bypass') {
      aiResponseText = evaluationResults[0].user_message;
    } else if (intent === 'resize_space') {
      aiResponseText = `Çalışma alanını küçültme talebinizi hazırladım. 14 m²'den 10–11 m²'ye indirme işlemini aşağıdaki etki kartından önizleyebilirsiniz.`;
    } else if (intent === 'move_space') {
      aiResponseText = `Seçili mekânı taşıma simülasyonu hazırlandı. Komşu mekân ve sirkülasyon etkilerini kart üzerinden inceleyebilirsiniz.`;
    } else if (intent === 'swap_spaces') {
      aiResponseText = `Mutfak ve çalışma alanı takas etki analizi oluşturuldu.`;
    } else if (intent === 'lock_space') {
      aiResponseText = `Çalışma odası kilitlendi. Artık sürükleme veya sohbet komutlarıyla değiştirilemez. Değişiklikleri serbest mekânlar üzerinden deneyeceğim.`;
    } else if (intent === 'undo') {
      aiResponseText = `Son yapılan değişiklik geri alındı.`;
    } else if (intent === 'ambiguous_request') {
      aiResponseText = `Bu prototipte bu isteği otomatik işleyemiyorum. Değiştirmek istediğiniz mekânı seçip büyütme, taşıma veya ilişki değiştirme işlemlerinden birini seçebilirsiniz.`;
    } else {
      aiResponseText = `İfade ettiğiniz konuyu not aldım: "${messageText}". Bu durumu şematik plan kararlarına yansıtacağız.`;
    }

    this.historyMemory.push({ role: 'assistant', text: aiResponseText });

    return {
      actionPayload,
      evaluationResults,
      aiResponseText
    };
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, match => {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return map[match];
  });
}

// Global Export
window.ContextualAssistant = ContextualAssistant;
