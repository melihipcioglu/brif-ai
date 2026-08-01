/**
 * BRIF.AI — Main Orchestration Script (v5 Conversation-First Engine)
 *
 * Integrates ConversationOrchestrator, WorkspacePresenter, ContextualAssistant,
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
      assistant.setContext({ spaceId: space.id, spaceName: space.name });
      // When user clicks a space, focus chat input dynamically (Requirement 2)
      const input = document.getElementById('assistantUserInput');
      if (input) {
        input.placeholder = `${space.name} hakkında neyi değiştirmek veya anlamak istiyorsunuz?`;
      }
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

  // --------------------------------------------------------------------------
  // Collapsible Secondary Manual Tools (Requirement 20)
  // --------------------------------------------------------------------------
  const toggleAdvancedToolsBtn = document.getElementById('toggleAdvancedToolsBtn');
  const advancedToolsPanel = document.getElementById('advancedToolsPanel');

  if (toggleAdvancedToolsBtn && advancedToolsPanel) {
    toggleAdvancedToolsBtn.addEventListener('click', () => {
      advancedToolsPanel.classList.toggle('hidden');
    });
  }

  // --------------------------------------------------------------------------
  // Stage Stepper Navigation (Preserves Chat History across stages)
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

    assistant.setContext({ stage: stageNum });

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
  // Chat Submission & Quick Replies Handling
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

  // Quick Reply Chips Event Delegation
  document.addEventListener('click', (e) => {
    const chipBtn = e.target.closest('.chip-btn');
    if (chipBtn && chipBtn.dataset.reply) {
      const replyText = chipBtn.dataset.reply;

      if (replyText.includes('yataktan') || replyText.includes('giyinme') || replyText.includes('mahrem')) {
        orchestrator.handleMasterBathFollowup(replyText);
      } else {
        orchestrator.appendUserMessage(replyText);
        setTimeout(() => {
          orchestrator.handleUserMessage(replyText);
        }, 300);
      }
    }

    // Side-by-Side Option Select Buttons
    if (e.target.id === 'btnSelectOpt1') {
      alert('✅ 1. Seçenek (Banyoyu Kuzeye Taşımak) uygulandı.');
      changeHistory.recordChange({
        action_type: 'master_bath_relocate_opt1',
        target_space_id: 'master_bath',
        target_space_name: 'Ebeveyn Banyosu',
        user_message: '1. Seçenek uygulandı.',
        warnings: []
      });
      updateArchitectDecisionReport();
    }

    if (e.target.id === 'btnSelectOpt2') {
      alert('✅ 2. Seçenek (Mevcut konumu koruyup girişi değiştirmek) uygulandı.');
      changeHistory.recordChange({
        action_type: 'master_bath_relocate_opt2',
        target_space_id: 'master_bath',
        target_space_name: 'Ebeveyn Banyosu',
        user_message: '2. Seçenek uygulandı.',
        warnings: []
      });
      updateArchitectDecisionReport();
    }
  });

  // Demo Scenario Buttons
  const demoScenarioMasterBath = document.getElementById('demoScenarioMasterBath');
  const demoScenarioFloorOverlay = document.getElementById('demoScenarioFloorOverlay');
  const demoScenarioOrientation = document.getElementById('demoScenarioOrientation');
  const demoScenario2m = document.getElementById('demoScenario2m');

  if (demoScenarioMasterBath) {
    demoScenarioMasterBath.addEventListener('click', () => {
      orchestrator.appendUserMessage('Ebeveyn banyosu burada olmasın, kuzey tarafında olsun.');
      setTimeout(() => orchestrator.triggerMasterBathScenario(), 300);
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

  if (demoScenario2m) {
    demoScenario2m.addEventListener('click', () => {
      orchestrator.appendUserMessage('Yatak odasını iki metre genişliğe düşür.');
      setTimeout(() => orchestrator.handleUserMessage('Yatak odasını iki metre genişliğe düşür'), 300);
    });
  }

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
