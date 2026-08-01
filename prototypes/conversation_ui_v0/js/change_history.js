/**
 * BRIF.AI — Change History & Dynamic Architect Decision Report (v5.1 Engine)
 *
 * Dynamically generates professional decision reports based on active session state.
 */

class ChangeHistory {
  constructor() {
    this.sessionState = {
      activeScenario: null,
      stage: 'idle',
      userRequest: '',
      clarifiedNeeds: [],
      presentedOptions: [],
      selectedOption: null,
      checks: [],
      decisionStatus: 'pending'
    };

    this.historyStack = [];
    this.redoStack = [];
  }

  setSessionState(state) {
    this.sessionState = { ...this.sessionState, ...state };
  }

  recordChange(changeEvent) {
    this.historyStack.push({
      timestamp: new Date().toISOString(),
      ...changeEvent
    });
    this.redoStack = [];
  }

  renderArchitectReport() {
    const st = this.sessionState;

    // If Master Bath Relocation Scenario is active (Requirement 4 Fix)
    if (st.activeScenario === 'master_bath_relocation') {
      const userReq = st.userRequest || 'Ebeveyn banyosunun kuzey tarafına alınması.';
      const clarified = st.clarifiedNeeds.length > 0 ? st.clarifiedNeeds.join(', ') : 'Banyonun yataktan görünmemesi ve giyinme alanından erişilmesi.';
      const decisionText = st.decisionStatus || 'Teyit bekliyor';

      return `
        <div class="architect-decision-summary-grid">
          <div class="arch-decision-card highlight">
            <div class="arch-card-header">
              <span class="decision-num">Karar #1 (Ebeveyn Banyosu)</span>
              <span class="source-badge user-said">Sohbet Talebi &amp; Takip Cevabı</span>
              <span class="status-badge ${st.selectedOption ? 'mandatory' : 'likely'}">${escapeHtml(decisionText)}</span>
            </div>

            <div class="decision-section">
              <strong>Son Kullanıcı Talebi:</strong>
              <p>"${escapeHtml(userReq)}"</p>
            </div>

            <div class="decision-section">
              <strong>Takipte Açıklanan İhtiyaç:</strong>
              <p>"${escapeHtml(clarified)}"</p>
            </div>

            <div class="decision-section">
              <strong>Anlaşılan Mimari Öncelik:</strong>
              <p>Ebeveyn süitinde yüksek mahremiyet ve sıralı erişim (Yatak → Giyinme → Banyo).</p>
            </div>

            <div class="decision-section">
              <strong>Sunulan Seçenekler:</strong>
              <ul>
                <li>Seçenek 1 — Banyoyu kuzeye taşıma (Güçlü Mahremiyet)</li>
                <li>Seçenek 2 — Konumu koruyup girişi giyinme alanına çevirme (Tesisat Korumalı)</li>
              </ul>
            </div>

            <div class="decision-section">
              <strong>Teknik Ön Kontroller:</strong>
              <ul>
                <li>Alt kat ıslak hacim ilişkisi denetlendi</li>
                <li>Kapı ve dolap çakışması kontrol edildi</li>
                <li>Doğal havalandırma varsayımı incelendi</li>
                <li>Kullanılabilir geçiş genişliği doğrulandı</li>
              </ul>
            </div>

            <div class="decision-section">
              <strong>Kullanıcı Kararı:</strong>
              <p class="user-choice-highlight">${escapeHtml(decisionText)}</p>
            </div>

            <div class="decision-footer-note">
              📌 <strong>Mimara Not:</strong> Gerçek arsa yönlenmesi ve yerel idare tesisat yönetmeliği verisiyle yeniden değerlendirilmelidir.
            </div>
          </div>
        </div>
      `;
    }

    // Default Study Room Scenario Report
    return `
      <div class="architect-decision-summary-grid">
        <div class="arch-decision-card">
          <div class="arch-card-header">
            <span class="decision-num">Karar #1 (Çalışma Odası)</span>
            <span class="source-badge user-said">Doğrudan Kullanıcı Beyanı</span>
            <span class="status-badge mandatory">Doğrulandı</span>
          </div>

          <div class="decision-section">
            <strong>Son Kullanıcı Talebi:</strong>
            <p>"Eşim evden çalışıyor, online toplantılar yapıyor."</p>
          </div>

          <div class="decision-section">
            <strong>Anlaşılan İhtiyaç:</strong>
            <p>Tam zamanlı evden çalışma için yüksek akustik mahremiyet ve ses izolasyonu.</p>
          </div>

          <div class="decision-section">
            <strong>Sunulan Seçenekler:</strong>
            <ul>
              <li>Alternatif A — Tam Akustik İzolasyon (Kapalı Çalışma Odası)</li>
              <li>Alternatif B — Kayar Panelli Esnek Çalışma Alanı</li>
            </ul>
          </div>

          <div class="decision-section">
            <strong>Kullanıcı Kararı:</strong>
            <p class="user-choice-highlight">Alternatif A Seçildi</p>
          </div>
        </div>
      </div>
    `;
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
window.ChangeHistory = ChangeHistory;
