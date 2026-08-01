/**
 * BRIF.AI — Main Orchestration Script (v6.2 Platform Architecture)
 *
 * Integrates DOMSurfaceRegistry, EntityHierarchy, ScopedDocumentStore,
 * WorkspaceScopeResolver, RenderCompatibilityGuard, ContextStateMachine,
 * ContextValidator, ConversationOrchestrator, WorkspacePresenter, and ContextualAssistant.
 * Guarantees cross-surface context integrity under ActiveContextSnapshot.
 */

document.addEventListener('DOMContentLoaded', async () => {

  // Universal Asset Hierarchy, Document Store & DOM Surface Registry
  const hierarchy = new EntityHierarchy();
  const store = new ScopedDocumentStore();
  await store.initialize();

  const registry = new DOMSurfaceRegistry();
  window.appDOMRegistry = registry;

  const resolver = new WorkspaceScopeResolver(hierarchy, store);
  const guard = new RenderCompatibilityGuard(hierarchy);
  const stateMachine = new ContextStateMachine(hierarchy);
  window.appStateMachine = stateMachine;

  const validator = new ContextValidator(hierarchy, stateMachine);
  const changeHistory = new ChangeHistory({ hierarchy, store, resolver, guard });
  const ruleEvaluator = new RuleEvaluator();

  const assistant = new ContextualAssistant({ hierarchy, stateMachine });
  const presenter = new WorkspacePresenter('planEditorContainer', {
    hierarchy, store, resolver, guard, registry, stateMachine
  });
  const visualPreferencesPresenter = new WorkspacePresenter('visualPreferencesContent', {
    hierarchy, store, resolver, guard, registry
  });

  const orchestrator = new ConversationOrchestrator({
    hierarchy, stateMachine, store, resolver, assistant, presenter, historyManager: changeHistory
  });
  window.appOrchestrator = orchestrator;

  const localLLMGateway = new LocalLLMGateway({
    hierarchy,
    stateMachine,
    orchestrator,
    baseUrl: window.BRIF_AI_API_BASE_URL || 'http://127.0.0.1:8000'
  });
  orchestrator.setLocalLLMGateway(localLLMGateway);
  window.appLocalLLMGateway = localLLMGateway;

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
      orchestrator.selectEntity(space.id);
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
  window.appPlanEditor = planEditor;

  if (rawPlanAlternativesData) {
    planEditor.loadData(rawPlanAlternativesData);
  }

  // Initialize Stage 1 Workspace Dashboard
  const stage1Container = document.getElementById('stage1WorkspaceContainer');
  if (stage1Container) {
    const stage1Presenter = new WorkspacePresenter('stage1WorkspaceContainer', { hierarchy, store, resolver, guard, registry });
    stage1Presenter.setMode('stage1_dashboard', { hasUserMessages: false });
  }

  // Subscribe state transitions to atomically clear stale space program cards & update decision report
  stateMachine.subscribe((snapshot) => {
    changeHistory.setSessionState(snapshot);
    visualPreferencesPresenter.renderVisualPreferences(snapshot);
    populateSpaceGrids();
    updateArchitectDecisionReport(snapshot);
  });

  // Synthetic Project Selector Dropdown
  const syntheticProjectSelect = document.getElementById('syntheticProjectSelect');
  if (syntheticProjectSelect) {
    syntheticProjectSelect.addEventListener('change', (e) => {
      const projId = e.target.value;
      orchestrator.selectProject(projId);
    });
  }

  // Chat Scope Filter Dropdown
  const chatScopeFilterSelect = document.getElementById('chatScopeFilterSelect');
  if (chatScopeFilterSelect) {
    chatScopeFilterSelect.addEventListener('change', (e) => {
      orchestrator.setChatFilterMode(e.target.value);
    });
  }

  // Assumptions Modal Drawer Dialog
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

  // Stage Stepper Navigation
  const stepNodes = document.querySelectorAll('.step-node');
  const stageViews = document.querySelectorAll('.stage-view');

  stepNodes.forEach(node => {
    node.addEventListener('click', () => {
      const stageNum = parseInt(node.dataset.stage, 10);
      switchStage(stageNum);
    });
  });

  function switchStage(stageNum) {
    const isArch = !document.getElementById('architectStageView').classList.contains('hidden');
    if (isArch) {
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
      const stage1Presenter = new WorkspacePresenter('stage1WorkspaceContainer', { hierarchy, store, resolver, guard, registry });
      stage1Presenter.setMode('stage1_dashboard', { hasUserMessages: true });
    }
    if (stageNum === 3) populateSpaceGrids();
    if (stageNum === 4 && planEditor && stateMachine.getContext().projectId === 'proj_house_2story') {
      planEditor.render();
    }
  }

  visualPreferencesPresenter.bindVisualPreferenceInteractions({
    stateMachine,
    onStageChange: switchStage
  });

  // Toggle Architect View
  const toggleViewBtn = document.getElementById('toggleViewBtn');
  const toggleBtnText = document.getElementById('toggleBtnText');
  const architectStageView = document.getElementById('architectStageView');

  function toggleArchitectView(showArch) {
    if (showArch) {
      stateMachine.dispatch({ type: "ARCHITECT_VIEW_OPENED" });
      stageViews.forEach(v => v.classList.add('hidden'));
      architectStageView.classList.remove('hidden');
      toggleBtnText.textContent = 'Müşteri Görünümüne Dön';
      updateArchitectDecisionReport();
    } else {
      architectStageView.classList.add('hidden');
      toggleBtnText.textContent = 'Mimar Önizlemesine Geç';
      switchStage(stateMachine.getContext().activeStage || 4);
    }
  }

  if (toggleViewBtn) {
    toggleViewBtn.addEventListener('click', () => {
      const isArch = !architectStageView.classList.contains('hidden');
      toggleArchitectView(!isArch);
    });
  }

  // Chat Form Submission
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

  // Event Delegation
  document.addEventListener('click', (e) => {
    const proposalButton = e.target.closest('.proposal-approve-btn');
    if (proposalButton && proposalButton.dataset.proposalId) {
      orchestrator.approveProposalById(proposalButton.dataset.proposalId);
      return;
    }

    // Dynamic Level/Building Navigation Tab Click Delegation (Requirement 1: Sekmeler doğrudan class değiştirmemeli)
    const floorBtn = e.target.closest('.plan-floor-btn');
    if (floorBtn && floorBtn.dataset.entityId) {
      const entityId = floorBtn.dataset.entityId;
      const entityType = floorBtn.dataset.entityType;
      if (entityType === 'building') {
        stateMachine.transitionToContext({ buildingId: entityId });
      } else {
        stateMachine.transitionToContext({ levelId: entityId });
      }
      return;
    }

    // Quick Reply Chips
    const chipBtn = e.target.closest('.chip-btn');
    if (chipBtn && chipBtn.dataset.action) {
      orchestrator.handleQuickReply({
        label: chipBtn.textContent || chipBtn.dataset.reply || '',
        action: chipBtn.dataset.action,
        value: chipBtn.dataset.value || '',
        optionId: chipBtn.dataset.optionId || '',
        scenarioId: chipBtn.dataset.scenarioId || '',
        decisionId: chipBtn.dataset.decisionId || '',
        preferenceKey: chipBtn.dataset.preferenceKey || '',
        preferenceValue: chipBtn.dataset.preferenceValue || ''
      });
      return;
    }

    // Empty State & Resume Actions
    if (e.target.id === 'btnResumeContext') {
      orchestrator.resumeSuspendedContext();
      return;
    }
    if (e.target.id === 'btnEmptyShowUpper') {
      const ctx = stateMachine.getContext();
      orchestrator.selectProject(ctx.projectId);
      return;
    }
    if (e.target.id === 'btnEmptySelectLevel') {
      switchStage(3);
      return;
    }
    if (e.target.id === 'btnShowScopeDecisions') {
      orchestrator.setChatFilterMode('active_decision');
      return;
    }
    if (e.target.id === 'btnOpenAllProjectDecisions') {
      orchestrator.setChatFilterMode('all');
      return;
    }
    if (e.target.id === 'btnReturnToCustomerView') {
      toggleArchitectView(false);
      return;
    }

    // Workspace Option 1 Apply Button
    if (e.target.id === 'btnApplyOpt1') {
      orchestrator.applyMasterBathOption(1);
      updateArchitectDecisionReport();
      return;
    }

    // Workspace Option 2 Apply Button
    if (e.target.id === 'btnApplyOpt2') {
      orchestrator.applyMasterBathOption(2);
      updateArchitectDecisionReport();
      return;
    }

    // Space Card "Sohbette Değiştir" Button Delegation
    const spaceBtn = e.target.closest('.space-card-btn');
    if (spaceBtn) {
      const spaceId = spaceBtn.dataset.spaceId;
      if (spaceId) {
        orchestrator.selectEntity(spaceId);
        const input = document.getElementById('assistantUserInput');
        if (input) {
          input.focus();
        }
      }
    }
  });

  // Dynamic Scoped Demo Action Buttons Delegation
  document.addEventListener('click', (e) => {
    const scenarioBtn = e.target.closest('.scenario-btn');
    if (scenarioBtn && scenarioBtn.dataset.handler) {
      const handler = scenarioBtn.dataset.handler;
      if (typeof orchestrator[handler] === 'function') {
        orchestrator[handler]();
      }
    }
  });

  function populateSpaceGrids() {
    const groundGrid = document.getElementById('spaceGridGround');
    const upperGrid = document.getElementById('spaceGridUpper');
    if (!groundGrid || !upperGrid) return;

    const ctx = stateMachine.getContext();
    const doc = resolver.resolveDocument(ctx, 'space_program');

    if (doc && doc.data && guard.isDocumentCompatible(doc, ctx)) {
      groundGrid.innerHTML = doc.data.groundSpaces ? doc.data.groundSpaces.map(s => renderSpaceCardHtml(s)).join('') : '';
      upperGrid.innerHTML = doc.data.upperSpaces ? doc.data.upperSpaces.map(s => renderSpaceCardHtml(s)).join('') : '';
    } else {
      groundGrid.innerHTML = '';
      upperGrid.innerHTML = '';
    }
  }

  function renderSpaceCardHtml(s) {
    return `
      <div class="space-card" data-space-id="${s.id}">
        <div class="space-card-header">
          <h4 class="space-title">${escapeHtml(s.name)}</h4>
          <span class="status-badge mandatory">Zorunlu</span>
        </div>
        <div class="space-meta">${escapeHtml(s.floor || 'Kapsam Tanımlı')} • ${s.area} m² Net</div>
        <div class="space-rationale">📌 Dayanak: ${escapeHtml(s.source || 'Mimar varsayımı')}</div>
        <button class="space-card-btn" data-space-id="${s.id}" data-space-name="${escapeHtml(s.name)}">💬 Sohbette Değiştir</button>
      </div>
    `;
  }

  function updateArchitectDecisionReport(activeSnapshot = stateMachine.getSnapshot()) {
    const container = document.getElementById('architectDecisionHistory');
    if (container) {
      container.innerHTML = changeHistory.renderArchitectReport(activeSnapshot);
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
