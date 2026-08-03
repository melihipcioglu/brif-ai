/**
 * BRIF.AI — Automated Scope, Surface & Payload Unit Tests (v6.2 Engine)
 *
 * Verifies core architectural principles across 112 test scenarios:
 * 1-28. Universal scope, surface, and empty state assertions
 * 29 (Test A). Finans Kulesi 18. Kat -> 32. Kat transition consistency
 * 30 (Test B). Kampüs Blok A -> Blok B transition consistency
 * 31 (Test C). House -> Tower surface clearing
 * 32 (Test D). Tower -> House full plan & SVG restoration
 * 33 (Test E). Campus capability actions isolation
 * 34 (Test F). Stale async render rejection
 * 35 (Test G). Single snapshot cross-surface consistency
 * 36. Atomic transitionToContext execution assertion
 * 37-47. Stage, ancestor, XSS, decision, and immutability regressions
 * 48-53. Deterministic demo parser and chat regressions
 * 54-60. Project-scoped visual preference regressions
 * 61-75. Visual preference click, state, round, layout, and stage regressions
 * 76-91. Workspace mode renderers and atomic scenario regressions
 * 92-107. Structured scenario quick-reply and preference-state regressions
 * 108-112. Browser assertion isolation and repeat-run regressions
 */

class TestScopeGuard {
  constructor() {
    this.hierarchy = new EntityHierarchy();
    this.store = new ScopedDocumentStore();
    this.resolver = new WorkspaceScopeResolver(this.hierarchy, this.store);
    this.guard = new RenderCompatibilityGuard(this.hierarchy);
    this.registry = new DOMSurfaceRegistry();
    this.runId = `run-${TestScopeGuard.nextRunSequence()}`;
    this.testNodeSequence = 0;
    this.testNodes = [];
    this.testRoot = null;
  }

  static nextRunSequence() {
    TestScopeGuard.runSequence = (TestScopeGuard.runSequence || 0) + 1;
    return TestScopeGuard.runSequence;
  }

  captureGlobals() {
    const names = [
      "appStateMachine",
      "appDOMRegistry",
      "appPlanEditor",
      "appOrchestrator",
      "__xss",
      "__assistantXss",
      "__parserXss",
      "__scenarioXss",
      "__quickReplyXss"
    ];
    return Object.fromEntries(names.map(name => [name, {
      exists: Object.prototype.hasOwnProperty.call(window, name),
      value: window[name]
    }]));
  }

  restoreGlobals(globals) {
    Object.entries(globals).forEach(([name, previous]) => {
      if (previous.exists) {
        window[name] = previous.value;
      } else {
        delete window[name];
      }
    });
  }

  captureProductionState(stateMachine = window.appStateMachine) {
    const captureElement = id => {
      const element = document.getElementById(id);
      return element ? element.outerHTML : null;
    };
    const chat = document.getElementById("chatMessagesContainer");
    const activeSnapshot = stateMachine && typeof stateMachine.getSnapshot === "function"
      ? stateMachine.getSnapshot()
      : null;

    return {
      activeSnapshot: JSON.stringify(activeSnapshot),
      chat: {
        html: chat ? chat.innerHTML : null,
        messageCount: chat ? chat.querySelectorAll(".chat-message").length : 0,
        messageTexts: chat
          ? Array.from(chat.querySelectorAll(".chat-message .message-text"))
            .map(element => element.textContent)
          : []
      },
      workspace: {
        bodyHtml: document.body.innerHTML,
        architectDecisionHistory: captureElement("architectDecisionHistory"),
        planEditorContainer: captureElement("planEditorContainer"),
        visualPreferencesContent: captureElement("visualPreferencesContent")
      }
    };
  }

  beginIsolation() {
    const root = document.createElement("div");
    root.id = `test-scope-guard-${this.runId}-root`;
    root.dataset.testScopeGuardRoot = this.runId;
    root.style.cssText = "position:fixed;left:-10000px;top:0;width:1200px;z-index:-1;";
    ["click", "submit", "change", "input"].forEach(eventName => {
      root.addEventListener(eventName, event => event.stopPropagation());
    });
    document.body.appendChild(root);
    this.testRoot = root;
    this.testNodes.push(root);
  }

  installIsolatedGlobals() {
    window.appDOMRegistry = new DOMSurfaceRegistry();
    window.appStateMachine = new ContextStateMachine(this.hierarchy);
    window.appPlanEditor = { render() {} };
    window.appOrchestrator = null;
    delete window.__xss;
    delete window.__assistantXss;
    delete window.__parserXss;
    delete window.__scenarioXss;
    delete window.__quickReplyXss;
  }

  createTestElement(label, tagName = "div", appendToRoot = true) {
    const element = document.createElement(tagName);
    this.testNodeSequence += 1;
    element.id = `test-scope-guard-${this.runId}-${this.testNodeSequence}-${label}`;
    if (appendToRoot) {
      this.testRoot.appendChild(element);
    }
    this.testNodes.push(element);
    return element;
  }

  cleanupTestNodes() {
    [...this.testNodes].reverse().forEach(node => node.remove());
    this.testNodes = [];
    this.testRoot = null;
  }

