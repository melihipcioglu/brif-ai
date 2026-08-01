/**
 * BRIF.AI — Main Orchestration Script (v5.2 Refined Engine)
 *
 * Connects ConversationOrchestrator, WorkspacePresenter, ContextualAssistant,
 * PlanEditor, RuleEvaluator, and ChangeHistory.
 */

document.addEventListener('DOMContentLoaded', async () => {

  // Core Engines
  const changeHistory = new ChangeHistory();
  const ruleEvaluator = new RuleEvaluator();
  const assistant = new ContextualAssistant();
  const presenter = new WorkspacePresenter('planEditorContainer');

  const orchestrator = new ConversationOrchestrator({
    assistant: assistant,
    presenter: presenter,
    historyManager: changeHistory
  });

  let planEditor = null;
  let rawPlanAlternativesData = null;

  // Load Structured Plan Data
  try {
    const res = await fetch('data/plan_alternatives.demo.json');
    if (res.ok) {
      rawPlanAlternativesData = await res.json();
    }
  } catch (err) {
    console.error('Plan alternatives load error:', err);
  }

  // Initialize Plan Editor
  planEditor = new PlanEditor('planEditorContainer', {
    onSpaceSelect: (space) => {
      orchestrator.selectSpace(space.id, space.name);
    },
    onPlanChange: (event) => {
      const space = planEditor.getSpaceById(event.spaceId);
      if (!space) return;

      const evalResults = ruleEvaluator.evaluateSpaceOperation(space, event.type, {});
      changeHistory.recordChange({
        action_type: event.type,
        target_space_id: space.id,
        target_space_name: space.name,
        user_message: `Manuel editörden ${space.name} ${event.type} yapıldı.`,
        warnings: evalResults.filter(r => r.severity !== 'PASS')
      });
      updateArchitectDecisionReport();
    }
  });

  if (rawPlanAlternativesData) {
    planEditor.loadData(rawPlanAlternativesData);
  }

  // Initialize Stage 1 Workspace Dashboard (Requirement 13)
  const stage1Container = document.getElementById('stage1WorkspaceContainer');
  if (stage1Container) {
    const stage1Presenter = new WorkspacePresenter('stage1WorkspaceContainer');
    stage1Presenter.setMode('stage1_dashboard', { hasUserMessages: false });
  }

  // --------------------------------------------------------------------------
  // Assumptions Modal Drawer Dialog (Requirement 9 Fix)
  // --------------------------------------------------------------------------
  const assumptionsModal = document.getElementById('assumptionsModal');
  const openAssumptionsBtn = document.getElementById('openAssumptionsBtn');
  const closeAssumptionsBtn = document.getElementById('closeAssumptionsBtn');
  const cancelAssumptionsBtn = document.getElementById('cancelAssumptionsBtn');
  const assumptionsForm = document.getElementById('assumptionsForm');

  if (openAssumptionsBtn && assumptionsModal) {
    openAssumptionsBtn.addEventListener('click', () => {
      assumptionsModal.classList.remove('hidden');
    });
  }

  if (closeAssumptionsBtn && assumptionsModal) {
    closeAssumptionsBtn.addEventListener('click', () => {
      assumptionsModal.classList.add('hidden');
    });
  }

  if (cancelAssumptionsBtn && assumptionsModal) {
    cancelAssumptionsBtn.addEventListener('click', () => {
      assumptionsModal.classList.add('hidden');
    });
  }

  if (assumptionsForm) {
    assumptionsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      assumptionsModal.classList.add('hidden');
      orchestrator.appendAssistantMessage("📌 Plan varsayımları güncellendi.");
    });
  }

  // Collapsible Secondary Manual Tools
  const toggleAdvancedToolsBtn = document.getElementById('toggleAdvancedToolsBtn');
  const advancedToolsPanel = document.getElementById('advancedToolsPanel');

  if (toggleAdvancedToolsBtn && advancedToolsPanel) {
    toggleAdvancedToolsBtn.addEventListener('click', () => {
      advancedToolsPanel.classList.toggle('hidden');
    });
  }

  // --------------------------------------------------------------------------
  // Stage Stepper Navigation (Stage-Aware Greetings)
  // --------------------------------------------------------------------------
  const stepNodes = document.querySelectorAll('.step-node');
  const stageViews = document.querySelectorAll('.stage-view');

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

    orchestrator.setStage(stageNum);

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

    if (stageNum === 1 && stage1Container) {
      const stage1Presenter = new WorkspacePresenter('stage1WorkspaceContainer');
      stage1Presenter.setMode('stage1_dashboard', { hasUserMessages: true });
    }
    if (stageNum === 3) populateSpaceGrids();
    if (stageNum === 4 && planEditor) planEditor.render();
  }

  // --------------------------------------------------------------------------
  // Toggle Architect View
  // --------------------------------------------------------------------------
  const toggleViewBtn = document.getElementById('toggleViewBtn');
  const toggleBtnText = document.getElementById('toggleBtnText');
  const architectStageView = document.getElementById('architectStageView');

  function toggleArchitectView(showArch) {
    assistant.setContext({ isArchitectView: showArch });

    if (showArch) {
      stageViews.forEach(v => v.classList.add('hidden'));
      architectStageView.classList.remove('hidden');
      toggleBtnText.textContent = 'Müşteri Görünümüne Dön';
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
  // Chat Submission & Event Delegation
  // --------------------------------------------------------------------------
  const assistantChatForm = document.getElementById('assistantChatForm');
  const assistantUserInput = document.getElementById('assistantUserInput');

  if (assistantChatForm) {
    assistantChatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = assistantUserInput.value.trim();
      if (!text) return;

      orchestrator.appendUserMessage(text);
      assistantUserInput.value = '';

      setTimeout(() => {
        orchestrator.handleUserMessage(text);
      }, 300);
    });
  }

  // Event Delegation for Quick Reply Chips & Workspace Option Buttons
  document.addEventListener('click', (e) => {
    const chipBtn = e.target.closest('.chip-btn');
    if (chipBtn && chipBtn.dataset.reply) {
      const replyText = chipBtn.dataset.reply;
      orchestrator.appendUserMessage(replyText);
      setTimeout(() => {
        orchestrator.handleUserMessage(replyText);
      }, 300);
      return;
    }

    if (e.target.id === 'btnApplyOpt1') {
      orchestrator.applyMasterBathOption(1);
      updateArchitectDecisionReport();
      return;
    }

    if (e.target.id === 'btnApplyOpt2') {
      orchestrator.applyMasterBathOption(2);
      updateArchitectDecisionReport();
      return;
    }

    if (e.target.id === 'btnDeferDecision') {
      orchestrator.deferMasterBathDecision();
      updateArchitectDecisionReport();
      return;
    }

    // Space Card "Sohbette Değiştir" Button Delegation (Requirement 14)
    const spaceBtn = e.target.closest('.space-card-btn');
    if (spaceBtn) {
      const spaceId = spaceBtn.dataset.spaceId;
      const spaceName = spaceBtn.dataset.spaceName;
      if (spaceId && spaceName) {
        orchestrator.selectSpace(spaceId, spaceName);
        const input = document.getElementById('assistantUserInput');
        if (input) {
          input.value = `${spaceName} hakkında düzenleme yapalım`;
          input.focus();
        }
      }
    }
  });

  // Demo Scenario Shortcut Buttons
  const demoScenarioMasterBath = document.getElementById('demoScenarioMasterBath');
  const demoScenarioFloorOverlay = document.getElementById('demoScenarioFloorOverlay');
  const demoScenarioOrientation = document.getElementById('demoScenarioOrientation');

  if (demoScenarioMasterBath) {
    demoScenarioMasterBath.addEventListener('click', () => {
      orchestrator.appendUserMessage('Ebeveyn banyosu burada olmasın, kuzey tarafında olsun.');
      setTimeout(() => orchestrator.triggerMasterBathScenario('Ebeveyn banyosu burada olmasın, kuzey tarafında olsun.'), 300);
    });
  }

  if (demoScenarioFloorOverlay) {
    demoScenarioFloorOverlay.addEventListener('click', () => {
      orchestrator.appendUserMessage('Alt planla üst plan üst üste gelince burada ne olduğunu anlamadım.');
      setTimeout(() => orchestrator.triggerFloorOverlayScenario(), 300);
    });
  }

  if (demoScenarioOrientation) {
    demoScenarioOrientation.addEventListener('click', () => {
      orchestrator.appendUserMessage('Burası kuzey cephesi olmasın.');
      setTimeout(() => orchestrator.triggerOrientationScenario(), 300);
    });
  }

  // --------------------------------------------------------------------------
  // Space Program Cards Grid Population (Requirement 14 Fix)
  // --------------------------------------------------------------------------
  function populateSpaceGrids() {
    if (!rawPlanAlternativesData || !planEditor) return;
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
        <div class="space-rationale">📌 Dayanak: ${escapeHtml(s.source_type || 'Mimar varsayımı')}</div>
        <button class="space-card-btn" data-space-id="${s.id}" data-space-name="${escapeHtml(s.name)}">💬 Sohbette Değiştir</button>
      </div>
    `;
  }

  function updateArchitectDecisionReport() {
    const container = document.getElementById('architectDecisionHistory');
    if (container) {
      container.innerHTML = changeHistory.renderArchitectReport();
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, match => {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
      return map[match];
    });
  }

});
