/**
 * BRIF.AI — Surface & Scope Compatibility Guard (v6.1.2 Platform Architecture)
 *
 * Core architectural principle:
 * "Every visible workspace surface must be resolved from the active scope and its capabilities."
 *
 * Ensures no rejected render path ends in an unexplained blank container.
 */

class RenderCompatibilityGuard {
  constructor(hierarchy) {
    this.hierarchy = hierarchy || new EntityHierarchy();
  }

  // Universal Document & Surface Scope Compatibility Validator (Requirements 1 & 2)
  isDocumentCompatible(doc, activeContext) {
    if (!doc || !activeContext) {
      console.warn('[BRIF Görünüm Uyum Kontrolü] Geçersiz belge veya aktif kapsam.');
      return false;
    }

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

  // Capability Compatibility Validator (Requirement 6)
  isCapabilityCompatible(action, activeCapabilities) {
    if (!action) return false;
    const reqCaps = action.requiredCapabilities || [];
    if (reqCaps.length === 0) return true;

    return reqCaps.every(cap => activeCapabilities.includes(cap));
  }

  // Context-Derived Explicit Empty State Renderer (Requirements 3 & 9)
  renderEmptyState(container, activeContext, scopeTitle) {
    if (!container) return;
    container.innerHTML = ''; // Clear stale content immediately

    const title = scopeTitle || this.hierarchy.getScopeTitle(activeContext);

    container.innerHTML = `
      <div class="empty-state-workspace-card">
        <div class="empty-state-icon">📂</div>
        <h3 class="empty-state-title">Bu kapsam için çalışma alanı verisi bulunmuyor</h3>
        <p class="empty-state-desc">
          Şu anda <strong>${escapeHtml(title)}</strong> kapsamındasınız. Bu kapsamla uyumlu şematik plan veya belge verisi tanımlanmamış. Başka projeye ait plan kullanılmayacaktır.
        </p>

        <div class="empty-state-actions">
          <button class="empty-act-btn" id="btnEmptyShowUpper">Üst Kapsamı Göster</button>
          <button class="empty-act-btn" id="btnEmptySelectLevel">Başka Kat Seç</button>
          <button class="empty-act-btn highlight" id="btnResumeContext">↩ Önceki Bağlama Dön</button>
        </div>
      </div>
    `;
  }

  // Architect Decision Report Specific Explicit Empty State Renderer (Requirements 3 & 9)
  renderReportEmptyState(container, activeContext, incompatibleReportTitle) {
    if (!container) return;
    container.innerHTML = ''; // Clear container — NO BLANK CONTAINERS!

    const title = this.hierarchy.getScopeTitle(activeContext);
    const incTitle = incompatibleReportTitle ? ` (${incompatibleReportTitle})` : '';

    container.innerHTML = `
      <div class="empty-state-workspace-card report-empty" id="reportEmptyStateContainer">
        <div class="empty-state-icon">📜</div>
        <h3 class="empty-state-title">Bu aktif kapsam için mimar karar raporu bulunmuyor</h3>
        <p class="empty-state-desc">
          Şu anda <strong>${escapeHtml(title)}</strong> kapsamındasınız. Mevcut mimar kararları${escapeHtml(incTitle)} farklı bir kapsama ait olduğu için gösterilmiyor.
        </p>

        <div class="empty-state-actions">
          <button class="empty-act-btn highlight" id="btnShowScopeDecisions">Bu Kapsamdaki Kararları Göster</button>
          <button class="empty-act-btn" id="btnOpenAllProjectDecisions">Tüm Proje Kararlarını Aç</button>
          <button class="empty-act-btn" id="btnResumeContext">Önceki Karara Dön</button>
          <button class="empty-act-btn" id="btnReturnToCustomerView">Müşteri Görünümüne Dön</button>
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
