/**
 * BRIF.AI — Decision History & Undo/Redo Manager (v4 Demo)
 *
 * Records user changes, actions, warnings, confirmations, and provides
 * full Undo/Redo stack + Architect Decision Report synthesis.
 */

class ChangeHistory {
  constructor() {
    this.historyStack = [];
    this.currentIndex = -1;
  }

  recordChange(entry) {
    // Truncate redo stack if new action performed after undo
    if (this.currentIndex < this.historyStack.length - 1) {
      this.historyStack = this.historyStack.slice(0, this.currentIndex + 1);
    }

    const record = {
      id: 'change_' + Date.now(),
      timestamp: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      user_message: entry.user_message || 'Şematik plan düzenlemesi',
      action_type: entry.action_type || 'edit', // 'resize', 'drag', 'swap', 'lock', 'unlock', 'preference'
      target_space_id: entry.target_space_id || 'study',
      target_space_name: entry.target_space_name || 'Çalışma Odası',
      floor: entry.floor || 'ground',
      alternative: entry.alternative || 'b',
      before_state: entry.before_state || {},
      after_state: entry.after_state || {},
      warnings: entry.warnings || [],
      user_confirmation: entry.user_confirmation !== undefined ? entry.user_confirmation : true,
      undone: false
    };

    this.historyStack.push(record);
    this.currentIndex = this.historyStack.length - 1;
    return record;
  }

  canUndo() {
    return this.currentIndex >= 0;
  }

  canRedo() {
    return this.currentIndex < this.historyStack.length - 1;
  }

  undo() {
    if (!this.canUndo()) return null;
    const item = this.historyStack[this.currentIndex];
    item.undone = true;
    this.currentIndex--;
    return item;
  }

  redo() {
    if (!this.canRedo()) return null;
    this.currentIndex++;
    const item = this.historyStack[this.currentIndex];
    item.undone = false;
    return item;
  }

  getHistory() {
    return this.historyStack;
  }

  renderArchitectReport() {
    if (this.historyStack.length === 0) {
      return `
        <div class="arch-history-empty">
          <p>Henüz kayıtlı revizyon işlemi bulunmamaktadır. Yapılan plan değişiklikleri ve sohbet komutları kronolojik olarak burada raporlanır.</p>
        </div>
      `;
    }

    return this.historyStack.map((item, idx) => `
      <div class="arch-history-item ${item.undone ? 'undone' : ''}">
        <div class="arch-item-header">
          <span class="item-step">#${idx + 1} — ${item.timestamp}</span>
          <span class="item-action-badge">${item.action_type.toUpperCase()}</span>
          ${item.undone ? '<span class="item-undone-badge">GERİ ALINDI</span>' : ''}
        </div>
        <div class="arch-item-body">
          <p><strong>Ham Kullanıcı Talebi:</strong> "${escapeHtml(item.user_message)}"</p>
          <p><strong>Etkilenen Mekân:</strong> ${escapeHtml(item.target_space_name)} (${item.floor === 'ground' ? 'Zemin Kat' : 'Üst Kat'})</p>
          ${item.warnings.length > 0 ? `
            <div class="arch-item-warnings">
              <strong>Tetiklenen Ön Kontroller:</strong>
              <ul>
                ${item.warnings.map(w => `<li><span class="badge-verify">${escapeHtml(w.category)}</span> ${escapeHtml(w.user_message)}</li>`).join('')}
              </ul>
            </div>
          ` : '<p class="pass-note">✅ Ön kontrolden geçti.</p>'}
        </div>
      </div>
    `).join('');
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
