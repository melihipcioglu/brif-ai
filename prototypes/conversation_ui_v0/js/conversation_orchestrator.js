/**
 * BRIF.AI — Conversation Orchestrator & State Engine (v5.1 Engine)
 *
 * Manages conversation session state, Turkish text normalization, step-by-step progress,
 * and workspace synchronization.
 */

class ConversationOrchestrator {
  constructor(options = {}) {
    this.assistant = options.assistant;
    this.presenter = options.presenter;
    this.historyManager = options.historyManager;
    this.intentParser = new DemoIntentParser();

    this.chatContainerId = 'chatMessages';

    // Single Source of Truth Session State (Requirement 10)
    this.sessionState = {
      activeScenario: null, // 'master_bath_relocation', 'floor_overlay', 'orientation', 'resize_study'
      stage: 'idle', // 'awaiting_reason', 'evaluating', 'presenting_options', 'applied', 'deferred'
      userRequest: '',
      clarifiedNeeds: [],
      presentedOptions: [],
      selectedOption: null,
      checks: [],
      decisionStatus: 'pending'
    };
  }

  handleUserMessage(messageText) {
    if (!messageText) return;

    // Normalize text
    const norm = this.intentParser.normalizeText(messageText);

    // 1. If we are currently awaiting a reason for Master Bath Relocation (State Engine)
    if (this.sessionState.activeScenario === 'master_bath_relocation' && this.sessionState.stage === 'awaiting_reason') {
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

    // 5. Contextual Assistant Default Process
    const result = this.assistant.processUserMessage(messageText);
    this.appendAssistantMessage(result.aiResponseText);
  }

  triggerMasterBathScenario(userRequestText) {
    this.sessionState.activeScenario = 'master_bath_relocation';
    this.sessionState.stage = 'awaiting_reason';
    this.sessionState.userRequest = userRequestText || 'Ebeveyn banyosunun kuzey tarafına alınması.';
    this.sessionState.decisionStatus = 'pending';

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
    this.sessionState.stage = 'evaluating';
    this.sessionState.clarifiedNeeds.push(reasonText);

    // Show Progress View in Main Workspace (Requirement 2)
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

    // Progress step animation simulation
    setTimeout(() => {
      this.sessionState.stage = 'presenting_options';
      this.sessionState.presentedOptions = [
        'Seçenek 1 — Banyoyu Kuzeye Taşımak (Güçlü Mahremiyet)',
        'Seçenek 2 — Konumu Koru, Giriş Yönünü Değiştir (Tesisat Korumalı)'
      ];

      // Render Options Side-by-Side in Workspace (Requirement 3)
      if (this.presenter) {
        this.presenter.setMode('options_side_by_side');
      }

      this.appendAssistantMessage(
        `Anladım. İstediğiniz yalnız bir konum değişikliği değil; yatak odası → giyinme → banyo hiyerarşisi. Bunu iki farklı mimari seçenek olarak çalışma alanında hazırladım. Seçeneklerden birini onaylayabilir veya inceleyebilirsiniz.`,
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
    this.sessionState.stage = 'applied';
    this.sessionState.decisionStatus = `Seçenek ${optionNum} Seçildi`;

    const optTitle = optionNum === 1 ? '1. Seçenek (Banyoyu Kuzeye Taşımak)' : '2. Seçenek (Mevcut konumu koruyup girişi değiştirmek)';

    this.appendAssistantMessage(`✅ ${optTitle} başarıyla plan kararlarına işlendi.`);

    if (this.presenter) {
      this.presenter.setMode('options_side_by_side', { selectedOption: optionNum });
    }

    this.syncStateWithHistory();
  }

  deferMasterBathDecision() {
    this.sessionState.stage = 'deferred';
    this.sessionState.decisionStatus = 'Karar Mimara Bırakıldı';

    this.appendAssistantMessage(`📌 Karar teyidi mimar değerlendirmesine bırakıldı. Karar Raporuna not eklendi.`);

    this.syncStateWithHistory();
  }

  triggerFloorOverlayScenario() {
    this.sessionState.activeScenario = 'floor_overlay';
    if (this.presenter) {
      this.presenter.setMode('overlay');
    }

    this.appendAssistantMessage(
      "Bunu iki katı aynı koordinat düzleminde üst üste göstererek açıklayayım. Soluk alan zemin kattır. Üstteki canlı mavi alan ebeveyn banyosudur. Düşey tesisat aksı kesikli çizgiyle gösterilmiştir. Sarı alan ise merdiven boşluğudur.",
      [
        "Sadece üst katı göster",
        "Alt katı yarı saydam göster",
        "Islak hacimleri göster",
        "Normal plana dön"
      ]
    );
  }

  triggerOrientationScenario() {
    this.sessionState.activeScenario = 'orientation';
    if (this.presenter) {
      this.presenter.setMode('orientation');
    }

    this.appendAssistantMessage(
      "Cephe yönlenmesini gerçek plan üzerinde gösteriyorum. Kuzey cephesi servis alanları, Güney cephesi salon ve teras için ayarlanmıştır. Bu bir prototip varsayımıdır.",
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
        <div class="message-text">${escapeHtml(text)}</div>
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
