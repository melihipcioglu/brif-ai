/**
 * BRIF.AI — Conversation Orchestrator & State Engine (v6.0 Engine)
 *
 * Dispatches state machine events, attaches context snapshots to every message,
 * and runs ContextValidator on every view or scope switch.
 */

class ConversationOrchestrator {
  constructor(options = {}) {
    this.hierarchy = options.hierarchy || new EntityHierarchy();
    this.stateMachine = options.stateMachine || new ContextStateMachine(this.hierarchy);
    this.validator = new ContextValidator(this.hierarchy, this.stateMachine);

    this.assistant = options.assistant;
    this.presenter = options.presenter;
    this.historyManager = options.historyManager;
    this.intentParser = new DemoIntentParser();

    this.chatContainerId = 'chatMessages';

    // Subscribe to state changes
    this.stateMachine.subscribe((ctx) => {
      this.validateAndSyncUI(ctx);
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
      this.appendAssistantMessage(
        "Mekân programını inceliyoruz. Tanımlı alanları, katlarını ve kullanım önceliklerini konuşarak düzenleyebiliriz."
      );
    } else if (stageNum === 4) {
      this.appendAssistantMessage(
        "Taslak plan aşamasındayız. Seçili kat ve mekân kararları hakkında konuşabilirsiniz."
      );
    }
  }

  selectProject(projId) {
    if (projId === "proj_tower_50floor") {
      this.stateMachine.dispatch({
        type: "PROJECT_SELECTED",
        payload: { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18", entityId: "space_meeting_18a" }
      });
      this.appendAssistantMessage("🏢 50 Katlı Finans Kulesi Projesi yüklendi. Aktif bağlam: A Kulesi / 18. Kat / 18A Yönetim Toplantı Odası.");
    } else if (projId === "proj_campus_multiblock") {
      this.stateMachine.dispatch({
        type: "PROJECT_SELECTED",
        payload: { projectId: "proj_campus_multiblock", buildingId: "block_a_r_d", levelId: "lvl_2_block_a", entityId: "space_robotics_lab" }
      });
      this.appendAssistantMessage("🏛️ Çok Bloklu Teknoloji Kampüsü yüklendi. Aktif bağlam: Blok A (AR-GE Binası) / 2. Kat.");
    } else {
      this.stateMachine.dispatch({
        type: "PROJECT_SELECTED",
        payload: { projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground", entityId: "space_study" }
      });
      this.appendAssistantMessage("🏡 İki Katlı Müstakil Konut Projesi yüklendi.");
    }
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
      // Suspend current scenario without showing it on wrong scope (Requirement 3)
      if (ctx.scenarioId) {
        this.stateMachine.dispatch({
          type: "SCENARIO_SUSPENDED",
          payload: { reason: validation.message }
        });
      }

      // Render Suspended Context Banner in Workspace (Requirement 3)
      if (this.presenter) {
        this.presenter.renderSuspendedContextBanner(validation.message);
      }
    }
  }

  handleUserMessage(messageText) {
    if (!messageText) return;

    const ctx = this.stateMachine.getContext();

    // Check for Master Bath initial trigger
    if (this.intentParser.isMasterBathInitial(messageText)) {
      this.triggerMasterBathScenario(messageText);
      return;
    }

    const result = this.assistant.processUserMessage(messageText);
    this.appendAssistantMessage(result.aiResponseText);
  }

  triggerMasterBathScenario(userRequestText) {
    this.stateMachine.dispatch({
      type: "LEVEL_SELECTED",
      payload: { levelId: "lvl_upper" }
    });

    this.stateMachine.dispatch({
      type: "ENTITY_SELECTED",
      payload: { entityId: "space_master_bath", entityType: "space" }
    });

    this.stateMachine.dispatch({
      type: "SCENARIO_STARTED",
      payload: {
        scenarioId: "master_bath_relocation",
        decisionId: "dec_master_bath",
        targetEntityId: "space_master_bath"
      }
    });

    this.appendAssistantMessage(
      "Banyoyu kuzey kenarına almak istiyorsunuz. Buradaki önceliğiniz yataktan görünmemesi mi, giyinme alanından erişilmesi mi, yoksa daha mahrem bir kullanım mı?",
      [
        "Yataktan görünmesini istemiyorum",
        "Giyinme alanından geçilsin",
        "Daha mahrem olsun"
      ]
    );

    this.syncStateWithHistory();
  }

  processMasterBathReason(reasonText) {
    if (this.presenter) {
      this.presenter.setMode('progress', {
        steps: [
          { text: "Talebin amacı yorumlanıyor", status: "completed" },
          { text: "Yatak–giyinme–banyo ilişkisi kontrol ediliyor", status: "completed" },
          { text: "Alt kat ıslak hacim ilişkisi inceleniyor", status: "checking" },
          { text: "Kapı ve mobilya çakışmaları kontrol ediliyor", status: "pending" },
          { text: "Cephe ve havalandırma varsayımları değerlendiriliyor", status: "pending" },
          { text: "İki seçenek hazırlanıyor", status: "pending" }
        ]
      });
    }

    setTimeout(() => {
      if (this.presenter) {
        this.presenter.setMode('options_side_by_side');
      }

      this.appendAssistantMessage(
        `🗣️ <strong>Sözlü Beyan:</strong> "${escapeHtml(reasonText)}"<br>🧠 <strong>Sistemin Yorumu:</strong> Ebeveyn süitinde mahremiyet önceliği.<br>📐 <strong>Mimari Öneri:</strong> Yatak → Giyinme → Banyo sıralı erişim.<br><br>İki mimari seçeneği sunuyorum.`,
        [
          "1. Seçeneği Uygula",
          "2. Seçeneği Uygula",
          "Henüz karar vermiyorum"
        ]
      );

      this.syncStateWithHistory();
    }, 1200);
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
    this.stateMachine.dispatch({
      type: "SCENARIO_STARTED",
      payload: { scenarioId: "floor_overlay" }
    });

    if (this.presenter) {
      this.presenter.setMode('overlay');
    }

    this.appendAssistantMessage(
      "Kat ilişkisini aynı koordinat üzerinde gösteriyorum. Mavi alanlar ıslak hacimler, sarı alan merdiven boşluğudur.",
      ["Sadece üst katı göster", "Alt katı saydam göster", "Normal plana dön"]
    );
  }

  triggerOrientationScenario() {
    this.stateMachine.dispatch({
      type: "SCENARIO_STARTED",
      payload: { scenarioId: "orientation" }
    });

    if (this.presenter) {
      this.presenter.setMode('orientation');
    }

    this.appendAssistantMessage(
      "Cephe yönlenmesini kat planı üzerinde gösteriyorum.",
      ["Kuzey cephesini göster", "Güney salon ilişkisini göster", "Normal plana dön"]
    );
  }

  syncStateWithHistory() {
    if (this.historyManager) {
      this.historyManager.setSessionState(this.stateMachine.getContext());
    }
  }

  appendUserMessage(text) {
    const chatContainer = document.getElementById(this.chatContainerId);
    if (!chatContainer) return;

    const ctx = this.stateMachine.getContext();

    // Context Snapshot attached to message (Requirement 4)
    const snapshot = {
      messageId: `msg_${Date.now()}`,
      projectId: ctx.projectId,
      buildingId: ctx.buildingId,
      levelId: ctx.levelId,
      zoneId: ctx.zoneId,
      entityId: ctx.entityId,
      entityType: ctx.entityType,
      scenarioId: ctx.scenarioId,
      decisionId: ctx.decisionId,
      timestamp: new Date().toISOString()
    };

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    msgDiv.innerHTML = `
      <div class="message-avatar user">MK</div>
      <div class="message-content">
        <div class="message-sender">Siz</div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  appendAssistantMessage(text, quickReplies = []) {
    const chatContainer = document.getElementById(this.chatContainerId);
    if (!chatContainer) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message';

    let chipsHtml = '';
    if (quickReplies.length > 0) {
      chipsHtml = `
        <div class="suggestion-chips">
          ${quickReplies.map(reply => `<button class="chip-btn followup-chip" data-reply="${escapeHtml(reply)}">${escapeHtml(reply)}</button>`).join('')}
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="message-avatar brif">B</div>
      <div class="message-content">
        <div class="message-sender">BRIF.AI Mimari Asistan</div>
        <div class="message-text">${text}</div>
        ${chipsHtml}
      </div>
    `;

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
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