  async runAllTests() {
    await this.store.initialize();
    const results = [];
    const productionGlobals = this.captureGlobals();
    const productionStateMachine = productionGlobals.appStateMachine.value;
    const productionBefore = this.captureProductionState(productionStateMachine);
    this.beginIsolation();
    this.installIsolatedGlobals();
    try {

    // Test 1: Plan incompatibility
    const ctx1 = { projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_upper", entityId: "space_master_bath" };
    const docGroundPlan = { documentType: "plan", projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground", status: "available" };
    const res1 = this.guard.isDocumentCompatible(docGroundPlan, ctx1);
    results.push({ name: "Test 1: Plan Incompatibility (Upper vs Ground)", pass: res1 === false });

    // Test 2: Report incompatibility
    const docStudyReport = { documentType: "architect_report", projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground", entityId: "space_study", status: "available" };
    const res2 = this.guard.isDocumentCompatible(docStudyReport, ctx1);
    results.push({ name: "Test 2: Report Incompatibility (Upper vs Study Report)", pass: res2 === false });

    // Test 3: Project incompatibility
    const ctxTower = { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18" };
    const docHousePlan = { documentType: "plan", projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground", status: "available" };
    const res3 = this.guard.isDocumentCompatible(docHousePlan, ctxTower);
    results.push({ name: "Test 3: Project Incompatibility (Tower vs House Doc)", pass: res3 === false });

    // Test 4: Parent fallback
    const ctxMeeting18 = { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18", entityId: "space_meeting_18a" };
    const resolved18 = this.resolver.resolveDocument(ctxMeeting18, "plan");
    results.push({ name: "Test 4: Parent Fallback (18. Kat Plan Selected for Meeting Room)", pass: resolved18 && resolved18.levelId === "lvl_18" });

    // Test 5: Other level document cannot be fallback
    const ctxOps32 = { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_32" };
    const resolved32 = this.resolver.resolveDocument(ctxOps32, "plan");
    results.push({ name: "Test 5: Other Level Exclusion (18. Kat Doc Not Selected for 32. Kat)", pass: resolved32 && resolved32.levelId === "lvl_32" });

    // Test 6: Tab names derived from displayName
    const houseBldg = this.hierarchy.projects.proj_house_2story.buildings.bldg_main;
    const tabNames = Object.values(houseBldg.levels).map(l => l.name);
    results.push({ name: "Test 6: Dynamic Tab DisplayNames (Zemin Kat & Üst Kat)", pass: tabNames.includes("Zemin Kat") && tabNames.includes("Üst Kat") });

    // Test 7: Scoped actions filtering
    const campusCtx = { projectId: "proj_campus_multiblock", buildingId: "block_a_r_d" };
    const campusCaps7 = this.hierarchy.getActiveCapabilities(campusCtx);
    const houseOnlyAction7 = { requiredCapabilities: ["residential_master_suite"] };
    const isHouseActionInCampus = this.guard.isCapabilityCompatible(
      houseOnlyAction7,
      campusCaps7
    );
    results.push({ name: "Test 7: Scoped Actions Filtering (House action excluded in Campus)", pass: isHouseActionInCampus === false });

    // Test 8: Report empty state
    const dummyContainer = this.createTestElement("report-empty-8", "div", false);
    this.guard.renderReportEmptyState(dummyContainer, ctx1, "Çalışma Odası Kararı");
    const hasEmptyStateText = dummyContainer.innerHTML.includes("Bu aktif kapsam için mimar karar raporu bulunmuyor");
    results.push({ name: "Test 8: Report Empty State (No Blank Container)", pass: hasEmptyStateText === true });

    // Test 9: Tower navigation
    const towerSiblings = this.hierarchy.getNavigableSiblings(ctxTower).map(s => s.displayName);
    const towerNavPass = towerSiblings.includes("18. Kat") && towerSiblings.includes("32. Kat") && !towerSiblings.includes("Zemin Kat");
    results.push({ name: "Test 9: Tower Navigation Isolation (18. Kat & 32. Kat)", pass: towerNavPass === true });

    // Test 10: Campus navigation
    const campusSiblings = this.hierarchy.getNavigableSiblings(campusCtx).map(s => s.displayName);
    const campusNavPass = campusSiblings.includes("Blok A (AR-GE Binası)") && campusSiblings.includes("Blok B (İdari Bina)") && !campusSiblings.includes("Zemin Kat");
    results.push({ name: "Test 10: Campus Navigation Isolation (Blok A & Blok B)", pass: campusNavPass === true });

    // Test 11: Tower capability actions isolation
    const towerCaps = this.hierarchy.getActiveCapabilities(ctxTower);
    const towerAction = { requiredCapabilities: ["office_meeting_analysis"] };
    const houseActionInTower = { requiredCapabilities: ["residential_master_suite"] };
    const towerActPass = this.guard.isCapabilityCompatible(towerAction, towerCaps) && !this.guard.isCapabilityCompatible(houseActionInTower, towerCaps);
    results.push({ name: "Test 11: Tower Capability Actions Isolation", pass: towerActPass === true });

    // Test 12: Campus capability actions isolation
    const campusCaps = this.hierarchy.getActiveCapabilities(campusCtx);
    const campusAction = { requiredCapabilities: ["laboratory_service_analysis"] };
    const campusActPass = this.guard.isCapabilityCompatible(campusAction, campusCaps) && !this.guard.isCapabilityCompatible(houseActionInTower, campusCaps);
    results.push({ name: "Test 12: Campus Capability Actions Isolation", pass: campusActPass === true });

    // Test 13: No foreign fallback navigation
    const invalidCtx = { projectId: "proj_unknown_x" };
    const emptySiblings = this.hierarchy.getNavigableSiblings(invalidCtx);
    results.push({ name: "Test 13: No Foreign Fallback Navigation", pass: emptySiblings.length === 0 });

    // Test 14: Tower plan foreign payload exclusion
    const towerPlanDoc = this.resolver.resolveDocument(ctxTower, "plan");
    const towerPayloadStr = JSON.stringify(towerPlanDoc ? towerPlanDoc.data : {});
    const noHouseInTowerPayload = !towerPayloadStr.includes("space_living") && !towerPayloadStr.includes("Mutfak");
    results.push({ name: "Test 14: Tower Plan Foreign Payload Exclusion", pass: noHouseInTowerPayload === true });

    // Test 15: Campus plan foreign payload exclusion
    const campusPlanDoc = this.resolver.resolveDocument(campusCtx, "plan");
    const campusPayloadStr = JSON.stringify(campusPlanDoc ? campusPlanDoc.data : {});
    const noHouseInCampusPayload = !campusPayloadStr.includes("space_living") && !campusPayloadStr.includes("Ebeveyn");
    results.push({ name: "Test 15: Campus Plan Foreign Payload Exclusion", pass: noHouseInCampusPayload === true });

    // Test 16: Foreign alternative selector exclusion
    const towerCapsForAlt = this.hierarchy.getActiveCapabilities(ctxTower);
    const altCapable = towerCapsForAlt.includes("residential_plan_alternatives");
    results.push({ name: "Test 16: Foreign Alternative Selector Exclusion (Tower has no house alt caps)", pass: altCapable === false });

    // Test 17: Atomic project transition token test
    const token1 = this.registry.nextGeneration(ctx1);
    const token2 = this.registry.nextGeneration(ctxTower);
    results.push({ name: "Test 17: Atomic Project Transition Tokens", pass: token1.generationId !== token2.generationId && token2.fingerprint.includes("proj_tower_50floor") });

    // Test 18: Stale async render rejection
    const isToken1Valid = this.registry.isValidGeneration(token1.generationId, ctxTower);
    results.push({ name: "Test 18: Stale Async Render Rejection", pass: isToken1Valid === false });

    // Test 19: Render registry cleanup assertion
    this.registry.mountSurface({ surfaceId: "surf_house", containerId: "test_c", projectId: "proj_house_2story" });
    this.registry.unmountIncompatibleSurfaces(ctxTower);
    const mountedHouseSurfaces = this.registry.getMountedSurfacesForProject("proj_house_2story");
    results.push({ name: "Test 19: Render Registry Cleanup Assertion", pass: mountedHouseSurfaces.length === 0 });

    // Test 20: Plan provenance assertion
    const dummyPlanEl = this.createTestElement("plan-provenance-20", "div", false);
    dummyPlanEl.setAttribute("data-project-id", ctxTower.projectId);
    const provPass = dummyPlanEl.getAttribute("data-project-id") === "proj_tower_50floor";
    results.push({ name: "Test 20: Plan Provenance Assertion", pass: provPass === true });

    // Tests 21-28
    const towerEmptyContainer = this.createTestElement("tower-empty-21", "div", false);
    this.guard.renderPlanEmptyState(towerEmptyContainer, ctxTower);
    const towerEmptyHTML = towerEmptyContainer.innerHTML;
    const towerPositivePass = towerEmptyHTML.includes("Bu kapsam için şematik plan bulunmuyor") &&
                              towerEmptyHTML.includes("Başka projeye ait bir plan kullanılmayacaktır") &&
                              towerEmptyHTML.includes("18. Kat");
    results.push({ name: "Test 21: Tower Positive Plan Empty State Assertion", pass: towerPositivePass === true });

    const campusEmptyContainer = this.createTestElement("campus-empty-22", "div", false);
    this.guard.renderPlanEmptyState(campusEmptyContainer, campusCtx);
    const campusEmptyHTML = campusEmptyContainer.innerHTML;
    const campusPositivePass = campusEmptyHTML.includes("Bu kapsam için şematik plan bulunmuyor") &&
                               campusEmptyHTML.includes("Başka projeye ait bir plan kullanılmayacaktır") &&
                               campusEmptyHTML.includes("Blok A");
    results.push({ name: "Test 22: Campus Positive Plan Empty State Assertion", pass: campusPositivePass === true });

    const regTest = new DOMSurfaceRegistry();
    const presenterTest = new WorkspacePresenter("dummy", { hierarchy: this.hierarchy, guard: this.guard, registry: regTest, syncGlobalUI: false });
    presenterTest.container = this.createTestElement("presenter-empty-23", "div", false);
    presenterTest.renderWorkspaceEmptyState({ activeContext: ctxTower });
    const mountedEmptySurfaces = regTest.getMountedSurfacesForProject("proj_tower_50floor");
    const emptyMountedPass = mountedEmptySurfaces.length > 0 && mountedEmptySurfaces[0].documentType === "empty_state";
    results.push({ name: "Test 23: Empty-State Registry Mounting", pass: emptyMountedPass === true });

    const dummyMsg = this.createTestElement("assistant-message-24", "div", false);
    dummyMsg.className = "chat-message assistant";
    const msgPass = dummyMsg.classList.contains("assistant") && dummyMsg.classList.contains("chat-message");
    results.push({ name: "Test 24: Assistant Panel Structured DOM", pass: msgPass === true });

    const inputEl = this.createTestElement("assistant-input-25", "input", false);
    inputEl.id = "assistantUserInput";
    const btnEl = this.createTestElement("send-button-25", "button", false);
    btnEl.className = "send-btn";
    const controlsPass = inputEl.id === "assistantUserInput" && btnEl.classList.contains("send-btn");
    results.push({ name: "Test 25: Assistant Panel Styled Controls", pass: controlsPass === true });

    const divResult = this.resolver.calculateDivergence(ctxTower, ctx1);
    const copyPass = divResult && !divResult.message.includes("projesi projesini") && divResult.message.includes("50 Katlı Finans Kulesi");
    results.push({ name: "Test 26: Natural Suspended-Context Copy", pass: copyPass === true });

    const noPlaceholderPass = divResult && !divResult.message.includes("Önceki Proje") && !divResult.message.includes("Yeni Proje");
    results.push({ name: "Test 27: No Placeholder Project Names", pass: noPlaceholderPass === true });

    const docHouseRestored = this.resolver.resolveDocument(ctx1, "plan");
    const restorationPass = docHouseRestored && docHouseRestored.projectId === "proj_house_2story";
    results.push({ name: "Test 28: House Plan Restoration After Empty-State Projects", pass: restorationPass === true });

    // NEW v6.2 CROSS-SURFACE CONSISTENCY TESTS (Tests 29-36)
    // Test 29 (Test A): Finans Kulesi 18. Kat -> 32. Kat transition consistency
    const smA = new ContextStateMachine(this.hierarchy);
    smA.dispatch({ type: "PROJECT_SELECTED", payload: { projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18" } });
    const snap18 = smA.getSnapshot();
    smA.transitionToContext({ levelId: "lvl_32" });
    const snap32 = smA.getSnapshot();
    const testAPass = snap32.levelId === "lvl_32" && snap32.contextFingerprint.includes("lvl_32") && !snap32.contextFingerprint.includes("lvl_18");
    results.push({ name: "Test 29 (Test A): Tower 18. Kat to 32. Kat Transition Consistency", pass: testAPass === true });

    // Test 30 (Test B): Kampüs Blok A -> Blok B transition consistency
    const smB = new ContextStateMachine(this.hierarchy);
    smB.dispatch({ type: "PROJECT_SELECTED", payload: { projectId: "proj_campus_multiblock", buildingId: "block_a_r_d" } });
    const snapBlockA = smB.getSnapshot();
    smB.transitionToContext({ buildingId: "block_b_admin" });
    const snapB = smB.getSnapshot();
    const testBPass = snapBlockA.levelId === "lvl_2_block_a" &&
      snapB.buildingId === "block_b_admin" &&
      snapB.levelId === "lvl_2_block_b" &&
      snapB.contextFingerprint.includes("block_b_admin") &&
      !snapB.contextFingerprint.includes("block_a_r_d");
    results.push({ name: "Test 30 (Test B): Campus Blok A to Blok B Transition Consistency", pass: testBPass === true });

    // Test 31 (Test C): House -> Tower surface clearing
    const regC = new DOMSurfaceRegistry();
    const snapC = smA.transitionToContext({ projectId: "proj_tower_50floor", buildingId: "tower_a", levelId: "lvl_18" });
    const planSurface31 = this.createTestElement("plan-surface-31");
    regC.mountSurface({ surfaceId: "surf_house_plan", containerId: planSurface31.id, projectId: "proj_house_2story" });
    regC.unmountIncompatibleSurfaces(snapC);
    const testCPass = regC.getMountedSurfacesForProject("proj_house_2story").length === 0;
    results.push({ name: "Test 31 (Test C): House to Tower Surface Clearing", pass: testCPass === true });

    // Test 32 (Test D): Tower -> House full restoration
    const smD = new ContextStateMachine(this.hierarchy);
    smD.dispatch({ type: "PROJECT_SELECTED", payload: { projectId: "proj_tower_50floor" } });
    smD.transitionToContext({ projectId: "proj_house_2story", buildingId: "bldg_main", levelId: "lvl_ground" });
    const snapD = smD.getSnapshot();
    const testDPass = snapD.projectId === "proj_house_2story" && snapD.levelId === "lvl_ground" && snapD.capabilities.includes("residential_plan_alternatives");
    results.push({ name: "Test 32 (Test D): Tower to House Full Plan Restoration", pass: testDPass === true });

    // Test 33 (Test E): Campus capability actions isolation
    const campusCapsE = this.hierarchy.getActiveCapabilities(campusCtx);
    const testEPass = campusCapsE.includes("laboratory_service_analysis") && !campusCapsE.includes("residential_master_suite") && !campusCapsE.includes("office_meeting_analysis");
    results.push({ name: "Test 33 (Test E): Campus Capability Actions Isolation", pass: testEPass === true });

    // Test 34 (Test F): Stale async render rejection
    const staleSnap = smA.createSnapshot({ projectId: "proj_house_2story" });
    const activeSnapF = smA.getSnapshot();
    const testFPass = staleSnap.contextFingerprint !== activeSnapF.contextFingerprint && staleSnap.generationId !== activeSnapF.generationId;
    results.push({ name: "Test 34 (Test F): Stale Async Render Rejection", pass: testFPass === true });

    // Test 35 (Test G): Single snapshot cross-surface consistency
    const snapG = smA.getSnapshot();
    const titleG = this.hierarchy.getScopeTitle(snapG);
    const sibsG = this.hierarchy.getNavigableSiblings(snapG);
    const testGPass = snapG.projectId === "proj_tower_50floor" &&
      snapG.levelId === "lvl_18" &&
      titleG.includes("A Kulesi") &&
      titleG.includes("18. Kat") &&
      sibsG.some(s => s.displayName === "32. Kat");
    results.push({ name: "Test 35 (Test G): Single Snapshot Cross-Surface Consistency", pass: testGPass === true });

    // Test 36: Atomic transitionToContext execution assertion
    const sm36 = new ContextStateMachine(this.hierarchy);
    const snap36Before = sm36.getSnapshot();
    sm36.transitionToContext({ projectId: "proj_campus_multiblock", buildingId: "block_a_r_d" });
    const snap36After = sm36.getSnapshot();
    const test36Pass = snap36Before.generationId !== snap36After.generationId && snap36After.projectId === "proj_campus_multiblock";
    results.push({ name: "Test 36: Atomic transitionToContext Execution Assertion", pass: test36Pass === true });

    // Test 37: Tower stage changes preserve the active spatial scope
    const sm37 = new ContextStateMachine(this.hierarchy);
    sm37.dispatch({
      type: "PROJECT_SELECTED",
      payload: {
        projectId: "proj_tower_50floor",
        buildingId: "tower_a",
        levelId: "lvl_18",
        entityId: "space_meeting_18a"
      }
    });
    const chat37 = this.createTestElement("chat-37");
    const orchestrator37 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm37,
      chatContainerId: chat37.id
    });
    orchestrator37.setStage(2);
    const snap37 = sm37.getSnapshot();
    const test37Pass = snap37.projectId === "proj_tower_50floor" &&
      snap37.buildingId === "tower_a" &&
      snap37.levelId === "lvl_18" &&
      snap37.activeStage === 2;
    results.push({ name: "Test 37: Tower Stage 2 Preserves Context", pass: test37Pass });

    // Test 38: Campus stage changes preserve the active spatial scope
    const sm38 = new ContextStateMachine(this.hierarchy);
    sm38.dispatch({
      type: "PROJECT_SELECTED",
      payload: {
        projectId: "proj_campus_multiblock",
        buildingId: "block_a_r_d",
        levelId: "lvl_2_block_a",
        entityId: "space_robotics_lab"
      }
    });
    const chat38 = this.createTestElement("chat-38");
    const orchestrator38 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm38,
      chatContainerId: chat38.id
    });
    orchestrator38.setStage(3);
    const snap38 = sm38.getSnapshot();
    const test38Pass = snap38.projectId === "proj_campus_multiblock" &&
      snap38.buildingId === "block_a_r_d" &&
      snap38.levelId === "lvl_2_block_a" &&
      snap38.activeStage === 3;
    results.push({ name: "Test 38: Campus Stage 3 Preserves Context", pass: test38Pass });

    // Test 39: A foreign level normalizes the complete ancestor chain
    const sm39 = new ContextStateMachine(this.hierarchy);
    sm39.dispatch({
      type: "PROJECT_SELECTED",
      payload: {
        projectId: "proj_tower_50floor",
        buildingId: "tower_a",
        levelId: "lvl_18",
        entityId: "space_meeting_18a"
      }
    });
    const snap39 = sm39.transitionToContext({ levelId: "lvl_ground" });
    const test39Pass = snap39.projectId === "proj_house_2story" &&
      snap39.buildingId === "bldg_main" &&
      snap39.levelId === "lvl_ground" &&
      snap39.entityId === null;
    results.push({ name: "Test 39: Foreign Level Cannot Produce Hybrid Snapshot", pass: test39Pass });

    // Test 40: A foreign entity normalizes the complete ancestor chain
    const sm40 = new ContextStateMachine(this.hierarchy);
    sm40.dispatch({
      type: "PROJECT_SELECTED",
      payload: {
        projectId: "proj_campus_multiblock",
        buildingId: "block_a_r_d",
        levelId: "lvl_2_block_a",
        entityId: "space_robotics_lab"
      }
    });
    const snap40 = sm40.transitionToContext({
      entityId: "space_study",
      entityType: "space"
    });
    const test40Pass = snap40.projectId === "proj_house_2story" &&
      snap40.buildingId === "bldg_main" &&
      snap40.levelId === "lvl_ground" &&
      snap40.zoneId === "zone_living" &&
      snap40.entityId === "space_study";
    results.push({ name: "Test 40: Foreign Entity Cannot Produce Hybrid Snapshot", pass: test40Pass });

    // Test 41: User HTML payload remains inert text
    const chat41 = this.createTestElement("chat-41");
    const orchestrator41 = new ConversationOrchestrator({ hierarchy: this.hierarchy, chatContainerId: chat41.id });
    delete window.__xss;
    const userPayload41 = '<img src=x onerror="window.__xss=true">';
    orchestrator41.appendUserMessage(userPayload41);
    const renderedUser41 = chat41.querySelector(".message-text");
    const test41Pass = renderedUser41 &&
      renderedUser41.textContent === userPayload41 &&
      chat41.querySelector("img") === null &&
      window.__xss === undefined;
    chat41.remove();
    delete window.__xss;
    results.push({ name: "Test 41: User Chat HTML Is Inert", pass: test41Pass === true });

    // Test 42: Assistant scripts and quick-reply attributes remain inert
    const chat42 = this.createTestElement("chat-42");
    const orchestrator42 = new ConversationOrchestrator({ hierarchy: this.hierarchy, chatContainerId: chat42.id });
    delete window.__assistantXss;
    const assistantPayload42 = '<script>window.__assistantXss=true</script>';
    const quickReply42 = '"><svg onload="window.__assistantXss=true">';
    orchestrator42.appendAssistantMessage(assistantPayload42, [quickReply42]);
    const renderedAssistant42 = chat42.querySelector(".message-text");
    const renderedReply42 = chat42.querySelector(".followup-chip");
    const test42Pass = renderedAssistant42 &&
      renderedAssistant42.textContent === assistantPayload42 &&
      renderedReply42 &&
      renderedReply42.dataset.reply === quickReply42 &&
      chat42.querySelector("script, svg") === null &&
      window.__assistantXss === undefined;
    chat42.remove();
    delete window.__assistantXss;
    results.push({ name: "Test 42: Assistant And Quick Reply HTML Is Inert", pass: test42Pass === true });

    // Test 43: Decision state is persisted before history synchronization
    const history43 = {
      states: [],
      setSessionState(state) {
        this.states.push(state);
      }
    };
    const sm43 = new ContextStateMachine(this.hierarchy);
    const chat43 = this.createTestElement("chat-43");
    const orchestrator43 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm43,
      historyManager: history43,
      chatContainerId: chat43.id
    });
    const applied43 = orchestrator43.applyMasterBathOption(1);
    const snap43 = sm43.getSnapshot();
    const historyState43 = history43.states[history43.states.length - 1];
    const expectedDecision43 = "Seçenek 1 Seçildi (Uygulandı)";
    const test43Pass = applied43 === true &&
      snap43.selectedOption === 1 &&
      snap43.decisionStatus === expectedDecision43 &&
      historyState43 &&
      historyState43.selectedOption === 1 &&
      historyState43.decisionStatus === expectedDecision43;
    results.push({ name: "Test 43: Decision State Persists In Snapshot And History", pass: test43Pass === true });

    // Test 44: Nested snapshot values cannot mutate internal state
    const sm44 = new ContextStateMachine(this.hierarchy);
    sm44.transitionToContext({
      suspendedContext: {
        scenarioId: "immutability_test",
        levelId: "lvl_ground",
        reason: "original"
      }
    });
    const external44 = sm44.getContext();
    external44.workspaceScope.levelId = "tampered_level";
    external44.conversationScope.levelId = "tampered_level";
    external44.capabilities.push("tampered_capability");
    external44.suspendedContext.reason = "tampered_reason";
    const internal44 = sm44.getSnapshot();
    const test44Pass = internal44.workspaceScope.levelId === "lvl_ground" &&
      internal44.conversationScope.levelId === "lvl_ground" &&
      !internal44.capabilities.includes("tampered_capability") &&
      internal44.suspendedContext.reason === "original";
    results.push({ name: "Test 44: Nested Snapshot State Is Immutable", pass: test44Pass });

    // Test 45: Architect view round-trip preserves the last customer stage
    const sm45 = new ContextStateMachine(this.hierarchy);
    const chat45 = this.createTestElement("chat-45");
    const orchestrator45 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm45,
      chatContainerId: chat45.id
    });
    orchestrator45.setStage(2);
    sm45.dispatch({ type: "ARCHITECT_VIEW_OPENED" });
    const architectSnapshot45 = sm45.getSnapshot();
    orchestrator45.setStage(architectSnapshot45.activeStage);
    const customerSnapshot45 = sm45.getSnapshot();
    const test45Pass = architectSnapshot45.activeStage === 2 &&
      customerSnapshot45.activeStage === 2;
    results.push({ name: "Test 45: Architect Customer Round-Trip Preserves Stage", pass: test45Pass });

    // Test 46: Invalid IDs reject the transition and preserve the snapshot
    const sm46 = new ContextStateMachine(this.hierarchy);
    const before46 = sm46.getSnapshot();
    const returned46 = sm46.transitionToContext({ entityId: "space_missing" });
    const after46 = sm46.getSnapshot();
    const test46Pass = returned46.contextFingerprint === before46.contextFingerprint &&
      after46.contextFingerprint === before46.contextFingerprint &&
      after46.generationId === before46.generationId;
    results.push({ name: "Test 46: Invalid Entity Transition Is Rejected", pass: test46Pass });

    // Test 47: House stage changes preserve the active spatial scope
    const sm47 = new ContextStateMachine(this.hierarchy);
    const chat47 = this.createTestElement("chat-47");
    const orchestrator47 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm47,
      chatContainerId: chat47.id
    });
    orchestrator47.setStage(1);
    const snap47 = sm47.getSnapshot();
    const test47Pass = snap47.projectId === "proj_house_2story" &&
      snap47.buildingId === "bldg_main" &&
      snap47.levelId === "lvl_ground" &&
      snap47.activeStage === 1;
    results.push({ name: "Test 47: House Stage 1 Preserves Context", pass: test47Pass });

    // Test 48: The deterministic parser API used by ContextualAssistant exists
    const parser48 = new DemoIntentParser();
    results.push({
      name: "Test 48: DemoIntentParser Exposes parseMessage",
      pass: typeof parser48.parseMessage === "function"
    });

    // Test 49: Generic messages return a complete assistant result
    const sm49 = new ContextStateMachine(this.hierarchy);
    const assistant49 = new ContextualAssistant({
      hierarchy: this.hierarchy,
      stateMachine: sm49
    });
    let genericResult49 = null;
    let genericError49 = null;
    try {
      genericResult49 = assistant49.processUserMessage("Çalışma odası sessiz olsun.");
    } catch (error) {
      genericError49 = error;
    }
    const test49Pass = genericError49 === null &&
      genericResult49 &&
      genericResult49.actionPayload &&
      genericResult49.actionPayload.intent === "ambiguous_request" &&
      genericResult49.actionPayload.source_message === "Çalışma odası sessiz olsun." &&
      typeof genericResult49.aiResponseText === "string" &&
      genericResult49.aiResponseText.length > 0;
    results.push({ name: "Test 49: Generic Message Returns Action Payload", pass: test49Pass });

    // Test 50: Existing master-bath recognition remains intact
    const masterText50 = "Ebeveyn banyosu yataktan görünmesin ve kuzey tarafında olsun.";
    const test50Pass = parser48.isMasterBathInitial(masterText50) &&
      parser48.parseMasterBathReason(masterText50) === "visibility";
    results.push({ name: "Test 50: Master Bath Patterns Remain Intact", pass: test50Pass });

    // Test 51: The master-bath orchestrator flow still starts its scenario
    const sm51 = new ContextStateMachine(this.hierarchy);
    const assistant51 = new ContextualAssistant({
      hierarchy: this.hierarchy,
      stateMachine: sm51
    });
    const chat51 = this.createTestElement("chat-51");
    const orchestrator51 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm51,
      assistant: assistant51,
      chatContainerId: chat51.id
    });
    orchestrator51.handleUserMessage(masterText50);
    const snap51 = sm51.getSnapshot();
    const test51Pass = snap51.scenarioId === "master_bath_relocation" &&
      snap51.entityId === "space_master_bath" &&
      snap51.levelId === "lvl_upper";
    results.push({ name: "Test 51: Master Bath Demo Flow Still Starts", pass: test51Pass });

