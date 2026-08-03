/**
 * BRIF.AI — Change History & Scoped Architect Report Renderer (v6.1.2 Refined)
 *
 * Enforces scope compatibility via RenderCompatibilityGuard before rendering decision reports.
 * Displays human-readable scope breadcrumb instead of raw technical IDs.
 * Guarantees no rejected render path ends in an unexplained blank container.
 */

class ChangeHistory {
  constructor(options = {}) {
    this.hierarchy = options.hierarchy || new EntityHierarchy();
    this.store = options.store || new ScopedDocumentStore();
    this.resolver = options.resolver || new WorkspaceScopeResolver(this.hierarchy, this.store);
    this.guard = options.guard || new RenderCompatibilityGuard(this.hierarchy);
    this.sessionState = null;
  }

  setSessionState(state) {
    this.sessionState = state ? {
      ...state,
      workspaceScope: state.workspaceScope ? { ...state.workspaceScope } : null,
      conversationScope: state.conversationScope ? { ...state.conversationScope } : null
    } : null;
  }

  // Scoped Decision Report Renderer (Requirements 3, 9, 11 & 12)
  renderArchitectReport(activeSnapshot = null) {
    const st = activeSnapshot || this.sessionState;
    const container = document.getElementById('architectDecisionHistory');

    if (!st) {
      if (container) {
        container.replaceChildren();
        const empty = document.createElement('div');
        empty.className = 'empty-state-workspace-card report-empty';
        empty.textContent = 'Karar raporu için aktif bir proje kapsamı bulunmuyor.';
        container.appendChild(empty);
        return container.innerHTML;
      }
      return '';
    }

    const doc = this.resolver.resolveDocument(st, 'architect_report');

    // If report is missing or incompatible with activeContext (Requirement 3: NO BLANK REPORT AREA)
    if (!doc || !this.guard.isDocumentCompatible(doc, st)) {
      if (container) {
        const entity = this.hierarchy.findEntity(st.entityId);
        const reportTitle = entity ? `${entity.name} Kararı` : 'Aktif Kapsam Kararı';
        this.guard.renderReportEmptyState(container, st, reportTitle);
        return container.innerHTML;
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

    const html = `
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

    if (container) {
      container.innerHTML = html;
    }

    return html;
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
