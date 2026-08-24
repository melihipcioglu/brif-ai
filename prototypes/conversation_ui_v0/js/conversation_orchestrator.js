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
    this.validator = options.validator || (typeof ContextValidator !== 'undefined'
      ? new ContextValidator(this.hierarchy, this.stateMachine)
      : { validateActiveContext: () => ({ isValid: true }) });

    this.assistant = options.assistant;
    this.presenter = options.presenter;
    this.historyManager = options.historyManager;
    this.intentParser = options.intentParser || (typeof DemoIntentParser !== 'undefined'
      ? new DemoIntentParser()
      : { isMasterBathInitial: () => false, parseMasterBathPreference: () => null });
    this.localLLMGateway = options.localLLMGateway || null;
    this.proposalRecords = [];
    this.briefMutationProposalRecords = [];
    this.metricRequirementProposalRecords = [];
    this.siteGeometryProposalRecords = [];
    this.pendingProposals = new Map();
    this.proposalSequence = 0;
    this.userMessageSequence = 0;
    this.lastUserMessageText = '';
    this.lastUserMessageRef = '';

    const initialBriefSnapshots = options.briefSnapshotsByProject
      ? JSON.parse(JSON.stringify(options.briefSnapshotsByProject))
      : {};
    this.demoBriefSnapshotsSeed = JSON.parse(JSON.stringify(initialBriefSnapshots));
    this.briefSnapshotsByProject = initialBriefSnapshots;

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

  getActiveBriefSnapshot() {
    const activeProjectId = this.stateMachine.getSnapshot().projectId;
    return this.briefSnapshotsByProject[activeProjectId] || null;
  }

  replaceActiveBriefSnapshot(newSnapshot) {
    const activeProjectId = this.stateMachine.getSnapshot().projectId;
    if (!newSnapshot || newSnapshot.project_id !== activeProjectId) {
      return false;
    }
    this.briefSnapshotsByProject[activeProjectId] = JSON.parse(JSON.stringify(newSnapshot));
    return true;
  }

  async loadProjectBrief(projectId) {
    if (!this.localLLMGateway) return false;
    const res = await this.localLLMGateway.fetchProjectBrief(projectId);
    if (res.ok && res.snapshot) {
      this.briefSnapshotsByProject[projectId] = res.snapshot;
      return true;
    }
    if (res.status === 404) {
      const seed = this.demoBriefSnapshotsSeed ? this.demoBriefSnapshotsSeed[projectId] : null;
      if (seed) {
        const initRes = await this.localLLMGateway.initializeProjectBrief(projectId, seed);
        if (initRes.ok && initRes.snapshot) {
          this.briefSnapshotsByProject[projectId] = initRes.snapshot;
          return true;
        }
      }
    }
    return false;
  }

  getSpaceDisplayName(spaceId) {
    if (!spaceId) return '';
    const activeBrief = this.getActiveBriefSnapshot();
    if (activeBrief && Array.isArray(activeBrief.space_requests)) {
      for (const req of activeBrief.space_requests) {
        const cleanReqId = req.id.replace(/^sr_/, '');
        if (spaceId.includes(cleanReqId)) {
          const idxMatch = spaceId.match(/_(\d{2})$/);
          if (idxMatch && req.minimum_quantity > 1) {
            return `${req.display_name} ${parseInt(idxMatch[1], 10)}`;
          }
          return req.display_name;
        }
      }
    }
    return spaceId;
  }

  getBriefMutationDescription(briefMutation) {
    if (!briefMutation) return '';
    const type = briefMutation.mutation_type;
    if (type === 'ADD_BRIEF_ITEM' && briefMutation.brief_item) {
      return `“${briefMutation.brief_item.normalized_statement}” brief'e eklensin mi?`;
    }
    if (type === 'ADD_SPACE_REQUEST' && briefMutation.space_request) {
      return `“${briefMutation.space_request.display_name}” mekân talebi brief'e eklensin mi?`;
    }
    if (type === 'ADD_USAGE_SCENARIO' && briefMutation.usage_scenario) {
      return `“${briefMutation.usage_scenario.title}” kullanım senaryosu brief'e eklensin mi?`;
    }
    return briefMutation.description || 'Brief güncellemesi eklensin mi?';
  }

  getSpatialRelationshipDescription(spatialRel) {
    if (!spatialRel) return '';
    const displayA = this.getSpaceDisplayName(spatialRel.source_space_id);
    const displayB = this.getSpaceDisplayName(spatialRel.target_space_id);

    const relationDescriptions = {
      ADJACENT_TO: 'birbirine bitişik',
      NEAR: 'birbirine yakın',
      SEPARATED_FROM: 'birbirinden ayrışmış',
      VISUAL_CONNECTION: 'arasında görsel bağlantı',
      DIRECT_ACCESS: 'arasında doğrudan geçiş',
      INDIRECT_ACCESS: 'arasında dolaylı bağlantı',
      ACOUSTIC_SEPARATION: 'arasında ses yalıtımı / akustik ayrım',
      PRIVACY_SEPARATION: 'arasında mahremiyet ayrımı'
    };
    const relText = relationDescriptions[spatialRel.relation_type] || spatialRel.relation_type;
    return `“${displayA} ile ${displayB} ${relText} olmalı.” mekânsal ilişkisi onaylansın mı?`;
  }

  getMetricRequirementDescription(metricReq) {
    if (!metricReq) return '';
    const displayName = this.getSpaceDisplayName(metricReq.space_id);
    const valStr = typeof metricReq.value === 'number'
      ? String(metricReq.value).replace('.', ',')
      : String(metricReq.value || '');
    if (metricReq.requirement_type === 'MIN_AREA') {
      return `“${displayName} en az ${valStr} m² olsun.” plan girdilerine eklensin mi?`;
    }
    if (metricReq.requirement_type === 'MAX_AREA') {
      return `“${displayName} en fazla ${valStr} m² olsun.” plan girdilerine eklensin mi?`;
    }
    if (metricReq.requirement_type === 'MIN_CLEAR_WIDTH') {
      return `“${displayName} net genişliği en az ${valStr} m olsun.” plan girdilerine eklensin mi?`;
    }
    return `“${displayName} ölçü gereksinimi” plan girdilerine eklensin mi?`;
  }

  getSiteGeometryDescription(siteGeometry) {
    if (!siteGeometry) return '';
    const formatCoord = (num) => typeof num === 'number'
      ? String(num).replace('.', ',')
      : String(num || '');
    const verticesStr = (siteGeometry.vertices || [])
      .map(v => `(${formatCoord(v.x_m)};${formatCoord(v.y_m)})`)
      .join(', ');
    if (siteGeometry.role === 'PARCEL_BOUNDARY') {
      return `“Parsel sınırı: ${verticesStr}.” plan girdilerine eklensin mi?`;
    }
    if (siteGeometry.role === 'BUILDABLE_ENVELOPE') {
      return `“Yapılaşma zarfı: ${verticesStr}.” plan girdilerine eklensin mi?`;
    }
    return `“Site geometrisi: ${verticesStr}.” plan girdilerine eklensin mi?`;
  }

  getFloorPlateDescription(floorPlate) {
    if (!floorPlate) return '';
    const formatCoord = (num) => typeof num === 'number'
      ? String(num).replace('.', ',')
      : String(num || '');
    const verticesStr = (floorPlate.vertices || [])
      .map(v => `(${formatCoord(v.x_m)};${formatCoord(v.y_m)})`)
      .join(', ');
    return `“Taban oturumu: ${verticesStr}.” plan girdilerine eklensin mi?`;
  }

  setChatInputLocked(locked) {
    if (typeof document === 'undefined') return;
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
      if (!locked) {
        const span = sendBtn.querySelector('span');
        if (span) {
          span.textContent = 'Gönder';
        } else {
          sendBtn.textContent = 'Gönder';
        }
      }
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
    if (typeof document === 'undefined') return;
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
          if (proposal.floorPlate) {
            label.textContent = this.getFloorPlateDescription(proposal.floorPlate);
          } else if (proposal.siteGeometry) {
            label.textContent = this.getSiteGeometryDescription(proposal.siteGeometry);
          } else if (proposal.metricRequirement) {
            label.textContent = this.getMetricRequirementDescription(proposal.metricRequirement);
          } else if (proposal.briefMutation) {
            label.textContent = this.getBriefMutationDescription(proposal.briefMutation);
          } else if (proposal.spatialRelationship) {
            label.textContent = this.getSpatialRelationshipDescription(proposal.spatialRelationship);
          } else if (proposal.action) {
            label.textContent = proposal.action.description;
          } else {
            label.textContent = proposal.description || 'Öneri';
          }
          proposals.appendChild(label);
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'chip-btn proposal-approve-btn';
          button.dataset.proposalId = proposal.id;
          if (proposal.status === 'approved') {
            button.disabled = true;
            button.classList.add('proposal-approved');
            button.textContent = (proposal.siteGeometry || proposal.metricRequirement || proposal.floorPlate)
              ? 'Plan girdisine eklendi'
              : (proposal.spatialRelationship
                ? 'İlişki onaylandı'
                : (proposal.briefMutation ? 'Brief\'e eklendi' : 'Onaylandı'));
            button.setAttribute('aria-disabled', 'true');
          } else if (proposal.status === 'stale') {
            button.disabled = true;
            button.classList.add('proposal-stale');
            button.textContent = 'Yeniden değerlendirilmeli';
            button.setAttribute('aria-disabled', 'true');
          } else {
            if (proposal.floorPlate) {
              button.textContent = 'Taban oturumunu onayla';
            } else if (proposal.siteGeometry) {
              button.textContent = proposal.siteGeometry.role === 'BUILDABLE_ENVELOPE'
                ? 'Yapılaşma zarfını onayla'
                : 'Parseli onayla';
            } else if (proposal.metricRequirement) {
              button.textContent = 'Ölçüyü onayla';
            } else if (proposal.spatialRelationship) {
              button.textContent = 'Mekânsal ilişkiyi onayla';
            } else if (proposal.briefMutation) {
              button.textContent = 'Brief\'e eklemeyi onayla';
            } else {
              button.textContent = 'Öneriyi onayla';
            }
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

    this.userMessageSequence += 1;
    this.lastUserMessageRef = `chatmsg_${this.userMessageSequence}`;
    this.lastUserMessageText = String(messageText);

    const pendingCommand = await this.handlePendingProposalCommand(messageText);
    if (pendingCommand) return pendingCommand;

    if (this.isRequestPending) return null;

    // Always refresh the active brief from the authoritative server before
    // sending a conversation turn. If the project has never been persisted,
    // loadProjectBrief initializes it from the immutable demo seed.
    if (this.localLLMGateway) {
      const activeProjectId = this.stateMachine.getSnapshot().projectId;
      const briefReady = await this.loadProjectBrief(activeProjectId);
      if (!briefReady) {
        this.appendAssistantMessage(
          "Aktif proje brief'i sunucudan yüklenemedi. Konuşma isteği gönderilmedi."
        );
        return { status: 'brief_unavailable' };
      }
    }

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

  handleStructuredLLMResponse(
    result,
    contextFingerprint,
    generationId = null,
    authoritativePlanInputStateVersion = null,
    proposalBriefVersion = null,
    proposalSourceMessageText = null,
    proposalSourceMessageRef = null
  ) {
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
    const proposedBriefMutations = Array.isArray(result.proposed_brief_mutations)
      ? result.proposed_brief_mutations
      : [];

    const actionProposals = proposedActions.map(action => {
      const actionCopy = JSON.parse(JSON.stringify(action));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        candidate.action &&
        JSON.stringify(candidate.action) === JSON.stringify(actionCopy)
      );
      if (existing) return existing;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: actionCopy,
        briefMutation: null,
        spatialRelationship: null,
        metricRequirement: null,
        siteGeometry: null,
        contextFingerprint,
        generationId: proposalGenerationId,
        userMessageText: this.lastUserMessageText || '',
        userMessageRef: this.lastUserMessageRef || 'chatmsg_1'
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });

    const mutationProposals = proposedBriefMutations.map(mutation => {
      const mutationCopy = JSON.parse(JSON.stringify(mutation));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        candidate.briefMutation &&
        JSON.stringify(candidate.briefMutation) === JSON.stringify(mutationCopy)
      );
      if (existing) return existing;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: null,
        briefMutation: mutationCopy,
        spatialRelationship: null,
        metricRequirement: null,
        siteGeometry: null,
        answersCurrentOpenQuestion: result.answers_current_open_question === true,
        contextFingerprint,
        generationId: proposalGenerationId,
        userMessageText: this.lastUserMessageText || '',
        userMessageRef: this.lastUserMessageRef || 'chatmsg_1'
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });

    const proposedSpatialRels = Array.isArray(result.proposed_spatial_relationships)
      ? result.proposed_spatial_relationships
      : [];

    const spatialProposals = proposedSpatialRels.map(rel => {
      const relCopy = JSON.parse(JSON.stringify(rel));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        candidate.spatialRelationship &&
        JSON.stringify(candidate.spatialRelationship) === JSON.stringify(relCopy)
      );
      if (existing) return existing;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: null,
        briefMutation: null,
        spatialRelationship: relCopy,
        metricRequirement: null,
        siteGeometry: null,
        answersCurrentOpenQuestion: result.answers_current_open_question === true,
        contextFingerprint,
        generationId: proposalGenerationId,
        userMessageText: this.lastUserMessageText || '',
        userMessageRef: this.lastUserMessageRef || 'chatmsg_1'
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });

    const proposedMetricReqs = Array.isArray(result.proposed_metric_requirements)
      ? result.proposed_metric_requirements
      : [];

    const metricProposals = proposedMetricReqs.map(metricReq => {
      const metricCopy = JSON.parse(JSON.stringify(metricReq));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        candidate.metricRequirement &&
        JSON.stringify(candidate.metricRequirement) === JSON.stringify(metricCopy)
      );
      if (existing) return existing;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: null,
        briefMutation: null,
        spatialRelationship: null,
        metricRequirement: metricCopy,
        siteGeometry: null,
        expectedBriefVersion: proposalBriefVersion !== undefined
          ? proposalBriefVersion
          : null,
        expectedPlanInputStateVersion: authoritativePlanInputStateVersion !== undefined
          ? authoritativePlanInputStateVersion
          : null,
        contextFingerprint,
        generationId: proposalGenerationId,
        userMessageText: this.lastUserMessageText || '',
        userMessageRef: this.lastUserMessageRef || 'chatmsg_1'
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });

    const proposedSiteGeoms = Array.isArray(result.proposed_site_geometries)
      ? result.proposed_site_geometries
      : [];

    const siteProposals = proposedSiteGeoms.map(siteGeom => {
      const siteCopy = JSON.parse(JSON.stringify(siteGeom));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        candidate.siteGeometry &&
        JSON.stringify(candidate.siteGeometry) === JSON.stringify(siteCopy)
      );
      if (existing) return existing;

      const frozenUserMessageText = typeof proposalSourceMessageText === 'string'
        ? proposalSourceMessageText
        : '';
      const frozenUserMessageRef = typeof proposalSourceMessageRef === 'string'
        ? proposalSourceMessageRef
        : null;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: null,
        briefMutation: null,
        spatialRelationship: null,
        metricRequirement: null,
        siteGeometry: siteCopy,
        floorPlate: null,
        expectedBriefVersion: proposalBriefVersion !== undefined
          ? proposalBriefVersion
          : null,
        expectedPlanInputStateVersion: authoritativePlanInputStateVersion !== undefined
          ? authoritativePlanInputStateVersion
          : null,
        contextFingerprint,
        generationId: proposalGenerationId,
        userMessageText: frozenUserMessageText,
        userMessageRef: frozenUserMessageRef
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });

    const proposedFloorPlates = Array.isArray(result.proposed_floor_plates)
      ? result.proposed_floor_plates
      : [];

    const floorPlateProposals = proposedFloorPlates.map(fp => {
      const fpCopy = JSON.parse(JSON.stringify(fp));
      const existing = Array.from(this.pendingProposals.values()).find(candidate =>
        candidate.contextFingerprint === contextFingerprint &&
        candidate.generationId === proposalGenerationId &&
        candidate.floorPlate &&
        JSON.stringify(candidate.floorPlate) === JSON.stringify(fpCopy)
      );
      if (existing) return existing;

      const frozenUserMessageText = typeof proposalSourceMessageText === 'string'
        ? proposalSourceMessageText
        : '';
      const frozenUserMessageRef = typeof proposalSourceMessageRef === 'string'
        ? proposalSourceMessageRef
        : null;

      this.proposalSequence += 1;
      const id = `proposal_${this.proposalSequence}`;
      const proposal = {
        id,
        action: null,
        briefMutation: null,
        spatialRelationship: null,
        metricRequirement: null,
        siteGeometry: null,
        floorPlate: fpCopy,
        expectedBriefVersion: proposalBriefVersion !== undefined
          ? proposalBriefVersion
          : null,
        expectedPlanInputStateVersion: authoritativePlanInputStateVersion !== undefined
          ? authoritativePlanInputStateVersion
          : null,
        contextFingerprint,
        generationId: proposalGenerationId,
        userMessageText: frozenUserMessageText,
        userMessageRef: frozenUserMessageRef
      };
      this.pendingProposals.set(id, proposal);
      return proposal;
    });

    const proposals = [
      ...actionProposals,
      ...mutationProposals,
      ...spatialProposals,
      ...metricProposals,
      ...siteProposals,
      ...floorPlateProposals
    ];
    this.appendAssistantMessage(assistantMessage, [], proposals);
  }

  async approveProposalById(proposalId) {
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

    if (proposal.floorPlate) {
      if (!this.localLLMGateway) {
        this.appendAssistantMessage('Yerel LLM ağ geçidi tanımlı değil; taban oturumu onaylanamadı.');
        return null;
      }
      if (proposal.expectedBriefVersion === null || proposal.expectedBriefVersion === undefined) {
        this.appendAssistantMessage('Öneri için geçerli brief versiyonu bulunamadı; onaylanamadı.');
        return null;
      }
      if (!proposal.userMessageText || typeof proposal.userMessageText !== 'string' || !proposal.userMessageText.trim()) {
        this.appendAssistantMessage('Kullanıcı kaynak mesajı bulunamadığı için taban oturumu onaylanamadı.');
        return null;
      }
      if (!proposal.userMessageRef || typeof proposal.userMessageRef !== 'string' || !proposal.userMessageRef.trim()) {
        this.appendAssistantMessage('Kullanıcı kaynak referansı bulunamadığı için taban oturumu onaylanamadı.');
        return null;
      }
      const payload = {
        proposed_floor_plate: proposal.floorPlate,
        current_project_id: current.projectId,
        expected_brief_version: proposal.expectedBriefVersion,
        expected_plan_input_state_version: proposal.expectedPlanInputStateVersion,
        proposal_fingerprint: proposal.contextFingerprint,
        current_fingerprint: current.contextFingerprint,
        proposal_generation_id: proposal.generationId,
        current_generation_id: current.generationId,
        user_message: proposal.userMessageText,
        source_reference: proposal.userMessageRef
      };
      const response = await this.localLLMGateway.approveFloorPlate(current.projectId, payload);
      if (response && response.success && response.resulting_plan_input_state) {
        const record = response.approval_record || {
          proposal_status: 'user_approved',
          approved_at: new Date().toISOString(),
          context_fingerprint: current.contextFingerprint,
          generation_id: current.generationId,
          proposed_floor_plate: proposal.floorPlate,
          resulting_plan_input_state_version: response.resulting_plan_input_state.state_version
        };
        if (!Array.isArray(this.floorPlateProposalRecords)) {
          this.floorPlateProposalRecords = [];
        }
        this.floorPlateProposalRecords.push(record);
        this.lastPlanInputStateVersion = response.resulting_plan_input_state.state_version;
        this.pendingProposals.delete(proposalId);
        this.allChatMessages.forEach(message => {
          if (!Array.isArray(message.proposedActions)) return;
          message.proposedActions.forEach(candidate => {
            if (candidate.id === proposalId) candidate.status = 'approved';
          });
        });

        // Invalidate other pending plan-input proposals (metric, site, floor-plate) only if state version actually changed
        const resultingVersion = response.resulting_plan_input_state.state_version;
        const expectedVersion = proposal.expectedPlanInputStateVersion;

        let stalePlanInputProposals = [];
        if (resultingVersion !== expectedVersion) {
          stalePlanInputProposals = Array.from(this.pendingProposals.values()).filter(p =>
            (p.metricRequirement || p.siteGeometry || p.floorPlate) &&
            p.expectedPlanInputStateVersion === proposal.expectedPlanInputStateVersion
          );
          const staleIds = new Set(stalePlanInputProposals.map(p => p.id));
          stalePlanInputProposals.forEach(staleP => {
            this.pendingProposals.delete(staleP.id);
          });
          this.allChatMessages.forEach(message => {
            if (!Array.isArray(message.proposedActions)) return;
            message.proposedActions.forEach(candidate => {
              if (staleIds.has(candidate.id)) {
                candidate.status = 'stale';
              }
            });
          });
        }

        this.appendAssistantMessage('Bina taban oturumu plan girdilerine kaydedildi.');

        if (stalePlanInputProposals.length > 0) {
          this.appendAssistantMessage(
            'Plan girdileri değiştiği için diğer plan girdisi önerileri yeniden değerlendirilmelidir.'
          );
        }

        return record;
      } else {
        const httpStatus = (response && typeof response.httpStatus === 'number')
          ? response.httpStatus
          : null;

        if (httpStatus === 409) {
          this.appendAssistantMessage(
            'Bu taban oturumu önerisi artık güncel proje durumuna ait değil. Yeniden değerlendirilmesi gerekiyor.'
          );
        } else if (httpStatus === 422) {
          this.appendAssistantMessage(
            'Bina taban oturumu geçersiz olduğu için onaylanamadı.'
          );
        } else if (httpStatus === 404) {
          this.appendAssistantMessage(
            'Proje veya brief verisi bulunamadığı için taban oturumu onaylanamadı.'
          );
        } else if (httpStatus !== null && httpStatus >= 500) {
          this.appendAssistantMessage(
            'Bina taban oturumu şu anda kaydedilemedi. Sunucu tarafında bir hata oluştu.'
          );
        } else if (httpStatus === 0) {
          if (response && response.failureKind === 'timeout') {
            this.appendAssistantMessage(
              'Taban oturumu onay isteği zaman aşımına uğradı. Lütfen tekrar deneyin.'
            );
          } else {
            this.appendAssistantMessage(
              'Yerel sunucuya ulaşılamadı. Lütfen bağlantınızı kontrol edin.'
            );
          }
        } else {
          this.appendAssistantMessage(
            'Bina taban oturumu onaylanamadı.'
          );
        }
        return null;
      }
    }

    if (proposal.siteGeometry) {
      if (!this.localLLMGateway) {
        this.appendAssistantMessage('Yerel LLM ağ geçidi tanımlı değil; site geometrisi onaylanamadı.');
        return null;
      }
      if (proposal.expectedBriefVersion === null || proposal.expectedBriefVersion === undefined) {
        this.appendAssistantMessage('Öneri için geçerli brief versiyonu bulunamadı; onaylanamadı.');
        return null;
      }
      if (!proposal.userMessageText || typeof proposal.userMessageText !== 'string' || !proposal.userMessageText.trim()) {
        this.appendAssistantMessage('Kullanıcı kaynak mesajı bulunamadığı için site geometrisi onaylanamadı.');
        return null;
      }
      if (!proposal.userMessageRef || typeof proposal.userMessageRef !== 'string' || !proposal.userMessageRef.trim()) {
        this.appendAssistantMessage('Kullanıcı kaynak referansı bulunamadığı için site geometrisi onaylanamadı.');
        return null;
      }
      const payload = {
        proposed_geometry: proposal.siteGeometry,
        current_project_id: current.projectId,
        expected_brief_version: proposal.expectedBriefVersion,
        expected_plan_input_state_version: proposal.expectedPlanInputStateVersion,
        proposal_fingerprint: proposal.contextFingerprint,
        current_fingerprint: current.contextFingerprint,
        proposal_generation_id: proposal.generationId,
        current_generation_id: current.generationId,
        user_message: proposal.userMessageText,
        source_reference: proposal.userMessageRef
      };
      const response = await this.localLLMGateway.approveSiteGeometry(current.projectId, payload);
      if (response && response.success && response.resulting_plan_input_state) {
        const record = response.approval_record || {
          proposal_status: 'user_approved',
          approved_at: new Date().toISOString(),
          context_fingerprint: current.contextFingerprint,
          generation_id: current.generationId,
          proposed_site_geometry: proposal.siteGeometry,
          resulting_plan_input_state_version: response.resulting_plan_input_state.state_version
        };
        if (!Array.isArray(this.siteGeometryProposalRecords)) {
          this.siteGeometryProposalRecords = [];
        }
        this.siteGeometryProposalRecords.push(record);
        this.lastPlanInputStateVersion = response.resulting_plan_input_state.state_version;
        this.pendingProposals.delete(proposalId);
        this.allChatMessages.forEach(message => {
          if (!Array.isArray(message.proposedActions)) return;
          message.proposedActions.forEach(candidate => {
            if (candidate.id === proposalId) candidate.status = 'approved';
          });
        });

        // Invalidate other pending plan-input proposals (metric or site or floorPlate) only if state version actually changed
        const resultingVersion = response.resulting_plan_input_state.state_version;
        const expectedVersion = proposal.expectedPlanInputStateVersion;

        let stalePlanInputProposals = [];
        if (resultingVersion !== expectedVersion) {
          stalePlanInputProposals = Array.from(this.pendingProposals.values()).filter(p =>
            (p.metricRequirement || p.siteGeometry || p.floorPlate) &&
            p.expectedPlanInputStateVersion === proposal.expectedPlanInputStateVersion
          );
          const staleIds = new Set(stalePlanInputProposals.map(p => p.id));
          stalePlanInputProposals.forEach(staleP => {
            this.pendingProposals.delete(staleP.id);
          });
          this.allChatMessages.forEach(message => {
            if (!Array.isArray(message.proposedActions)) return;
            message.proposedActions.forEach(candidate => {
              if (staleIds.has(candidate.id)) {
                candidate.status = 'stale';
              }
            });
          });
        }

        const confirmationText = proposal.siteGeometry.role === 'BUILDABLE_ENVELOPE'
          ? 'Yapılaşma zarfı plan girdilerine kaydedildi.'
          : (proposal.siteGeometry.role === 'PARCEL_BOUNDARY'
            ? 'Parsel sınırı plan girdilerine kaydedildi.'
            : 'Site geometrisi plan girdilerine kaydedildi.');
        this.appendAssistantMessage(confirmationText);

        if (stalePlanInputProposals.length > 0) {
          this.appendAssistantMessage(
            'Plan girdileri değiştiği için diğer plan girdisi önerileri yeniden değerlendirilmelidir.'
          );
        }

        return record;
      } else {
        const httpStatus = (response && typeof response.httpStatus === 'number')
          ? response.httpStatus
          : null;

        if (httpStatus === 409) {
          this.appendAssistantMessage(
            'Bu geometri önerisi artık güncel proje durumuna ait değil. Yeniden değerlendirilmesi gerekiyor.'
          );
        } else if (httpStatus === 422) {
          this.appendAssistantMessage(
            'Site geometrisi geçersiz olduğu için onaylanamadı.'
          );
        } else if (httpStatus === 404) {
          this.appendAssistantMessage(
            'Proje veya brief verisi bulunamadığı için site geometrisi onaylanamadı.'
          );
        } else if (httpStatus !== null && httpStatus >= 500) {
          this.appendAssistantMessage(
            'Site geometrisi şu anda kaydedilemedi. Sunucu tarafında bir hata oluştu.'
          );
        } else if (httpStatus === 0) {
          if (response && response.failureKind === 'timeout') {
            this.appendAssistantMessage(
              'Site geometri onay isteği zaman aşımına uğradı. Lütfen tekrar deneyin.'
            );
          } else {
            this.appendAssistantMessage(
              'Yerel sunucuya ulaşılamadı. Lütfen bağlantınızı kontrol edin.'
            );
          }
        } else {
          this.appendAssistantMessage(
            'Site geometrisi onaylanamadı.'
          );
        }
        return null;
      }
    }

    if (proposal.metricRequirement) {
      if (!this.localLLMGateway) {
        this.appendAssistantMessage('Yerel LLM ağ geçidi tanımlı değil; ölçü gereksinimi onaylanamadı.');
        return null;
      }
      const activeBrief = this.getActiveBriefSnapshot();
      if (!activeBrief) {
        this.appendAssistantMessage('Aktif brief snapshot bulunamadı.');
        return null;
      }
      if (proposal.expectedBriefVersion === null || proposal.expectedBriefVersion === undefined) {
        this.appendAssistantMessage('Öneri için geçerli brief versiyonu bulunamadı; onaylanamadı.');
        return null;
      }
      const payload = {
        proposed_requirement: proposal.metricRequirement,
        current_project_id: current.projectId,
        expected_brief_version: proposal.expectedBriefVersion,
        expected_plan_input_state_version: proposal.expectedPlanInputStateVersion,
        proposal_fingerprint: proposal.contextFingerprint,
        current_fingerprint: current.contextFingerprint,
        proposal_generation_id: proposal.generationId,
        current_generation_id: current.generationId,
        user_message: proposal.userMessageText || '',
        source_reference: proposal.userMessageRef || 'chatmsg_1'
      };
      const response = await this.localLLMGateway.approveMetricRequirement(current.projectId, payload);
      if (response && response.success && response.resulting_plan_input_state) {
        const record = response.approval_record || {
          proposal_status: 'user_approved',
          approved_at: new Date().toISOString(),
          context_fingerprint: current.contextFingerprint,
          generation_id: current.generationId,
          proposed_metric_requirement: proposal.metricRequirement,
          resulting_plan_input_state_version: response.resulting_plan_input_state.state_version
        };
        if (!Array.isArray(this.metricRequirementProposalRecords)) {
          this.metricRequirementProposalRecords = [];
        }
        this.metricRequirementProposalRecords.push(record);
        this.lastPlanInputStateVersion = response.resulting_plan_input_state.state_version;
        this.pendingProposals.delete(proposalId);
        this.allChatMessages.forEach(message => {
          if (!Array.isArray(message.proposedActions)) return;
          message.proposedActions.forEach(candidate => {
            if (candidate.id === proposalId) candidate.status = 'approved';
          });
        });

        // Invalidate other metric/site proposals created against the same old expectedPlanInputStateVersion only if state version changed
        const resultingVersion = response.resulting_plan_input_state.state_version;
        const expectedVersion = proposal.expectedPlanInputStateVersion;

        let stalePlanInputProposals = [];
        if (resultingVersion !== expectedVersion) {
          stalePlanInputProposals = Array.from(this.pendingProposals.values()).filter(p =>
            (p.metricRequirement || p.siteGeometry || p.floorPlate) &&
            p.expectedPlanInputStateVersion === proposal.expectedPlanInputStateVersion
          );
          const staleIds = new Set(stalePlanInputProposals.map(p => p.id));
          stalePlanInputProposals.forEach(staleP => {
            this.pendingProposals.delete(staleP.id);
          });
          this.allChatMessages.forEach(message => {
            if (!Array.isArray(message.proposedActions)) return;
            message.proposedActions.forEach(candidate => {
              if (staleIds.has(candidate.id)) {
                candidate.status = 'stale';
              }
            });
          });
        }

        const spaceName = this.getSpaceDisplayName(proposal.metricRequirement.space_id);
        const req = proposal.metricRequirement;
        const valStr = typeof req.value === 'number'
          ? String(req.value).replace('.', ',')
          : String(req.value || '');
        let confirmationText = '';
        if (req.requirement_type === 'MIN_AREA') {
          confirmationText = `${spaceName} için minimum ${valStr} m² gereksinimi plan girdilerine kaydedildi.`;
        } else if (req.requirement_type === 'MAX_AREA') {
          confirmationText = `${spaceName} için maksimum ${valStr} m² gereksinimi plan girdilerine kaydedildi.`;
        } else if (req.requirement_type === 'MIN_CLEAR_WIDTH') {
          confirmationText = `${spaceName} için minimum ${valStr} m net genişlik gereksinimi plan girdilerine kaydedildi.`;
        } else {
          confirmationText = `${spaceName} için ölçü gereksinimi plan girdilerine kaydedildi.`;
        }
        this.appendAssistantMessage(confirmationText);

        if (stalePlanInputProposals.length > 0) {
          const hasSite = stalePlanInputProposals.some(p => p.siteGeometry);
          this.appendAssistantMessage(
            hasSite
              ? 'Plan girdileri değiştiği için diğer plan girdisi önerileri yeniden değerlendirilmelidir.'
              : 'Plan girdileri değiştiği için diğer ölçü önerileri yeniden değerlendirilmelidir.'
          );
        }

        return record;
      } else {
        const httpStatus = (response && typeof response.httpStatus === 'number')
          ? response.httpStatus
          : null;

        if (httpStatus === 409) {
          this.appendAssistantMessage(
            'Bu ölçü önerisi artık güncel proje durumuna ait değil. Yeniden değerlendirilmesi gerekiyor.'
          );
        } else if (httpStatus === 422) {
          this.appendAssistantMessage(
            'Ölçü gereksinimi geçersiz olduğu için onaylanamadı.'
          );
        } else if (httpStatus === 404) {
          this.appendAssistantMessage(
            'Proje veya brief verisi bulunamadığı için ölçü gereksinimi onaylanamadı.'
          );
        } else if (httpStatus !== null && httpStatus >= 500) {
          this.appendAssistantMessage(
            'Ölçü gereksinimi şu anda kaydedilemedi. Sunucu tarafında bir hata oluştu.'
          );
        } else if (httpStatus === 0) {
          if (response && response.failureKind === 'timeout') {
            this.appendAssistantMessage(
              'Ölçü onay isteği zaman aşımına uğradı. Lütfen tekrar deneyin.'
            );
          } else {
            this.appendAssistantMessage(
              'Yerel sunucuya ulaşılamadı. Lütfen bağlantınızı kontrol edin.'
            );
          }
        } else {
          this.appendAssistantMessage(
            'Ölçü gereksinimi onaylanamadı.'
          );
        }
        return null;
      }
    }

    if (proposal.spatialRelationship) {
      if (!this.localLLMGateway) {
        this.appendAssistantMessage('Yerel LLM ağ geçidi tanımlı değil; mekânsal ilişki onaylanamadı.');
        return null;
      }
      const activeBrief = this.getActiveBriefSnapshot();
      if (!activeBrief) {
        this.appendAssistantMessage('Aktif brief snapshot bulunamadı.');
        return null;
      }
      const payload = {
        brief_snapshot: activeBrief,
        proposed_relationship: proposal.spatialRelationship,
        current_project_id: current.projectId,
        expected_brief_version: activeBrief.brief_version,
        proposal_fingerprint: proposal.contextFingerprint,
        current_fingerprint: current.contextFingerprint,
        proposal_generation_id: proposal.generationId,
        current_generation_id: current.generationId,
        user_message: proposal.userMessageText || '',
        source_reference: proposal.userMessageRef || 'chatmsg_1',
        answers_current_open_question: proposal.answersCurrentOpenQuestion === true
      };
      const response = await this.localLLMGateway.approveSpatialRelationship(payload);
      const replaced = (response && response.success && response.resulting_snapshot)
        ? this.replaceActiveBriefSnapshot(response.resulting_snapshot)
        : false;
      if (replaced) {
        const record = response.approval_record || {
          proposal_status: 'user_approved',
          approved_at: new Date().toISOString(),
          context_fingerprint: current.contextFingerprint,
          generation_id: current.generationId,
          proposed_spatial_relationship: proposal.spatialRelationship,
          resulting_brief_version: response.resulting_snapshot.brief_version,
          resulting_evidence_id: response.resulting_snapshot.evidence[response.resulting_snapshot.evidence.length - 1]?.id || 'ev_1'
        };
        if (!Array.isArray(this.spatialRelationshipProposalRecords)) {
          this.spatialRelationshipProposalRecords = [];
        }
        this.spatialRelationshipProposalRecords.push(record);
        this.pendingProposals.delete(proposalId);
        this.allChatMessages.forEach(message => {
          if (!Array.isArray(message.proposedActions)) return;
          message.proposedActions.forEach(candidate => {
            if (candidate.id === proposalId) candidate.status = 'approved';
          });
        });
        this.appendAssistantMessage('Bu mekânsal ilişki onaylandı.');
        return record;
      } else {
        const errorMsg = (response && response.error) ? response.error : 'Bilinmeyen hata';
        this.appendAssistantMessage(`Mekânsal ilişki onaylanamadı: ${errorMsg}`);
        return null;
      }
    }

    if (proposal.briefMutation) {
      if (!this.localLLMGateway) {
        this.appendAssistantMessage('Yerel LLM ağ geçidi tanımlı değil; brief güncellemesi onaylanamadı.');
        return null;
      }
      const activeBrief = this.getActiveBriefSnapshot();
      if (!activeBrief) {
        this.appendAssistantMessage('Aktif brief snapshot bulunamadı.');
        return null;
      }
      const payload = {
        brief_snapshot: activeBrief,
        proposed_mutation: proposal.briefMutation,
        current_project_id: current.projectId,
        expected_brief_version: activeBrief.brief_version,
        proposal_fingerprint: proposal.contextFingerprint,
        current_fingerprint: current.contextFingerprint,
        proposal_generation_id: proposal.generationId,
        current_generation_id: current.generationId,
        user_message: proposal.userMessageText || '',
        source_reference: proposal.userMessageRef || 'chatmsg_1',
        answers_current_open_question: proposal.answersCurrentOpenQuestion === true
      };
      const response = await this.localLLMGateway.approveBriefMutation(payload);
      const replaced = (response && response.success && response.resulting_snapshot)
        ? this.replaceActiveBriefSnapshot(response.resulting_snapshot)
        : false;
      if (replaced) {
        const record = response.approval_record || {
          proposal_status: 'user_approved',
          approved_at: new Date().toISOString(),
          context_fingerprint: current.contextFingerprint,
          generation_id: current.generationId,
          mutation_id: proposal.briefMutation.mutation_id,
          proposed_brief_mutation: proposal.briefMutation,
          resulting_brief_version: response.resulting_snapshot.brief_version
        };
        this.briefMutationProposalRecords.push(record);
        this.pendingProposals.delete(proposalId);
        this.allChatMessages.forEach(message => {
          if (!Array.isArray(message.proposedActions)) return;
          message.proposedActions.forEach(candidate => {
            if (candidate.id === proposalId) candidate.status = 'approved';
          });
        });
        this.appendAssistantMessage('Bu gereksinim onaylı brief\'e eklendi.');
        return record;
      } else {
        const errorMsg = (response && response.error) ? response.error : 'Bilinmeyen hata';
        this.appendAssistantMessage(`Brief güncellemesi onaylanamadı: ${errorMsg}`);
        return null;
      }
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
    if (proposal.siteGeometry) {
      this.appendAssistantMessage('Site geometri önerisi iptal edildi. Plan girdileri değiştirilmedi.');
    } else if (proposal.metricRequirement) {
      this.appendAssistantMessage('Ölçü önerisi iptal edildi. Plan girdileri değiştirilmedi.');
    } else if (proposal.spatialRelationship) {
      this.appendAssistantMessage('Mekânsal ilişki önerisi iptal edildi.');
    } else if (proposal.briefMutation) {
      this.appendAssistantMessage('Brief önerisi iptal edildi; mevcut brief değiştirilmedi.');
    } else if (proposal.floorPlate) {
      this.appendAssistantMessage('Taban oturumu önerisi iptal edildi. Plan girdileri değiştirilmedi.');
    } else {
      this.appendAssistantMessage('Bekleyen öneri iptal edildi. Plan değiştirilmedi.');
    }
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
      action: proposal.action ? JSON.parse(JSON.stringify(proposal.action)) : null,
      brief_mutation: proposal.briefMutation ? JSON.parse(JSON.stringify(proposal.briefMutation)) : null,
      spatial_relationship: proposal.spatialRelationship ? JSON.parse(JSON.stringify(proposal.spatialRelationship)) : null,
      metric_requirement: proposal.metricRequirement ? JSON.parse(JSON.stringify(proposal.metricRequirement)) : null,
      site_geometry: proposal.siteGeometry ? JSON.parse(JSON.stringify(proposal.siteGeometry)) : null,
      floor_plate: proposal.floorPlate ? JSON.parse(JSON.stringify(proposal.floorPlate)) : null
    }));
  }

  getConversationSummary() {
    const transcript = this.allChatMessages
      .slice(-6)
      .map(message => message.role + ': ' + message.text);
    const pending = this.getPendingProposalContext().map(proposal => {
      if (proposal.action) {
        return `${proposal.status}: ${proposal.action.description}`;
      }
      if (proposal.brief_mutation) {
        return `${proposal.status}: ${this.getBriefMutationDescription(proposal.brief_mutation)}`;
      }
      if (proposal.spatial_relationship) {
        return `${proposal.status}: ${this.getSpatialRelationshipDescription(proposal.spatial_relationship)}`;
      }
      if (proposal.metric_requirement) {
        return `${proposal.status}: ${this.getMetricRequirementDescription(proposal.metric_requirement)}`;
      }
      if (proposal.site_geometry) {
        return `${proposal.status}: ${this.getSiteGeometryDescription(proposal.site_geometry)}`;
      }
      if (proposal.floor_plate) {
        return `${proposal.status}: ${this.getFloorPlateDescription(proposal.floor_plate)}`;
      }
      return proposal.status;
    });
    return [...transcript, ...pending].join('\n');
  }

  getCurrentDecisions() {
    return this.proposalRecords.map(record => {
      if (record.proposed_action) {
        return record.proposal_status + ': ' + record.proposed_action.description;
      }
      if (record.proposed_brief_mutation) {
        return record.proposal_status + ': Brief mutation v' + record.resulting_brief_version;
      }
      if (record.proposed_metric_requirement) {
        return record.proposal_status + ': Metric requirement v' + record.resulting_plan_input_state_version;
      }
      if (record.proposed_site_geometry) {
        return record.proposal_status + ': Site geometry v' + record.resulting_plan_input_state_version;
      }
      if (record.proposed_floor_plate) {
        return record.proposal_status + ': Floor plate v' + record.resulting_plan_input_state_version;
      }
      return record.proposal_status;
    });
  }

  async handlePendingProposalCommand(messageText) {
    const pending = this.getActivePendingProposals();
    if (pending.length === 0) return null;
    const normalized = String(messageText || '').trim().toLocaleLowerCase('tr-TR');

    if (['onayla', 'onaylıyorum', 'kabul et', 'kabul ediyorum'].some(command =>
      normalized.includes(command)
    )) {
      if (pending.length > 1) {
        this.appendAssistantMessage(
          'Birden fazla brief önerisi bekliyor. İstediğiniz öneriyi düğmesinden onaylayabilirsiniz.'
        );
        return { status: 'multiple_pending_requires_explicit_choice' };
      }
      const record = await this.approveProposalById(pending[0].id);
      return { status: record ? 'approved' : 'stale', record };
    }

    if (['vazgeç', 'iptal et', 'reddet'].some(command =>
      normalized.includes(command)
    )) {
      if (pending.length > 1) {
        this.appendAssistantMessage(
          'Birden fazla brief önerisi bekliyor. İstediğiniz öneriyi düğmesinden reddedebilirsiniz.'
        );
        return { status: 'multiple_pending_requires_explicit_choice' };
      }
      const dismissed = this.dismissProposalById(pending[0].id);
      return { status: dismissed ? 'dismissed' : 'stale' };
    }

    return null;
  }

  handleLocalLLMFallback(messageText, status = 'error') {
    // Pending proposal commands are already awaited before an LLM request.
    // Calling the async command handler here returns a truthy Promise and
    // would suppress the visible fallback/error message.
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
        .map(proposal => {
          if (proposal.action && proposal.action.description) return proposal.action.description;
          if (proposal.brief_mutation) return this.getBriefMutationDescription(proposal.brief_mutation);
          if (proposal.spatial_relationship) return this.getSpatialRelationshipDescription(proposal.spatial_relationship);
          if (proposal.metric_requirement) return this.getMetricRequirementDescription(proposal.metric_requirement);
          if (proposal.site_geometry) return this.getSiteGeometryDescription(proposal.site_geometry);
          if (proposal.floor_plate) return this.getFloorPlateDescription(proposal.floor_plate);
          return 'Öneri';
        })
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
    if (status === 'disabled') {
      this.handleDemoUserMessage(messageText);
    }
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

  validateAndSanitizePlanSvg(planDoc) {
    if (!planDoc || typeof planDoc !== 'object') {
      return { isValid: false, error: 'Geçersiz SVG plan belgesi.' };
    }
    if (planDoc.schema_version !== 'svg_plan_document.v0') {
      return { isValid: false, error: 'Desteklenmeyen SVG plan belge sürümü.' };
    }
    if (typeof planDoc.svg !== 'string' || !planDoc.svg.trim()) {
      return { isValid: false, error: 'Boş SVG içeriği.' };
    }

    const trimmedSvg = planDoc.svg.trim();
    if (!trimmedSvg.includes('<svg')) {
      return { isValid: false, error: 'SVG kök etiketi bulunamadı.' };
    }

    const ParserClass = (typeof DOMParser !== 'undefined' ? DOMParser : (typeof window !== 'undefined' ? window.DOMParser : null));
    if (!ParserClass) {
      return { isValid: false, error: 'DOMParser ortamda bulunamadı.' };
    }

    const parser = new ParserClass();
    const xmlDoc = parser.parseFromString(trimmedSvg, 'image/svg+xml');

    const parserErrors = xmlDoc.getElementsByTagName('parsererror');
    if (parserErrors && parserErrors.length > 0) {
      return { isValid: false, error: 'SVG ayrıştırma hatası.' };
    }
    if (typeof xmlDoc.querySelector === 'function' && xmlDoc.querySelector('parsererror')) {
      return { isValid: false, error: 'SVG ayrıştırma hatası.' };
    }

    const root = xmlDoc.documentElement;
    if (!root || (root.localName !== 'svg' && (root.tagName || '').toLowerCase() !== 'svg')) {
      return { isValid: false, error: 'Geçersiz SVG kök etiketi.' };
    }

    const allElements = xmlDoc.getElementsByTagName('*');
    for (let i = 0; i < allElements.length; i++) {
      const el = allElements[i];
      const tag = (el.localName || el.tagName || '').toLowerCase();
      if (tag === 'script') {
        return { isValid: false, error: 'SVG içinde script etiketi reddedildi.' };
      }
      if (tag === 'foreignobject') {
        return { isValid: false, error: 'SVG içinde foreignObject etiketi reddedildi.' };
      }
      if (el.attributes) {
        if (typeof el.attributes.length === 'number') {
          for (let j = 0; j < el.attributes.length; j++) {
            const attr = el.attributes[j];
            const attrName = (attr.name || attr.nodeName || '').toLowerCase();
            const attrVal = String(attr.value !== undefined ? attr.value : (attr.nodeValue || ''));
            if (attrName.startsWith('on')) {
              return { isValid: false, error: 'SVG içinde olay yakalayıcı (on*) öznitelik reddedildi.' };
            }
            if (/^\s*javascript\s*:/i.test(attrVal)) {
              return { isValid: false, error: 'SVG içinde javascript: bağlantısı reddedildi.' };
            }
          }
        } else {
          for (const attrKey of Object.keys(el.attributes)) {
            const attrName = attrKey.toLowerCase();
            const attrVal = String(el.attributes[attrKey] || '');
            if (attrName.startsWith('on')) {
              return { isValid: false, error: 'SVG içinde olay yakalayıcı (on*) öznitelik reddedildi.' };
            }
            if (/^\s*javascript\s*:/i.test(attrVal)) {
              return { isValid: false, error: 'SVG içinde javascript: bağlantısı reddedildi.' };
            }
          }
        }
      }
    }

    let importedNode = root;
    if (typeof document !== 'undefined' && typeof document.importNode === 'function') {
      try {
        importedNode = document.importNode(root, true);
      } catch (_e) {
        importedNode = root.cloneNode ? root.cloneNode(true) : root;
      }
    }

    return { isValid: true, node: importedNode, rawSvg: trimmedSvg };
  }

  async requestProjectPlanPreview() {
    const snapshot = this.stateMachine ? this.stateMachine.getSnapshot() : null;
    const projectId = snapshot ? snapshot.projectId : null;

    if (!projectId || typeof projectId !== 'string' || !projectId.trim()) {
      const errRes = { ok: false, status: 0, error: 'Aktif proje seçili değil.' };
      this.renderPlanPreviewResult(errRes);
      return errRes;
    }

    if (!this.localLLMGateway) {
      const errRes = { ok: false, status: 0, error: 'Plan servisi ağ geçidi tanımlı değil.' };
      this.renderPlanPreviewResult(errRes);
      return errRes;
    }

    this.renderPlanPreviewLoading();

    try {
      const result = await this.localLLMGateway.previewProjectPlan(projectId);

      // Protect against cross-project stale response
      const currentSnapshot = this.stateMachine ? this.stateMachine.getSnapshot() : null;
      const currentProjectId = currentSnapshot ? currentSnapshot.projectId : null;
      if (currentProjectId !== projectId || (result && result.kind === 'stale')) {
        if (typeof document !== 'undefined') {
          const container = document.getElementById('planPreviewContent');
          if (container) {
            container.replaceChildren();
          }
        }
        return {
          ok: false,
          status: 0,
          kind: 'stale',
          projectId,
          error: 'Proje bağlamı değiştiği için önceki plan sonucu kullanılmadı.'
        };
      }

      this.renderPlanPreviewResult(result);
      if (result && result.ok && result.kind === 'success') {
        this.appendAssistantMessage(
          'Taslak plan oluşturuldu. Bu görünüm sunucuda doğrulanmış proje girdileri üzerinden oluşturulan şematik yerleşimdir.'
        );
      }
      return result;
    } catch (err) {
      const errRes = { ok: false, status: 0, error: err.message || 'Plan servisine ulaşılamadı.' };
      this.renderPlanPreviewResult(errRes);
      return errRes;
    }
  }

  renderPlanPreviewLoading() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById('planPreviewContent');
    if (!container) return;
    container.replaceChildren();

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'plan-preview-loading';
    const spinner = document.createElement('div');
    spinner.className = 'plan-preview-spinner';
    const text = document.createElement('p');
    text.className = 'loading-text';
    text.textContent = 'Mekânsal çözücü çalışıyor, plan geometrisi hesaplanıyor...';

    loadingDiv.appendChild(spinner);
    loadingDiv.appendChild(text);
    container.appendChild(loadingDiv);
  }

  renderPlanPreviewResult(result) {
    if (typeof document === 'undefined') return;
    const container = document.getElementById('planPreviewContent');
    if (!container) return;
    container.replaceChildren();

    if (result && result.ok && result.kind === 'success') {
      const planDoc = result.document;
      const validation = this.validateAndSanitizePlanSvg(planDoc);
      if (!validation.isValid) {
        this.renderPlanPreviewError(validation.error || 'Plan görseli güvenlik kontrolünden geçemedi.');
        return;
      }

      const previewCard = document.createElement('div');
      previewCard.className = 'plan-preview-card-body';

      // Metadata Bar
      const metaBar = document.createElement('div');
      metaBar.className = 'plan-preview-meta-bar';

      const statusChip = document.createElement('span');
      statusChip.className = 'meta-chip chip-status';
      statusChip.textContent = `Çözücü Durumu: ${result.solution ? result.solution.status : 'FEASIBLE'}`;
      metaBar.appendChild(statusChip);

      const roomCount = result.solution && Array.isArray(result.solution.rooms)
        ? result.solution.rooms.length
        : 0;
      const roomsChip = document.createElement('span');
      roomsChip.className = 'meta-chip chip-rooms';
      roomsChip.textContent = `Mekân Sayısı: ${roomCount}`;
      metaBar.appendChild(roomsChip);

      const gridStep = result.solution && result.solution.grid_step_m !== undefined
        ? result.solution.grid_step_m
        : 0.1;
      const gridChip = document.createElement('span');
      gridChip.className = 'meta-chip chip-grid';
      gridChip.textContent = `Grid Adımı: ${gridStep} m`;
      metaBar.appendChild(gridChip);

      previewCard.appendChild(metaBar);

      // SVG Container
      const svgWrapper = document.createElement('div');
      svgWrapper.className = 'plan-preview-svg-wrapper';
      svgWrapper.appendChild(validation.node);
      previewCard.appendChild(svgWrapper);

      // Disclaimer note
      const note = document.createElement('div');
      note.className = 'plan-preview-disclaimer';
      note.textContent = 'ℹ️ Bu çizim deterministik BRIF.AI mekânsal motoru tarafından üretilmiş şematik yerleşimdir. Resmî mimari uygulama projesi değildir.';
      previewCard.appendChild(note);

      container.appendChild(previewCard);
    } else if (result && result.kind === 'not_ready') {
      const blockedBox = document.createElement('div');
      blockedBox.className = 'plan-preview-blocked';

      const title = document.createElement('h4');
      title.className = 'blocked-title';
      title.textContent = 'Taslak plan henüz oluşturulamıyor';
      blockedBox.appendChild(title);

      if (Array.isArray(result.blockers) && result.blockers.length > 0) {
        const list = document.createElement('ul');
        list.className = 'blocked-list';
        result.blockers.forEach(msg => {
          const item = document.createElement('li');
          item.className = 'blocked-item';
          item.textContent = msg;
          list.appendChild(item);
        });
        blockedBox.appendChild(list);
      } else {
        const fallbackText = document.createElement('p');
        fallbackText.className = 'blocked-text';
        fallbackText.textContent = 'Proje henüz plan önizlemesi için hazır değil.';
        blockedBox.appendChild(fallbackText);
      }

      const retryBtn = document.createElement('button');
      retryBtn.type = 'button';
      retryBtn.className = 'retry-btn';
      retryBtn.textContent = 'Tekrar Dene';
      retryBtn.onclick = () => {
        this.requestProjectPlanPreview();
      };
      blockedBox.appendChild(retryBtn);

      container.appendChild(blockedBox);
    } else {
      const msg = (result && typeof result.error === 'string' && result.error.trim())
        ? result.error.trim()
        : 'Plan önizlemesi oluşturulamadı.';
      this.renderPlanPreviewError(msg);
    }
  }

  renderPlanPreviewError(errorMessage) {
    if (typeof document === 'undefined') return;
    const container = document.getElementById('planPreviewContent');
    if (!container) return;
    container.replaceChildren();

    const errBox = document.createElement('div');
    errBox.className = 'plan-preview-error';

    const icon = document.createElement('div');
    icon.className = 'error-icon';
    icon.textContent = '⚠️';
    errBox.appendChild(icon);

    const text = document.createElement('p');
    text.className = 'error-message';
    text.textContent = errorMessage;
    errBox.appendChild(text);

    const retryBtn = document.createElement('button');
    retryBtn.type = 'button';
    retryBtn.className = 'retry-btn';
    retryBtn.textContent = 'Tekrar Dene';
    retryBtn.onclick = () => {
      this.requestProjectPlanPreview();
    };
    errBox.appendChild(retryBtn);

    container.appendChild(errBox);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, match => {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return map[match];
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ConversationOrchestrator;
}
if (typeof window !== 'undefined') {
  window.ConversationOrchestrator = ConversationOrchestrator;
}
