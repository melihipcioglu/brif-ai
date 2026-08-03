/**
 * BRIF.AI — Workspace Presenter & Surface Engine (v6.2 Platform Architecture)
 *
 * Scope-driven presenter resolving candidate documents and workspace surfaces strictly from ActiveContextSnapshot.
 * Enforces:
 * 1. Single Snapshot Source for all 14 workspace surfaces
 * 2. Fingerprint & Generation Token Guarding before DOM commit
 * 3. Contextual Chat Input Placeholder (Residential vs Tower vs Campus)
 * 4. Full House Plan Restoration (SVG, alternatives, spaces, capabilities)
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

    // 1. Next Generation Token & Fingerprint
    const token = this.registry.nextGeneration(ctx);

    // 2. Atomic Cleanup of Incompatible Surfaces from DOM Registry
    this.registry.unmountIncompatibleSurfaces(ctx);

    // 3. Render Assistant Badge & Header Info strictly from Snapshot (Requirement 2)
    this.assertUIContextConsistency(ctx);

    // 4. Render Contextual Chat Input Placeholder (Requirement 5)
    this.renderContextualChatPlaceholder(ctx);

    // 5. Render Dynamic Navigation Tabs strictly from Snapshot (Requirements 1, 2 & 6)
    this.renderDynamicNavigationTabs(ctx);

    // 6. Render Alternative Selectors Bar strictly scoped by Snapshot Capabilities (Requirements 2 & 4)
    this.renderAlternativeSelectors(ctx);

    // 7. Workspace Document Pipeline & Explicit Empty State (Requirements 1, 2 & 6)
    if (this.currentMode === 'plan' || this.currentMode === 'stage3_program') {
      const docType = this.currentMode === 'stage3_program' ? 'space_program' : 'plan';
      const doc = this.resolver.resolveDocument(ctx, docType);

      // Verify token freshness and fingerprint match before committing to DOM (Requirement 3)
      if (!this.registry.isValidGeneration(token.generationId, ctx)) {
        console.warn(`[BRIF Generation Reject] Stale render generation ${token.generationId} rejected.`);
        return;
      }

      // Check if document exists, is compatible, AND has renderable SVG plan payload
      const hasRenderablePlan = doc && doc.data && (doc.data.rawSvg || doc.data.svgPath || doc.projectId === 'proj_house_2story');

      if (!doc || !this.guard.isDocumentCompatible(doc, ctx) || !hasRenderablePlan) {
        console.warn(`[BRIF Görünüm Uyum Kontrolü] Uyumsuz veya render edilebilir planı bulunmayan belge türü: ${docType}`);
        this.renderWorkspaceEmptyState({
          activeContext: ctx,
          requestedDocumentType: docType,
          generationId: token.generationId
        });
        return;
      }

      // Restore Full Interactive House Plan (Requirement 7)
      if (ctx.projectId === 'proj_house_2story' && window.appPlanEditor) {
        window.appPlanEditor.render();
      }

      // Add Payload Provenance Attributes in Dev Mode
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

    // 8. Render Capability-Based Scoped Actions Bar (Requirement 4)
    this.renderScopedActions(ctx);
  }

  renderVisualPreferences(activeContext) {
    if (!this.container || !activeContext) return null;

    const token = this.registry.nextGeneration(activeContext);
    this.registry.unmountIncompatibleSurfaces(activeContext);
    this.container.replaceChildren();
    this.container.removeAttribute('data-document-id');
    this.container.removeAttribute('data-project-id');
    this.container.removeAttribute('data-scope-fingerprint');
    this.container.removeAttribute('data-render-generation');

    const doc = this.resolver.resolveDocument(activeContext, 'visual_preferences');
    const templateId = doc && doc.data ? doc.data.templateId : null;
    const template = templateId ? document.getElementById(templateId) : null;

    if (
      !doc ||
      !this.guard.isDocumentCompatible(doc, activeContext) ||
      !template ||
      !template.content
    ) {
      this.renderVisualPreferencesEmptyState(activeContext, token);
      return null;
    }

    if (!this.registry.isValidGeneration(token.generationId, activeContext)) {
      console.warn(`[BRIF Generation Reject] Stale visual preference render ${token.generationId} rejected.`);
      return null;
    }

    this.container.appendChild(template.content.cloneNode(true));
    this.applyVisualPreferenceSnapshot(activeContext);
    this.container.setAttribute('data-document-id', doc.documentId);
    this.container.setAttribute('data-project-id', doc.projectId);
    this.container.setAttribute('data-scope-fingerprint', token.fingerprint);
    this.container.setAttribute('data-render-generation', token.generationId);

    this.registry.mountSurface({
      surfaceId: `surf_${doc.documentId}`,
      documentId: doc.documentId,
      documentType: 'visual_preferences',
      projectId: doc.projectId,
      scopeFingerprint: token.fingerprint,
      containerId: this.container.id
    });

    return doc;
  }

  bindVisualPreferenceInteractions(options = {}) {
    if (!this.container || this.visualPreferenceClickHandler) return false;
    if (!options.stateMachine || typeof options.stateMachine.dispatch !== 'function') return false;

    this.visualPreferenceStateMachine = options.stateMachine;
    this.visualPreferenceStageChange = options.onStageChange || null;
    this.visualPreferenceClickHandler = event => {
      this.handleVisualPreferenceInteraction(event);
    };
    this.container.addEventListener('click', this.visualPreferenceClickHandler);
    return true;
  }

  handleVisualPreferenceInteraction(event) {
    const target = event && event.target;
    if (!target || typeof target.closest !== 'function') return false;

    const stateMachine = this.visualPreferenceStateMachine;
    if (!stateMachine) return false;

    const activeContext = stateMachine.getSnapshot();
    const renderedProjectId = this.container.getAttribute('data-project-id');
    const doc = this.resolver.resolveDocument(activeContext, 'visual_preferences');
    if (
      renderedProjectId !== activeContext.projectId ||
      !doc ||
      !this.guard.isDocumentCompatible(doc, activeContext)
    ) {
      return false;
    }

    const preferenceButton = target.closest('.pref-btn-primary, .pref-btn-secondary');
    if (preferenceButton && this.container.contains(preferenceButton)) {
      const card = preferenceButton.closest('.pref-card-large');
      const roundContainer = card ? card.closest('.pref-round-container') : null;
      const roundId = roundContainer ? roundContainer.dataset.round : null;
      const cardId = card ? card.dataset.cardId : null;
      const preference = preferenceButton.dataset.action;
      if (!roundId || !cardId || !['like', 'neutral'].includes(preference)) return false;

      stateMachine.dispatch({
        type: 'VISUAL_PREFERENCE_RECORDED',
        payload: {
          projectId: activeContext.projectId,
          roundId,
          cardId,
          preference
        }
      });
      return true;
    }

    const roundTab = target.closest('.round-tab');
    if (roundTab && this.container.contains(roundTab)) {
      const roundId = roundTab.dataset.round;
      if (!roundId) return false;
      stateMachine.dispatch({
        type: 'VISUAL_PREFERENCE_ROUND_SELECTED',
        payload: {
          projectId: activeContext.projectId,
          roundId
        }
      });
      return true;
    }

    const nextButton = target.closest('#btnNextToProgram');
    if (nextButton && this.container.contains(nextButton)) {
      if (typeof this.visualPreferenceStageChange === 'function') {
        this.visualPreferenceStageChange(3);
      } else {
        stateMachine.dispatch({
          type: 'STAGE_CHANGED',
          payload: { activeStage: 3 }
        });
      }
      return true;
    }

    return false;
  }

  applyVisualPreferenceSnapshot(activeContext) {
    if (!this.container || !activeContext) return;

    const preferencesByProject = activeContext.visualPreferencesByProject || {};
    const projectPreferences = preferencesByProject[activeContext.projectId] || {};
    const roundTabs = Array.from(this.container.querySelectorAll('.round-tab'));
    const roundContainers = Array.from(
      this.container.querySelectorAll('.pref-round-container')
    );
    const activeRoundId = projectPreferences.activeRoundId ||
      (roundTabs[0] ? roundTabs[0].dataset.round : null);

    roundTabs.forEach(tab => {
      const isActive = tab.dataset.round === activeRoundId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', String(isActive));
    });

    let activeRoundExists = false;
    roundContainers.forEach(roundContainer => {
      const isActive = roundContainer.dataset.round === activeRoundId;
      activeRoundExists = activeRoundExists || isActive;
      roundContainer.classList.toggle('active', isActive);
      roundContainer.classList.toggle('hidden', !isActive);
    });

    const roundContent = this.container.querySelector('[data-pref-round-content]');
    if (roundContent) {
      roundContent.querySelectorAll('.preference-round-empty').forEach(element => element.remove());
      if (activeRoundId && !activeRoundExists) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state-workspace-card preference-round-empty';
        const title = document.createElement('h3');
        title.className = 'empty-state-title';
        title.textContent = 'Bu tur henüz tanımlanmadı.';
        emptyState.appendChild(title);
        roundContent.appendChild(emptyState);
      }
    }

    const roundSelections = projectPreferences.rounds || {};
    this.container.querySelectorAll('.pref-card-large').forEach(card => {
      const roundContainer = card.closest('.pref-round-container');
      const roundId = roundContainer ? roundContainer.dataset.round : null;
      const selection = roundId ? roundSelections[roundId] : null;
      const isSelected = Boolean(selection && selection.cardId === card.dataset.cardId);
      const preference = isSelected ? selection.preference : null;

      card.classList.toggle('preference-selected', preference === 'like');
      card.classList.toggle('preference-neutral', preference === 'neutral');
      card.removeAttribute('data-preference-status');
      card.querySelectorAll('.pref-selection-status').forEach(element => element.remove());

      card.querySelectorAll('.pref-btn-primary, .pref-btn-secondary').forEach(button => {
        button.setAttribute(
          'aria-pressed',
          String(isSelected && button.dataset.action === preference)
        );
      });

      if (preference) {
        card.setAttribute('data-preference-status', preference);
        const status = document.createElement('div');
        status.className = 'pref-selection-status';
        status.textContent = preference === 'like' ? 'Seçildi' : 'Kararsız';
        card.appendChild(status);
      }
    });
  }

  renderVisualPreferencesEmptyState(activeContext, token) {
    if (!this.container || !activeContext) return;

    this.container.replaceChildren();

    const scrollArea = document.createElement('div');
    scrollArea.className = 'pref-scroll-area';

    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state-workspace-card visual-preferences-empty';

    const icon = document.createElement('div');
    icon.className = 'empty-state-icon';
    icon.textContent = '🖼️';

    const title = document.createElement('h3');
    title.className = 'empty-state-title';
    title.textContent = 'Bu proje türü için görsel tercih seti henüz tanımlanmadı.';

    const description = document.createElement('p');
    description.className = 'empty-state-desc';
    description.textContent = 'Konut projesine ait tercihler bu kapsamda gösterilmez.';

    emptyState.append(icon, title, description);
    scrollArea.appendChild(emptyState);
    this.container.appendChild(scrollArea);

    const fingerprint = token ? token.fingerprint : this.registry.getScopeFingerprint(activeContext);
    const generationId = token ? token.generationId : this.registry.currentGenerationId;
    const documentId = `doc_visual_preferences_empty_${activeContext.projectId}`;

    this.container.setAttribute('data-document-id', documentId);
    this.container.setAttribute('data-project-id', activeContext.projectId);
    this.container.setAttribute('data-scope-fingerprint', fingerprint);
    this.container.setAttribute('data-render-generation', generationId);

    this.registry.mountSurface({
      surfaceId: `surf_${documentId}`,
      documentId: documentId,
      documentType: 'empty_state',
      projectId: activeContext.projectId,
      scopeFingerprint: fingerprint,
      containerId: this.container.id
    });
  }

  // Unified Workspace Empty State Surface Renderer (Requirements 1, 2 & 6)
  renderWorkspaceEmptyState(params = {}) {
    const activeContext = params.activeContext;
    if (!this.container || !activeContext) return;

    const token = params.generationId || (this.registry ? this.registry.currentGenerationId : 0);
    const fp = this.registry ? this.registry.getScopeFingerprint(activeContext) : '';

    this.guard.renderPlanEmptyState(this.container, activeContext, {
      generationId: token,
      scopeFingerprint: fp
    });

    if (this.registry) {
      this.registry.mountSurface({
        surfaceId: `surf_empty_state_${activeContext.projectId}_${activeContext.levelId || 'proj'}`,
        documentId: `doc_empty_state_${activeContext.projectId}`,
        documentType: 'empty_state',
        projectId: activeContext.projectId,
        scopeFingerprint: fp,
        containerId: this.container.id
      });
    }
  }

  // Contextual Chat Input Placeholder Renderer (Requirement 5)
  renderContextualChatPlaceholder(activeContext) {
    const inputEl = document.getElementById('assistantUserInput');
    if (!inputEl || !activeContext) return;

    const projId = activeContext.projectId;

    if (projId === 'proj_house_2story') {
      inputEl.placeholder = "Örn. Ebeveyn banyosunun girişini giyinme alanından yapalım.";
    } else if (projId === 'proj_tower_50floor') {
      inputEl.placeholder = "Örn. Toplantı odasını yönetim çekirdeğine yaklaştıralım.";
    } else if (projId === 'proj_campus_multiblock') {
      inputEl.placeholder = "Örn. Numune hazırlama alanını servis girişine yaklaştıralım.";
    } else {
      inputEl.placeholder = "Mimari ihtiyacınızı veya değiştirmek istediğiniz kararı yazın.";
    }
  }

  // UI Context Consistency Assertion (Requirement 2)
  assertUIContextConsistency(ctx) {
    if (!ctx) return;

    // Update Header Synthetic Select Dropdown
    const projectSelect = document.getElementById('syntheticProjectSelect');
    if (projectSelect && projectSelect.value !== ctx.projectId) {
      projectSelect.value = ctx.projectId;
    }

    // Update Assistant Scope Badge
    const badgeEl = document.getElementById('assistantContextBadge');
    if (badgeEl) {
      badgeEl.textContent = this.hierarchy.getScopeTitle(ctx);
    }
  }

  // Scoped Alternative Selector Renderer (Requirements 2 & 4)
  renderAlternativeSelectors(activeContext) {
    const altBar = document.querySelector('.alternative-selector-bar');
    if (!altBar || !activeContext) return;

    const activeCaps = activeContext.capabilities || this.hierarchy.getActiveCapabilities(activeContext);

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

  // Dynamic Navigation Tabs derived strictly from Navigable Siblings & Snapshot
  renderDynamicNavigationTabs(activeContext) {
    const planTabsContainer = document.getElementById('planFloorTabs');
    const programTabsContainer = document.getElementById('programFloorTabs');

    if (!activeContext) return;

    const siblings = this.hierarchy.getNavigableSiblings(activeContext);

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

  // Capability-Based Scoped Actions Bar Renderer (Requirement 4)
  renderScopedActions(activeContext) {
    const demoBar = document.getElementById('demoScenariosBar');
    if (!demoBar || !activeContext) return;

    const activeCapabilities = activeContext.capabilities || this.hierarchy.getActiveCapabilities(activeContext);
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

  // Simplified Single Suspended Context Top Notice Line
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
