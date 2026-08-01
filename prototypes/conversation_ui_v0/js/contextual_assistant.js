/**
 * BRIF.AI — Contextual Assistant Core Engine (v6.0 Refined)
 *
 * Uses EntityHierarchy and ContextStateMachine for dynamic, room-name-independent
 * scope resolution and context badge rendering.
 */

class ContextualAssistant {
  constructor(options = {}) {
    this.historyMemory = [];

    this.hierarchy = options.hierarchy || new EntityHierarchy();
    this.stateMachine = options.stateMachine || new ContextStateMachine(this.hierarchy);

    this.intentParser = new DemoIntentParser();
    this.ruleEvaluator = new RuleEvaluator();

    // Subscribe to state machine updates
    this.stateMachine.subscribe((ctx) => {
      this.updateContextBadge(ctx);
    });
  }

  updateContextBadge(ctx) {
    const badgeEl = document.getElementById('assistantContextBadge');
    const headerInfo = document.getElementById('chatHeaderRoomInfo');
    if (!badgeEl) return;

    ctx = ctx || this.stateMachine.getContext();

    // Derive label dynamically from asset hierarchy (Requirement 8)
    let badgeText = "";

    if (ctx.viewMode === "architect_report") {
      badgeText = `Mimar Önizlemesi — ${this.hierarchy.getScopeTitle(ctx)}`;
    } else if (ctx.suspendedContext) {
      badgeText = `Askıda Bağlam (${ctx.suspendedContext.scopeTitle || 'Önceki Kat'})`;
    } else if (ctx.activeScenario === "master_bath_relocation") {
      badgeText = `${this.hierarchy.getScopeTitle(ctx)} hakkında konuşuyorsunuz`;
    } else if (ctx.activeScenario === "floor_overlay") {
      badgeText = "Kat İlişkisi Anlatımı (Düşey Tesisat Aksı)";
    } else if (ctx.activeScenario === "orientation") {
      badgeText = `Cephe Yönlenmesi — ${this.hierarchy.getScopeTitle(ctx)}`;
    } else {
      badgeText = this.hierarchy.getScopeTitle(ctx);
    }

    badgeEl.textContent = badgeText;

    if (headerInfo) {
      const entity = this.hierarchy.findEntity(ctx.entityId);
      if (entity && entity.type === "space") {
        headerInfo.innerHTML = `📌 <strong>${escapeHtml(entity.name)}</strong> hakkında konuşuyorsunuz.`;
        headerInfo.classList.remove('hidden');
      } else {
        headerInfo.classList.add('hidden');
      }
    }
  }

  processUserMessage(messageText) {
    const ctx = this.stateMachine.getContext();
    const actionPayload = this.intentParser.parseMessage(messageText, ctx);
    
    let aiResponseText = `Talebinizi not aldım: "${messageText}". Bu durumu ${this.hierarchy.getScopeTitle(ctx)} kararlarına ve mimar özetine yansıtacağız.`;

    this.historyMemory.push({ role: 'user', text: messageText, contextSnapshot: { ...ctx, timestamp: new Date().toISOString() } });
    this.historyMemory.push({ role: 'assistant', text: aiResponseText });

    return { actionPayload, aiResponseText };
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
