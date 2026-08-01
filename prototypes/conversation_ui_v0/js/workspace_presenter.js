/**
 * BRIF.AI — Workspace Presenter (v5.2 Refined Engine)
 *
 * Controls Main Workspace (~68% left panel). Features:
 * - Workflow Status Bar (Talep -> İhtiyaç -> Değerlendirme -> Seçenekler -> Karar)
 * - Stage 1 Live Dashboard
 * - Analysis Progress Card ("Demo mimari değerlendirmesi")
 * - Side-by-Side Architectural Option Cards with Structured Sections
 * - Coordinated Floor Overlay Mode with Legend & Filter Buttons
 * - Real Floor Plan Orientation & Facade Mode with Disclaimer
 */

class WorkspacePresenter {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentMode = 'plan';
  }

  setMode(mode, data = {}) {
    this.currentMode = mode;
    this.render(data);
  }

  render(data = {}) {
    if (!this.container) return;

    if (this.currentMode === 'stage1_dashboard') {
      this.renderStage1Dashboard(data);
    } else if (this.currentMode === 'progress') {
      this.renderAnalysisProgress(data);
    } else if (this.currentMode === 'options_side_by_side') {
      this.renderMasterBathOptionsSideBySide(data);
    } else if (this.currentMode === 'overlay') {
      this.renderFloorOverlayMode(data);
    } else if (this.currentMode === 'orientation') {
      this.renderOrientationMode(data);
    }
  }

  // Workflow Tracker Bar (Requirement 7)
  renderWorkflowTrackerHtml(currentStep = 4) {
    const steps = [
      { num: 1, label: "Talep Alındı" },
      { num: 2, label: "İhtiyaç Netleştirildi" },
      { num: 3, label: "Değerlendirme Yapıldı" },
      { num: 4, label: "İki Seçenek Hazırlandı" },
      { num: 5, label: "Kullanıcı Kararı Bekleniyor" }
    ];

    return `
      <div class="workflow-tracker-bar">
        ${steps.map(s => `
          <div class="w-tracker-step ${s.num === currentStep ? 'active' : s.num < currentStep ? 'completed' : ''}">
            <span class="w-step-num">${s.num < currentStep ? '✓' : s.num}</span>
            <span class="w-step-name">${s.label}</span>
          </div>
          ${s.num < 5 ? '<span class="w-tracker-arrow">➔</span>' : ''}
        `).join('')}
      </div>
    `;
  }

  // 1. Stage 1 Live Dashboard (Requirement 13)
  renderStage1Dashboard(data = {}) {
    const hasData = data.hasUserMessages || false;

    this.container.innerHTML = `
      <div class="stage1-dashboard-wrapper">
        <div class="dashboard-header-banner">
          <h3>🧠 Şu Ana Kadar Sizi Nasıl Anladım?</h3>
          <p>Sohbet ilerledikçe evinizin yaşam ritmi, kullanım alışkanlıkları ve öncelikleri burada sentezlenir.</p>
        </div>

        <div class="dashboard-cards-grid">
          <div class="dna-card ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">👨‍👩‍👧‍👦</span> <strong>Hane Yapısı &amp; Düzen</strong></div>
            <p>${hasData ? '4 kişi — 2 yetişkin (ebeveyn) ve 2 okul çağında çocuk.' : 'Konuşma ilerledikçe hane yapınız burada oluşacak.'}</p>
          </div>

          <div class="dna-card ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">⏰</span> <strong>Günlük Kullanım Ritmi</strong></div>
            <p>${hasData ? '16:00 sonrası çocuk kullanım yoğunluğu, gündüz online toplantılar.' : 'Günlük zaman akışınız sohbetle buraya yansıyacak.'}</p>
          </div>

          <div class="dna-card highlight ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">🛡️</span> <strong>Mahremiyet Öncelikleri</strong></div>
            <p>${hasData ? 'Evden çalışma sırasında yüksek akustik ayrışma ve ses izolasyonu.' : 'Mahremiyet tercihleriniz sohbetle buraya işlenecek.'}</p>
          </div>

          <div class="dna-card ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">🏡</span> <strong>Kullanım Dengesi</strong></div>
            <p>${hasData ? 'Ortak aile alanı + gerektiğinde kapalı bireysel çalışma alanı.' : 'Bireysel ve ortak alan dengeniz burada belirlenecek.'}</p>
          </div>

          <div class="dna-card pending">
            <div class="dna-card-header"><span class="dna-icon">❓</span> <strong>Henüz Netleşmeyenler</strong></div>
            <p>${hasData ? 'Ebeveyn banyosu kapı açılımı ve giyinme odası sıralaması.' : 'Henüz konuşulmayan noktalar burada listelenecek.'}</p>
          </div>

          <div class="dna-card project-dna">
            <div class="dna-card-header"><span class="dna-icon">🧬</span> <strong>Proje DNA Özeti</strong></div>
            <p><strong>Aile odaklı • Kontrollü ayrışma • Dönüşebilir mekânlar</strong></p>
          </div>
        </div>
      </div>
    `;
  }

  // 2. Visible Evaluation Progress Card (Requirement 2)
  renderAnalysisProgress(data = {}) {
    const steps = data.steps || [
      { text: "Talebin amacı yorumlanıyor", status: "completed" },
      { text: "Yatak–giyinme–banyo ilişkisi kontrol ediliyor", status: "completed" },
      { text: "Alt kat ıslak hacim ilişkisi inceleniyor", status: "checking" },
      { text: "Kapı ve mobilya çakışmaları kontrol ediliyor", status: "pending" },
      { text: "Cephe ve havalandırma varsayımları değerlendiriliyor", status: "pending" },
      { text: "İki seçenek hazırlanıyor", status: "pending" }
    ];

    this.container.innerHTML = `
      <div class="analysis-progress-workspace-card">
        ${this.renderWorkflowTrackerHtml(3)}

        <div class="progress-card-header" style="margin-top:12px;">
          <span class="demo-eval-badge">📌 Demo Mimari Değerlendirmesi</span>
          <h3>Ebeveyn Banyosu İçin Seçenekler Hazırlanıyor</h3>
          <p>Talebinizin arkasındaki mimari ihtiyaçlar ve teknik kısıtlar simüle ediliyor.</p>
        </div>

        <ul class="workspace-progress-steps">
          ${steps.map(s => `
            <li class="w-step-item ${s.status}">
              <span class="step-icon">${s.status === 'completed' ? '✅' : s.status === 'checking' ? '🔄' : '⏳'}</span>
              <span class="step-text">${escapeHtml(s.text)}</span>
              <span class="step-status-badge ${s.status}">
                ${s.status === 'completed' ? 'Tamamlandı' : s.status === 'checking' ? 'Kontrol ediliyor' : 'Bekliyor'}
              </span>
            </li>
          `).join('')}
        </ul>
      </div>
    `;
  }

  // 3. Side-by-Side Options View (Requirements 6 & 8 - Applied ONLY on explicit button click)
  renderMasterBathOptionsSideBySide(data = {}) {
    const selected = data.selectedOption || null;

    this.container.innerHTML = `
      <div class="options-side-by-side-container">
        ${this.renderWorkflowTrackerHtml(selected ? 5 : 4)}

        <div class="options-banner">
          <div class="banner-tag">🏛️ İki Mimari Çözüm Alternatifi</div>
          <h3>Ebeveyn Banyosu Yerleşim Seçenekleri</h3>
          <p>Yataktan görünmeme ve giyinme alanından erişim talebiniz doğrultusunda hazırlanmıştır.</p>
        </div>

        <div class="options-grid">
          <!-- Option 1 Card -->
          <div class="option-card ${selected === 1 ? 'selected' : ''}" id="optionCard1">
            <div class="opt-badge">Seçenek 1</div>
            <h4>Banyoyu Kuzeye Taşımak</h4>

            <div class="opt-plan-mini">
              <svg viewBox="0 0 340 180" width="100%" height="150">
                <rect width="340" height="180" fill="#F8FAFC" stroke="#E2E8F0" rx="6"/>
                <!-- Bed Room -->
                <rect x="20" y="20" width="140" height="140" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
                <text x="90" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <!-- Faded old bath -->
                <rect x="20" y="100" width="60" height="50" fill="none" stroke="#DC2626" stroke-width="1.5" stroke-dasharray="3 3"/>
                <text x="50" y="125" font-size="9" fill="#DC2626" font-weight="700" text-anchor="middle">Eski Banyo</text>
                <!-- Dressing Corridor -->
                <rect x="175" y="20" width="60" height="140" fill="#F3E8FF" stroke="#7E22CE" stroke-width="1.5" rx="4"/>
                <text x="205" y="90" font-size="10" font-weight="700" fill="#6B21A8" text-anchor="middle" transform="rotate(-90 205 90)">Giyinme</text>
                <!-- New North Bath -->
                <rect x="245" y="20" width="80" height="140" fill="#F0FDF4" stroke="#166534" stroke-width="2.5" rx="4"/>
                <text x="285" y="80" font-size="10" font-weight="800" fill="#14532D" text-anchor="middle" transform="rotate(-90 285 80)">Kuzey Banyo</text>
                <!-- Movement Arrow -->
                <path d="M 60 100 L 140 50 L 240 50" fill="none" stroke="#10B981" stroke-width="2" stroke-dasharray="4 2"/>
                <polygon points="245,50 238,46 238,54" fill="#10B981"/>
              </svg>
            </div>

            <!-- Structured Headers (Requirement 6) -->
            <div class="opt-section">
              <span class="opt-sec-title">🔄 Ne değişiyor?</span>
              <p>Banyo ebeveyn süitinin kuzey cephesine kaydırılıyor, erişim giyinme alanından veriliyor.</p>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">🛡️ Neyi koruyor?</span>
              <p>Yatak başı mahremiyetini ve yatak → giyinme → banyo hiyerarşisini korur.</p>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">⚠️ Hangi riski oluşturuyor?</span>
              <p>Alt kat tesisat hizası zayıflayabilir, havalandırma pencere açılımı denetlenmeli.</p>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">🔍 Teyit gerekenler</span>
              <p>Dış cephe pencere açılımı ve alt kat banyo düşey aks uyumu.</p>
            </div>

            <div class="opt-actions">
              <button class="opt-btn primary" id="btnApplyOpt1">${selected === 1 ? '✅ Uygulandı (Seçenek 1)' : '1. Seçeneği Uygula'}</button>
            </div>
          </div>

          <!-- Option 2 Card -->
          <div class="option-card ${selected === 2 ? 'selected' : ''}" id="optionCard2">
            <div class="opt-badge secondary">Seçenek 2</div>
            <h4>Konumu Koru, Giriş Yönünü Değiştir</h4>

            <div class="opt-plan-mini">
              <svg viewBox="0 0 340 180" width="100%" height="150">
                <rect width="340" height="180" fill="#F8FAFC" stroke="#E2E8F0" rx="6"/>
                <!-- Bed Room -->
                <rect x="20" y="20" width="170" height="140" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
                <text x="105" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <!-- Bath with dressing entry -->
                <rect x="200" y="50" width="120" height="110" fill="#FEF3C7" stroke="#D97706" stroke-width="2" rx="4"/>
                <text x="260" y="105" font-size="10" font-weight="700" fill="#B45309" text-anchor="middle">Giyinmeden Girişli Banyo</text>
                <!-- Blocked old door -->
                <line x1="200" y1="35" x2="200" y2="50" stroke="#DC2626" stroke-width="3"/>
                <text x="190" y="40" font-size="9" fill="#DC2626" font-weight="800">🚫</text>
              </svg>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">🔄 Ne değişiyor?</span>
              <p>Banyo yeri korunur; doğrudan yatak odası kapısı kapatılıp giyinme alanından giriş açılır.</p>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">🛡️ Neyi koruyor?</span>
              <p>Zemin kat ile olan düşey tesisat hizası tamamen korunur.</p>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">⚠️ Hangi riski oluşturuyor?</span>
              <p>Giyinme odası dolap yerleşimi ve kapı açılım genişliği daralabilir.</p>
            </div>

            <div class="opt-section">
              <span class="opt-sec-title">🔍 Teyit gerekenler</span>
              <p>Dolap kapak açılımları ve kullanılabilir geçiş mesafesi.</p>
            </div>

            <div class="opt-actions">
              <button class="opt-btn secondary" id="btnApplyOpt2">${selected === 2 ? '✅ Uygulandı (Seçenek 2)' : '2. Seçeneği Uygula'}</button>
            </div>
          </div>
        </div>

        <div class="options-footer-bar">
          <button class="opt-footer-btn" id="btnDeferDecision">Henüz karar vermiyorum (Mimara bırak)</button>
        </div>
      </div>
    `;
  }

  // 4. Coordinated Floor Overlay Mode with Legend (Requirement 9)
  renderFloorOverlayMode(data = {}) {
    this.container.innerHTML = `
      <div class="overlay-mode-wrapper">
        <div class="overlay-header-bar">
          <span class="overlay-tag">🏢 Kat İlişkisi Anlatım Modu</span>
          <p>Soluk çizgiler Zemin Katı (%28 saydam), koyu çizgiler Üst Katı gösterir. Mavi alanlar ıslak hacimler, sarı alan merdiven boşluğudur.</p>
        </div>

        <!-- Small Legend (Requirement 9) -->
        <div class="overlay-legend-bar">
          <span class="legend-item"><span class="leg-box zemin"></span> Zemin Kat (Soluk %28)</span>
          <span class="legend-item"><span class="leg-box ust"></span> Üst Kat (Koyu)</span>
          <span class="legend-item"><span class="leg-box islak"></span> Islak Hacimler</span>
          <span class="legend-item"><span class="leg-box merdiven"></span> Merdiven Boşluğu</span>
          <span class="legend-item"><span class="leg-line tesisat"></span> Düşey Tesisat Aksı</span>
        </div>

        <!-- Filter Action Buttons -->
        <div class="overlay-filter-toolbar">
          <button class="overlay-filter-btn" id="btnOverlayUpperOnly">Yalnız Üst Kat</button>
          <button class="overlay-filter-btn active" id="btnOverlayTransparent">Alt Katı Saydam Göster</button>
          <button class="overlay-filter-btn" id="btnOverlayWetCores">Islak Hacimleri Vurgula</button>
          <button class="overlay-filter-btn" id="btnOverlayStairs">Merdiven Boşluğunu Göster</button>
          <button class="overlay-filter-btn" id="btnOverlayNormal">Normal Plana Dön</button>
        </div>

        <div class="overlay-svg-container">
          <svg viewBox="0 0 840 540" width="100%" height="100%" id="alignedOverlaySvg">
            <defs>
              <style>
                .ground-plan { opacity: 0.28; fill: #E2E8F0; stroke: #64748B; stroke-width: 2; stroke-dasharray: 4 4; }
                .upper-plan { fill: none; stroke: #0F172A; stroke-width: 3.5; stroke-linejoin: round; }
                .stair-cavity { fill: #FEF08A; stroke: #CA8A04; stroke-width: 3; }
                .wet-core-blue { fill: #E0F2FE; stroke: #0284C7; stroke-width: 2.5; }
                .plumbing-axis { stroke: #0284C7; stroke-width: 2; stroke-dasharray: 6 3; }
                .label-text { font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 700; }
              </style>
            </defs>

            <rect width="840" height="540" rx="12" fill="#FFFFFF" stroke="#CBD5E1"/>

            <!-- ALIGNED GROUND FLOOR (%28 Opacity) -->
            <g class="ground-plan">
              <rect x="60" y="100" width="190" height="240" rx="4"/>
              <text x="155" y="210" class="label-text" fill="#475569" text-anchor="middle">Zemin Mutfak (Soluk)</text>
              
              <rect x="260" y="100" width="130" height="100" rx="4" class="wet-core-blue"/>
              <text x="325" y="150" class="label-text" fill="#0284C7" text-anchor="middle">Alt Kat Mutfak/WC Çekirdeği</text>
            </g>

            <!-- ALIGNED UPPER FLOOR (Strong Line) -->
            <g class="upper-plan">
              <rect x="60" y="100" width="330" height="280" rx="4"/>
              <text x="200" y="310" class="label-text" fill="#0F172A" text-anchor="middle">Üst Kat Ebeveyn Süiti</text>

              <!-- Upper Wet Core (Master Bath) -->
              <rect x="260" y="100" width="130" height="110" rx="4" class="wet-core-blue"/>
              <text x="325" y="145" class="label-text" fill="#0369A1" text-anchor="middle">Üst Kat Ebeveyn Banyosu</text>
              <text x="325" y="165" font-size="10" fill="#0284C7" text-anchor="middle">💧 Canlı Mavi Tesisat</text>

              <!-- Yellow Stairwell -->
              <rect x="430" y="240" width="130" height="180" rx="4" class="stair-cavity"/>
              <text x="495" y="320" font-size="12" font-weight="800" fill="#854D0E" text-anchor="middle">MERDİVEN BOŞLUĞU</text>
              <text x="495" y="340" font-size="9.5" font-weight="700" fill="#A16207" text-anchor="middle">🟡 İki katta da boş hacimdir</text>
            </g>

            <!-- Vertical Plumbing Axis -->
            <line x1="325" y1="80" x2="325" y2="230" class="plumbing-axis"/>
            <text x="335" y="90" font-size="10" font-weight="700" fill="#0284C7">↕ Düşey Tesisat Yakınlığı Aksı</text>
          </svg>
        </div>
      </div>
    `;
  }

  // 5. Real Floor Plan Orientation Mode (Requirement 10)
  renderOrientationMode(data = {}) {
    this.container.innerHTML = `
      <div class="orientation-workspace-wrapper">
        <div class="orientation-banner">
          <span class="orient-tag">☀️ Cephe Yönlenmesi &amp; Güneş Açısı İnceleme</span>
          <div class="disclaimer-chip">⚠️ Kuzey cephesi doğrudan güneş ihtiyacı daha düşük servis hacimleri için değerlendirilebilir. Ancak gerçek karar arsa yönü, komşu yapılar, açıklıklar ve yerel koşullarla doğrulanmalıdır.</div>
        </div>

        <div class="orientation-svg-container">
          <svg viewBox="0 0 840 540" width="100%" height="100%">
            <rect width="840" height="540" rx="12" fill="#FFFFFF" stroke="#E2E8F0"/>

            <!-- NORTH FACADE BAND (Light Blue) -->
            <rect x="50" y="40" width="740" height="28" fill="#DBEAFE" rx="4"/>
            <text x="420" y="58" font-size="11.5" font-weight="800" fill="#1E40AF" text-anchor="middle">KUZEY CEPHE (SERVİS &amp; BANYO ALANLARI)</text>

            <!-- SOUTH FACADE BAND (Light Yellow) -->
            <rect x="50" y="470" width="740" height="28" fill="#FEF3C7" rx="4"/>
            <text x="420" y="488" font-size="11.5" font-weight="800" fill="#B45309" text-anchor="middle">GÜNEY CEPHE (SABAH/ÖĞLE GÜNEŞİ - SALON &amp; TERAS)</text>

            <!-- REAL UPPER FLOOR PLAN OVERLAY -->
            <rect x="70" y="80" width="700" height="380" fill="none" stroke="#1E293B" stroke-width="4" rx="6"/>

            <!-- Ebeveyn Süiti -->
            <rect x="90" y="100" width="240" height="200" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
            <text x="210" y="190" font-size="13" font-weight="700" fill="#1E40AF" text-anchor="middle">Ebeveyn Süiti</text>

            <!-- Proposed North Bath Position -->
            <rect x="350" y="100" width="180" height="150" fill="#F0FDF4" stroke="#166534" stroke-width="2.5" rx="4"/>
            <text x="440" y="175" font-size="12.5" font-weight="800" fill="#14532D" text-anchor="middle">Önerilen Kuzey Banyo</text>

            <!-- Movement Arrow -->
            <path d="M 210 310 Q 325 360 440 260" fill="none" stroke="#10B981" stroke-width="3" stroke-dasharray="6 3"/>
            <polygon points="440,260 430,254 432,266" fill="#10B981"/>
            <text x="325" y="355" font-size="11" font-weight="700" fill="#047857" text-anchor="middle">Kuzeye Taşıma Önerisi</text>

            <!-- North Compass Arrow -->
            <g transform="translate(730, 130)">
              <circle cx="0" cy="0" r="18" fill="#F8FAFC" stroke="#0F172A" stroke-width="2"/>
              <path d="M0 -12 L6 8 L0 3 L-6 8 Z" fill="#0F172A"/>
              <text x="0" y="24" font-size="10" font-weight="800" fill="#0F172A" text-anchor="middle">K</text>
            </g>
          </svg>
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
window.WorkspacePresenter = WorkspacePresenter;
