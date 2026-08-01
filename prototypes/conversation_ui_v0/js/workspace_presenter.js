/**
 * BRIF.AI — Workspace Presenter & Surface Engine (v6.1.3 Platform Architecture)
 *
 * Scope-driven presenter resolving candidate documents and workspace surfaces via DOMSurfaceRegistry,
 * generation tokens, and capability checks.
 * Guarantees: "No stale or foreign workspace payload may survive an active-scope transition."
 */

class WorkspacePresenter {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.hierarchy = options.hierarchy || new EntityHierarchy();
    this.store = options.store || new ScopedDocumentStore();
    this.resolver = options.resolver || new WorkspaceScopeResolver(this.hierarchy, this.store);
    this.guard = options.guard || new RenderCompatibilityGuard(this.hierarchy);
    this.registry = options.registry || (window.appDOMRegistry || new DOMSurfaceRegistry());

    this.currentMode = 'plan';
  }

  setMode(mode, data = {}) {
    this.currentMode = mode;
    this.render(data);
  }

  render(data = {}) {
    if (!this.container) return;

    const ctx = data.activeContext || (window.appStateMachine ? window.appStateMachine.getContext() : null);
    if (!ctx) return;

    // 1. Next Generation Token & Fingerprint (Requirement 4)
    const token = this.registry.nextGeneration(ctx);

    // 2. Atomic Cleanup of Incompatible Surfaces (Requirement 3 & 5)
    this.registry.unmountIncompatibleSurfaces(ctx);

    // 3. UI Context Consistency Assertions (Requirement 8)
    this.assertUIContextConsistency(ctx);

    // 4. Render Dynamic Navigation Tabs (Requirements 4 & 5)
    this.renderDynamicNavigationTabs(ctx);

    // 5. Render Alternative Selectors Bar strictly scoped by Capability (Requirements 1 & 9)
    this.renderAlternativeSelectors(ctx);

    // 6. Workspace Document Pipeline (Requirement 2)
    if (this.currentMode === 'plan' || this.currentMode === 'stage3_program') {
      const docType = this.currentMode === 'stage3_program' ? 'space_program' : 'plan';
      const doc = this.resolver.resolveDocument(ctx, docType);

      // Verify token freshness before committing to DOM (Requirement 4)
      if (!this.registry.isValidGeneration(token.generationId, ctx)) {
        console.warn(`[BRIF Generation Reject] Stale render generation ${token.generationId} rejected.`);
        return;
      }

      if (!doc || !this.guard.isDocumentCompatible(doc, ctx)) {
        console.warn(`[BRIF Görünüm Uyum Kontrolü] Uyumsuz veya eksik belge türü: ${docType}`);
        this.guard.renderPlanEmptyState(this.container, ctx);
        return;
      }

      // Add Payload Provenance Attributes in Dev Mode (Requirement 8)
      this.container.setAttribute('data-document-id', doc.documentId);
      this.container.setAttribute('data-project-id', doc.projectId || ctx.projectId);
      this.container.setAttribute('data-scope-fingerprint', token.fingerprint);
      this.container.setAttribute('data-render-generation', token.generationId);

      this.registry.mountSurface({
        surfaceId: `surf_${doc.documentId}`,
        documentId: doc.documentId,
        documentType: docType,
        projectId: doc.projectId || ctx.projectId,
        scopeFingerprint: token.fingerprint,
        containerId: this.container.id
      });
    }

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

    // 7. Render Capability-Based Scoped Actions Bar (Requirements 6 & 7)
    this.renderScopedActions(ctx);
  }

  // UI Context Consistency Assertion (Requirement 8)
  assertUIContextConsistency(ctx) {
    if (!ctx) return;
    const badgeEl = document.getElementById('assistantContextBadge');
    if (badgeEl) {
      badgeEl.textContent = this.hierarchy.getScopeTitle(ctx);
    }
  }

  // Scoped Alternative Selector Renderer (Requirements 1 & 9)
  renderAlternativeSelectors(activeContext) {
    const altBar = document.querySelector('.alternative-selector-bar');
    if (!altBar || !activeContext) return;

    const activeCaps = this.hierarchy.getActiveCapabilities(activeContext);

    // Alternative cards are ONLY mounted if residential_plan_alternatives capability is present!
    if (!activeCaps.includes('residential_plan_alternatives')) {
      altBar.style.display = 'none';
      altBar.innerHTML = '';
      return;
    }

    altBar.style.display = 'grid';
    altBar.innerHTML = `
      <button class="alt-tab-btn active" id="btnAltA" data-alt="a">
        <span class="alt-code">Alternatif A</span>
        <span class="alt-name">Kontrollü Ayrışma</span>
      </button>
      <button class="alt-tab-btn" id="btnAltB" data-alt="b">
        <span class="alt-code">Alternatif B</span>
        <span class="alt-name">Esnek Bağlantı</span>
      </button>
    `;
  }

  // Dynamic Navigation Tabs derived strictly from Navigable Siblings (Requirements 4 & 5)
  renderDynamicNavigationTabs(activeContext) {
    const planTabsContainer = document.getElementById('planFloorTabs');
    const programTabsContainer = document.getElementById('programFloorTabs');

    if (!activeContext) return;

    const siblings = this.hierarchy.getNavigableSiblings(activeContext);

    // ABSENCE OF SCOPED NAVIGATION MUST NEVER CAUSE FALLBACK TO ANOTHER PROJECT'S NAVIGATION!
    if (!siblings || siblings.length === 0) {
      if (planTabsContainer) planTabsContainer.innerHTML = '<span class="nav-empty-tag">Bu kapsam için alternatif seviye tanımlanmamış</span>';
      if (programTabsContainer) programTabsContainer.innerHTML = '<span class="nav-empty-tag">Bu kapsam için alternatif seviye tanımlanmamış</span>';
      return;
    }

    const tabsHtml = siblings.map(sib => `
      <button class="plan-floor-btn ${sib.isActive ? 'active' : ''}" data-entity-id="${sib.entityId}" data-entity-type="${sib.entityType}">
        ${escapeHtml(sib.displayName)}
      </button>
    `).join('');

    if (planTabsContainer) planTabsContainer.innerHTML = tabsHtml;
    if (programTabsContainer) programTabsContainer.innerHTML = tabsHtml;
  }

  // Capability-Based Scoped Actions Bar Renderer (Requirements 6 & 7)
  renderScopedActions(activeContext) {
    const demoBar = document.getElementById('demoScenariosBar');
    if (!demoBar || !activeContext) return;

    const activeCapabilities = this.hierarchy.getActiveCapabilities(activeContext);
    const docPackage = this.store.getWorkspacePackage(activeContext.projectId);

    if (!docPackage || !docPackage.scopedActions) {
      demoBar.innerHTML = '';
      return;
    }

    const validActions = docPackage.scopedActions.filter(act => {
      return this.guard.isCapabilityCompatible(act, activeCapabilities);
    });

    if (validActions.length === 0) {
      demoBar.innerHTML = '';
      return;
    }

    demoBar.innerHTML = `
      <span class="scenario-label">⚡ Kapsama Özel Demo Aksiyonları:</span>
      ${validActions.map(a => `
        <button class="scenario-btn" data-handler="${a.handler}">${escapeHtml(a.displayName)}</button>
      `).join('')}
    `;
  }

  // Simplified Single Suspended Context Top Notice Line (Requirement 10)
  renderSuspendedContextBanner(messageText) {
    if (!this.container) return;

    const bannerHtml = `
      <div class="suspended-context-line">
        <span class="suspended-icon">ℹ️</span>
        <span class="suspended-text">${escapeHtml(messageText)}</span>
        <button class="resume-context-link" id="btnResumeContext">↩ Önceki Bağlama Dön</button>
      </div>
    `;

    const existing = this.container.querySelector('.suspended-context-line');
    if (existing) existing.remove();
    this.container.insertAdjacentHTML('afterbegin', bannerHtml);
  }

  renderBreadcrumbHtml(activeContext) {
    if (!activeContext) return '';

    const ancestors = this.hierarchy.getAncestors(activeContext.entityId || activeContext.levelId || activeContext.buildingId);
    const crumbs = [];

    if (ancestors.project) crumbs.push(ancestors.project.name);
    if (ancestors.building) crumbs.push(ancestors.building.name);
    if (ancestors.level) crumbs.push(ancestors.level.name);
    if (ancestors.zone) crumbs.push(ancestors.zone.name);
    if (ancestors.entity && ancestors.entity.type === 'space') crumbs.push(ancestors.entity.name);

    if (crumbs.length === 0) return '';

    return `
      <div class="workspace-breadcrumb-bar">
        ${crumbs.map((c, i) => `
          <span class="breadcrumb-item ${i === crumbs.length - 1 ? 'active' : ''}">${escapeHtml(c)}</span>
          ${i < crumbs.length - 1 ? '<span class="breadcrumb-sep">›</span>' : ''}
        `).join('')}
      </div>
    `;
  }

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

  renderStage1Dashboard(data = {}) {
    const hasData = data.hasUserMessages || false;

    this.container.innerHTML = `
      <div class="stage1-dashboard-wrapper">
        <div class="dashboard-header-banner">
          <h3>🧠 Sizi Nasıl Anladım? (Proje DNA Özeti)</h3>
          <p>Sohbet ilerledikçe evinizin yaşam ritmi, kullanım alışkanlıkları ve öncelikleri kaynaklarıyla burada sentezlenir.</p>
        </div>

        <div class="dashboard-cards-grid">
          <div class="dna-card ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">👨‍👩‍👧‍👦</span> <strong>Hane Yapısı &amp; Düzen</strong></div>
            <p>${hasData ? '4 kişi — 2 yetişkin (ebeveyn) ve 2 okul çağında çocuk.' : 'Konuşma ilerledikçe hane yapınız burada oluşacak.'}</p>
            <div class="provenance-tag">📌 Kaynak: ${hasData ? 'Kullanıcı beyanı (Güven: Yüksek)' : 'Henüz konuşulmadı'}</div>
          </div>

          <div class="dna-card ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">⏰</span> <strong>Günlük Kullanım Ritmi</strong></div>
            <p>${hasData ? '16:00 sonrası çocuk kullanım yoğunluğu, gündüz online toplantılar.' : 'Günlük zaman akışınız sohbetle buraya yansıyacak.'}</p>
            <div class="provenance-tag">📌 Kaynak: ${hasData ? 'Kullanıcı beyanı (Güven: Yüksek)' : 'Henüz konuşulmadı'}</div>
          </div>

          <div class="dna-card highlight ${hasData ? 'updated' : ''}">
            <div class="dna-card-header"><span class="dna-icon">🛡️</span> <strong>Mahremiyet Öncelikleri</strong></div>
            <p>${hasData ? 'Evden çalışma sırasında yüksek akustik ayrışma ve ses izolasyonu.' : 'Mahremiyet tercihleriniz sohbetle buraya işlenecek.'}</p>
            <div class="provenance-tag">📌 Kaynak: ${hasData ? 'Doğrudan kullanıcı talebi' : 'Demo proje varsayımı'}</div>
          </div>

          <div class="dna-card pending">
            <div class="dna-card-header"><span class="dna-icon">❓</span> <strong>Henüz Netleşmeyenler</strong></div>
            <p>${hasData ? 'Ebeveyn banyosu kapı açılımı ve giyinme odası sıralaması.' : 'Henüz konuşulmayan noktalar burada listelenecek.'}</p>
          </div>

          <div class="dna-card project-dna">
            <div class="dna-card-header"><span class="dna-icon">🧬</span> <strong>Proje DNA Özeti</strong></div>
            <p><strong>Aile odaklı • Kontrollü ayrışma • Dönüşebilir mekânlar</strong></p>
            <div class="provenance-tag">🏷️ Demo proje varsayımı</div>
          </div>
        </div>
      </div>
    `;
  }

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
          <div class="option-card ${selected === 1 ? 'selected' : ''}" id="optionCard1">
            <div class="opt-badge">Seçenek 1</div>
            <h4>Banyoyu Kuzeye Taşımak</h4>

            <div class="opt-plan-mini">
              <svg viewBox="0 0 340 180" width="100%" height="150">
                <rect width="340" height="180" fill="#F8FAFC" stroke="#E2E8F0" rx="6"/>
                <rect x="20" y="20" width="140" height="140" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
                <text x="90" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <rect x="20" y="100" width="60" height="50" fill="none" stroke="#DC2626" stroke-width="1.5" stroke-dasharray="3 3"/>
                <text x="50" y="125" font-size="9" fill="#DC2626" font-weight="700" text-anchor="middle">Eski Banyo</text>
                <rect x="175" y="20" width="60" height="140" fill="#F3E8FF" stroke="#7E22CE" stroke-width="1.5" rx="4"/>
                <text x="205" y="90" font-size="10" font-weight="700" fill="#6B21A8" text-anchor="middle" transform="rotate(-90 205 90)">Giyinme</text>
                <rect x="245" y="20" width="80" height="140" fill="#F0FDF4" stroke="#166534" stroke-width="2.5" rx="4"/>
                <text x="285" y="80" font-size="10" font-weight="800" fill="#14532D" text-anchor="middle" transform="rotate(-90 285 80)">Kuzey Banyo</text>
              </svg>
            </div>

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

            <div class="opt-actions">
              <button class="opt-btn primary" id="btnApplyOpt1">${selected === 1 ? '✅ Uygulandı (Seçenek 1)' : '1. Seçeneği Uygula'}</button>
            </div>
          </div>

          <div class="option-card ${selected === 2 ? 'selected' : ''}" id="optionCard2">
            <div class="opt-badge secondary">Seçenek 2</div>
            <h4>Konumu Koru, Giriş Yönünü Değiştir</h4>

            <div class="opt-plan-mini">
              <svg viewBox="0 0 340 180" width="100%" height="150">
                <rect width="340" height="180" fill="#F8FAFC" stroke="#E2E8F0" rx="6"/>
                <rect x="20" y="20" width="170" height="140" fill="#EFF6FF" stroke="#2563EB" stroke-width="2" rx="4"/>
                <text x="105" y="80" font-size="11" font-weight="700" fill="#1E40AF" text-anchor="middle">Yatak Odası</text>
                <rect x="200" y="50" width="120" height="110" fill="#FEF3C7" stroke="#D97706" stroke-width="2" rx="4"/>
                <text x="260" y="105" font-size="10" font-weight="700" fill="#B45309" text-anchor="middle">Giyinmeden Girişli Banyo</text>
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

  renderFloorOverlayMode(data = {}) {
    this.container.innerHTML = `
      <div class="overlay-mode-wrapper">
        <div class="overlay-header-bar">
          <span class="overlay-tag">🏢 Kat İlişkisi Anlatım Modu</span>
          <p>Plan üzerinde kısa kodlar gösterilmektedir. Açıklamalar sağ paneldedir.</p>
        </div>

        <div class="overlay-readable-grid">
          <div class="overlay-svg-container">
            <svg viewBox="0 0 600 400" width="100%" height="100%" id="alignedOverlaySvg">
              <rect width="600" height="400" rx="8" fill="#FFFFFF" stroke="#CBD5E1"/>

              <g class="ground-plan" style="opacity:0.28; fill:#E2E8F0; stroke:#64748B; stroke-width:2; stroke-dasharray:4 4;">
                <rect x="40" y="60" width="220" height="260" rx="4"/>
                <text x="150" y="190" font-size="14" font-weight="800" fill="#475569" text-anchor="middle">Z1</text>
              </g>

              <g class="upper-plan" style="fill:none; stroke:#0F172A; stroke-width:3;">
                <rect x="40" y="60" width="340" height="260" rx="4"/>
                <rect x="240" y="60" width="140" height="110" rx="4" fill="#E0F2FE" stroke="#0284C7" stroke-width="2"/>
                <text x="310" y="120" font-size="14" font-weight="800" fill="#0369A1" text-anchor="middle">Ü1</text>

                <rect x="420" y="160" width="120" height="160" rx="4" fill="#FEF08A" stroke="#CA8A04" stroke-width="2.5"/>
                <text x="480" y="240" font-size="14" font-weight="800" fill="#854D0E" text-anchor="middle">M1</text>
              </g>

              <line x1="310" y1="40" x2="310" y2="180" stroke="#0284C7" stroke-width="2.5" stroke-dasharray="6 3"/>
              <text x="320" y="52" font-size="11" font-weight="800" fill="#0284C7">T1</text>
            </svg>
          </div>

          <div class="overlay-legend-panel">
            <h4 class="legend-panel-title">📌 Kat İlişkisi Kod Açıklamaları</h4>
            <ul class="legend-code-list">
              <li><strong class="code-badge zemin">Z1</strong> Zemin kat servis/ıslak hacim çekirdeği</li>
              <li><strong class="code-badge ust">Ü1</strong> Üst kat ebeveyn banyosu</li>
              <li><strong class="code-badge merdiven">M1</strong> Merdiven / düşey boşluk</li>
              <li><strong class="code-badge tesisat">T1</strong> Yaklaşık düşey tesisat aksı</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }

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
            <rect x="50" y="40" width="740" height="28" fill="#DBEAFE" rx="4"/>
            <text x="420" y="58" font-size="11.5" font-weight="800" fill="#1E40AF" text-anchor="middle">KUZEY CEPHE (SERVİS ALANLARI)</text>
            <rect x="50" y="470" width="740" height="28" fill="#FEF3C7" rx="4"/>
            <text x="420" y="488" font-size="11.5" font-weight="800" fill="#B45309" text-anchor="middle">GÜNEY CEPHE (SALON &amp; TERAS)</text>
            <rect x="70" y="80" width="700" height="380" fill="none" stroke="#1E293B" stroke-width="4" rx="6"/>
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
