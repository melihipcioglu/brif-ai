/**
 * BRIF.AI — Change History & Dynamic Professional Architect Report (v5.2 Refined)
 *
 * Generates fully localized (Turkish) professional decision report based on active session state.
 */

class ChangeHistory {
  constructor() {
    this.sessionState = {
      activeStage: 1,
      activeAlternative: 'A',
      activeFloor: 'upper',
      selectedSpaceId: 'master_bath',
      selectedSpaceName: 'Ebeveyn Banyosu',
      activeScenario: null,
      conversationStep: 'idle',
      userRequest: '',
      clarifiedNeeds: [],
      presentedOptions: [],
      selectedOption: null,
      decisionStatus: 'Karar bekleniyor'
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

    // If Master Bath Scenario is active
    if (st.activeScenario === 'master_bath_relocation') {
      const userReq = st.userRequest || 'Ebeveyn banyosunun kuzey tarafına alınması.';
      const clarified = st.clarifiedNeeds.length > 0 ? st.clarifiedNeeds.join(', ') : 'Banyonun yataktan görünmemesi ve giyinme alanından erişilmesi.';
      const decisionText = st.decisionStatus || 'Karar bekleniyor';

      return `
        <div class="architect-decision-summary-grid">
          <div class="arch-decision-card highlight">
            <div class="arch-card-header">
              <span class="decision-num">Karar #1 (Ebeveyn Banyosu)</span>
              <span class="status-badge ${st.selectedOption ? 'mandatory' : 'likely'}">${escapeHtml(decisionText)}</span>
            </div>

            <div class="decision-section">
              <strong>1. Kullanıcının İlk Talebi:</strong>
              <p>"${escapeHtml(userReq)}"</p>
            </div>

            <div class="decision-section">
              <strong>2. Takipte Açıklanan İhtiyaç:</strong>
              <p>"${escapeHtml(clarified)}"</p>
            </div>

            <div class="decision-section">
              <strong>3. Sistemin Mimari Yorumu:</strong>
              <p>Ebeveyn süitinde sıralı erişim hiyerarşisi (Yatak → Giyinme → Banyo) ve görsel mahremiyet önceliği.</p>
            </div>

            <div class="decision-section">
              <strong>4. Sunulan Seçenekler:</strong>
              <ul>
                <li>Seçenek 1 — Banyoyu kuzeye taşıma (Güçlü Mahremiyet)</li>
                <li>Seçenek 2 — Konumu koruyup girişi giyinme alandan açma (Tesisat Korumalı)</li>
              </ul>
            </div>

            <div class="decision-section">
              <strong>5. Yapılan Demo Ön Kontroller:</strong>
              <ul>
                <li>Alt kat ıslak hacim ilişkisi şematik olarak incelendi</li>
                <li>Kapı–dolap çakışması ve geçiş genişliği değerlendirildi</li>
                <li>Dış cephe pencere havalandırma varsayımı denetlendi</li>
              </ul>
            </div>

            <div class="decision-section">
              <strong>6. Kullanıcının Kararı:</strong>
              <p class="user-choice-highlight">${escapeHtml(decisionText)}</p>
            </div>

            <div class="decision-section">
              <strong>7. Açık Kalan Konular:</strong>
              <p>Dış cephe pencere açılımı ve alt kat tesisat aksı kesinleştirmesi.</p>
            </div>

            <div class="decision-section">
              <strong>8. Mimara Aktarılacak Not:</strong>
              <p>Gerçek arsa yönlenmesi, komşu cephe mesafeleri ve idare yönetmeliğiyle yeniden değerlendirilmelidir.</p>
            </div>

            <div class="decision-meta-row">
              <span><strong>Kaynak:</strong> Kullanıcı sohbet beyanı</span> • 
              <span><strong>Güven Düzeyi:</strong> Yüksek</span> • 
              <span><strong>Doğrulama Durumu:</strong> Takip cevabıyla netleştirildi</span> • 
              <span><strong>Teknik Durum:</strong> Demo ön kontrolde incelendi</span>
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
            <span class="status-badge mandatory">Uygulandı</span>
          </div>

          <div class="decision-section">
            <strong>1. Kullanıcının İlk Talebi:</strong>
            <p>"Eşim evden çalışıyor, online toplantılar yapıyor."</p>
          </div>

          <div class="decision-section">
            <strong>2. Takipte Açıklanan İhtiyaç:</strong>
            <p>"Çalışma sırasında tam ses izolasyonu ve sessizlik."</p>
          </div>

          <div class="decision-section">
            <strong>3. Sistemin Mimari Yorumu:</strong>
            <p>Tam zamanlı evden çalışma için yüksek akustik mahremiyet ve kapalı oda kurgusu.</p>
          </div>

          <div class="decision-section">
            <strong>4. Sunulan Seçenekler:</strong>
            <ul>
              <li>Alternatif A — Tam Akustik İzolasyon (Kapalı Çalışma Odası)</li>
              <li>Alternatif B — Kayar Panelli Esnek Çalışma Alanı</li>
            </ul>
          </div>

          <div class="decision-section">
            <strong>5. Kullanıcının Kararı:</strong>
            <p class="user-choice-highlight">Alternatif A Seçildi (Uygulandı)</p>
          </div>

          <div class="decision-meta-row">
            <span><strong>Kaynak:</strong> Doğrudan kullanıcı beyanı</span> • 
            <span><strong>Güven Düzeyi:</strong> Yüksek</span> • 
            <span><strong>Doğrulama Durumu:</strong> Kullanıcı seçimiyle doğrulandı</span>
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
