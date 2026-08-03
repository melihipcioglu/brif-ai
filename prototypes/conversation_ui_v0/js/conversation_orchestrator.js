/**
 * BRIF.AI — Conversation Orchestrator & State Engine (v6.1.4 Platform Architecture)
 *
 * Atomically updates workspace on project switches, filters conversation by active scope,
 * attaches context snapshots to every message, and handles scoped actions for all project types.
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

    this.chatContainerId = options.chatContainerId || 'chatMessagesContainer';
    this.allChatMessages = [];
    this.chatFilterMode = 'active_scope';

    // Subscribe to StateMachine & automatically re-render Presenter surfaces
    this.stateMachine.subscribe((ctx) => {
      this.syncStateWithHistory(ctx);
      this.validateAndSyncUI(ctx);
      if (this.presenter) {
        this.presenter.render({ activeContext: ctx });
      }
      this.renderFilteredChatMessages();
    });
  }

  setStage(stageNum) {
    this.stateMachine.dispatch({
      type: "STAGE_CHANGED",
      payload: { activeStage: stageNum }
    });

    if (stageNum === 3) {
      this.appendAssistantMessage("Mekân programını inceliyoruz. Aktif proje kapsamındaki tanımlı alanları düzenleyebiliriz.");
    } else if (stageNum === 4) {
      this.appendAssistantMessage("Taslak plan aşamasındayız. Seçili kat ve mekân kararları hakkında konuşabilirsiniz.");
    }
  }

  selectProject(projId) {
    let initPayload = { projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground", entityId: "space_study" };

    if (projId === "proj_tower_50floor") {
      initPayload = { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18", entityId: "space_meeting_18a" };
    } else if (projId === "proj_campus_multiblock") {
      initPayload = { projectId: "proj_campus_multiblock", buildingId: "block_a_r_d", levelId: "lvl_2_block_a", entityId: "space_robotics_lab" };
    }

    this.stateMachine.dispatch({
      type: "PROJECT_SELECTED",
      payload: initPayload
    });

    const ctx = this.stateMachine.getContext();
    const title = this.hierarchy.getScopeTitle(ctx);

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
        `📌 **${entity.name}** seçildi. Bu varlık hakkında düzenleme yapabiliriz.`
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
        return msg.snapshot.scenarioId === ctx.scenarioId || msg.snapshot.decisionId === ctx.decisionId;
      }

      return msg.snapshot.projectId === ctx.projectId && msg.snapshot.buildingId === ctx.buildingId;
    });

    filtered.forEach(msg => {
      const msgDiv = document.createElement('div');
      msgDiv.className = `chat-message ${msg.role === 'user' ? 'user' : 'assistant'}`;

      const avatar = document.createElement('div');
      avatar.className = `message-avatar ${msg.role === 'user' ? 'user' : 'brif'}`;
      avatar.textContent = msg.role === 'user' ? 'MK' : 'B';

      const content = document.createElement('div');
      content.className = 'message-content';

      const sender = document.createElement('div');
      sender.className = 'message-sender';
      sender.textContent = msg.role === 'user' ? 'Siz' : 'BRIF.AI Mimari Asistan';

      const messageText = document.createElement('div');
      messageText.className = 'message-text';
      messageText.textContent = msg.text === undefined || msg.text === null
        ? ''
        : String(msg.text);

      content.append(sender, messageText);

      if (msg.quickReplies && msg.quickReplies.length > 0) {
        const chips = document.createElement('div');
        chips.className = 'suggestion-chips';
        msg.quickReplies.forEach(reply => {
          const button = document.createElement('button');
          button.className = 'chip-btn followup-chip';
          button.dataset.reply = reply.label;
          button.dataset.action = reply.action;
          button.dataset.value = reply.value;
          button.dataset.optionId = reply.optionId;
          button.dataset.scenarioId = reply.scenarioId;
          button.dataset.decisionId = reply.decisionId;
          button.dataset.preferenceKey = reply.preferenceKey;
          button.dataset.preferenceValue = reply.preferenceValue;
          button.textContent = reply.label;
          chips.appendChild(button);
        });
        content.appendChild(chips);
      }

      msgDiv.append(avatar, content);
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

    const activeSnapshot = this.stateMachine.getSnapshot();
    const parsedPreference = this.intentParser.parseMasterBathPreference(messageText);
    if (this.isActiveMasterBathContext(activeSnapshot) && parsedPreference) {
      const registeredReply = (window.ScenarioQuickReplyRegistry?.master_bath_relocation || [])
        .find(reply => reply.optionId === parsedPreference.optionId);
      if (registeredReply) {
        this.recordMasterBathPreference({ ...registeredReply }, { appendUserMessage: false });
        return;
      }
    }

    const result = this.assistant.processUserMessage(messageText);
    this.appendAssistantMessage(result.aiResponseText);
  }

  normalizeQuickReply(reply, scopeSnapshot = null) {
    const isStructured = reply && typeof reply === 'object' && !Array.isArray(reply);
    const label = isStructured ? reply.label : reply;
    const scope = scopeSnapshot || {};
    return {
      label: label === undefined || label === null ? '' : String(label),
      action: isStructured && reply.action ? String(reply.action) : 'SEND_MESSAGE',
      value: isStructured && reply.value !== undefined ? String(reply.value) : String(label || ''),
      optionId: isStructured && reply.optionId ? String(reply.optionId) : '',
      scenarioId: isStructured && reply.scenarioId
        ? String(reply.scenarioId)
        : String(scope.scenarioId || ''),
      decisionId: isStructured && reply.decisionId
        ? String(reply.decisionId)
        : String(scope.decisionId || ''),
      preferenceKey: isStructured && reply.preferenceKey ? String(reply.preferenceKey) : '',
      preferenceValue: isStructured && reply.preferenceValue
        ? String(reply.preferenceValue)
        : ''
    };
  }

  isActiveMasterBathContext(snapshot) {
    if (!snapshot) return false;
    return snapshot.projectId === 'proj_house_2story' &&
      snapshot.scenarioId === 'master_bath_relocation' &&
      snapshot.decisionId === 'dec_master_bath' &&
      (snapshot.entityId === 'space_master_bath' ||
        snapshot.targetEntityId === 'space_master_bath');
  }

  handleQuickReply(replyPayload) {
    const reply = this.normalizeQuickReply(replyPayload);
    if (!reply.label) return false;

    if (reply.action === 'RECORD_MASTER_BATH_PREFERENCE') {
      return this.recordMasterBathPreference(reply, { appendUserMessage: true });
    }

    this.appendUserMessage(reply.label);
    this.handleUserMessage(reply.label);
    return true;
  }

  recordMasterBathPreference(replyPayload, options = {}) {
    const reply = this.normalizeQuickReply(replyPayload);
    const activeSnapshot = this.stateMachine.getSnapshot();
    const registeredReply = (window.ScenarioQuickReplyRegistry?.master_bath_relocation || [])
      .find(candidate =>
        candidate.optionId === reply.optionId &&
        candidate.preferenceKey === reply.preferenceKey &&
        candidate.preferenceValue === reply.preferenceValue
      );

    if (
      !registeredReply ||
      !this.isActiveMasterBathContext(activeSnapshot) ||
      reply.scenarioId !== activeSnapshot.scenarioId ||
      reply.decisionId !== activeSnapshot.decisionId
    ) {
      return false;
    }

    if (options.appendUserMessage) {
      this.appendUserMessage(registeredReply.label);
    }

    const updated = this.stateMachine.dispatch({
      type: 'SCENARIO_RESPONSE_RECORDED',
      payload: {
        projectId: activeSnapshot.projectId,
        scenarioId: activeSnapshot.scenarioId,
        decisionId: activeSnapshot.decisionId,
        optionId: registeredReply.optionId,
        preferenceKey: registeredReply.preferenceKey,
        preferenceValue: registeredReply.preferenceValue
      }
    });
    const savedResponse = updated.scenarioResponses[activeSnapshot.scenarioId];
    if (!savedResponse || savedResponse.optionId !== registeredReply.optionId) return false;

    const responsePrefix = {
      bed_visibility: 'Yataktan görünmeme önceliğini kaydettim.',
      access_route: 'Giyinme alanından erişim önceliğini kaydettim.',
      privacy: 'Artırılmış mahremiyet önceliğini kaydettim.'
    }[registeredReply.preferenceKey];
    this.appendAssistantMessage(
      `${responsePrefix} Bu yalnızca karar girdisidir; plan otomatik değiştirilmedi. ` +
      'Şimdi bu önceliğe göre iki yerleşim seçeneğini karşılaştırabilirsiniz.'
    );
    return true;
  }

  triggerMasterBathScenario(userRequestText) {
    this.stateMachine.dispatch({
      type: "SCENARIO_CONTEXT_STARTED",
      payload: {
        projectId: "proj_house_2story",
        buildingId: "bldg_main",
        levelId: "lvl_upper",
        entityId: "space_master_bath",
        entityType: "space",
        scenarioId: "master_bath_relocation",
        decisionId: "dec_master_bath",
        targetEntityId: "space_master_bath",
        workspaceMode: "plan"
      }
    });

    this.appendAssistantMessage(
      "Banyoyu kuzey kenarına almak istiyorsunuz. Buradaki önceliğiniz yataktan görünmemesi mi, giyinme alanından erişilmesi mi, yoksa daha mahrem bir kullanım mı?",
      (window.ScenarioQuickReplyRegistry?.master_bath_relocation || [])
        .map(reply => ({ ...reply }))
    );

    this.syncStateWithHistory();
  }

  applyMasterBathOption(optionNum) {
    const decisionStatus = `Seçenek ${optionNum} Seçildi (Uygulandı)`;
    this.stateMachine.dispatch({
      type: "DECISION_RECORDED",
      payload: {
        selectedOption: optionNum,
        decisionStatus: decisionStatus,
        workspaceMode: "options_side_by_side"
      }
    });

    const updated = this.stateMachine.getSnapshot();
    if (
      updated.selectedOption !== optionNum ||
      updated.decisionStatus !== decisionStatus
    ) {
      return false;
    }

    this.syncStateWithHistory();
    this.appendAssistantMessage(`✅ Seçenek ${optionNum} karar olarak kaydedildi; plan otomatik değiştirilmedi.`);
    return true;
  }

  resumeSuspendedContext() {
    this.stateMachine.dispatch({
      type: "SCENARIO_RESUMED",
      payload: { workspaceMode: "options_side_by_side" }
    });
    const ctx = this.stateMachine.getContext();
    this.appendAssistantMessage(`↩ Önceki bağlama dönüldü: ${this.hierarchy.getScopeTitle(ctx)}.`);

  }

  triggerFloorOverlayScenario() {
    this.stateMachine.dispatch({
      type: "SCENARIO_STARTED",
      payload: { scenarioId: "floor_overlay", workspaceMode: "overlay" }
    });
    this.appendAssistantMessage("Kat ilişkisini okunabilir kodlarla gösteriyorum.", ["Sadece üst katı göster", "Alt katı saydam göster", "Normal plana dön"]);
  }

  triggerOrientationScenario() {
    this.stateMachine.dispatch({
      type: "SCENARIO_STARTED",
      payload: { scenarioId: "orientation", workspaceMode: "orientation" }
    });
    this.appendAssistantMessage("Cephe yönlenmesini kat planı üzerinde gösteriyorum.", ["Kuzey cephesini göster", "Güney salon ilişkisini göster", "Normal plana dön"]);
  }

  // Scoped Tower Handlers
  triggerTowerMeetingScenario() {
    this.appendAssistantMessage("👥 A Kulesi 18. Kat Yönetim Toplantı Odası (18A) protokol ve akustik ilişkisi inceleniyor.");
  }
  triggerTowerCoreScenario() {
    this.appendAssistantMessage("🛗 50 Katlı Finans Kulesi yüksek hızlı asansör ve servis çekirdeği düşey hatları vurgulandı.");
  }
  triggerTowerFloorsScenario() {
    this.appendAssistantMessage("🏢 18. Kat (Yönetim) ile 32. Kat (Operasyon) arasındaki düşey iletişim aksı simüle ediliyor.");
  }

  // Scoped Campus Handlers
  triggerCampusLabScenario() {
    this.appendAssistantMessage("🔬 Blok A (AR-GE) Robotik Araştırma Laboratuvarı ağır yük zemin ve havalandırma aksı doğrulandı.");
  }
  triggerCampusBlocksScenario() {
    this.appendAssistantMessage("🌉 AR-GE Binası (Blok A) ile İdari Bina (Blok B) arasındaki tüp geçit bağlantısı vurgulandı.");
  }
  triggerCampusTechScenario() {
    this.appendAssistantMessage("⚡ Kampüs merkezi yüksek gerilim ve teknik destek zonu erişimleri inceleniyor.");
  }

  syncStateWithHistory(activeSnapshot = null) {
    if (this.historyManager) {
      this.historyManager.setSessionState(activeSnapshot || this.stateMachine.getSnapshot());
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
      quickReplies: quickReplies
        .map(reply => this.normalizeQuickReply(reply, ctx))
        .filter(reply => reply.label),
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
