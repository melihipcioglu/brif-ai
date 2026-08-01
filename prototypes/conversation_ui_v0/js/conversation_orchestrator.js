/**
 * BRIF.AI — Conversation Orchestrator (v5 Engine)
 *
 * Handles dialogue orchestration, professional architect persona responses,
 * step-by-step analysis progress simulation, and scenario execution.
 */

class ConversationOrchestrator {
  constructor(options = {}) {
    this.assistant = options.assistant;
    this.presenter = options.presenter;
    this.historyManager = options.historyManager;

    this.activeScenario = null;
    this.chatContainerId = 'chatMessages';
  }

  handleUserMessage(messageText) {
    const textLower = messageText.toLowerCase();

    // 1. Master Bath Relocation Scenario (Requirement 7)
    if (textLower.includes('ebeveyn banyosu') || textLower.includes('banyoyu kuzeye') || textLower.includes('banyo kuzey')) {
      this.triggerMasterBathScenario();
      return;
    }

    // 2. Floor Overlay Scenario (Requirement 9)
    if (textLower.includes('üst üste') || textLower.includes('alt kat üst kat') || textLower.includes('anlamadım')) {
      this.triggerFloorOverlayScenario();
      return;
    }

    // 3. Staircase Explanation Scenario
    if (textLower.includes('merdiven') || textLower.includes('sarı alan')) {
      this.triggerStairScenario();
      return;
    }

    // 4. Orientation / Facade Scenario (Requirement 8)
    if (textLower.includes('kuzey') || textLower.includes('güney') || textLower.includes('sabah güneşi')) {
      this.triggerOrientationScenario();
      return;
    }

    // 5. Default Contextual Assistant Process
    const result = this.assistant.processUserMessage(messageText);
    this.appendAssistantMessage(result.aiResponseText);
  }

  triggerMasterBathScenario() {
    this.appendAssistantMessage(
      "Banyoyu kuzey kenarına almak istiyorsunuz. Buradaki önceliğiniz yataktan görünmemesi mi, giyinme alanından erişilmesi mi, yoksa daha mahrem bir kullanım mı?",
      [
        "Yataktan görünmesini istemiyorum",
        "Giyinme alanından geçilsin",
        "Daha mahrem olsun",
        "Kuzey cephesini servis alanlarına ayırmak istiyorum"
      ]
    );
  }

  handleMasterBathFollowup(selectedOptionText) {
    this.appendUserMessage(selectedOptionText);

    // Render Step-by-Step Analysis Progress (Requirement 6)
    this.renderAnalysisProgress(
      "Ebeveyn banyosu için seçenek hazırlanıyor...",
      [
        "Talebinizin amacı yorumlanıyor...",
        "Yatak–giyinme–banyo sıralaması kontrol ediliyor...",
        "Alt kattaki ıslak hacimlerle düşey ilişki inceleniyor...",
        "Kapı ve mobilya çakışmaları denetleniyor...",
        "İki uygulanabilir seçenek hazırlanıyor..."
      ],
      () => {
        // Upon progress completion, display Side-by-Side Option Cards in Main Workspace (Requirement 7)
        if (this.presenter) {
          this.presenter.setMode('options_side_by_side');
        }

        this.appendAssistantMessage(
          "Anladım. İstediğiniz yalnız bir konum değişikliği değil; yatak odası → giyinme → banyo hiyerarşisi. Bunu iki farklı mimari seçenek olarak çalışma alanında hazırladım. Seçeneklerden birini onaylayabilir veya inceleyebilirsiniz.",
          [
            "1. Seçeneği Uygula",
            "2. Seçeneği Uygula",
            "İkisinin Birleşimini Göster",
            "Henüz karar vermiyorum"
          ]
        );
      }
    );
  }

  triggerFloorOverlayScenario() {
    if (this.presenter) {
      this.presenter.setMode('overlay');
    }

    this.appendAssistantMessage(
      "Bunu iki katı üst üste göstererek açıklayayım. Soluk mavi alan zemin kattaki mutfak ve ortak WC çekirdeğidir. Üstteki canlı mavi alan ebeveyn banyosudur. Tesisatı düşey hizada tutmak şematik bir yaklaşımdır. Sarı alan ise merdiven boşluğudur.",
      [
        "Sadece üst katı göster",
        "Alt katı yarı saydam göster",
        "Islak hacimleri göster",
        "Normal plana dön"
      ]
    );
  }

  triggerStairScenario() {
    this.appendAssistantMessage(
      "Sarı renkle vurgulanan alan merdiven boşluğudur. Bu bölüm iki katta da oda olarak kullanılmaz; zemin kat ile üst kat arasındaki düşey sirkülasyon boşluğudur.",
      ["Islak hacimleri göster", "Normal plana dön"]
    );
  }

  triggerOrientationScenario() {
    if (this.presenter) {
      this.presenter.setMode('orientation');
    }

    this.appendAssistantMessage(
      "Bu prototipte kuzey yönü varsayımsal olarak tanımlanmış. Gerçek arsa verisi girildiğinde yönlenme ve sabah güneşi hesabı yeniden kontrol edilmelidir. Cephe işaretlemesini plan üzerinde vurguluyorum.",
      ["Kuzey cephesini göster", "Güney salon ilişkisini göster", "Normal plana dön"]
    );
  }

  renderAnalysisProgress(title, steps, onComplete) {
    const chatContainer = document.getElementById(this.chatContainerId);
    if (!chatContainer) return;

    const progressDiv = document.createElement('div');
    progressDiv.className = 'message ai-message analysis-progress-card';
    progressDiv.innerHTML = `
      <div class="message-avatar brif">B</div>
      <div class="message-content">
        <div class="message-sender">BRIF.AI Mimari Değerlendirme (Demo Süreci)</div>
        <h4 style="font-size:13px; font-weight:700; color:#047857; margin-bottom:8px;">${escapeHtml(title)}</h4>
        <ul class="progress-steps-list">
          ${steps.map((step, i) => `<li id="step_item_${i}" class="step-item pending">⏳ ${escapeHtml(step)}</li>`).join('')}
        </ul>
      </div>
    `;

    chatContainer.appendChild(progressDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Sequentially activate step items
    let currentStepIdx = 0;
    const interval = setInterval(() => {
      const stepEl = document.getElementById(`step_item_${currentStepIdx}`);
      if (stepEl) {
        stepEl.className = 'step-item completed';
        stepEl.innerHTML = `✅ ${escapeHtml(steps[currentStepIdx])}`;
      }
      currentStepIdx++;

      if (currentStepIdx >= steps.length) {
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, 400);
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
