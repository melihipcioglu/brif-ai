/**
 * BRIF.AI — Change History & Professional Decision Summary (v5 Contract)
 *
 * Manages conversation decision tracking, undo/redo history stacks,
 * and formats professional decision reports for the Architect View.
 */

class ChangeHistory {
  constructor() {
    this.historyStack = [];
    this.redoStack = [];

    // Seed initial professional decision entries
    this.historyStack.push({
      id: 1,
      timestamp: new Date().toISOString(),
      action_type: 'initial_brief_synthesized',
      target_space_id: 'study',
      target_space_name: 'Çalışma Odası',
      user_request: 'Eşim evden çalışıyor, online toplantılar yapıyor.',
      understood_need: 'Tam zamanlı evden çalışma ritmi için yüksek akustik mahremiyet.',
      presented_options: ['Alternatif A (Tam İzolasyon)', 'Alternatif B (Kayar Panelli Esnek)'],
      technical_checks: ['Dolaşım geçişi uygun', 'Zemin kat gün ışığı yeterli'],
      user_decision: 'Alternatif A seçildi (Güçlü Sessizlik)',
      architect_notes: 'Online toplantı saatlerinde çocuk sesinden korunmalı.',
      source_type: 'Doğrudan kullanıcı beyanı',
      confidence: 'Yüksek',
      verification_status: 'Doğrulandı'
    });
  }

  recordChange(changeEvent) {
    const entry = {
      id: this.historyStack.length + 1,
      timestamp: new Date().toISOString(),
      action_type: changeEvent.action_type || 'user_request',
      target_space_id: changeEvent.target_space_id || 'study',
      target_space_name: changeEvent.target_space_name || 'Çalışma Odası',
      user_request: changeEvent.user_message || 'Plan düzenleme isteği',
      understood_need: changeEvent.understood_need || 'Mekânsal uyum ve konfor artışı',
      presented_options: changeEvent.options || ['Mevcut Yerleşimi Koruma', 'Konum/Ölçü Revizyonu'],
      technical_checks: (changeEvent.warnings || []).map(w => w.statusText || w.category),
      user_decision: changeEvent.decision || 'Önizleme Aşamasında',
      architect_notes: 'Gerçek arsa yönlenmesi ve yerel mevzuat verisiyle yeniden değerlendirilmelidir.',
      source_type: 'Sohbet Alanı Talebi',
      confidence: 'Orta',
      verification_status: 'Teyit Bekliyor'
    };

    this.historyStack.push(entry);
    this.redoStack = []; // Clear redo stack on new action
  }

  undo() {
    if (this.historyStack.length > 1) {
      const item = this.historyStack.pop();
      this.redoStack.push(item);
      return item;
    }
    return null;
  }

  redo() {
    if (this.redoStack.length > 0) {
      const item = this.redoStack.pop();
      this.historyStack.push(item);
      return item;
    }
    return null;
  }

  renderArchitectReport() {
    if (this.historyStack.length === 0) {
      return `<p class="empty-history-text">Henüz kaydedilmiş mimari karar bulunmuyor.</p>`;
    }

    let html = `<div class="architect-decision-summary-grid">`;

    this.historyStack.forEach((entry, idx) => {
      html += `
        <div class="arch-decision-card">
          <div class="arch-card-header">
            <span class="decision-num">Karar #${idx + 1}</span>
            <span class="source-badge user-said">${escapeHtml(entry.source_type)}</span>
            <span class="status-badge ${entry.verification_status === 'Doğrulandı' ? 'mandatory' : 'likely'}">${escapeHtml(entry.verification_status)}</span>
          </div>

          <div class="decision-section">
            <strong>Son Kullanıcı Talebi:</strong>
            <p>"${escapeHtml(entry.user_request)}"</p>
          </div>

          <div class="decision-section">
            <strong>Anlaşılan İhtiyaç:</strong>
            <p>${escapeHtml(entry.understood_need)}</p>
          </div>

          <div class="decision-section">
            <strong>Sunulan Seçenekler:</strong>
            <ul>
              ${entry.presented_options.map(opt => `<li>${escapeHtml(opt)}</li>`).join('')}
            </ul>
          </div>

          <div class="decision-section">
            <strong>Teknik Ön Kontroller:</strong>
            <ul>
              ${entry.technical_checks.length > 0 ? entry.technical_checks.map(tc => `<li>${escapeHtml(tc)}</li>`).join('') : '<li>Tüm ön teknik kontrollerden geçti.</li>'}
            </ul>
          </div>

          <div class="decision-section">
            <strong>Kullanıcı Kararı:</strong>
            <p class="user-choice-highlight">${escapeHtml(entry.user_decision)}</p>
          </div>

          <div class="decision-footer-note">
            📌 <strong>Mimara Not:</strong> ${escapeHtml(entry.architect_notes)}
          </div>
        </div>
      `;
    });

    html += `</div>`;
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
