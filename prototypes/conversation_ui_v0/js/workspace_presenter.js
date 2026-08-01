/**
 * BRIF.AI — Workspace Presenter (v5 Conversation-First Engine)
 *
 * Controls the Main Workspace (~65–70% left panel). Renders:
 * - Dynamic Floor Plans & Overlay Modes (e.g. Ground 30% opacity + Upper stroke)
 * - Wet Cores & Stair Cavity Visual Highlights
 * - Side-by-Side Architectural Option Cards (Option 1 vs Option 2)
 * - Before/After Plan Comparisons
 */

class WorkspacePresenter {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentMode = 'plan'; // 'plan', 'overlay', 'options_side_by_side', 'preferences', 'program'
  }

  setMode(mode, data = {}) {
    this.currentMode = mode;
    this.render(data);
  }

  render(data = {}) {
    if (!this.container) return;

    if (this.currentMode === 'overlay') {
      this.renderFloorOverlayMode();
    } else if (this.currentMode === 'options_side_by_side') {
      this.renderMasterBathOptionsSideBySide(data);
    } else if (this.currentMode === 'orientation') {
      this.renderOrientationHighlightMode();
    } else {
      // Default normal plan mode
      // PlanEditor handles default plan rendering into #planEditorContainer
    }
  }

  renderFloorOverlayMode() {
    const planEditorContainer = document.getElementById('planEditorContainer');
    if (!planEditorContainer) return;

    planEditorContainer.innerHTML = `
      <div class="overlay-mode-wrapper">
        <div class="overlay-badge-tag">🔍 Kat İlişkisi Anlatım Modu (%30 Saydam Zemin Kat + Üst Kat Tesisat Hizası)</div>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 560" width="100%" height="100%" id="overlaySvg">
          <defs>
            <style>
              .ground-overlay { opacity: 0.35; fill: #F1F5F9; stroke: #94A3B8; stroke-width: 2; stroke-dasharray: 4 4; }
              .upper-strong { fill: #FFFFFF; stroke: #0F172A; stroke-width: 3.5; }
              .wet-core { fill: #E0F2FE; stroke: #0284C7; stroke-width: 2.5; }
              .stair-highlight { fill: #FEF08A; stroke: #CA8A04; stroke-width: 3; }
              .plumbing-line { stroke: #0284C7; stroke-width: 2; stroke-dasharray: 6 3; }
            </style>
          </defs>

          <rect width="840" height="560" rx="12" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.5"/>

          <!-- GROUND FLOOR OVERLAY (35% Opacity) -->
          <g class="ground-overlay">
            <rect x="190" y="110" width="190" height="160" rx="4" />
            <text x="285" y="190" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="#64748B" text-anchor="middle">Zemin Mutfak (Soluk)</text>
            <rect x="60" y="110" width="130" height="80" rx="4" class="wet-core" opacity="0.4"/>
            <text x="125" y="150" font-family="'Inter', sans-serif" font-size="11" font-weight="600" fill="#0284C7" text-anchor="middle">Zemin WC</text>
          </g>

          <!-- UPPER FLOOR STRONG OUTLINE -->
          <g class="upper-strong">
            <rect x="190" y="110" width="220" height="160" rx="4" />
            <text x="300" y="190" font-family="'Inter', sans-serif" font-size="13" font-weight="700" fill="#0F172A" text-anchor="middle">Üst Kat Ebeveyn Odası</text>

            <!-- Wet Core Master Bath Highlighted (Blue) -->
            <rect x="60" y="110" width="130" height="100" rx="4" class="wet-core"/>
            <text x="125" y="155" font-family="'Inter', sans-serif" font-size="12" font-weight="700" fill="#0369A1" text-anchor="middle">Ebeveyn Banyosu</text>
            <text x="125" y="172" font-family="'Inter', sans-serif" font-size="10" fill="#0284C7" text-anchor="middle">💧 Canlı Mavi Tesisat</text>

            <!-- Stair Cavity Highlighted (Yellow) -->
            <rect x="430" y="270" width="130" height="180" rx="4" class="stair-highlight"/>
            <text x="495" y="350" font-family="'Inter', sans-serif" font-size="13" font-weight="800" fill="#854D0E" text-anchor="middle">MERDİVEN BOŞLUĞU</text>
            <text x="495" y="370" font-family="'Inter', sans-serif" font-size="10" font-weight="700" fill="#A16207" text-anchor="middle">🟡 Düşey Bağlantı Koyu</text>
          </g>

          <!-- Düşey Tesisat Çizgileri -->
          <line x1="125" y1="110" x2="125" y2="250" class="plumbing-line"/>
          <text x="135" y="230" font-family="'Inter', sans-serif" font-size="9" font-weight="700" fill="#0284C7">↕ Düşey Tesisat Aksı</text>
        </svg>
      </div>
    `;
  }

  renderMasterBathOptionsSideBySide(data) {
    const planEditorContainer = document.getElementById('planEditorContainer');
    if (!planEditorContainer) return;

    planEditorContainer.innerHTML = `
      <div class="options-side-by-side-container">
        <div class="options-banner">
          <h3>🏛️ Ebeveyn Banyosu Yerleşim Seçenekleri</h3>
          <p>Talebiniz üzerine hazırlanan iki mimari çözüm alternatifi aşağıda karşılaştırılmaktadır.</p>
        </div>

        <div class="options-grid">
          <!-- Option 1 Card -->
          <div class="option-card" id="optionCard1">
            <div class="opt-badge">Seçenek 1</div>
            <h4>Banyoyu Kuzeye Taşımak</h4>
            <div class="opt-plan-mini">
              <svg viewBox="0 0 350 220" width="100%" height="150">
                <rect width="350" height="220" fill="#FFFFFF" stroke="#E2E8F0" rx="6"/>
                <rect x="30" y="30" width="140" height="120" fill="#EFF6FF" stroke="#2563EB" stroke-width="2"/>
                <text x="100" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <rect x="180" y="30" width="120" height="60" fill="#F0FDF4" stroke="#166534" stroke-width="2"/>
                <text x="240" y="65" font-size="11" font-weight="700" fill="#14532D" text-anchor="middle">Kuzey Banyo</text>
              </svg>
            </div>
            <div class="opt-pros">
              <strong>✅ Olumlu Yönler:</strong>
              <ul>
                <li>Yataktan doğrudan görünmeme</li>
                <li>Güçlü mahremiyet</li>
                <li>Yatak → Giyinme → Banyo hiyerarşisi</li>
              </ul>
            </div>
            <div class="opt-risks">
              <strong>⚠️ Teyit Gereken Riskler:</strong>
              <ul>
                <li>Alt kat tesisat hizası zayıflayabilir</li>
                <li>Cephe havalandırma penceresi denetlenmeli</li>
              </ul>
            </div>
            <button class="select-option-btn primary" id="btnSelectOpt1">1. Seçeneği Uygula</button>
          </div>

          <!-- Option 2 Card -->
          <div class="option-card" id="optionCard2">
            <div class="opt-badge secondary">Seçenek 2</div>
            <h4>Mevcut Yeri Koruyup Giriş Yönünü Değiştirmek</h4>
            <div class="opt-plan-mini">
              <svg viewBox="0 0 350 220" width="100%" height="150">
                <rect width="350" height="220" fill="#FFFFFF" stroke="#E2E8F0" rx="6"/>
                <rect x="30" y="30" width="160" height="140" fill="#EFF6FF" stroke="#2563EB" stroke-width="2"/>
                <text x="110" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <rect x="200" y="100" width="110" height="70" fill="#FEF3C7" stroke="#D97706" stroke-width="2"/>
                <text x="255" y="140" font-size="10" font-weight="700" fill="#B45309" text-anchor="middle">Giyinmeden Girişli Banyo</text>
              </svg>
            </div>
            <div class="opt-pros">
              <strong>✅ Olumlu Yönler:</strong>
              <ul>
                <li>Düşey tesisat hizası tamamen korunur</li>
                <li>Minimum geometrik değişiklik</li>
              </ul>
            </div>
            <div class="opt-risks">
              <strong>⚠️ Teyit Gereken Riskler:</strong>
              <ul>
                <li>Giyinme alanı dolap açılımı daralabilir</li>
              </ul>
            </div>
            <button class="select-option-btn secondary" id="btnSelectOpt2">2. Seçeneği Uygula</button>
          </div>
        </div>
      </div>
    `;
  }

  renderOrientationHighlightMode() {
    const planEditorContainer = document.getElementById('planEditorContainer');
    if (!planEditorContainer) return;

    planEditorContainer.innerHTML = `
      <div class="orientation-highlight-wrapper">
        <div class="orientation-tag">☀️ Cephe Yönlenmesi &amp; Güneş Açısı İnceleme Modu</div>
        <svg viewBox="0 0 840 560" width="100%" height="100%">
          <rect width="840" height="560" rx="12" fill="#FFFFFF" stroke="#E2E8F0"/>
          <text x="420" y="40" font-size="14" font-weight="800" text-anchor="middle" fill="#0F172A">KUZEY CEPHE (SERVİS &amp; ÇALIŞMA ALANLARI)</text>
          <rect x="60" y="60" width="720" height="20" fill="#93C5FD" opacity="0.4"/>
          
          <text x="420" y="530" font-size="14" font-weight="800" text-anchor="middle" fill="#B45309">GÜNEY CEPHE (SABAH/ÖĞLE GÜNEŞİ - SALON &amp; TERAS)</text>
          <rect x="60" y="480" width="720" height="20" fill="#FDE68A" opacity="0.5"/>
        </svg>
      </div>
    `;
  }
}

// Global Export
window.WorkspacePresenter = WorkspacePresenter;
