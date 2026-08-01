/**
 * BRIF.AI — Render Compatibility Guard (v6.1 Platform Architecture)
 *
 * Core architectural guard enforcing:
 * "No workspace content may render unless its document scope is compatible with the active context."
 * Clears stale DOM content and renders honest empty states when compatibility fails.
 */

class RenderCompatibilityGuard {
  constructor(hierarchy) {
    this.hierarchy = hierarchy || new EntityHierarchy();
  }

  isDocumentCompatible(doc, activeContext) {
    if (!doc || !activeContext) return false;

    // 1. Status must be available
    if (doc.status !== 'available') return false;

    // 2. Project ID must match
    if (doc.projectId !== activeContext.projectId) return false;

    // 3. If buildingId defined on doc, must match activeContext
    if (doc.buildingId && activeContext.buildingId && doc.buildingId !== activeContext.buildingId) {
      return false;
    }

    // 4. If levelId defined on doc, must match activeContext
    if (doc.levelId && activeContext.levelId && doc.levelId !== activeContext.levelId) {
      return false;
    }

    // 5. If zoneId defined on doc, must match activeContext
    if (doc.zoneId && activeContext.zoneId && doc.zoneId !== activeContext.zoneId) {
      return false;
    }

    // 6. If entityId defined on doc, must match activeContext
    if (doc.entityId && activeContext.entityId && doc.entityId !== activeContext.entityId) {
      return false;
    }

    return true;
  }

  // Render Honest Empty State Component (Requirement 6)
  renderEmptyState(container, activeContext, scopeTitle) {
    if (!container) return;

    // Clear stale DOM content immediately — no leftover plans!
    container.innerHTML = '';

    const title = scopeTitle || this.hierarchy.getScopeTitle(activeContext);

    const emptyHtml = `
      <div class="empty-state-workspace-card">
        <div class="empty-state-icon">📂</div>
        <h3 class="empty-state-title">Bu kapsam için çalışma alanı verisi bulunmuyor</h3>
        <p class="empty-state-desc">
          Şu anda <strong>${escapeHtml(title)}</strong> için şematik plan veya belge verisi tanımlanmamış. Önceki görünümün verileri bu görünümde kullanılmayacaktır.
        </p>

        <div class="empty-state-actions">
          <button class="empty-act-btn" id="btnEmptyShowUpper">Üst Kapsamı Göster</button>
          <button class="empty-act-btn" id="btnEmptySelectLevel">Başka Kat Seç</button>
          <button class="empty-act-btn disabled" title="Prototip demo aksiyonu">Belge Ekle (Demo)</button>
          <button class="empty-act-btn highlight" id="btnResumeContext">↩ Önceki Bağlama Dön</button>
        </div>
      </div>
    `;

    container.innerHTML = emptyHtml;
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
