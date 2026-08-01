/**
 * BRIF.AI — Render Compatibility Guard (v6.1.1 Universal Platform Architecture)
 *
 * Core architectural guard enforcing:
 * "Every rendered workspace artifact must be resolved and validated against the active workspace scope before it enters the DOM."
 *
 * Bypassing this guard logs [BRIF Scope Violation] in dev mode.
 */

class RenderCompatibilityGuard {
  constructor(hierarchy) {
    this.hierarchy = hierarchy || new EntityHierarchy();
  }

  // Universal Document Compatibility Validator (Requirement 5)
  isDocumentCompatible(doc, activeContext) {
    if (!doc || !activeContext) {
      console.warn('[BRIF Scope Violation] Null document or active context passed to guard.');
      return false;
    }

    // Status must be available
    if (doc.status !== 'available') return false;

    // Scope check: Project ID
    const docProj = doc.scope ? doc.scope.projectId : doc.projectId;
    if (docProj && docProj !== activeContext.projectId) return false;

    // Scope check: Building ID
    const docBldg = doc.scope ? doc.scope.buildingId : doc.buildingId;
    if (docBldg && activeContext.buildingId && docBldg !== activeContext.buildingId) return false;

    // Scope check: Level ID
    const docLvl = doc.scope ? doc.scope.levelId : doc.levelId;
    if (docLvl && activeContext.levelId && docLvl !== activeContext.levelId) return false;

    // Scope check: Zone ID
    const docZone = doc.scope ? doc.scope.zoneId : doc.zoneId;
    if (docZone && activeContext.zoneId && docZone !== activeContext.zoneId) return false;

    // Scope check: Entity ID
    const docEnt = doc.scope ? doc.scope.entityId : doc.entityId;
    if (docEnt && activeContext.entityId && docEnt !== activeContext.entityId) return false;

    // Scope check: Decision ID (For Decision Reports)
    const docDec = doc.scope ? doc.scope.decisionId : doc.decisionId;
    if (docDec && activeContext.decisionId && docDec !== activeContext.decisionId) return false;

    return true;
  }

  // General Honest Empty State Renderer
  renderEmptyState(container, activeContext, scopeTitle) {
    if (!container) return;
    container.innerHTML = ''; // Clear stale DOM content immediately

    const title = scopeTitle || this.hierarchy.getScopeTitle(activeContext);

    container.innerHTML = `
      <div class="empty-state-workspace-card">
        <div class="empty-state-icon">📂</div>
        <h3 class="empty-state-title">Bu kapsam için çalışma alanı verisi bulunmuyor</h3>
        <p class="empty-state-desc">
          Şu anda <strong>${escapeHtml(title)}</strong> için şematik plan veya belge verisi tanımlanmamış. Önceki görünümün verileri bu görünümde kullanılmayacaktır.
        </p>

        <div class="empty-state-actions">
          <button class="empty-act-btn" id="btnEmptyShowUpper">Üst Kapsamı Göster</button>
          <button class="empty-act-btn" id="btnEmptySelectLevel">Başka Kat Seç</button>
          <button class="empty-act-btn highlight" id="btnResumeContext">↩ Önceki Bağlama Dön</button>
        </div>
      </div>
    `;
  }

  // Architect Report Specific Empty State Renderer (Requirement 3)
  renderReportEmptyState(container, activeContext, incompatibleReportTitle) {
    if (!container) return;
    container.innerHTML = '';

    const title = this.hierarchy.getScopeTitle(activeContext);
    const incTitle = incompatibleReportTitle ? ` (${incompatibleReportTitle})` : '';

    container.innerHTML = `
      <div class="empty-state-workspace-card report-empty">
        <div class="empty-state-icon">📜</div>
        <h3 class="empty-state-title">Bu aktif kapsam için mimar karar raporu bulunmuyor</h3>
        <p class="empty-state-desc">
          Şu anda <strong>${escapeHtml(title)}</strong> kapsamındasınız. Başka bir kapsama ait mimar kararları${escapeHtml(incTitle)} bu görünümle uyumlu olmadığı için gösterilmiyor.
        </p>

        <div class="empty-state-actions">
          <button class="empty-act-btn highlight" id="btnShowScopeDecisions">Aktif Kapsamdaki Kararları Göster</button>
          <button class="empty-act-btn" id="btnResumeContext">Önceki Karara Dön</button>
          <button class="empty-act-btn" id="btnOpenAllProjectDecisions">Tüm Proje Kararlarını Aç</button>
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
window.RenderCompatibilityGuard = RenderCompatibilityGuard;
