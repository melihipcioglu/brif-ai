/**
 * BRIF.AI — Change History & Dynamic Professional Architect Report (v6.1 Refined)
 *
 * Generates localized (Turkish) professional decision report based on active scope key.
 * Shows honest empty state if report does not belong to active project/level scope.
 */

class ChangeHistory {
  constructor() {
    this.sessionState = {
      projectId: 'proj_house_2story',
      buildingId: 'bldg_main',
      levelId: 'lvl_ground',
      selectedSpaceId: 'space_study',
      activeScenario: null,
      decisionStatus: 'Karar bekleniyor'
    };
  }

  setSessionState(state) {
    this.sessionState = { ...this.sessionState, ...state };
  }

  renderArchitectReport() {
    const st = this.sessionState;

    // Check scope mismatch for Master Bath decision (Requirement 11)
    if (st.activeScenario === 'master_bath_relocation') {
      // Must be in house_2story project
      if (st.projectId !== 'proj_house_2story') {
        return `
          <div class="empty-state-workspace-card">
            <div class="empty-state-icon">📋</div>
            <h3 class="empty-state-title">Bu görünümde seçili karara ait rapor bulunmuyor</h3>
            <p class="empty-state-desc">
              Ebeveyn banyosu taşınması kararı Konut projesine aittir. Aktif proje kapsamı farklı olduğundan bu rapor sızdırılmamıştır.
            </p>
          </div>
        `;
      }

      const userReq = st.userRequest || 'Ebeveyn banyosunun kuzey tarafına alınması.';
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
              <strong>2. Sistemin Mimari Yorumu:</strong>
              <p>Ebeveyn süitinde sıralı erişim hiyerarşisi (Yatak → Giyinme → Banyo) ve görsel mahremiyet önceliği.</p>
            </div>

            <div class="decision-section">
              <strong>3. Yapılan Demo Ön Kontroller:</strong>
              <ul>
                <li>Alt kat ıslak hacim ilişkisi şematik olarak incelendi</li>
                <li>Kapı–dolap çakışması ve geçiş genişliği değerlendirildi</li>
              </ul>
            </div>

            <div class="decision-section">
              <strong>4. Kullanıcının Kararı:</strong>
              <p class="user-choice-highlight">${escapeHtml(decisionText)}</p>
            </div>

            <div class="decision-meta-row">
              <span><strong>Kapsam Anahtarı:</strong> proj_house_2story/bldg_main/lvl_upper/space_master_bath</span> • 
              <span><strong>Kaynak:</strong> Kullanıcı sohbet beyanı</span> • 
              <span><strong>Güven Düzeyi:</strong> Yüksek</span>
            </div>
          </div>
        </div>
      `;
    }

    // Commercial Tower Report
    if (st.projectId === 'proj_tower_50floor') {
      return `
        <div class="architect-decision-summary-grid">
          <div class="arch-decision-card">
            <div class="arch-card-header">
              <span class="decision-num">Karar #101 (Finans Kulesi)</span>
              <span class="status-badge mandatory">Uygulandı</span>
            </div>

            <div class="decision-section">
              <strong>1. Kapsam:</strong>
              <p>50 Katlı Finans Kulesi › A Kulesi › 18. Kat › Yönetim Zonu</p>
            </div>

            <div class="decision-section">
              <strong>2. Kurumsal Yerleşim Kararı:</strong>
              <p>18A Toplantı Odası yönetim çekirdeğine yakın konumlandırıldı.</p>
            </div>

            <div class="decision-meta-row">
              <span><strong>Kapsam Anahtarı:</strong> proj_tower_50floor/tower_a/lvl_18/zone_exec_18</span> • 
              <span><strong>Kaynak:</strong> Kurumsal alan standardı</span>
            </div>
          </div>
        </div>
      `;
    }

    // Technology Campus Report
    if (st.projectId === 'proj_campus_multiblock') {
      return `
        <div class="architect-decision-summary-grid">
          <div class="arch-decision-card">
            <div class="arch-card-header">
              <span class="decision-num">Karar #201 (Teknoloji Kampüsü)</span>
              <span class="status-badge mandatory">Uygulandı</span>
            </div>

            <div class="decision-section">
              <strong>1. Kapsam:</strong>
              <p>Çok Bloklu Teknoloji Kampüsü › Blok A › 2. Kat</p>
            </div>

            <div class="decision-section">
              <strong>2. Laboratuvar Yerleşim Kararı:</strong>
              <p>Robotik Araştırma Laboratuvarı ağır yük ve havalandırma aksına hizalandı.</p>
            </div>

            <div class="decision-meta-row">
              <span><strong>Kapsam Anahtarı:</strong> proj_campus_multiblock/block_a_r_d/lvl_2_block_a</span> • 
              <span><strong>Kaynak:</strong> Teknik şartname</span>
            </div>
          </div>
        </div>
      `;
    }

    // Default Residential Study Report
    return `
      <div class="architect-decision-summary-grid">
        <div class="arch-decision-card">
          <div class="arch-card-header">
            <span class="decision-num">Karar #1 (Çalışma Odası)</span>
            <span class="status-badge mandatory">Uygulandı</span>
          </div>

          <div class="decision-section">
            <strong>1. Kullanıcının İlk Talebi:</strong>
            <p>"Evden çalışma ve online toplantılar."</p>
          </div>

          <div class="decision-section">
            <strong>2. Karar:</strong>
            <p class="user-choice-highlight">Alternatif A (Tam Akustik İzolasyon) Seçildi</p>
          </div>

          <div class="decision-meta-row">
            <span><strong>Kapsam Anahtarı:</strong> proj_house_2story/bldg_main/lvl_ground/space_study</span> • 
            <span><strong>Kaynak:</strong> Doğrudan kullanıcı beyanı</span>
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
