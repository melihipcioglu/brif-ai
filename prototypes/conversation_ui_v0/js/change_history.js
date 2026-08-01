/**
 * BRIF.AI — Change History & Scoped Architect Report Renderer (v6.1.1 Refined)
 *
 * Enforces scope compatibility via RenderCompatibilityGuard before rendering decision reports.
 * Displays human-readable scope breadcrumb instead of raw technical IDs.
 */

class ChangeHistory {
  constructor() {
    this.hierarchy = new EntityHierarchy();
    this.store = new ScopedDocumentStore();
    this.resolver = new WorkspaceScopeResolver(this.hierarchy, this.store);
    this.guard = new RenderCompatibilityGuard(this.hierarchy);

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

  // Scoped Decision Report Renderer (Requirements 3 & 11)
  renderArchitectReport() {
    const st = this.sessionState;
    const doc = this.resolver.resolveDocument(st, 'architect_report');

    // If report is missing or incompatible with activeContext (Requirement 3)
    if (!doc || !this.guard.isDocumentCompatible(doc, st)) {
      console.warn(`[BRIF Scope Violation] Report scope mismatch for active context: ${st.levelId || st.projectId}`);
      
      const container = document.getElementById('architectDecisionHistory');
      if (container) {
        this.guard.renderReportEmptyState(container, st, "Çalışma Odası Kararı");
      }
      return '';
    }

    const payload = doc.payload || {};
    const ancestors = this.hierarchy.getAncestors(doc.entityId || doc.levelId || doc.buildingId);
    const crumbs = [];

    if (ancestors.project) crumbs.push(ancestors.project.name);
    if (ancestors.building) crumbs.push(ancestors.building.name);
    if (ancestors.level) crumbs.push(ancestors.level.name);
    if (ancestors.zone) crumbs.push(ancestors.zone.name);
    if (ancestors.entity) crumbs.push(ancestors.entity.name);

    const humanBreadcrumb = crumbs.join(' › ');

    return `
      <div class="architect-decision-summary-grid">
        <div class="arch-decision-card highlight">
          <div class="arch-card-header">
            <span class="decision-num">${escapeHtml(payload.title || doc.displayName)}</span>
            <span class="status-badge mandatory">${escapeHtml(payload.status || 'Uygulandı')}</span>
          </div>

          <div class="decision-section">
            <strong>1. Kullanıcının İlk Talebi:</strong>
            <p>"${escapeHtml(payload.userRequest || 'Evden çalışma ve toplantı alanı.')}"</p>
          </div>

          <div class="decision-section">
            <strong>2. Sistemin Mimari Yorumu:</strong>
            <p>${escapeHtml(payload.interpretation || 'Yüksek akustik izolasyonlu çalışma düzeni.')}</p>
          </div>

          <div class="decision-section">
            <strong>3. Kullanıcının Kararı:</strong>
            <p class="user-choice-highlight">${escapeHtml(payload.decision || 'Uygulandı')}</p>
          </div>

          <div class="decision-meta-row">
            <span><strong>Kapsam:</strong> ${escapeHtml(humanBreadcrumb)}</span> • 
            <span><strong>Kaynak:</strong> ${escapeHtml(payload.meta ? payload.meta.source : 'Doğrudan beyan')}</span> • 
            <span><strong>Güven:</strong> Yüksek</span>
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
