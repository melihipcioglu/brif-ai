/**
 * BRIF.AI — Contextual Assistant Core Engine (v5.2 Refined)
 *
 * Single persistent assistant managing session context state, dynamic context badges,
 * and stage-aware greetings.
 */

class ContextualAssistant {
  constructor(options = {}) {
    this.historyMemory = []; // Keeps last 16 messages

    // Single Unified Session Context State (Requirement 1 & 2)
    this.currentContext = {
      stage: 1,
      prefRound: 1,
      alternative: 'a',
      floor: 'ground',
      spaceId: 'study',
      spaceName: 'Çalışma Odası',
      activeScenario: null,
      isArchitectView: false,
      workflowStep: 1
    };

    this.intentParser = new DemoIntentParser();
    this.ruleEvaluator = new RuleEvaluator();
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
      const spaceStr = ctx.spaceName ? ` — ${ctx.spaceName} Kararı` : '';
      badgeText = `Mimar Önizlemesi${spaceStr}`;
    } else if (ctx.activeScenario === 'master_bath_relocation') {
      badgeText = 'Ebeveyn Banyosu hakkında konuşuyorsunuz';
    } else if (ctx.activeScenario === 'floor_overlay') {
      badgeText = 'Kat İlişkisi Anlatımı';
    } else if (ctx.activeScenario === 'orientation') {
      badgeText = `Cephe Yönlenmesi — ${ctx.spaceName || 'Ebeveyn Süiti'}`;
    } else if (ctx.stage === 1) {
      badgeText = 'Yaşamınızı Anlama — Hane Yapısı';
    } else if (ctx.stage === 2) {
      badgeText = `Görsel Tercihler — Tur ${ctx.prefRound}`;
    } else if (ctx.stage === 3) {
      badgeText = `Mekân Programı — ${ctx.spaceName || 'Tüm Mekânlar'}`;
    } else if (ctx.stage === 4) {
      const altText = ctx.alternative === 'a' ? 'Alternatif A' : 'Alternatif B';
      const floorText = ctx.floor === 'ground' ? 'Zemin Kat' : 'Üst Kat';
      badgeText = ctx.spaceName 
        ? `${ctx.spaceName} hakkında konuşuyorsunuz` 
        : `Taslak Plan — ${altText} / ${floorText}`;
    }

    badgeEl.textContent = badgeText;

    if (headerInfo) {
      if (ctx.spaceName && (ctx.stage === 4 || ctx.stage === 3)) {
        headerInfo.innerHTML = `📌 <strong>${escapeHtml(ctx.spaceName)}</strong> hakkında konuşuyorsunuz.`;
        headerInfo.classList.remove('hidden');
      } else {
        headerInfo.classList.add('hidden');
      }
    }
  }

  processUserMessage(messageText) {
    this.historyMemory.push({ role: 'user', text: messageText });
    if (this.historyMemory.length > 16) {
      this.historyMemory = this.historyMemory.slice(-16);
    }

    const actionPayload = this.intentParser.parseMessage(messageText, this.currentContext);
    const dummySpace = { id: actionPayload.target.space_id, use_type: 'work' };
    const evaluationResults = this.ruleEvaluator.evaluateSpaceOperation(dummySpace, actionPayload.operation.type, {
      narrow_edge: actionPayload.operation.narrow_edge,
      is_misleading_rename: actionPayload.special_case === 'misleading_bypass'
    });

    let aiResponseText = '';
    const intent = actionPayload.intent;

    if (actionPayload.special_case === 'two_meter_bedroom') {
      aiResponseText = evaluationResults[0].user_message;
    } else if (actionPayload.special_case === 'misleading_bypass') {
      aiResponseText = evaluationResults[0].user_message;
    } else if (intent === 'resize_space') {
      aiResponseText = `${this.currentContext.spaceName || 'Çalışma odası'} alanını küçültme talebinizi değerlendirdim. Ön kontrolden geçen iki opsiyonu çalışma alanında inceleyebilirsiniz.`;
    } else if (intent === 'move_space') {
      aiResponseText = `Seçili mekânı taşıma simülasyonunu hazırladım. Komşu alanlar üzerindeki sirkülasyon etkisini kartlar üzerinden görebilirsiniz.`;
    } else {
      aiResponseText = `Talebinizi not aldım: "${messageText}". Bu durumu şematik plan kararlarına ve mimar özetine yansıtacağız.`;
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
