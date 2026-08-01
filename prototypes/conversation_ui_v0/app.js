/**
 * BRIF.AI — Main Orchestration Script (v4 Prototype)
 *
 * Connects ContextualAssistant, PlanEditor, RuleEvaluator, ChangeHistory,
 * and DemoIntentParser for full v4 interaction experience.
 */

document.addEventListener('DOMContentLoaded', async () => {

  // Instantiate Core Engines
  const changeHistory = new ChangeHistory();
  const ruleEvaluator = new RuleEvaluator();
  const assistant = new ContextualAssistant();

  let planEditor = null;
  let rawPlanAlternativesData = null;

  // Load Structured Plan Data JSON
  try {
    const res = await fetch('data/plan_alternatives.demo.json');
    if (res.ok) {
      rawPlanAlternativesData = await res.json();
    }
  } catch (err) {
    console.error('Plan alternatives JSON load error:', err);
  }

  // Initialize Plan Editor
  planEditor = new PlanEditor('planEditorContainer', {
    onSpaceSelect: (space) => {
      assistant.setContext({ spaceId: space.id, spaceName: space.name });
    },
    onPlanChange: (event) => {
      const space = planEditor.getSpaceById(event.spaceId);
      if (!space) return;

      // Evaluate Rules
      const evalResults = ruleEvaluator.evaluateSpaceOperation(space, event.type, {
        out_of_bounds: false,
        is_open_living: space.id === 'study' && space.x < 300
      });

      // Show Action Proposal Card (Requirement 2 & 16)
      showActionProposalCard({
        title: `İstenen Değişiklik: ${space.name} (${event.type.toUpperCase()})`,
        target: `${space.name} (${space.area} m² Net)`,
        preserve: 'Mutfak & Toplam Kapalı Alan',
        effects: 'Komşu mekân sirkülasyonu',
        rulesText: evalResults[0].statusText,
        space: space,
        actionType: event.type
      });

      // Record in Change History
      changeHistory.recordChange({
        action_type: event.type,
        target_space_id: space.id,
        target_space_name: space.name,
        floor: planEditor.currentFloor,
        alternative: planEditor.currentAlt,
        user_message: `Plan editöründen ${space.name} ${event.type} işlemi yapıldı.`,
        warnings: evalResults.filter(r => r.severity !== 'PASS')
      });

      updateArchitectDecisionReport();
    }
  });

  if (rawPlanAlternativesData) {
    planEditor.loadData(rawPlanAlternativesData);
  }

  // --------------------------------------------------------------------------
  // Stepper & Stage Navigation
  // --------------------------------------------------------------------------
  const stepNodes = document.querySelectorAll('.step-node');
  const stageViews = document.querySelectorAll('.stage-view');
  
  const toggleViewBtn = document.getElementById('toggleViewBtn');
  const toggleBtnText = document.getElementById('toggleBtnText');
  const architectStageView = document.getElementById('architectStageView');

  const panelTitle = document.getElementById('panelTitle');
  const panelStage1 = document.getElementById('panelStage1');
  const panelStage2 = document.getElementById('panelStage2');
  const panelStage3 = document.getElementById('panelStage3');
  const panelStage4 = document.getElementById('panelStage4');

  const drawerHandleBar = document.getElementById('drawerHandleBar');
  const contextualPanel = document.getElementById('contextualPanel');

  stepNodes.forEach(node => {
    node.addEventListener('click', () => {
      const stageNum = parseInt(node.dataset.stage, 10);
      switchStage(stageNum);
    });
  });

  function switchStage(stageNum) {
    if (assistant.currentContext.isArchitectView) {
      toggleArchitectView(false);
    }

    assistant.setContext({ stage: stageNum });

    // Stepper UI
    stepNodes.forEach(node => {
      const num = parseInt(node.dataset.stage, 10);
      node.classList.remove('active');
      const badge = node.querySelector('.step-badge');

      if (num === stageNum) {
        node.classList.add('active');
        if (badge) { badge.className = 'step-badge badge-active'; badge.textContent = 'Aktif'; }
      } else if (num < stageNum) {
        node.classList.add('completed');
        if (badge) { badge.className = 'step-badge badge-completed'; badge.textContent = 'Tamamlandı'; }
      }
    });

    stageViews.forEach(v => { v.classList.add('hidden'); v.classList.remove('active'); });
    const activeView = document.getElementById(`stageView${stageNum}`);
    if (activeView) { activeView.classList.remove('hidden'); activeView.classList.add('active'); }

    // Right Panel
    [panelStage1, panelStage2, panelStage3, panelStage4].forEach(p => p.classList.add('hidden'));
    if (stageNum === 1) { panelTitle.textContent = 'Sizi nasıl anladım?'; panelStage1.classList.remove('hidden'); }
    else if (stageNum === 2) { panelTitle.textContent = 'Görsellerden ne anladım?'; panelStage2.classList.remove('hidden'); }
    else if (stageNum === 3) { panelTitle.textContent = 'Program kararlarının dayanakları'; panelStage3.classList.remove('hidden'); populateSpaceGrids(); }
    else if (stageNum === 4) { panelTitle.textContent = 'Planı neden böyle kurduk?'; panelStage4.classList.remove('hidden'); planEditor.render(); }
  }

  function toggleArchitectView(showArch) {
    assistant.setContext({ isArchitectView: showArch });

    if (showArch) {
      stageViews.forEach(v => v.classList.add('hidden'));
      architectStageView.classList.remove('hidden');
      toggleBtnText.textContent = 'Müşteri Görünümüne Dön';
      panelTitle.textContent = 'Doğrulanmış brief ve güven durumu';
      updateArchitectDecisionReport();
    } else {
      architectStageView.classList.add('hidden');
      toggleBtnText.textContent = 'Mimar Önizlemesine Geç';
      switchStage(assistant.currentContext.stage);
    }
  }

  if (toggleViewBtn) {
    toggleViewBtn.addEventListener('click', () => {
      toggleArchitectView(!assistant.currentContext.isArchitectView);
    });
  }

  // --------------------------------------------------------------------------
  // Single Contextual Assistant Chat Handling (Requirements 1 & 17)
  // --------------------------------------------------------------------------
  const assistantChatForm = document.getElementById('assistantChatForm');
  const assistantUserInput = document.getElementById('assistantUserInput');

  if (assistantChatForm) {
    assistantChatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = assistantUserInput.value.trim();
      if (!text) return;

      // Handle assistant message
      const res = assistant.processUserMessage(text);
      assistantUserInput.value = '';

      // If user typed in Stage 1 chat
      const chatMessages = document.getElementById('chatMessages');
      if (chatMessages && assistant.currentContext.stage === 1) {
        appendChatMessage(chatMessages, 'user', 'Siz', 'MK', text);
        setTimeout(() => {
          appendChatMessage(chatMessages, 'brif', 'BRIF.AI Mimari Asistan', 'B', res.aiResponseText);
        }, 500);
      }

      // If in Stage 4 (Plan), check for special scenarios
      if (res.actionPayload.special_case === 'two_meter_bedroom') {
        triggerBedroom2mScenario();
      } else if (res.actionPayload.special_case === 'misleading_bypass') {
        triggerMisleadingBypassScenario();
      } else if (res.actionPayload.intent === 'resize_space') {
        showActionProposalCard({
          title: 'İstenen Değişiklik: Çalışma Alanını Küçült',
          target: '14 m² → 10–11 m²',
          preserve: 'Mutfak alanı, Toplam kapalı alan',
          effects: 'Çocuk odaları metrajı, Dolaşım payı',
          rulesText: 'Ön kontrolden geçti'
        });
      }

      // Record in Change History
      changeHistory.recordChange({
        action_type: res.actionPayload.intent,
        user_message: text,
        target_space_name: assistant.currentContext.spaceName || 'Çalışma Odası',
        warnings: res.evaluationResults.filter(r => r.severity !== 'PASS')
      });

      updateArchitectDecisionReport();
    });
  }

  function appendChatMessage(container, type, sender, avatar, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type === 'user' ? 'user-message' : 'ai-message'}`;
    msgDiv.innerHTML = `
      <div class="message-avatar ${type === 'user' ? 'user' : 'brif'}">${avatar}</div>
      <div class="message-content">
        <div class="message-sender">${sender}</div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  }

  // --------------------------------------------------------------------------
  // Stage 3 Space Grid Population
  // --------------------------------------------------------------------------
  function populateSpaceGrids() {
    if (!planEditor) return;
    const groundGrid = document.getElementById('spaceGridGround');
    const upperGrid = document.getElementById('spaceGridUpper');
    if (!groundGrid || !upperGrid) return;

    const groundSpaces = rawPlanAlternativesData.alternatives[planEditor.currentAlt].floors.ground;
    const upperSpaces = rawPlanAlternativesData.alternatives[planEditor.currentAlt].floors.upper;

    groundGrid.innerHTML = groundSpaces.map(s => renderSpaceCardHtml(s)).join('');
    upperGrid.innerHTML = upperSpaces.map(s => renderSpaceCardHtml(s)).join('');
  }

  function renderSpaceCardHtml(s) {
    return `
      <div class="space-card" data-space-id="${s.id}">
        <div class="space-card-header">
          <h4 class="space-title">${escapeHtml(s.name)}</h4>
          <span class="status-badge mandatory">Zorunlu</span>
        </div>
        <div class="space-meta">${s.floor === 'ground' ? 'Zemin Kat' : 'Üst Kat'} • ${s.area} m² Net</div>
        <div class="space-rationale">
          <span class="source-badge ${s.source_type.includes('kullanıcı') ? 'user-said' : 'sys-interp'}">${escapeHtml(s.source_type)}</span>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // Stage 4 Plan Controls Toolbar (Undo/Redo/Lock/Swap)
  // --------------------------------------------------------------------------
  const btnAltA = document.getElementById('btnAltA');
  const btnAltB = document.getElementById('btnAltB');
  const planFloorGroundBtn = document.getElementById('planFloorGroundBtn');
  const planFloorUpperBtn = document.getElementById('planFloorUpperBtn');

  if (btnAltA && btnAltB) {
    btnAltA.addEventListener('click', () => {
      btnAltA.classList.add('active'); btnAltB.classList.remove('active');
      planEditor.setAlternative('a');
      assistant.setContext({ alternative: 'a' });
    });

    btnAltB.addEventListener('click', () => {
      btnAltB.classList.add('active'); btnAltA.classList.remove('active');
      planEditor.setAlternative('b');
      assistant.setContext({ alternative: 'b' });
    });
  }

  if (planFloorGroundBtn && planFloorUpperBtn) {
    planFloorGroundBtn.addEventListener('click', () => {
      planFloorGroundBtn.classList.add('active'); planFloorUpperBtn.classList.remove('active');
      planEditor.setFloor('ground');
      assistant.setContext({ floor: 'ground' });
    });

    planFloorUpperBtn.addEventListener('click', () => {
      planFloorUpperBtn.classList.add('active'); planFloorGroundBtn.classList.remove('active');
      planEditor.setFloor('upper');
      assistant.setContext({ floor: 'upper' });
    });
  }

  const undoBtn = document.getElementById('undoBtn');
  const redoBtn = document.getElementById('redoBtn');
  const lockToggleBtn = document.getElementById('lockToggleBtn');
  const swapBtn = document.getElementById('swapBtn');

  if (undoBtn) {
    undoBtn.addEventListener('click', () => {
      const undone = changeHistory.undo();
      if (undone) {
        alert(`↩ Geri Alındı: ${undone.target_space_name} ${undone.action_type}`);
        updateArchitectDecisionReport();
      }
    });
  }

  if (redoBtn) {
    redoBtn.addEventListener('click', () => {
      const redone = changeHistory.redo();
      if (redone) {
        alert(`↪ İleri Alındı: ${redone.target_space_name} ${redone.action_type}`);
        updateArchitectDecisionReport();
      }
    });
  }

  if (lockToggleBtn) {
    lockToggleBtn.addEventListener('click', () => {
      if (planEditor && planEditor.selectedSpaceId) {
        const isLocked = planEditor.toggleLock(planEditor.selectedSpaceId);
        alert(isLocked ? '🔒 Mekân kilitlendi. Değişiklikler engellendi.' : '🔓 Mekân kilidi kaldırıldı.');
      }
    });
  }

  if (swapBtn) {
    swapBtn.addEventListener('click', () => {
      showActionProposalCard({
        title: 'İstenen Değişiklik: Mutfak ↔ Çalışma Odası Takası',
        target: 'Mutfak ile Çalışma Odasının yerlerini karşılıklı değiştir',
        preserve: 'Net alan büyüklükleri',
        effects: 'Teras ilişkisi zayıflar, ıslak hacim mesafesi uzar',
        rulesText: 'Konfor açısından riskli'
      });
    });
  }

  // Demo Scenario Buttons
  const demoScenario2m = document.getElementById('demoScenario2m');
  const demoScenarioBypass = document.getElementById('demoScenarioBypass');
  const demoScenarioResize = document.getElementById('demoScenarioResize');

  if (demoScenario2m) {
    demoScenario2m.addEventListener('click', () => {
      triggerBedroom2mScenario();
    });
  }

  if (demoScenarioBypass) {
    demoScenarioBypass.addEventListener('click', () => {
      triggerMisleadingBypassScenario();
    });
  }

  if (demoScenarioResize) {
    demoScenarioResize.addEventListener('click', () => {
      showActionProposalCard({
        title: 'İstenen Değişiklik: Çalışma Alanını Küçült (11 m²)',
        target: '14 m² → 11 m²',
        preserve: 'Mutfak alanı, Toplam kapalı alan',
        effects: 'Çocuk odaları metrajı, Dolaşım payı',
        rulesText: 'Ön kontrolden geçti'
      });
    });
  }

  function triggerBedroom2mScenario() {
    const res = ruleEvaluator.evaluateSpaceOperation({ use_type: 'bedroom', id: 'master' }, 'resize', { narrow_edge: 1.9 });
    const warning = res[0];

    alert(`⚠️ UYARI (${warning.category}):\n\n${warning.user_message}\n\nÖnerilen Alternatifler:\n- ${warning.alternatives.join('\n- ')}`);

    changeHistory.recordChange({
      action_type: 'resize_risk_trigger',
      target_space_id: 'master',
      target_space_name: 'Ebeveyn Odası',
      user_message: 'Yatak odasını 2 metre genişliğe düşür.',
      warnings: res
    });

    updateArchitectDecisionReport();
  }

  function triggerMisleadingBypassScenario() {
    const res = ruleEvaluator.evaluateSpaceOperation({ use_type: 'study', id: 'study' }, 'rename', { is_misleading_rename: true });
    const warning = res[0];

    alert(`🛡️ BİLGİ / RED (${warning.category}):\n\n${warning.user_message}`);

    changeHistory.recordChange({
      action_type: 'misleading_bypass_attempt',
      target_space_id: 'study',
      target_space_name: 'Çalışma Odası',
      user_message: 'Buraya depo yazalım, siz sonradan yatak odası kullanın.',
      warnings: res
    });

    updateArchitectDecisionReport();
  }

  // --------------------------------------------------------------------------
  // Action Proposal Card Handling (Requirement 2 & 16)
  // --------------------------------------------------------------------------
  const actionProposalCard = document.getElementById('actionProposalCard');
  const proposalTitle = document.getElementById('proposalTitle');
  const propTarget = document.getElementById('propTarget');
  const propPreserve = document.getElementById('propPreserve');
  const propEffects = document.getElementById('propEffects');
  const propRules = document.getElementById('propRules');

  const btnPropApply = document.getElementById('btnPropApply');
  const btnPropCancel = document.getElementById('btnPropCancel');

  function showActionProposalCard(data) {
    if (!actionProposalCard) return;

    proposalTitle.textContent = data.title;
    propTarget.textContent = data.target;
    propPreserve.textContent = data.preserve;
    propEffects.textContent = data.effects;
    propRules.textContent = data.rulesText;

    actionProposalCard.classList.remove('hidden');
  }

  if (btnPropApply) {
    btnPropApply.addEventListener('click', () => {
      alert('✅ İşlem şematik plana uygulandı.');
      actionProposalCard.classList.add('hidden');
    });
  }

  if (btnPropCancel) {
    btnPropCancel.addEventListener('click', () => {
      actionProposalCard.classList.add('hidden');
    });
  }

  function updateArchitectDecisionReport() {
    const container = document.getElementById('architectDecisionHistory');
    if (container) {
      container.innerHTML = changeHistory.renderArchitectReport();
    }
  }

  // --------------------------------------------------------------------------
  // Mobile Drawer Toggle (<1024px)
  // --------------------------------------------------------------------------
  if (drawerHandleBar && contextualPanel) {
    drawerHandleBar.addEventListener('click', () => {
      contextualPanel.classList.toggle('drawer-open');
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, match => {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
      return map[match];
    });
  }

});
