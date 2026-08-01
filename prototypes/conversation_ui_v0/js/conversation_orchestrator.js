/**
 * BRIF.AI — Conversation Orchestrator & State Engine (v5.2 Refined)
 *
 * Single Source of Truth Session State, stage-aware greetings,
 * and user/system/architect separation.
 */

class ConversationOrchestrator {
  constructor(options = {}) {
    this.assistant = options.assistant;
    this.presenter = options.presenter;
    this.historyManager = options.historyManager;
    this.intentParser = new DemoIntentParser();

    this.chatContainerId = 'chatMessages';

    // Unified Session Context State (Requirement 1 & 10)
    this.sessionState = {
      activeStage: 1,
      activeAlternative: 'a',
      activeFloor: 'ground',
      selectedSpaceId: 'study',
      selectedSpaceName: 'Çalışma Odası',
      activeScenario: null, // 'master_bath_relocation', 'floor_overlay', 'orientation'
      conversationStep: 'idle', // 'awaiting_reason', 'evaluating', 'presenting_options', 'applied', 'deferred'
      userRequest: '',
      clarifiedNeeds: [],
      presentedOptions: [],
      selectedOption: null,
      decisionStatus: 'Karar bekleniyor'
    };
  }

  setStage(stageNum) {
    this.sessionState.activeStage = stageNum;
    this.assistant.setContext({ stage: stageNum });

    // Stage-Aware Initial Assistant Greeting (Requirement 3)
    if (stageNum === 3) {
      this.appendAssistantMessage(
        "Mekân programını inceliyoruz. Çalışma odası şu anda 10–12 m² aralığında tanımlı. Alanı, konumu veya zorunluluk durumunu konuşarak değiştirebiliriz."
      );
    } else if (stageNum === 4) {
      this.appendAssistantMessage(
        "Alternatif A’nın üst katını inceliyoruz. Ebeveyn banyosunun konumu ve erişimi hakkında konuşabilirsiniz."
      );
    }
  }

  selectSpace(spaceId, spaceName) {
    this.sessionState.selectedSpaceId = spaceId;
    this.sessionState.selectedSpaceName = spaceName;
    this.assistant.setContext({ spaceId: spaceId, spaceName: spaceName });

    // "Sohbette Değiştir" Action Response (Requirement 14)
    this.appendAssistantMessage(
      `📌 **${escapeHtml(spaceName)}** seçildi. Bu mekânın alanını, katını veya kullanım önceliğini sohbet üzerinden değiştirebiliriz.`
    );
  }

  handleUserMessage(messageText) {
    if (!messageText) return;

    const norm = this.intentParser.normalizeText(messageText);

    // 1. If currently awaiting reason for Master Bath
    if (this.sessionState.activeScenario === 'master_bath_relocation' && this.sessionState.conversationStep === 'awaiting_reason') {
      const reasonType = this.intentParser.parseMasterBathReason(messageText);
      this.processMasterBathReason(messageText, reasonType);
      return;
    }

    // 2. Master Bath Initial Trigger
    if (this.intentParser.isMasterBathInitial(messageText)) {
      this.triggerMasterBathScenario(messageText);
      return;
    }

    // 3. Floor Overlay Trigger
    if (norm.includes('ust uste') || norm.includes('alt kat ust kat') || norm.includes('anlamadim')) {
      this.triggerFloorOverlayScenario();
      return;
    }

    // 4. Orientation / Facade Trigger
    if (norm.includes('kuzey') || norm.includes('guney') || norm.includes('sabah gunesi')) {
      this.triggerOrientationScenario();
      return;
    }

    // 5. Default Contextual Assistant Process
    const result = this.assistant.processUserMessage(messageText);
    this.appendAssistantMessage(result.aiResponseText);
  }

  triggerMasterBathScenario(userRequestText) {
    this.sessionState.activeScenario = 'master_bath_relocation';
    this.sessionState.conversationStep = 'awaiting_reason';
    this.sessionState.selectedSpaceId = 'master_bath';
    this.sessionState.selectedSpaceName = 'Ebeveyn Banyosu';
    this.sessionState.userRequest = userRequestText || 'Ebeveyn banyosunun kuzey tarafına alınması.';
    this.sessionState.decisionStatus = 'Karar bekleniyor';

    // Update Context Badge dynamically (Requirement 1 & 2 Fix)
    this.assistant.setContext({
      activeScenario: 'master_bath_relocation',
      spaceId: 'master_bath',
      spaceName: 'Ebeveyn Banyosu'
    });

    this.appendAssistantMessage(
      "Banyoyu kuzey kenarına almak istiyorsunuz. Buradaki önceliğiniz yataktan görünmemesi mi, giyinme alanından erişilmesi mi, yoksa daha mahrem bir kullanım mı?",
      [
        "Yataktan görünmesini istemiyorum",
        "Giyinme alanından geçilsin",
        "Daha mahrem olsun",
        "Kuzey cephesini servis alanlarına ayırmak istiyorum"
      ]
    );

    this.syncStateWithHistory();
  }

