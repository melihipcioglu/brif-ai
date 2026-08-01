/**
 * BRIF.AI — Workspace Presenter (v5.1 Engine)
 *
 * Controls the Main Workspace (~68% left panel). Renders:
 * - Stage 1 "Yaşam Ritminizi Anlama" Live Dashboard
 * - Progress Analysis Steps View ("Demo mimari değerlendirmesi")
 * - Side-by-Side Architectural Option Cards (Option 1 vs Option 2)
 * - Coordinated Floor Overlay Mode (Aligned SVG, Stairwell, Wet Cores, Vertical Axis)
 * - Real Floor Plan Orientation & Facade Overlay (North/South bands, movement arrow)
 */

class WorkspacePresenter {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentMode = 'plan'; // 'stage1_dashboard', 'plan', 'progress', 'options_side_by_side', 'overlay', 'orientation'
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

  // --------------------------------------------------------------------------
  // 1. Stage 1 Live Dashboard (Requirement 6)
  // --------------------------------------------------------------------------
  renderStage1Dashboard(data = {}) {
    const hasData = data.hasUserMessages || false;

    this.container.innerHTML = `
      <div class="stage1-dashboard-wrapper">
        <div class="dashboard-header-banner">
          <h3>🧠 Şu Ana Kadar Sizi Nasıl Anladım?</h3>
          <p>Sohbet ilerledikçe evinizin yaşam ritmi, kullanım alışkanlıkları ve öncelikleri burada sentezlenir.</p>
        </div>

        <div class="dashboard-cards-grid">
          <!-- Hane Yapısı -->
          <div class="dna-card">
            <div class="dna-card-header"><span class="dna-icon">👨‍👩‍👧‍👦</span> <strong>Hane Yapısı &amp; Düzen</strong></div>
            <p>${hasData ? 'Evde tam zamanlı çalışan ebeveyn ve okul çağında çocuklar bulunuyor.' : 'Konuşma ilerledikçe hane yapınız burada oluşacak.'}</p>
          </div>

          <!-- Günlük Kullanım Ritmi -->
          <div class="dna-card">
            <div class="dna-card-header"><span class="dna-icon">⏰</span> <strong>Günlük Kullanım Ritmi</strong></div>
            <p>${hasData ? 'Gündüz yoğun online toplantılar, 16:00 sonrası ortak yaşam hareketliliği.' : 'Günlük zaman akışınız sohbetle buraya yansıyacak.'}</p>
          </div>

          <!-- Mahremiyet Öncelikleri -->
          <div class="dna-card highlight">
            <div class="dna-card-header"><span class="dna-icon">🛡️</span> <strong>Mahremiyet Öncelikleri</strong></div>
            <p>${hasData ? 'Çalışma alanı ve ebeveyn süiti için yüksek ses/görsel izolasyon talebi.' : 'Mahremiyet tercihleriniz sohbetle buraya işlenecek.'}</p>
          </div>

          <!-- Birlikte ve Bireysel Kullanım -->
          <div class="dna-card">
            <div class="dna-card-header"><span class="dna-icon">🏡</span> <strong>Kullanım Dengesi</strong></div>
            <p>${hasData ? 'Ortak yaşam alanında açık sosyalleşme, özel alanlarda net sınır.' : 'Bireysel ve ortak alan dengeniz burada belirlenecek.'}</p>
          </div>

          <!-- Henüz Netleşmeyenler -->
          <div class="dna-card pending">
            <div class="dna-card-header"><span class="dna-icon">❓</span> <strong>Henüz Netleşmeyenler</strong></div>
            <p>${hasData ? 'Ebeveyn banyosu kapı açılımı ve giyinme odası sıralaması.' : 'Henüz konuşulmayan noktalar burada listelenecek.'}</p>
          </div>

          <!-- Proje DNA'sı -->
          <div class="dna-card project-dna">
            <div class="dna-card-header"><span class="dna-icon">🧬</span> <strong>Proje DNA Özeti</strong></div>
            <p><strong>Dönüşebilir esneklik • Akustik konfor • Sıralı mahremiyet</strong></p>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 2. Visible Evaluation Progress Card (Requirement 2)
  // --------------------------------------------------------------------------
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
        <div class="progress-card-header">
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

  // --------------------------------------------------------------------------
  // 3. Side-by-Side Options View (Requirement 3)
  // --------------------------------------------------------------------------
  renderMasterBathOptionsSideBySide(data = {}) {
    const selected = data.selectedOption || null;

    this.container.innerHTML = `
      <div class="options-side-by-side-container">
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

            <!-- Mini SVG Floor Plan for Option 1 -->
            <div class="opt-plan-mini">
              <svg viewBox="0 0 340 180" width="100%" height="150">
                <rect width="340" height="180" fill="#F8FAFC" stroke="#E2E8F0" rx="6"/>
                <!-- Bed Room -->
                <rect x="20" y="20" width="150" height="140" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
                <text x="95" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <!-- Dressing Corridor -->
                <rect x="180" y="20" width="60" height="140" fill="#F3E8FF" stroke="#7E22CE" stroke-width="1.5" rx="4"/>
                <text x="210" y="90" font-size="10" font-weight="700" fill="#6B21A8" text-anchor="middle" transform="rotate(-90 210 90)">Giyinme</text>
                <!-- North Bath -->
                <rect x="250" y="20" width="70" height="140" fill="#F0FDF4" stroke="#166534" stroke-width="2" rx="4"/>
                <text x="285" y="80" font-size="10" font-weight="700" fill="#14532D" text-anchor="middle" transform="rotate(-90 285 80)">Kuzey Banyo</text>
                <!-- Circulation Arrow -->
                <path d="M 140 90 L 195 90 L 260 90" fill="none" stroke="#10B981" stroke-width="2.5" stroke-dasharray="4 2"/>
                <polygon points="265,90 258,86 258,94" fill="#10B981"/>
              </svg>
            </div>

            <div class="opt-pros">
              <strong>✅ Olumlu Yönler:</strong>
              <ul>
                <li>Yataktan doğrudan görünmeme</li>
                <li>Güçlü mahremiyet</li>
                <li>Yatak → Giyinme → Banyo sıralaması</li>
              </ul>
            </div>

            <div class="opt-risks">
              <strong>⚠️ Teyit Gerekenler:</strong>
              <ul>
                <li>Alt kat tesisat hizası</li>
                <li>Dış cephe &amp; havalandırma</li>
                <li>Ebeveyn süiti toplam alanı</li>
              </ul>
            </div>

            <div class="opt-actions">
              <button class="opt-btn primary" id="btnApplyOpt1">1. Seçeneği Uygula</button>
            </div>
          </div>

          <!-- Option 2 Card -->
          <div class="option-card ${selected === 2 ? 'selected' : ''}" id="optionCard2">
            <div class="opt-badge secondary">Seçenek 2</div>
            <h4>Konumu Koru, Giriş Yönünü Değiştir</h4>

            <!-- Mini SVG Floor Plan for Option 2 -->
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

            <div class="opt-pros">
              <strong>✅ Olumlu Yönler:</strong>
              <ul>
                <li>Tesisat ilişkisi korunur</li>
                <li>Daha az geometrik değişiklik</li>
                <li>Yataktan görüş azaltılır</li>
              </ul>
            </div>

            <div class="opt-risks">
              <strong>⚠️ Teyit Gerekenler:</strong>
              <ul>
                <li>Giyinme alanındaki dolap yerleşimi</li>
                <li>Kapı açılım genişliği</li>
                <li>Kullanılabilir geçiş genişliği</li>
              </ul>
            </div>

            <div class="opt-actions">
              <button class="opt-btn secondary" id="btnApplyOpt2">2. Seçeneği Uygula</button>
            </div>
          </div>
        </div>

        <div class="options-footer-bar">
          <button class="opt-footer-btn" id="btnDeferDecision">Henüz karar vermiyorum (Mimara bırak)</button>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 4. Coordinated Floor Overlay Mode (Requirement 7)
  // --------------------------------------------------------------------------
  renderFloorOverlayMode(data = {}) {
    this.container.innerHTML = `
      <div class="overlay-mode-wrapper">
        <div class="overlay-header-bar">
          <span class="overlay-tag">🏢 Kat İlişkisi Anlatım Modu</span>
          <p>Zemin Kat (%30 Saydam) ve Üst Kat aynı koordinat düzleminde çakıştırılmıştır.</p>
        </div>

        <div class="overlay-svg-container">
          <svg viewBox="0 0 840 560" width="100%" height="100%" id="alignedOverlaySvg">
            <defs>
              <style>
                .ground-plan { opacity: 0.28; fill: #E2E8F0; stroke: #64748B; stroke-width: 2; stroke-dasharray: 4 4; }
                .upper-plan { fill: none; stroke: #0F172A; stroke-width: 3.5; stroke-linejoin: round; }
                .stair-cavity { fill: #FEF08A; stroke: #CA8A04; stroke-width: 3; }
                .wet-core-blue { fill: #E0F2FE; stroke: #0284C7; stroke-width: 2.5; }
                .plumbing-axis { stroke: #0284C7; stroke-width: 2; stroke-dasharray: 6 3; }
                .room-text { font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 700; }
              </style>
            </defs>

            <rect width="840" height="560" rx="12" fill="#FFFFFF" stroke="#CBD5E1"/>

            <!-- ALIGNED GROUND FLOOR (%28 Opacity) -->
            <g class="ground-plan">
              <rect x="60" y="110" width="190" height="240" rx="4"/>
              <text x="155" y="220" class="room-text" fill="#475569" text-anchor="middle">Zemin Mutfak (Soluk)</text>
              
              <rect x="260" y="110" width="130" height="100" rx="4" class="wet-core-blue"/>
              <text x="325" y="160" class="room-text" fill="#0284C7" text-anchor="middle">Zemin WC</text>
            </g>

            <!-- ALIGNED UPPER FLOOR (Strong Line) -->
            <g class="upper-plan">
              <rect x="60" y="110" width="330" height="280" rx="4"/>
              <text x="200" y="320" class="room-text" fill="#0F172A" text-anchor="middle">Üst Kat Ebeveyn Süiti</text>

              <!-- Upper Wet Core (Master Bath) -->
              <rect x="260" y="110" width="130" height="110" rx="4" class="wet-core-blue"/>
              <text x="325" y="160" class="room-text" fill="#0369A1" text-anchor="middle">Ebeveyn Banyosu</text>
              <text x="325" y="180" font-size="10" fill="#0284C7" text-anchor="middle">💧 Canlı Mavi Tesisat</text>

              <!-- Yellow Stairwell -->
              <rect x="430" y="250" width="130" height="180" rx="4" class="stair-cavity"/>
              <text x="495" y="330" font-size="13" font-weight="800" fill="#854D0E" text-anchor="middle">MERDİVEN BOŞLUĞU</text>
              <text x="495" y="350" font-size="10" font-weight="700" fill="#A16207" text-anchor="middle">🟡 Düşey Bağlantı</text>
            </g>

            <!-- Vertical Plumbing Axis -->
            <line x1="325" y1="90" x2="325" y2="240" class="plumbing-axis"/>
            <text x="335" y="100" font-size="10" font-weight="700" fill="#0284C7">↕ Düşey Tesisat Aksı</text>
          </svg>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 5. Real Floor Plan Orientation Mode (Requirement 8)
  // --------------------------------------------------------------------------
  renderOrientationMode(data = {}) {
    this.container.innerHTML = `
      <div class="orientation-workspace-wrapper">
        <div class="orientation-banner">
          <span class="orient-tag">☀️ Cephe Yönlenmesi &amp; Güneş Açısı İnceleme</span>
          <div class="disclaimer-chip">⚠️ Yönlenme prototip varsayımıdır. Gerçek arsa yönleri girildiğinde yeniden kontrol edilmelidir.</div>
        </div>

        <div class="orientation-svg-container">
          <svg viewBox="0 0 840 560" width="100%" height="100%">
            <rect width="840" height="560" rx="12" fill="#FFFFFF" stroke="#E2E8F0"/>

            <!-- NORTH FACADE BAND (Light Blue) -->
            <rect x="50" y="50" width="740" height="30" fill="#DBEAFE" rx="4"/>
            <text x="420" y="70" font-size="12" font-weight="800" fill="#1E40AF" text-anchor="middle">KUZEY CEPHE (SERVİS &amp; BANYO ALANLARI)</text>

            <!-- SOUTH FACADE BAND (Light Yellow) -->
            <rect x="50" y="480" width="740" height="30" fill="#FEF3C7" rx="4"/>
            <text x="420" y="500" font-size="12" font-weight="800" fill="#B45309" text-anchor="middle">GÜNEY CEPHE (SABAH/ÖĞLE GÜNEŞİ - SALON &amp; TERAS)</text>

            <!-- REAL FLOOR PLAN OVERLAY -->
            <rect x="80" y="100" width="680" height="360" fill="none" stroke="#1E293B" stroke-width="4" rx="6"/>

            <!-- Rooms -->
            <rect x="100" y="120" width="220" height="150" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
            <text x="210" y="195" font-size="13" font-weight="700" fill="#1E40AF" text-anchor="middle">Salon (Güney Açılımlı)</text>

            <rect x="340" y="120" width="180" height="150" fill="#F0FDF4" stroke="#166534" stroke-width="2.5" rx="4"/>
            <text x="430" y="195" font-size="13" font-weight="800" fill="#14532D" text-anchor="middle">Kuzey Banyo Konumu</text>

            <!-- Movement Arrow -->
            <path d="M 210 280 Q 320 320 430 280" fill="none" stroke="#10B981" stroke-width="3" stroke-dasharray="6 3"/>
            <polygon points="430,280 420,274 422,286" fill="#10B981"/>
            <text x="320" y="325" font-size="11" font-weight="700" fill="#047857" text-anchor="middle">Kuzeye Taşıma Önerisi</text>

            <!-- North Compass Arrow -->
            <g transform="translate(740, 140)">
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
