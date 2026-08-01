/**
 * BRIF.AI — Conversation Orchestrator & State Engine (v6.1 Platform Architecture)
 *
 * Atomically updates workspace on project switches, filters conversation by active scope,
 * and attaches context snapshots to every message.
 */

class ConversationOrchestrator {
  constructor(options = {}) {
    this.hierarchy = options.hierarchy || new EntityHierarchy();
    this.stateMachine = options.stateMachine || new ContextStateMachine(this.hierarchy);
    this.store = options.store || new ScopedDocumentStore();
    this.resolver = options.resolver || new WorkspaceScopeResolver(this.hierarchy, this.store);
    this.validator = new ContextValidator(this.hierarchy, this.stateMachine);

    this.assistant = options.assistant;
    this.presenter = options.presenter;
    this.historyManager = options.historyManager;
    this.intentParser = new DemoIntentParser();

    this.chatContainerId = 'chatMessages';
    this.allChatMessages = []; // Full message history with context snapshots
    this.chatFilterMode = 'active_scope'; // 'active_scope', 'active_decision', 'active_level', 'active_project', 'all'

    // Subscribe to state machine updates
    this.stateMachine.subscribe((ctx) => {
      this.validateAndSyncUI(ctx);
      this.renderFilteredChatMessages();
    });
  }

  setStage(stageNum) {
    let levelId = "lvl_ground";
    if (stageNum === 4) {
      const ctx = this.stateMachine.getContext();
      levelId = ctx.levelId || "lvl_ground";
    }

    this.stateMachine.dispatch({
      type: "LEVEL_SELECTED",
      payload: { levelId: levelId }
    });

    if (stageNum === 3) {
      this.appendAssistantMessage("Mekân programını inceliyoruz. Aktif proje kapsamındaki tanımlı alanları düzenleyebiliriz.");
    } else if (stageNum === 4) {
      this.appendAssistantMessage("Taslak plan aşamasındayız. Seçili kat ve mekân kararları hakkında konuşabilirsiniz.");
    }
  }

