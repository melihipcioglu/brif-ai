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
    this.localLLMGateway = options.localLLMGateway || null;
    this.proposalRecords = [];
    this.pendingProposals = new Map();
    this.proposalSequence = 0;

    this.chatContainerId = options.chatContainerId || 'chatMessagesContainer';
    this.allChatMessages = [];
    this.chatFilterMode = 'active_scope';

    this.isRequestPending = false;
    this.currentAbortController = null;
    this.requestTimerId = null;
    this.requestStartTime = 0;
    this.pendingWaitingMessageIndex = -1;
    this.activeRequestMessage = null;
    this.handledCancellationMessages = new Map();

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

  setChatInputLocked(locked) {
    const chatContainer = document.getElementById(this.chatContainerId);
    const parent = chatContainer ? (chatContainer.closest('[data-test-scope-guard-root]') || chatContainer.parentElement) : document;
    const input = (parent && parent.querySelector('#assistantUserInput')) || document.getElementById('assistantUserInput');
    const sendBtn = (parent && parent.querySelector('#sendBtn')) || document.getElementById('sendBtn') ||
      (document.getElementById('assistantChatForm')?.querySelector('button[type="submit"]'));
    if (input) {
      input.disabled = locked;
      if (locked) {
        if (this._originalPlaceholder === undefined) {
          this._originalPlaceholder = input.placeholder || '';
        }
        input.placeholder = 'Mimari talebiniz değerlendiriliyor...';
      } else {
        if (this._originalPlaceholder !== undefined) {
          input.placeholder = this._originalPlaceholder;
          delete this._originalPlaceholder;
        }
      }
    }
    if (sendBtn) {
      sendBtn.disabled = locked;
    }
  }

  startPendingRequest(messageText) {
    if (this.isRequestPending) return false;
    this.isRequestPending = true;
    this.activeRequestMessage = String(messageText || '');
    this.setChatInputLocked(true);
    this.currentAbortController = new AbortController();
    this.requestStartTime = Date.now();

    const ctx = this.stateMachine.getContext();
    this.allChatMessages.push({
      role: 'assistant',
      text: 'Mimari talebiniz değerlendiriliyor (0 sn)',
      quickReplies: [],
      proposedActions: [],
      isWaitingIndicator: true,
      canCancel: true,
      snapshot: { ...ctx, timestamp: new Date().toISOString() }
    });
    this.pendingWaitingMessageIndex = this.allChatMessages.length - 1;
    this.renderFilteredChatMessages();

    if (this.requestTimerId) clearInterval(this.requestTimerId);
    this.requestTimerId = setInterval(() => {
      if (!this.isRequestPending || this.pendingWaitingMessageIndex < 0) {
        if (this.requestTimerId) clearInterval(this.requestTimerId);
        this.requestTimerId = null;
        return;
      }
      const sec = Math.floor((Date.now() - this.requestStartTime) / 1000);
      const waitingMsg = this.allChatMessages[this.pendingWaitingMessageIndex];
      if (waitingMsg && waitingMsg.isWaitingIndicator) {
        waitingMsg.text = `Mimari talebiniz değerlendiriliyor (${sec} sn)`;
        this.renderFilteredChatMessages();
      }
    }, 1000);

    return true;
  }

  finishPendingRequest() {
    if (this.requestTimerId) {
      clearInterval(this.requestTimerId);
      this.requestTimerId = null;
    }
    if (
      this.pendingWaitingMessageIndex >= 0 &&
      this.allChatMessages[this.pendingWaitingMessageIndex]?.isWaitingIndicator
    ) {
      this.allChatMessages.splice(this.pendingWaitingMessageIndex, 1);
    }
    this.pendingWaitingMessageIndex = -1;
    this.currentAbortController = null;
    this.isRequestPending = false;
    this.activeRequestMessage = null;
    this.setChatInputLocked(false);
    this.renderFilteredChatMessages();
  }

  cancelCurrentRequest() {
    if (!this.isRequestPending) return false;
    const canceledMessage = this.activeRequestMessage || '';
    if (canceledMessage) {
      const handledCount = this.handledCancellationMessages.get(canceledMessage) || 0;
      this.handledCancellationMessages.set(canceledMessage, handledCount + 1);
    }
    if (this.currentAbortController) {
      this.currentAbortController.abort();
    }
    this.finishPendingRequest();
    this.appendAssistantMessage(
      'İstek kullanıcı tarafından iptal edildi. Plan veya karar kayıtları değiştirilmedi.',
      [],
      [],
      { retryMessage: canceledMessage || null }
    );
    return true;
  }

  retryLastMessage(messageText) {
    if (this.isRequestPending) return false;
    return this.handleUserMessage(messageText);
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

  setLocalLLMGateway(gateway) {
    this.localLLMGateway = gateway;
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

      if (msg.proposedActions && msg.proposedActions.length > 0) {
        const proposals = document.createElement('div');
        proposals.className = 'suggestion-chips';
        msg.proposedActions.forEach(proposal => {
          const label = document.createElement('span');
          label.className = 'message-text';
          label.textContent = proposal.action.description;
          proposals.appendChild(label);
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'chip-btn proposal-approve-btn';
          button.dataset.proposalId = proposal.id;
          if (proposal.status === 'approved') {
            button.disabled = true;
            button.classList.add('proposal-approved');
            button.textContent = 'Onaylandı';
            button.setAttribute('aria-disabled', 'true');
          } else {
            button.textContent = 'Öneriyi onayla';
          }
          proposals.appendChild(button);
        });
        content.appendChild(proposals);
      }

      if (msg.canCancel || msg.isWaitingIndicator) {
        const cancelBox = document.createElement('div');
        cancelBox.className = 'suggestion-chips';
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'chip-btn cancel-request-btn';
        cancelBtn.id = 'cancelRequestBtn';
        cancelBtn.textContent = 'İptal et';
        cancelBox.appendChild(cancelBtn);
        content.appendChild(cancelBox);
      }

      if (msg.retryMessage) {
        const retryBox = document.createElement('div');
        retryBox.className = 'suggestion-chips';
        const retryBtn = document.createElement('button');
        retryBtn.type = 'button';
        retryBtn.className = 'chip-btn retry-request-btn';
        retryBtn.dataset.retryMessage = msg.retryMessage;
        retryBtn.textContent = 'Tekrar dene';
        retryBox.appendChild(retryBtn);
        content.appendChild(retryBox);
      }

      msgDiv.append(avatar, content);
      chatContainer.appendChild(msgDiv);
    });

    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  async handleUserMessage(messageText) {
    if (!messageText) return null;

    const pendingCommand = this.handlePendingProposalCommand(messageText);
    if (pendingCommand) return pendingCommand;

    if (this.isRequestPending) return null;

    this.startPendingRequest(messageText);

    try {
      if (this.localLLMGateway) {
        return await this.localLLMGateway.interpret(
          messageText,
          { signal: this.currentAbortController?.signal }
        );
      }
      return this.handleDemoUserMessage(messageText);
    } finally {
      this.finishPendingRequest();
    }
  }

  handleDemoUserMessage(messageText) {
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

  handleStructuredLLMResponse(result, contextFingerprint, generationId = null) {
    const needsSeparateQuestion = result.needs_follow_up
      && result.follow_up_question
      && !result.assistant_message.includes(result.follow_up_question);
    const assistantMessage = needsSeparateQuestion
      ? result.assistant_message + '\n\n' + result.follow_up_question
      : result.assistant_message;
    const current = this.stateMachine.getSnapshot();
    const proposalGenerationId = Number.isInteger(generationId)
      ? generationId
      : current.generationId;
    const proposedActions = Array.isArray(result.proposed_actions)
      ? result.proposed_actions
      : [];
    const proposals = proposedActions.map(action => {
      const actionCopy = JSON.parse(JSON.stringify(action));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        JSON.stringify(candidate.action) === JSON.stringify(actionCopy)
      );
      if (existing) return existing;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: actionCopy,
        contextFingerprint,
        generationId: proposalGenerationId
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });
    this.appendAssistantMessage(assistantMessage, [], proposals);
  }

  approveProposalById(proposalId) {
    const proposal = this.pendingProposals.get(proposalId);
    if (!proposal) return null;
    const current = this.stateMachine.getSnapshot();
    if (
      proposal.contextFingerprint !== current.contextFingerprint ||
      proposal.generationId !== current.generationId
    ) {
      this.appendAssistantMessage('Bağlam değiştiği için bu öneri onaylanamadı.');
      return null;
    }

    const record = {
      proposal_status: 'user_approved',
      approved_at: new Date().toISOString(),
      context_fingerprint: current.contextFingerprint,
      proposed_action: JSON.parse(JSON.stringify(proposal.action))
    };
    this.proposalRecords.push(record);
    this.pendingProposals.delete(proposalId);
    this.allChatMessages.forEach(message => {
      if (!Array.isArray(message.proposedActions)) return;
      message.proposedActions.forEach(candidate => {
        if (candidate.id === proposalId) candidate.status = 'approved';
      });
    });
    this.appendAssistantMessage(
      'Öneri onay kaydı oluşturuldu. Plan henüz değiştirilmedi.'
    );
    return record;
  }

  dismissProposalById(proposalId) {
    const proposal = this.pendingProposals.get(proposalId);
    if (!proposal) return false;
    const current = this.stateMachine.getSnapshot();
    if (
      proposal.contextFingerprint !== current.contextFingerprint ||
      proposal.generationId !== current.generationId
    ) {
      this.appendAssistantMessage('Bağlam değiştiği için bu öneri iptal edilemedi.');
      return false;
    }

    this.pendingProposals.delete(proposalId);
    this.appendAssistantMessage('Bekleyen öneri iptal edildi. Plan değiştirilmedi.');
    return true;
  }

  getActivePendingProposals(snapshot = null) {
    const active = snapshot || this.stateMachine.getSnapshot();
    return Array.from(this.pendingProposals.values()).filter(proposal =>
      proposal.contextFingerprint === active.contextFingerprint &&
      proposal.generationId === active.generationId
    );
  }

  getPendingProposalContext(snapshot = null) {
    return this.getActivePendingProposals(snapshot).map(proposal => ({
      status: 'pending_user_confirmation',
      context_fingerprint: proposal.contextFingerprint,
      generation_id: proposal.generationId,
      action: JSON.parse(JSON.stringify(proposal.action))
    }));
  }

  getConversationSummary() {
    const transcript = this.allChatMessages
      .slice(-6)
      .map(message => message.role + ': ' + message.text);
    const pending = this.getPendingProposalContext().map(proposal =>
      `${proposal.status}: ${proposal.action.description}`
    );
    return [...transcript, ...pending].join('\n');
  }

  getCurrentDecisions() {
    return this.proposalRecords.map(record => (
      record.proposal_status + ': ' + record.proposed_action.description
    ));
  }

  handlePendingProposalCommand(messageText) {
    const pending = this.getActivePendingProposals();
    if (pending.length === 0) return null;
    const normalized = String(messageText || '').trim().toLocaleLowerCase('tr-TR');

    if (['onayla', 'onaylıyorum', 'kabul et', 'kabul ediyorum'].some(command =>
      normalized.includes(command)
    )) {
      const record = this.approveProposalById(pending[0].id);
      return { status: record ? 'approved' : 'stale', record };
    }

    if (['vazgeç', 'iptal et', 'reddet'].some(command =>
      normalized.includes(command)
    )) {
      const dismissed = this.dismissProposalById(pending[0].id);
      return { status: dismissed ? 'dismissed' : 'stale' };
    }

    return null;
  }

  handleLocalLLMFallback(messageText, status = 'error') {
    const commandResult = this.handlePendingProposalCommand(messageText);
    if (commandResult) return commandResult;

    if (status === 'canceled') {
      const handledCount = this.handledCancellationMessages.get(messageText) || 0;
      if (handledCount > 0) {
        if (handledCount === 1) {
          this.handledCancellationMessages.delete(messageText);
        } else {
          this.handledCancellationMessages.set(messageText, handledCount - 1);
        }
        return { status: 'canceled' };
      }
      this.appendAssistantMessage(
        'İstek kullanıcı tarafından iptal edildi. Plan veya karar kayıtları değiştirilmedi.',
        [],
        [],
        { retryMessage: messageText }
      );
      return { status: 'canceled' };
    }

    const reason = {
      disabled: 'Yerel yapay zekâ bağlantısı devre dışı. Demo konuşma modu kullanılıyor.',
      error: 'Yerel yapay zekâ servisi doğrulanamayan bir yanıt döndürdü.',
      invalid: 'Yerel yapay zekâ servisi doğrulanamayan bir yanıt döndürdü.',
      timeout: 'Yerel yapay zekâ yanıtı zaman aşımına uğradı (yanıt süresi sınırı aşıldı).',
      unreachable: 'Yerel yapay zekâ servisine ulaşılamıyor. Lütfen Ollama servisinin ve yerel sunucunun çalıştığından emin olun.'
    }[status] || 'Yerel yapay zekâ servisi yanıt veremedi.';

    const pending = this.getPendingProposalContext();
    if (pending.length > 0) {
      const descriptions = pending
        .map(proposal => proposal.action.description)
        .join(' ');
      this.appendAssistantMessage(
        `${reason} Bekleyen öneriniz: ${descriptions} ` +
        'Plan otomatik değiştirilmedi. Öneriyi onaylayabilir, ' +
        'ayrıntılandırabilir veya vazgeçebilirsiniz.',
        [],
        [],
        { retryMessage: messageText }
      );
      return { status: 'pending_continuation', failureStatus: status };
    }

    this.appendAssistantMessage(reason, [], [], { retryMessage: messageText });
    this.handleDemoUserMessage(messageText);
    return { status: status, failureStatus: status };
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

  appendAssistantMessage(text, quickReplies = [], proposedActions = [], options = {}) {
    if (this.pendingWaitingMessageIndex >= 0 && this.allChatMessages[this.pendingWaitingMessageIndex]?.isWaitingIndicator) {
      this.allChatMessages.splice(this.pendingWaitingMessageIndex, 1);
      this.pendingWaitingMessageIndex = -1;
    }

    const ctx = this.stateMachine.getContext();
    this.allChatMessages.push({
      role: 'assistant',
      text: text,
      quickReplies: quickReplies
        .map(reply => this.normalizeQuickReply(reply, ctx))
        .filter(reply => reply.label),
      proposedActions: Array.isArray(proposedActions) ? proposedActions : [],
      retryMessage: options.retryMessage || null,
      isWaitingIndicator: options.isWaitingIndicator || false,
      canCancel: options.canCancel || false,
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