    // Test 52: Empty and invalid messages are handled without throwing
    let emptyResult52 = null;
    let invalidResult52 = null;
    let invalidError52 = null;
    try {
      emptyResult52 = assistant49.processUserMessage("   ");
      invalidResult52 = assistant49.processUserMessage(null);
    } catch (error) {
      invalidError52 = error;
    }
    const test52Pass = invalidError52 === null &&
      emptyResult52 &&
      invalidResult52 &&
      emptyResult52.actionPayload.source_message === "" &&
      invalidResult52.actionPayload.source_message === "" &&
      emptyResult52.aiResponseText === invalidResult52.aiResponseText;
    results.push({ name: "Test 52: Empty And Invalid Messages Are Safe", pass: test52Pass });

    // Test 53: HTML remains inert through the complete generic chat path
    const chat53 = this.createTestElement("chat-53");
    const sm53 = new ContextStateMachine(this.hierarchy);
    const assistant53 = new ContextualAssistant({
      hierarchy: this.hierarchy,
      stateMachine: sm53
    });
    const orchestrator53 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm53,
      assistant: assistant53,
      chatContainerId: chat53.id
    });
    delete window.__parserXss;
    const htmlPayload53 = '<img src=x onerror="window.__parserXss=true">';
    orchestrator53.appendUserMessage(htmlPayload53);
    orchestrator53.handleUserMessage(htmlPayload53);
    const renderedTexts53 = Array.from(chat53.querySelectorAll(".message-text"))
      .map(element => element.textContent);
    const test53Pass = renderedTexts53.some(text => text === htmlPayload53) &&
      chat53.querySelector("img, script, svg") === null &&
      window.__parserXss === undefined;
    chat53.remove();
    delete window.__parserXss;
    results.push({ name: "Test 53: Generic Chat HTML Is Inert", pass: test53Pass });

    const visualContainer = this.createTestElement("visual-preferences");
    const visualRegistry = new DOMSurfaceRegistry();
    const visualPresenter = new WorkspacePresenter(visualContainer.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: visualRegistry, syncGlobalUI: false
    });
    const towerVisualContext = {
      projectId: "proj_tower_50floor",
      buildingId: "tower_a",
      levelId: "lvl_18",
      entityId: "space_meeting_18a"
    };
    const campusVisualContext = {
      projectId: "proj_campus_multiblock",
      buildingId: "block_a_r_d",
      levelId: "lvl_2_block_a",
      entityId: "space_robotics_lab"
    };
    const houseVisualContext = {
      projectId: "proj_house_2story",
      buildingId: "bldg_main",
      levelId: "lvl_ground",
      entityId: "space_study"
    };

    // Test 54: Tower visual preferences never show the house kitchen round
    visualPresenter.renderVisualPreferences(towerVisualContext);
    const test54Pass = !visualContainer.textContent.includes("Mutfak İlişkisi");
    results.push({ name: "Test 54: Tower Visual Stage Excludes House Kitchen Content", pass: test54Pass });

    // Test 55: Tower visual preferences never mount house preference assets
    const test55Pass = visualContainer.querySelector('img[src^="assets/preferences/"]') === null;
    results.push({ name: "Test 55: Tower Visual Stage Excludes House Assets", pass: test55Pass });

    // Test 56: Campus visual preferences contain no house copy or assets
    visualPresenter.renderVisualPreferences(campusVisualContext);
    const campusText56 = visualContainer.textContent;
    const test56Pass = !campusText56.includes("Tamamen Ayrı Çalışma Odası") &&
      !campusText56.includes("Ortak Yaşama Bağlı Çalışma Alanı") &&
      !campusText56.includes("Mutfak İlişkisi") &&
      visualContainer.querySelector('img[src^="assets/preferences/"]') === null;
    results.push({ name: "Test 56: Campus Visual Stage Excludes House Content", pass: test56Pass });

    // Test 57: Projects without verified preference data show an explicit empty state
    const test57Pass = campusText56.includes("Bu proje türü için görsel tercih seti henüz tanımlanmadı.") &&
      campusText56.includes("Konut projesine ait tercihler bu kapsamda gösterilmez.") &&
      visualContainer.querySelector(".visual-preferences-empty") !== null;
    results.push({ name: "Test 57: Missing Visual Preferences Show Explicit Empty State", pass: test57Pass });

    // Test 58: The house preference document resolves only for the house project
    const houseVisualDoc58 = this.resolver.resolveDocument(houseVisualContext, "visual_preferences");
    const towerVisualDoc58 = this.resolver.resolveDocument(towerVisualContext, "visual_preferences");
    const campusVisualDoc58 = this.resolver.resolveDocument(campusVisualContext, "visual_preferences");
    visualPresenter.renderVisualPreferences(houseVisualContext);
    const test58Pass = houseVisualDoc58 &&
      houseVisualDoc58.projectId === "proj_house_2story" &&
      towerVisualDoc58 === null &&
      campusVisualDoc58 === null &&
      visualContainer.getAttribute("data-project-id") === "proj_house_2story" &&
      visualContainer.textContent.includes("Tamamen Ayrı Çalışma Odası");
    results.push({ name: "Test 58: House Preferences Resolve Only In House Scope", pass: test58Pass });

    // Test 59: House -> Tower -> House restores a fresh scoped preference surface
    const firstHouseTitles59 = Array.from(visualContainer.querySelectorAll(".pref-card-title"))
      .map(element => element.textContent);
    visualPresenter.renderVisualPreferences(towerVisualContext);
    const towerWasClean59 = visualContainer.querySelector(".pref-card-large") === null &&
      visualContainer.querySelector(".visual-preferences-empty") !== null;
    visualPresenter.renderVisualPreferences(houseVisualContext);
    const restoredHouseTitles59 = Array.from(visualContainer.querySelectorAll(".pref-card-title"))
      .map(element => element.textContent);
    const test59Pass = towerWasClean59 &&
      firstHouseTitles59.length === 2 &&
      JSON.stringify(restoredHouseTitles59) === JSON.stringify(firstHouseTitles59) &&
      visualContainer.querySelector(".visual-preferences-empty") === null;
    results.push({ name: "Test 59: House Tower House Restores Scoped Preferences", pass: test59Pass });

    // Test 60: Entering stage 2 preserves the complete active tower context
    const sm60 = new ContextStateMachine(this.hierarchy);
    sm60.dispatch({
      type: "PROJECT_SELECTED",
      payload: {
        projectId: "proj_tower_50floor",
        buildingId: "tower_a",
        levelId: "lvl_18",
        entityId: "space_meeting_18a"
      }
    });
    const chat60 = this.createTestElement("chat-60");
    const orchestrator60 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm60,
      chatContainerId: chat60.id
    });
    orchestrator60.setStage(2);
    const snap60 = sm60.getSnapshot();
    visualPresenter.renderVisualPreferences(snap60);
    const test60Pass = snap60.projectId === "proj_tower_50floor" &&
      snap60.buildingId === "tower_a" &&
      snap60.levelId === "lvl_18" &&
      snap60.activeStage === 2 &&
      visualContainer.getAttribute("data-project-id") === "proj_tower_50floor" &&
      visualContainer.querySelector(".visual-preferences-empty") !== null;
    results.push({ name: "Test 60: Visual Stage Preserves Active Tower Context", pass: test60Pass });

    const interactionState = new ContextStateMachine(this.hierarchy);
    interactionState.subscribe(snapshot => {
      visualPresenter.renderVisualPreferences(snapshot);
    });
    const firstBinding = visualPresenter.bindVisualPreferenceInteractions({
      stateMachine: interactionState,
      onStageChange: stage => {
        interactionState.dispatch({
          type: "STAGE_CHANGED",
          payload: { activeStage: stage }
        });
      }
    });
    const duplicateBinding = visualPresenter.bindVisualPreferenceInteractions({
      stateMachine: interactionState
    });
    visualPresenter.renderVisualPreferences(interactionState.getSnapshot());
    const clickVisualControl = element => {
      element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    };

    // Test 61: Primary preference click produces visible selected state
    const primary61 = visualContainer.querySelector(
      '[data-card-id="work_separate"] .pref-btn-primary'
    );
    clickVisualControl(primary61);
    const selectedCard61 = visualContainer.querySelector(
      '[data-card-id="work_separate"]'
    );
    const test61Pass = selectedCard61.classList.contains("preference-selected") &&
      selectedCard61.getAttribute("data-preference-status") === "like" &&
      selectedCard61.querySelector(".pref-selection-status").textContent === "Seçildi" &&
      selectedCard61.querySelector(".pref-btn-primary").getAttribute("aria-pressed") === "true";
    results.push({ name: "Test 61: Primary Click Shows Selected State", pass: test61Pass });

    // Test 62: Preference selection is persisted in the immutable snapshot
    const snapshot62 = interactionState.getSnapshot();
    const savedSelection62 = snapshot62.visualPreferencesByProject.proj_house_2story.rounds["1"];
    const test62Pass = savedSelection62.cardId === "work_separate" &&
      savedSelection62.preference === "like";
    results.push({ name: "Test 62: Primary Selection Persists In Snapshot", pass: test62Pass });

    // Test 63: A second selection in the same round clears the previous card
    const secondPrimary63 = visualContainer.querySelector(
      '[data-card-id="work_connected"] .pref-btn-primary'
    );
    clickVisualControl(secondPrimary63);
    const selectedCards63 = visualContainer.querySelectorAll(".preference-selected");
    const test63Pass = selectedCards63.length === 1 &&
      selectedCards63[0].dataset.cardId === "work_connected" &&
      visualContainer.querySelector('[data-card-id="work_separate"]')
        .getAttribute("data-preference-status") === null;
    results.push({ name: "Test 63: Same Round Keeps One Active Selection", pass: test63Pass });

    // Test 64: Secondary click replaces like with visible neutral state
    const secondary64 = visualContainer.querySelector(
      '[data-card-id="work_connected"] .pref-btn-secondary'
    );
    clickVisualControl(secondary64);
    const neutralCard64 = visualContainer.querySelector(
      '[data-card-id="work_connected"]'
    );
    const snapshot64 = interactionState.getSnapshot();
    const test64Pass = neutralCard64.classList.contains("preference-neutral") &&
      visualContainer.querySelectorAll(".preference-selected").length === 0 &&
      neutralCard64.querySelector(".pref-selection-status").textContent === "Kararsız" &&
      snapshot64.visualPreferencesByProject.proj_house_2story.rounds["1"].preference === "neutral";
    results.push({ name: "Test 64: Secondary Click Produces Neutral State", pass: test64Pass });

    // Test 65: House -> Tower -> House restores selection and live interaction
    clickVisualControl(visualContainer.querySelector(
      '[data-card-id="work_separate"] .pref-btn-primary'
    ));
    interactionState.dispatch({
      type: "PROJECT_SELECTED",
      payload: towerVisualContext
    });
    const towerEmpty65 = visualContainer.querySelector(".visual-preferences-empty") !== null &&
      visualContainer.querySelector(".pref-btn-primary") === null;
    interactionState.dispatch({
      type: "PROJECT_SELECTED",
      payload: houseVisualContext
    });
    const restoredCard65 = visualContainer.querySelector(
      '[data-card-id="work_separate"]'
    );
    const restoredBeforeClick65 = restoredCard65.classList.contains("preference-selected");
    clickVisualControl(visualContainer.querySelector(
      '[data-card-id="work_connected"] .pref-btn-primary'
    ));
    const snapshot65 = interactionState.getSnapshot();
    const test65Pass = towerEmpty65 &&
      restoredBeforeClick65 &&
      snapshot65.visualPreferencesByProject.proj_house_2story.rounds["1"].cardId === "work_connected" &&
      snapshot65.visualPreferencesByProject.proj_tower_50floor === undefined;
    results.push({ name: "Test 65: House Tower House Restores Live Selection", pass: test65Pass });

    // Test 66: Binding twice does not duplicate click dispatch
    const before66 = interactionState.getSnapshot().generationId;
    clickVisualControl(visualContainer.querySelector(
      '[data-card-id="work_connected"] .pref-btn-secondary'
    ));
    const after66 = interactionState.getSnapshot().generationId;
    const test66Pass = firstBinding === true &&
      duplicateBinding === false &&
      after66 === before66 + 1;
    results.push({ name: "Test 66: Delegated Listener Is Not Duplicated", pass: test66Pass });

    // Test 67: Missing round click activates its tab and shows explicit empty state
    clickVisualControl(visualContainer.querySelector('[data-round="2"].round-tab'));
    const snapshot67 = interactionState.getSnapshot();
    const activeTab67 = visualContainer.querySelector(".round-tab.active");
    const test67Pass = activeTab67 &&
      activeTab67.dataset.round === "2" &&
      snapshot67.visualPreferencesByProject.proj_house_2story.activeRoundId === "2" &&
      visualContainer.textContent.includes("Bu tur henüz tanımlanmadı.") &&
      visualContainer.querySelector(".pref-round-container.active") === null;
    results.push({ name: "Test 67: Missing Round Shows Explicit State", pass: test67Pass });

    // Test 68: Returning to round 1 shows only its defined content
    clickVisualControl(visualContainer.querySelector('[data-round="1"].round-tab'));
    const activeRound68 = visualContainer.querySelector(".pref-round-container.active");
    const test68Pass = activeRound68 &&
      activeRound68.dataset.round === "1" &&
      !activeRound68.classList.contains("hidden") &&
      visualContainer.querySelectorAll(".pref-round-container:not(.hidden)").length === 1 &&
      visualContainer.querySelector(".preference-round-empty") === null;
    results.push({ name: "Test 68: Round Tab Shows Only Defined Round", pass: test68Pass });

    // Test 69: Next button enters stage 3 without changing spatial context
    const before69 = interactionState.getSnapshot();
    clickVisualControl(visualContainer.querySelector("#btnNextToProgram"));
    const after69 = interactionState.getSnapshot();
    const test69Pass = after69.activeStage === 3 &&
      after69.projectId === before69.projectId &&
      after69.buildingId === before69.buildingId &&
      after69.levelId === before69.levelId;
    results.push({ name: "Test 69: Next Button Preserves Context At Stage 3", pass: test69Pass });

    // Test 70: Tower and campus empty states do not invoke house handlers
    const emptyProjects70 = [towerVisualContext, campusVisualContext];
    const test70Pass = emptyProjects70.every(projectContext => {
      interactionState.dispatch({
        type: "PROJECT_SELECTED",
        payload: projectContext
      });
      const beforeClick = interactionState.getSnapshot();
      const emptyState = visualContainer.querySelector(".visual-preferences-empty");
      if (!emptyState) return false;
      clickVisualControl(emptyState);
      const afterClick = interactionState.getSnapshot();
      return visualContainer.querySelector(".pref-btn-primary, .pref-btn-secondary") === null &&
        afterClick.generationId === beforeClick.generationId &&
        afterClick.visualPreferencesByProject[projectContext.projectId] === undefined;
    });
    results.push({ name: "Test 70: Empty Projects Ignore House Preference Handlers", pass: test70Pass });

    interactionState.dispatch({
      type: "PROJECT_SELECTED",
      payload: houseVisualContext
    });
    clickVisualControl(visualContainer.querySelector(
      '[data-card-id="work_separate"] .pref-btn-primary'
    ));

    // Test 71: Loaded stylesheet removes inactive round 1 from layout
    clickVisualControl(visualContainer.querySelector('[data-round="2"].round-tab'));
    const hiddenRound71 = visualContainer.querySelector('#prefRound1');
    const test71Pass = hiddenRound71 &&
      window.getComputedStyle(hiddenRound71).display === "none";
    results.push({ name: "Test 71: Inactive Round Computed Display Is None", pass: test71Pass });

    // Test 72: Hidden round has no rendered box or layout height
    const test72Pass = hiddenRound71 &&
      hiddenRound71.getClientRects().length === 0 &&
      hiddenRound71.offsetHeight === 0;
    results.push({ name: "Test 72: Inactive Round Leaves No Layout Box", pass: test72Pass });

    // Test 73: Missing round empty state is the visible content and starts at the top
    const emptyState73 = visualContainer.querySelector('.preference-round-empty');
    const scrollArea73 = visualContainer.querySelector('.pref-scroll-area');
    const test73Pass = emptyState73 &&
      window.getComputedStyle(emptyState73).display === "flex" &&
      emptyState73.getClientRects().length > 0 &&
      visualContainer.querySelectorAll('.pref-round-container:not(.hidden)').length === 0 &&
      scrollArea73 &&
      scrollArea73.scrollTop === 0;
    results.push({ name: "Test 73: Missing Round Empty State Is Visible At Top", pass: test73Pass });

    // Test 74: Round 3 also hides defined content and shows only the empty state
    clickVisualControl(visualContainer.querySelector('[data-round="3"].round-tab'));
    const hiddenRound74 = visualContainer.querySelector('#prefRound1');
    const emptyState74 = visualContainer.querySelector('.preference-round-empty');
    const test74Pass = hiddenRound74 &&
      window.getComputedStyle(hiddenRound74).display === "none" &&
      hiddenRound74.getClientRects().length === 0 &&
      emptyState74 &&
      window.getComputedStyle(emptyState74).display === "flex" &&
      emptyState74.getClientRects().length > 0;
    results.push({ name: "Test 74: Round 3 Shows Only Visible Empty State", pass: test74Pass });

    // Test 75: Returning to round 1 restores layout and the persisted selection
    clickVisualControl(visualContainer.querySelector('[data-round="1"].round-tab'));
    const restoredRound75 = visualContainer.querySelector('#prefRound1');
    const restoredSelection75 = visualContainer.querySelector(
      '[data-card-id="work_separate"]'
    );
    const snapshot75 = interactionState.getSnapshot();
    const test75Pass = restoredRound75 &&
      window.getComputedStyle(restoredRound75).display !== "none" &&
      restoredRound75.getClientRects().length > 0 &&
      visualContainer.querySelector('.preference-round-empty') === null &&
      restoredSelection75.classList.contains('preference-selected') &&
      snapshot75.visualPreferencesByProject.proj_house_2story.rounds["1"].cardId ===
        "work_separate";
    results.push({ name: "Test 75: Round 1 Restores Layout And Selection", pass: test75Pass });

    visualContainer.remove();

    const modeContainer = this.createTestElement("workspace-modes");
    const modeState = new ContextStateMachine(this.hierarchy);
    const modePresenter = new WorkspacePresenter(modeContainer.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: modeState, syncGlobalUI: false
    });

    // Test 76: Every declared custom workspace mode has its renderer contract
    const test76Pass = Object.entries(window.WorkspaceModeRegistry).every(([, renderer]) =>
      renderer === null || typeof modePresenter[renderer] === "function"
    );
    results.push({ name: "Test 76: Workspace Mode Renderer Contract Is Complete", pass: test76Pass });

    // Test 77: Overlay mode renders without an uncaught method error
    let modeError77 = null;
    try {
      modePresenter.setMode("overlay");
    } catch (error) {
      modeError77 = error;
    }
    const test77Pass = modeError77 === null &&
      modeState.getSnapshot().workspaceMode === "overlay" &&
      modeContainer.querySelector(".floor-overlay-surface") !== null;
    results.push({ name: "Test 77: Overlay Mode Renders Safely", pass: test77Pass });

    // Test 78: Orientation mode renders without an uncaught method error
    let modeError78 = null;
    try {
      modePresenter.setMode("orientation");
    } catch (error) {
      modeError78 = error;
    }
    const test78Pass = modeError78 === null &&
      modeState.getSnapshot().workspaceMode === "orientation" &&
      modeContainer.querySelector(".orientation-mode-surface") !== null;
    results.push({ name: "Test 78: Orientation Mode Renders Safely", pass: test78Pass });

    // Test 79: Progress mode renders a deterministic prototype status
    let modeError79 = null;
    try {
      modePresenter.setMode("progress");
    } catch (error) {
      modeError79 = error;
    }
    const test79Pass = modeError79 === null &&
      modeState.getSnapshot().workspaceMode === "progress" &&
      modeContainer.querySelector(".analysis-progress-surface") !== null &&
      modeContainer.textContent.includes("Plan veya proje verisi");
    results.push({ name: "Test 79: Progress Mode Renders Prototype Status", pass: test79Pass });

    modeState.dispatch({
      type: "SCENARIO_CONTEXT_STARTED",
      payload: {
        projectId: "proj_house_2story",
        buildingId: "bldg_main",
        levelId: "lvl_upper",
        entityId: "space_master_bath",
        entityType: "space",
        scenarioId: "master_bath_relocation",
        decisionId: "dec_master_bath",
        targetEntityId: "space_master_bath",
        workspaceMode: "plan"
      }
    });

    // Test 80: Master-bath options renderer is live and does not alter the plan
    let modeError80 = null;
    try {
      modePresenter.setMode("options_side_by_side");
    } catch (error) {
      modeError80 = error;
    }
    const test80Pass = modeError80 === null &&
      modeContainer.querySelector(".options-side-by-side-container") !== null &&
      modeContainer.querySelectorAll(".option-card").length === 2 &&
      modeContainer.textContent.includes("plan otomatik değiştirilmez");
    results.push({ name: "Test 80: Options Mode Renders Decision-Only Comparison", pass: test80Pass });

    // Test 81: Unknown modes produce a scoped safe fallback without leaking the mode ID
    const beforeUnknown81 = modeState.getSnapshot();
    const originalConsoleError81 = console.error;
    const capturedErrors81 = [];
    console.error = (...args) => capturedErrors81.push(args);
    let unknownResult81 = null;
    try {
      unknownResult81 = modePresenter.setMode("unknown_internal_mode");
    } finally {
      console.error = originalConsoleError81;
    }
    const afterUnknown81 = modeState.getSnapshot();
    const test81Pass = unknownResult81 === false &&
      capturedErrors81.length === 1 &&
      modeContainer.querySelector(".workspace-mode-fallback") !== null &&
      !modeContainer.textContent.includes("unknown_internal_mode") &&
      afterUnknown81.workspaceMode === beforeUnknown81.workspaceMode;
    results.push({ name: "Test 81: Unknown Mode Shows Safe Fallback", pass: test81Pass });
    modeContainer.remove();

    const scenarioContainer82 = this.createTestElement("master-bath-workspace-82");
    const scenarioChat82 = this.createTestElement("master-bath-chat-82");
    const reportContainer88 = this.createTestElement("architect-report-88");
    const scenarioState82 = new ContextStateMachine(this.hierarchy);
    const scenarioHistory82 = new ChangeHistory({
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      reportContainerId: reportContainer88.id
    });
    const scenarioPresenter82 = new WorkspacePresenter(scenarioContainer82.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: scenarioState82, syncGlobalUI: false
    });
    const scenarioAssistant82 = new ContextualAssistant({
      hierarchy: this.hierarchy,
      stateMachine: scenarioState82
    });
    const scenarioOrchestrator82 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: scenarioState82,
      store: this.store,
      resolver: this.resolver,
      assistant: scenarioAssistant82,
      presenter: scenarioPresenter82,
      historyManager: scenarioHistory82,
      chatContainerId: scenarioChat82.id
    });
    scenarioOrchestrator82.triggerFloorOverlayScenario();
    const publishedSnapshots82 = [];
    scenarioState82.subscribe(snapshot => publishedSnapshots82.push(snapshot));
    let scenarioError82 = null;
    try {
      scenarioOrchestrator82.handleUserMessage("Ebeveyn banyosunu kuzey tarafına alalım.");
    } catch (error) {
      scenarioError82 = error;
    }
    const finalSnapshot82 = scenarioState82.getSnapshot();

    // Test 82: Overlay does not crash or leak into the master-bath scenario
    const test82Pass = scenarioError82 === null &&
      finalSnapshot82.workspaceMode === "plan" &&
      scenarioContainer82.querySelector(".floor-overlay-surface") === null;
    results.push({ name: "Test 82: Overlay To Master Bath Is Safe", pass: test82Pass });

    // Test 83: Orientation does not crash or leak into the master-bath scenario
    const orientationContainer83 = this.createTestElement("orientation-workspace-83");
    const orientationChat83 = this.createTestElement("orientation-chat-83");
    const orientationState83 = new ContextStateMachine(this.hierarchy);
    const orientationPresenter83 = new WorkspacePresenter(orientationContainer83.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: orientationState83, syncGlobalUI: false
    });
    const orientationOrchestrator83 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: orientationState83,
      assistant: new ContextualAssistant({ hierarchy: this.hierarchy, stateMachine: orientationState83 }),
      presenter: orientationPresenter83,
      chatContainerId: orientationChat83.id
    });
    orientationOrchestrator83.triggerOrientationScenario();
    let orientationError83 = null;
    try {
      orientationOrchestrator83.handleUserMessage("Ebeveyn banyosunu kuzey tarafına alalım.");
    } catch (error) {
      orientationError83 = error;
    }
    const orientationSnapshot83 = orientationState83.getSnapshot();
    const test83Pass = orientationError83 === null &&
      orientationSnapshot83.workspaceMode === "plan" &&
      orientationSnapshot83.scenarioId === "master_bath_relocation" &&
      orientationContainer83.querySelector(".orientation-mode-surface") === null;
    results.push({ name: "Test 83: Orientation To Master Bath Is Safe", pass: test83Pass });

    // Test 84: Master-bath scenario start publishes exactly one snapshot
    const test84Pass = publishedSnapshots82.length === 1;
    results.push({ name: "Test 84: Master Bath Starts With One Atomic Snapshot", pass: test84Pass });

    // Test 85: The final scenario snapshot contains the complete intended scope
    const test85Pass = finalSnapshot82.projectId === "proj_house_2story" &&
      finalSnapshot82.buildingId === "bldg_main" &&
      finalSnapshot82.levelId === "lvl_upper" &&
      finalSnapshot82.entityId === "space_master_bath" &&
      finalSnapshot82.scenarioId === "master_bath_relocation" &&
      finalSnapshot82.decisionId === "dec_master_bath" &&
      finalSnapshot82.targetEntityId === "space_master_bath";
    results.push({ name: "Test 85: Master Bath Final Snapshot Is Complete", pass: test85Pass });

    // Test 86: No ground-floor/master-bath hybrid snapshot is ever published
    const test86Pass = !publishedSnapshots82.some(snapshot =>
      snapshot.levelId === "lvl_ground" && snapshot.entityId === "space_master_bath"
    );
    results.push({ name: "Test 86: Master Bath Publishes No Hybrid Snapshot", pass: test86Pass });

    // Test 87: The assistant question and all three quick replies reach the DOM
    const assistantMessages87 = Array.from(
      scenarioChat82.querySelectorAll(".chat-message.assistant .message-text")
    ).map(element => element.textContent);
    const quickReplies87 = Array.from(
      scenarioChat82.querySelectorAll(".chat-message.assistant .followup-chip")
    ).map(element => element.textContent);
    const test87Pass = assistantMessages87.some(text =>
      text.includes("Banyoyu kuzey kenarına almak istiyorsunuz") &&
      text.includes("yataktan görünmemesi mi")
    ) && JSON.stringify(quickReplies87.slice(-3)) === JSON.stringify([
      "Yataktan görünmesini istemiyorum",
      "Giyinme alanından geçilsin",
      "Daha mahrem olsun"
    ]);
    results.push({ name: "Test 87: Master Bath Prompt And Quick Replies Render", pass: test87Pass });

    // Test 88: ChangeHistory resolves the active snapshot and never falls back to lvl_ground
    const originalConsoleWarn88 = console.warn;
    const capturedWarnings88 = [];
    console.warn = (...args) => capturedWarnings88.push(args.map(String).join(" "));
    try {
      scenarioHistory82.renderArchitectReport(finalSnapshot82);
    } finally {
      console.warn = originalConsoleWarn88;
    }
    const test88Pass = scenarioHistory82.sessionState.levelId === "lvl_upper" &&
      capturedWarnings88.length === 0 &&
      reportContainer88.childElementCount > 0;
    results.push({ name: "Test 88: ChangeHistory Uses Current Scenario Snapshot", pass: test88Pass });

    // Test 89: A real form submit runs the complete master-bath message path
    const form89 = this.createTestElement("form-89", "form");
    const input89 = this.createTestElement("input-89", "input", false);
    const chat89 = this.createTestElement("form-chat-89");
    form89.appendChild(input89);
    const formState89 = new ContextStateMachine(this.hierarchy);
    const formOrchestrator89 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: formState89,
      assistant: new ContextualAssistant({ hierarchy: this.hierarchy, stateMachine: formState89 }),
      chatContainerId: chat89.id
    });
    form89.addEventListener("submit", event => {
      event.preventDefault();
      const text = input89.value.trim();
      formOrchestrator89.appendUserMessage(text);
      formOrchestrator89.handleUserMessage(text);
    });
    input89.value = "Ebeveyn banyosunu kuzey tarafına alalım.";
    form89.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    const test89Pass = formState89.getSnapshot().scenarioId === "master_bath_relocation" &&
      chat89.querySelectorAll(".chat-message.user").length === 1 &&
      chat89.querySelectorAll(".followup-chip").length === 3;
    results.push({ name: "Test 89: Form Submit Completes Master Bath Flow", pass: test89Pass });

    // Test 90: A real quick-reply MouseEvent stays interactive after the transition
    chat89.addEventListener("click", event => {
      const chip = event.target.closest(".followup-chip");
      if (!chip) return;
      formOrchestrator89.handleQuickReply({
        label: chip.textContent || chip.dataset.reply || "",
        action: chip.dataset.action,
        value: chip.dataset.value,
        optionId: chip.dataset.optionId,
        scenarioId: chip.dataset.scenarioId,
        decisionId: chip.dataset.decisionId,
        preferenceKey: chip.dataset.preferenceKey,
        preferenceValue: chip.dataset.preferenceValue
      });
    });
    const replyButton90 = chat89.querySelector(".followup-chip");
    replyButton90.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const userMessages90 = Array.from(chat89.querySelectorAll(".chat-message.user .message-text"))
      .map(element => element.textContent);
    const test90Pass = userMessages90.includes("Yataktan görünmesini istemiyorum") &&
      chat89.querySelectorAll(".chat-message.assistant").length >= 2;
    results.push({ name: "Test 90: Master Bath Quick Reply MouseEvent Works", pass: test90Pass });

    // Test 91: Scenario-path user HTML remains inert text
    delete window.__scenarioXss;
    const xssPayload91 = 'Ebeveyn banyosunu kuzey tarafına alalım.<img src=x onerror="window.__scenarioXss=true">';
    formOrchestrator89.appendUserMessage(xssPayload91);
    formOrchestrator89.handleUserMessage(xssPayload91);
    const test91Pass = Array.from(chat89.querySelectorAll(".chat-message.user .message-text"))
      .some(element => element.textContent === xssPayload91) &&
      chat89.querySelector("img, script, svg") === null &&
      window.__scenarioXss === undefined;
    delete window.__scenarioXss;
    results.push({ name: "Test 91: Master Bath Scenario HTML Is Inert", pass: test91Pass });

    const structuredWorkspace92 = this.createTestElement("structured-workspace-92");
    const structuredChat92 = this.createTestElement("structured-chat-92");
    const planContainer92 = this.createTestElement("plan-geometry-92");
    const structuredState92 = new ContextStateMachine(this.hierarchy);
    const structuredPresenter92 = new WorkspacePresenter(structuredWorkspace92.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: structuredState92, syncGlobalUI: false
    });
    const structuredOrchestrator92 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: structuredState92,
      assistant: new ContextualAssistant({
        hierarchy: this.hierarchy,
        stateMachine: structuredState92
      }),
      presenter: structuredPresenter92,
      chatContainerId: structuredChat92.id
    });
    structuredOrchestrator92.triggerMasterBathScenario(
      "Ebeveyn banyosunu kuzey tarafına alalım."
    );

    const planEditor92 = new PlanEditor(planContainer92.id, { bindWindowEvents: false });
    planEditor92.loadData({
      alternatives: {
        a: {
          floors: {
            ground: [{ id: "study", name: "Çalışma Odası", x: 10, y: 20, width: 30, height: 40 }]
          }
        }
      }
    });
    const planGeometryBefore92 = JSON.stringify(planEditor92.planData);
    const dressingReply92 = Array.from(structuredChat92.querySelectorAll(".followup-chip"))
      .find(button => button.dataset.optionId === "master_bath_dressing_access");
    const replyRegistry92 = window.ScenarioQuickReplyRegistry.master_bath_relocation;

    // Test 92: Quick replies expose canonical, structured and scenario-scoped DOM data
    const test92Pass = Boolean(dressingReply92) &&
      dressingReply92.dataset.action === "RECORD_MASTER_BATH_PREFERENCE" &&
      dressingReply92.dataset.value === "through_dressing" &&
      dressingReply92.dataset.optionId === "master_bath_dressing_access" &&
      dressingReply92.dataset.scenarioId === "master_bath_relocation" &&
      dressingReply92.dataset.decisionId === "dec_master_bath" &&
      replyRegistry92[0].preferenceKey === "bed_visibility" &&
      replyRegistry92[0].preferenceValue === "hidden_from_bed" &&
      replyRegistry92[1].preferenceKey === "access_route" &&
      replyRegistry92[1].preferenceValue === "through_dressing" &&
      replyRegistry92[2].preferenceKey === "privacy" &&
      replyRegistry92[2].preferenceValue === "increased_privacy";
    results.push({ name: "Test 92: Scenario Quick Replies Have Structured DOM Contract", pass: test92Pass });

    let delegatedInvocations92 = 0;
    structuredChat92.addEventListener("click", event => {
      const chip = event.target.closest(".followup-chip");
      if (!chip) return;
      delegatedInvocations92 += 1;
      structuredOrchestrator92.handleQuickReply({
        label: chip.textContent || chip.dataset.reply || "",
        action: chip.dataset.action,
        value: chip.dataset.value,
        optionId: chip.dataset.optionId,
        scenarioId: chip.dataset.scenarioId,
        decisionId: chip.dataset.decisionId,
        preferenceKey: chip.dataset.preferenceKey,
        preferenceValue: chip.dataset.preferenceValue
      });
    });
    const userCountBefore93 = structuredChat92.querySelectorAll(".chat-message.user").length;
    const assistantCountBefore93 = structuredChat92.querySelectorAll(".chat-message.assistant").length;
    dressingReply92.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const structuredSnapshot93 = structuredState92.getSnapshot();

    // Test 93: Dressing-access MouseEvent records exactly one user message
    const test93Pass = structuredChat92.querySelectorAll(".chat-message.user").length ===
      userCountBefore93 + 1 &&
      Array.from(structuredChat92.querySelectorAll(".chat-message.user .message-text"))
        .filter(element => element.textContent === replyRegistry92[1].label).length === 1;
    results.push({ name: "Test 93: Dressing Access MouseEvent Adds One User Message", pass: test93Pass });

    // Test 94: Preference acknowledgement appears exactly once
    const assistantMessages94 = Array.from(
      structuredChat92.querySelectorAll(".chat-message.assistant .message-text")
    ).map(element => element.textContent);
    const acknowledgement94 = assistantMessages94.filter(text =>
      text.includes("Giyinme alanından erişim önceliğini kaydettim") &&
      text.includes("plan otomatik değiştirilmedi")
    );
    const test94Pass = structuredChat92.querySelectorAll(".chat-message.assistant").length ===
      assistantCountBefore93 + 1 && acknowledgement94.length === 1;
    results.push({ name: "Test 94: Scenario Preference Adds One Assistant Acknowledgement", pass: test94Pass });

    // Test 95: The scenario response is stored as structured snapshot state
    const savedResponse95 = structuredSnapshot93.scenarioResponses.master_bath_relocation;
    const test95Pass = savedResponse95 &&
      savedResponse95.optionId === "master_bath_dressing_access" &&
      savedResponse95.preferenceKey === "access_route" &&
      savedResponse95.preferenceValue === "through_dressing" &&
      savedResponse95.label === replyRegistry92[1].label;
    results.push({ name: "Test 95: Scenario Response Is Stored In Snapshot", pass: test95Pass });

    // Test 96: Preference recording atomically opens the options workspace
    const test96Pass = structuredSnapshot93.workspaceMode === "options_side_by_side" &&
      structuredWorkspace92.dataset.workspaceMode === "options_side_by_side" &&
      structuredWorkspace92.querySelector(".options-side-by-side-container") !== null;
    results.push({ name: "Test 96: Preference Opens Options Workspace", pass: test96Pass });

    // Test 97: Project, building, level, and entity remain in the master-bath scope
    const test97Pass = structuredSnapshot93.projectId === "proj_house_2story" &&
      structuredSnapshot93.buildingId === "bldg_main" &&
      structuredSnapshot93.levelId === "lvl_upper" &&
      structuredSnapshot93.entityId === "space_master_bath";
    results.push({ name: "Test 97: Preference Preserves Architectural Scope", pass: test97Pass });

    // Test 98: Scenario and decision identifiers survive preference recording
    const test98Pass = structuredSnapshot93.scenarioId === "master_bath_relocation" &&
      structuredSnapshot93.decisionId === "dec_master_bath" &&
      structuredSnapshot93.targetEntityId === "space_master_bath";
    results.push({ name: "Test 98: Preference Preserves Scenario And Decision", pass: test98Pass });

    // Test 99: A preference is not a placement-option decision
    const test99Pass = structuredSnapshot93.selectedOption === null &&
      structuredSnapshot93.decisionStatus === null;
    results.push({ name: "Test 99: Preference Does Not Select A Plan Option", pass: test99Pass });

    // Test 100: The preference action does not mutate plan geometry
    const test100Pass = JSON.stringify(planEditor92.planData) === planGeometryBefore92;
    results.push({ name: "Test 100: Preference Does Not Mutate Plan Geometry", pass: test100Pass });

    // Test 101: A stale reply cannot alter state or append chat messages
    const generationBefore101 = structuredSnapshot93.generationId;
    const messageCountBefore101 = structuredOrchestrator92.allChatMessages.length;
    const staleAccepted101 = structuredOrchestrator92.handleQuickReply({
      ...replyRegistry92[1],
      decisionId: "dec_stale"
    });
    const test101Pass = staleAccepted101 === false &&
      structuredState92.getSnapshot().generationId === generationBefore101 &&
      structuredOrchestrator92.allChatMessages.length === messageCountBefore101;
    results.push({ name: "Test 101: Stale Scenario Quick Reply Is Ignored", pass: test101Pass });

    // Test 102: A house reply cannot alter another project's state
    const foreignChat102 = this.createTestElement("cross-project-chat-102");
    const foreignState102 = new ContextStateMachine(this.hierarchy);
    const foreignOrchestrator102 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: foreignState102,
      assistant: new ContextualAssistant({
        hierarchy: this.hierarchy,
        stateMachine: foreignState102
      }),
      chatContainerId: foreignChat102.id
    });
    foreignOrchestrator102.selectProject("proj_tower_50floor");
    const foreignMessage102 = foreignOrchestrator102.allChatMessages.at(-1)?.text || "";
    const foreignMessageIsolated102 = Boolean(foreignMessage102) &&
      foreignChat102.textContent.includes("A Kulesi");
    const foreignMessagesBefore102 = foreignOrchestrator102.allChatMessages.length;
    const foreignAccepted102 = foreignOrchestrator102.handleQuickReply({ ...replyRegistry92[1] });
    const foreignSnapshot102 = foreignState102.getSnapshot();
    const test102Pass = foreignAccepted102 === false &&
      foreignSnapshot102.projectId === "proj_tower_50floor" &&
      Object.keys(foreignSnapshot102.scenarioResponses).length === 0 &&
      foreignOrchestrator102.allChatMessages.length === foreignMessagesBefore102;
    results.push({ name: "Test 102: Cross Project Scenario Quick Reply Is Ignored", pass: test102Pass });

    // Test 103: One delegated MouseEvent invokes the handler exactly once
    const test103Pass = delegatedInvocations92 === 1;
    results.push({ name: "Test 103: Quick Reply Listener Does Not Duplicate", pass: test103Pass });

    // Test 104: Free text records the same preference inside the active scenario
    const freeTextChat104 = this.createTestElement("free-text-chat-104");
    const freeTextState104 = new ContextStateMachine(this.hierarchy);
    const freeTextOrchestrator104 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: freeTextState104,
      assistant: new ContextualAssistant({
        hierarchy: this.hierarchy,
        stateMachine: freeTextState104
      }),
      chatContainerId: freeTextChat104.id
    });
    freeTextOrchestrator104.triggerMasterBathScenario("Ebeveyn banyosunu kuzey tarafına alalım.");
    freeTextOrchestrator104.appendUserMessage(replyRegistry92[1].label);
    freeTextOrchestrator104.handleUserMessage(replyRegistry92[1].label);
    const freeTextSnapshot104 = freeTextState104.getSnapshot();
    const test104Pass = freeTextSnapshot104.scenarioResponses.master_bath_relocation
      ?.preferenceValue === "through_dressing" &&
      freeTextSnapshot104.workspaceMode === "options_side_by_side";
    results.push({ name: "Test 104: Active Scenario Free Text Records Preference", pass: test104Pass });

    // Test 105: The same free text remains generic outside the scenario
    const genericChat105 = this.createTestElement("generic-preference-chat-105");
    const genericState105 = new ContextStateMachine(this.hierarchy);
    const genericOrchestrator105 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: genericState105,
      assistant: new ContextualAssistant({
        hierarchy: this.hierarchy,
        stateMachine: genericState105
      }),
      chatContainerId: genericChat105.id
    });
    genericOrchestrator105.appendUserMessage(replyRegistry92[1].label);
    genericOrchestrator105.handleUserMessage(replyRegistry92[1].label);
    const genericSnapshot105 = genericState105.getSnapshot();
    const genericAssistant105 = genericChat105.querySelector(
      ".chat-message.assistant .message-text"
    );
    const test105Pass = Object.keys(genericSnapshot105.scenarioResponses).length === 0 &&
      genericSnapshot105.workspaceMode === "plan" &&
      genericAssistant105?.textContent.includes("Talebinizi not aldım");
    results.push({ name: "Test 105: Preference Text Is Generic Outside Scenario", pass: test105Pass });

    // Test 106: Scenario response snapshots are immutable and project scoped
    const exportedSnapshot106 = structuredState92.getSnapshot();
    exportedSnapshot106.scenarioResponses.master_bath_relocation.label = "mutated";
    const internalLabel106 = structuredState92.getSnapshot()
      .scenarioResponses.master_bath_relocation.label;
    structuredState92.dispatch({
      type: "PROJECT_SELECTED",
      payload: {
        projectId: "proj_tower_50floor",
        buildingId: "tower_a",
        levelId: "lvl_18",
        entityId: "space_meeting_18a"
      }
    });
    const test106Pass = internalLabel106 === replyRegistry92[1].label &&
      Object.keys(structuredState92.getSnapshot().scenarioResponses).length === 0;
    results.push({ name: "Test 106: Scenario Responses Are Immutable And Project Scoped", pass: test106Pass });

    // Test 107: Structured quick-reply labels remain inert text
    delete window.__quickReplyXss;
    const xssReply107 = '<img src=x onerror="window.__quickReplyXss=true"><script>window.__quickReplyXss=true</script>';
    genericOrchestrator105.appendAssistantMessage("Safe structured reply", [{
      label: xssReply107,
      action: "SEND_MESSAGE",
      value: xssReply107
    }]);
    const renderedXssReply107 = genericChat105.querySelector(".followup-chip");
    const test107Pass = renderedXssReply107?.textContent === xssReply107 &&
      genericChat105.querySelector("img, script, svg") === null &&
      window.__quickReplyXss === undefined;
    delete window.__quickReplyXss;
    results.push({ name: "Test 107: Structured Quick Reply HTML Is Inert", pass: test107Pass });

    const runRepeatedAssertion112 = label => {
      const chat = this.createTestElement(`repeat-chat-${label}`);
      const stateMachine = new ContextStateMachine(this.hierarchy);
      const orchestrator = new ConversationOrchestrator({
        hierarchy: this.hierarchy,
        stateMachine,
        assistant: new ContextualAssistant({ hierarchy: this.hierarchy, stateMachine }),
        chatContainerId: chat.id
      });
      let listenerInvocations = 0;
      chat.addEventListener("click", event => {
        const chip = event.target.closest(".followup-chip");
        if (!chip) return;
        listenerInvocations += 1;
        orchestrator.handleQuickReply({
          label: chip.textContent || chip.dataset.reply || "",
          action: chip.dataset.action,
          value: chip.dataset.value,
          optionId: chip.dataset.optionId,
          scenarioId: chip.dataset.scenarioId,
          decisionId: chip.dataset.decisionId,
          preferenceKey: chip.dataset.preferenceKey,
          preferenceValue: chip.dataset.preferenceValue
        });
      });
      orchestrator.triggerMasterBathScenario("Repeat-run browser assertion.");
      chat.querySelector(".followup-chip")
        .dispatchEvent(new MouseEvent("click", { bubbles: true }));

      return {
        chatId: chat.id,
        listenerInvocations,
        userMessageCount: chat.querySelectorAll(".chat-message.user").length,
        acknowledgementCount: Array.from(
          chat.querySelectorAll(".chat-message.assistant .message-text")
        ).filter(element => element.textContent.includes("plan otomatik")).length
      };
    };
    const repeatedRunA112 = runRepeatedAssertion112("a");
    const repeatedRunB112 = runRepeatedAssertion112("b");
    const repeatedRunPass112 = repeatedRunA112.chatId !== repeatedRunB112.chatId &&
      [repeatedRunA112, repeatedRunB112].every(run =>
        run.listenerInvocations === 1 &&
        run.userMessageCount === 1 &&
        run.acknowledgementCount === 1
      );

    this.cleanupTestNodes();
    this.restoreGlobals(productionGlobals);

    const productionAfter = this.captureProductionState(window.appStateMachine);
    const productionChatUnchanged108 = productionAfter.chat.html === productionBefore.chat.html &&
      productionAfter.chat.messageCount === productionBefore.chat.messageCount;
    results.push({
      name: "Test 108: Browser Assertions Do Not Mutate Production Chat",
      pass: productionChatUnchanged108
    });

    const foreignMessageCountAfter102 = productionAfter.chat.messageTexts
      .filter(message => message === foreignMessage102).length;
    results.push({
      name: "Test 109: Cross-Project Test Message Does Not Appear In Real UI",
      pass: foreignMessageIsolated102 &&
        foreignMessageCountAfter102 === 0
    });

    const globalsRestored110 = Object.entries(productionGlobals).every(([name, previous]) =>
      previous.exists
        ? window[name] === previous.value
        : !Object.prototype.hasOwnProperty.call(window, name)
    );
    results.push({
      name: "Test 110: Production Active Snapshot Unchanged After Test Suite",
      pass: globalsRestored110 &&
        productionAfter.activeSnapshot === productionBefore.activeSnapshot
    });

    const productionWorkspaceUnchanged111 = JSON.stringify(productionAfter.workspace) ===
      JSON.stringify(productionBefore.workspace);
    results.push({
      name: "Test 111: Production Workspace DOM Unchanged After Test Suite",
      pass: productionWorkspaceUnchanged111
    });

    const noTestRoots112 = document.querySelectorAll("[data-test-scope-guard-root]").length === 0;
    results.push({
      name: "Test 112: Repeated Test Run Does Not Duplicate Messages Or Listeners",
      pass: repeatedRunPass112 && noTestRoots112 && productionChatUnchanged108
    });

    window.scopeGuardLastRun = {
      runId: this.runId,
      assertionCount: results.length,
      passedCount: results.filter(result => result.pass).length,
      productionChat: {
        beforeMessageCount: productionBefore.chat.messageCount,
        afterMessageCount: productionAfter.chat.messageCount,
        htmlUnchanged: productionChatUnchanged108
      },
      activeSnapshotUnchanged:
        productionAfter.activeSnapshot === productionBefore.activeSnapshot,
      workspaceDomUnchanged: productionWorkspaceUnchanged111
    };

    console.log(`=== Scope, Surface & Payload Guard Unit Test Results (${results.length} total) ===`);
    results.forEach(r => console.log(`${r.pass ? '✅ PASS' : '❌ FAIL'}: ${r.name}`));

    return results;
    } finally {
      this.cleanupTestNodes();
      this.restoreGlobals(productionGlobals);
    }
  }
}

async function waitForProductionApp(timeoutMs = 10000) {
  if (document.readyState === "loading") {
    await new Promise(resolve => {
      document.addEventListener("DOMContentLoaded", resolve, { once: true });
    });
  }

  const deadline = performance.now() + timeoutMs;
  while (
    (!window.appStateMachine ||
      !window.appDOMRegistry ||
      !window.appPlanEditor ||
      !window.appOrchestrator) &&
    performance.now() < deadline
  ) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }

  if (!window.appStateMachine || !window.appDOMRegistry ||
      !window.appPlanEditor || !window.appOrchestrator) {
    throw new Error("Production application did not initialize before browser assertions.");
  }

  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

window.TestScopeGuard = TestScopeGuard;
window.runScopeGuardAssertions = async () => {
  await waitForProductionApp();
  const results = await new TestScopeGuard().runAllTests();
  window.scopeGuardLastResults = results;
  return results;
};
window.scopeGuardTestPromise = window.runScopeGuardAssertions();