  processMasterBathReason(reasonText, reasonType) {
    this.sessionState.conversationStep = 'evaluating';
    this.sessionState.clarifiedNeeds.push(reasonText);

    // Render Analysis Progress View in Workspace (Requirement 2)
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
      this.sessionState.conversationStep = 'presenting_options';
      this.sessionState.presentedOptions = [
        'Seçenek 1 — Banyoyu Kuzeye Taşımak (Güçlü Mahremiyet)',
        'Seçenek 2 — Konumu Koru, Giriş Yönünü Değiştir (Tesisat Korumalı)'
      ];

      if (this.presenter) {
        this.presenter.setMode('options_side_by_side');
      }

      // Clear Separation of User Intent, System Interpretation & Architectural Recommendation (Requirement 5)
      const formattedResponse = `
        🗣️ <strong>Sözlü Beyan:</strong> "${escapeHtml(reasonText)}"<br>
        🧠 <strong>Sistemin Yorumu:</strong> Ebeveyn süitinde mahremiyet ve görünmezlik önceliği.<br>
        📐 <strong>Mimari Öneri:</strong> Yatak → Giyinme → Banyo sıralı erişim hiyerarşisi.<br><br>
        Bu doğrultuda hazırlanan 2 farklı mimari çözümü çalışma alanında sunuyorum.
      `;

      this.appendAssistantMessage(
        formattedResponse,
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
    this.sessionState.selectedOption = optionNum;
    this.sessionState.conversationStep = 'applied';
    this.sessionState.decisionStatus = `Seçenek ${optionNum} Seçildi (Uygulandı)`;

    const optTitle = optionNum === 1 ? '1. Seçenek (Banyoyu Kuzeye Taşımak)' : '2. Seçenek (Mevcut konumu koruyup girişi değiştirmek)';

    this.appendAssistantMessage(`✅ ${optTitle} onaylandı ve şematik plana uygulandı.`);

    if (this.presenter) {
      this.presenter.setMode('options_side_by_side', { selectedOption: optionNum });
    }

    this.syncStateWithHistory();
  }

  deferMasterBathDecision() {
    this.sessionState.conversationStep = 'deferred';
    this.sessionState.decisionStatus = 'Mimara Bırakıldı';

    this.appendAssistantMessage(`📌 Karar teyidi mimar değerlendirmesine bırakıldı. Mimar Karar Raporuna not eklendi.`);

    this.syncStateWithHistory();
  }

  triggerFloorOverlayScenario() {
    this.sessionState.activeScenario = 'floor_overlay';
    this.assistant.setContext({ activeScenario: 'floor_overlay' });

    if (this.presenter) {
      this.presenter.setMode('overlay');
    }

    this.appendAssistantMessage(
      "Soluk çizgiler zemin katı, koyu çizgiler üst katı gösteriyor. Mavi alanlar iki kattaki ıslak hacimlerdir. Kesikli çizgi, tesisatın düşeyde yakın tutulduğu yaklaşık aksı gösterir.",
      [
        "Sadece üst katı göster",
        "Alt katı saydam göster",
        "Islak hacimleri vurgula",
        "Merdiven boşluğunu göster",
        "Normal plana dön"
      ]
    );
  }

  triggerOrientationScenario() {
    this.sessionState.activeScenario = 'orientation';
    this.assistant.setContext({ activeScenario: 'orientation' });

    if (this.presenter) {
      this.presenter.setMode('orientation');
    }

    this.appendAssistantMessage(
      "Kuzey cephesi doğrudan güneş ihtiyacı daha düşük servis hacimleri için değerlendirilebilir. Ancak gerçek karar arsa yönü, komşu yapılar, açıklıklar ve yerel koşullarla doğrulanmalıdır.",
      ["Kuzey cephesini göster", "Güney salon ilişkisini göster", "Normal plana dön"]
    );
  }

  syncStateWithHistory() {
    if (this.historyManager) {
      this.historyManager.setSessionState(this.sessionState);
    }
  }

  appendUserMessage(text) {
    const chatContainer = document.getElementById(this.chatContainerId);
    if (!chatContainer) return;

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