  // Atomic Workspace Transition on Project Switch (Requirement 15)
  selectProject(projId) {
    let initPayload = { projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground", entityId: "space_study" };

    if (projId === "proj_tower_50floor") {
      initPayload = { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18", entityId: "space_meeting_18a" };
    } else if (projId === "proj_campus_multiblock") {
      initPayload = { projectId: "proj_campus_multiblock", buildingId: "block_a_r_d", levelId: "lvl_2_block_a", entityId: "space_robotics_lab" };
    }

    // Atomic State Transition
    this.stateMachine.dispatch({
      type: "PROJECT_SELECTED",
      payload: initPayload
    });

    const ctx = this.stateMachine.getContext();
    const title = this.hierarchy.getScopeTitle(ctx);

    // Update Presenter atomically
    if (this.presenter) {
      this.presenter.render({ activeContext: ctx });
    }

    this.appendAssistantMessage(`🏢 Proje kapsamı güncellendi: ${title}.`);
    this.syncStateWithHistory();
  }

  selectLevel(levelId) {
    this.stateMachine.dispatch({
      type: "LEVEL_SELECTED",
      payload: { levelId: levelId }
    });
  }

  selectEntity(entityId) {
    const entity = this.hierarchy.findEntity(entityId);
    if (entity) {
      this.stateMachine.dispatch({
        type: "ENTITY_SELECTED",
        payload: { entityId: entityId, entityType: entity.type }
      });

      this.appendAssistantMessage(
        `📌 **${escapeHtml(entity.name)}** seçildi. Bu varlık hakkında düzenleme yapabiliriz.`
      );
    }
  }

  validateAndSyncUI(ctx) {
    const validation = this.validator.validateActiveContext(ctx);

    if (!validation.isValid && validation.suspendedData) {
      if (ctx.scenarioId) {
        this.stateMachine.dispatch({
          type: "SCENARIO_SUSPENDED",
          payload: { reason: validation.message }
        });
      }

      if (this.presenter) {
        this.presenter.renderSuspendedContextBanner(validation.message);
      }
    }
  }

  setChatFilterMode(filterMode) {
    this.chatFilterMode = filterMode;
    this.renderFilteredChatMessages();
  }

  // Scoped Chat Message Filtering (Requirement 10)
  renderFilteredChatMessages() {
    const chatContainer = document.getElementById(this.chatContainerId);
    if (!chatContainer) return;

    const ctx = this.stateMachine.getContext();
    chatContainer.innerHTML = '';

    const filtered = this.allChatMessages.filter(msg => {
      if (this.chatFilterMode === 'all') return true;
      if (!msg.snapshot) return true;

      if (this.chatFilterMode === 'active_project') {
        return msg.snapshot.projectId === ctx.projectId;
      }
      if (this.chatFilterMode === 'active_level') {
        return msg.snapshot.projectId === ctx.projectId && msg.snapshot.levelId === ctx.levelId;
      }
      if (this.chatFilterMode === 'active_decision') {
        return msg.snapshot.scenarioId === ctx.scenarioId;
      }

      // Default 'active_scope': matches current project & building
      return msg.snapshot.projectId === ctx.projectId && msg.snapshot.buildingId === ctx.buildingId;
    });

    filtered.forEach(msg => {
      const msgDiv = document.createElement('div');
      msgDiv.className = `message ${msg.role === 'user' ? 'user-message' : 'ai-message'}`;

      let chipsHtml = '';
      if (msg.quickReplies && msg.quickReplies.length > 0) {
        chipsHtml = `
          <div class="suggestion-chips">
            ${msg.quickReplies.map(r => `<button class="chip-btn followup-chip" data-reply="${escapeHtml(r)}">${escapeHtml(r)}</button>`).join('')}
          </div>
        `;
      }

      msgDiv.innerHTML = `
        <div class="message-avatar ${msg.role === 'user' ? 'user' : 'brif'}">${msg.role === 'user' ? 'MK' : 'B'}</div>
        <div class="message-content">
          <div class="message-sender">${msg.role === 'user' ? 'Siz' : 'BRIF.AI Mimari Asistan'}</div>
          <div class="message-text">${msg.text}</div>
          ${chipsHtml}
        </div>
      `;
      chatContainer.appendChild(msgDiv);
    });

    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  handleUserMessage(messageText) {
    if (!messageText) return;

    if (this.intentParser.isMasterBathInitial(messageText)) {
      this.triggerMasterBathScenario(messageText);
      return;
    }

    const result = this.assistant.processUserMessage(messageText);
    this.appendAssistantMessage(result.aiResponseText);
  }

  triggerMasterBathScenario(userRequestText) {
    this.stateMachine.dispatch({ type: "LEVEL_SELECTED", payload: { levelId: "lvl_upper" } });
    this.stateMachine.dispatch({ type: "ENTITY_SELECTED", payload: { entityId: "space_master_bath", entityType: "space" } });
    this.stateMachine.dispatch({
      type: "SCENARIO_STARTED",
      payload: { scenarioId: "master_bath_relocation", decisionId: "dec_master_bath", targetEntityId: "space_master_bath" }
    });

    this.appendAssistantMessage(
      "Banyoyu kuzey kenarına almak istiyorsunuz. Buradaki önceliğiniz yataktan görünmemesi mi, giyinme alanından erişilmesi mi, yoksa daha mahrem bir kullanım mı?",
      ["Yataktan görünmesini istemiyorum", "Giyinme alanından geçilsin", "Daha mahrem olsun"]
    );

    this.syncStateWithHistory();
  }

  applyMasterBathOption(optionNum) {
    const ctx = this.stateMachine.getContext();
    ctx.selectedOption = optionNum;
    ctx.decisionStatus = `Seçenek ${optionNum} Seçildi (Uygulandı)`;

    this.appendAssistantMessage(`✅ Seçenek ${optionNum} onaylandı ve plan kararlarına işlendi.`);

    if (this.presenter) {
      this.presenter.setMode('options_side_by_side', { selectedOption: optionNum });
    }

    this.syncStateWithHistory();
  }

  resumeSuspendedContext() {
    this.stateMachine.dispatch({ type: "SCENARIO_RESUMED" });
    const ctx = this.stateMachine.getContext();
    this.appendAssistantMessage(`↩ Önceki bağlama dönüldü: ${this.hierarchy.getScopeTitle(ctx)}.`);

    if (this.presenter) {
      this.presenter.setMode('options_side_by_side');
    }
  }

  triggerFloorOverlayScenario() {
    this.stateMachine.dispatch({ type: "SCENARIO_STARTED", payload: { scenarioId: "floor_overlay" } });
    if (this.presenter) this.presenter.setMode('overlay');
    this.appendAssistantMessage("Kat ilişkisini okunabilir kodlarla gösteriyorum.", ["Sadece üst katı göster", "Alt katı saydam göster", "Normal plana dön"]);
  }

  triggerOrientationScenario() {
    this.stateMachine.dispatch({ type: "SCENARIO_STARTED", payload: { scenarioId: "orientation" } });
    if (this.presenter) this.presenter.setMode('orientation');
    this.appendAssistantMessage("Cephe yönlenmesini kat planı üzerinde gösteriyorum.", ["Kuzey cephesini göster", "Güney salon ilişkisini göster", "Normal plana dön"]);
  }

  syncStateWithHistory() {
    if (this.historyManager) {
      this.historyManager.setSessionState(this.stateMachine.getContext());
    }
  }

  appendUserMessage(text) {
    const ctx = this.stateMachine.getContext();
    this.allChatMessages.push({
      role: 'user',
      text: text,
      snapshot: { ...ctx, timestamp: new Date().toISOString() }
    });
    this.renderFilteredChatMessages();
  }

  appendAssistantMessage(text, quickReplies = []) {
    const ctx = this.stateMachine.getContext();
    this.allChatMessages.push({
      role: 'assistant',
      text: text,
      quickReplies: quickReplies,
      snapshot: { ...ctx, timestamp: new Date().toISOString() }
    });
    this.renderFilteredChatMessages();
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
window.ConversationOrchestrator = ConversationOrchestrator;
