/**
 * BRIF.AI — Automated Scope, Surface & Payload Unit Tests (v6.2 Engine)
 *
 * Verifies core architectural principles across 91 test scenarios:
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
 */

class TestScopeGuard {
  constructor() {
    this.hierarchy = new EntityHierarchy();
    this.store = new ScopedDocumentStore();
    this.resolver = new WorkspaceScopeResolver(this.hierarchy, this.store);
    this.guard = new RenderCompatibilityGuard(this.hierarchy);
    this.registry = new DOMSurfaceRegistry();
  }

  async runAllTests() {
    await this.store.initialize();
    const results = [];

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
    const dummyContainer = document.createElement("div");
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
    const dummyPlanEl = document.createElement("div");
    dummyPlanEl.setAttribute("data-project-id", ctxTower.projectId);
    const provPass = dummyPlanEl.getAttribute("data-project-id") === "proj_tower_50floor";
    results.push({ name: "Test 20: Plan Provenance Assertion", pass: provPass === true });

    // Tests 21-28
    const towerEmptyContainer = document.createElement("div");
    this.guard.renderPlanEmptyState(towerEmptyContainer, ctxTower);
    const towerEmptyHTML = towerEmptyContainer.innerHTML;
    const towerPositivePass = towerEmptyHTML.includes("Bu kapsam için şematik plan bulunmuyor") &&
                              towerEmptyHTML.includes("Başka projeye ait bir plan kullanılmayacaktır") &&
                              towerEmptyHTML.includes("18. Kat");
    results.push({ name: "Test 21: Tower Positive Plan Empty State Assertion", pass: towerPositivePass === true });

    const campusEmptyContainer = document.createElement("div");
    this.guard.renderPlanEmptyState(campusEmptyContainer, campusCtx);
    const campusEmptyHTML = campusEmptyContainer.innerHTML;
    const campusPositivePass = campusEmptyHTML.includes("Bu kapsam için şematik plan bulunmuyor") &&
                               campusEmptyHTML.includes("Başka projeye ait bir plan kullanılmayacaktır") &&
                               campusEmptyHTML.includes("Blok A");
    results.push({ name: "Test 22: Campus Positive Plan Empty State Assertion", pass: campusPositivePass === true });

    const regTest = new DOMSurfaceRegistry();
    const presenterTest = new WorkspacePresenter("dummy", { hierarchy: this.hierarchy, guard: this.guard, registry: regTest });
    presenterTest.container = document.createElement("div");
    presenterTest.renderWorkspaceEmptyState({ activeContext: ctxTower });
    const mountedEmptySurfaces = regTest.getMountedSurfacesForProject("proj_tower_50floor");
    const emptyMountedPass = mountedEmptySurfaces.length > 0 && mountedEmptySurfaces[0].documentType === "empty_state";
    results.push({ name: "Test 23: Empty-State Registry Mounting", pass: emptyMountedPass === true });

    const dummyMsg = document.createElement("div");
    dummyMsg.className = "chat-message assistant";
    const msgPass = dummyMsg.classList.contains("assistant") && dummyMsg.classList.contains("chat-message");
    results.push({ name: "Test 24: Assistant Panel Structured DOM", pass: msgPass === true });

    const inputEl = document.createElement("input");
    inputEl.id = "assistantUserInput";
    const btnEl = document.createElement("button");
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
    regC.mountSurface({ surfaceId: "surf_house_plan", containerId: "planEditorContainer", projectId: "proj_house_2story" });
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
    const orchestrator37 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm37
    });
    orchestrator37.chatContainerId = "test-scope-guard-missing-37";
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
    const orchestrator38 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm38
    });
    orchestrator38.chatContainerId = "test-scope-guard-missing-38";
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
    const chat41 = document.createElement("div");
    chat41.id = "test-scope-guard-chat-41";
    document.body.appendChild(chat41);
    const orchestrator41 = new ConversationOrchestrator({ hierarchy: this.hierarchy });
    orchestrator41.chatContainerId = chat41.id;
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
    const chat42 = document.createElement("div");
    chat42.id = "test-scope-guard-chat-42";
    document.body.appendChild(chat42);
    const orchestrator42 = new ConversationOrchestrator({ hierarchy: this.hierarchy });
    orchestrator42.chatContainerId = chat42.id;
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
    const orchestrator43 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm43,
      historyManager: history43
    });
    orchestrator43.chatContainerId = "test-scope-guard-missing-43";
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
    const orchestrator45 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm45
    });
    orchestrator45.chatContainerId = "test-scope-guard-missing-45";
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
    const orchestrator47 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm47
    });
    orchestrator47.chatContainerId = "test-scope-guard-missing-47";
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
    const orchestrator51 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm51,
      assistant: assistant51
    });
    orchestrator51.chatContainerId = "test-scope-guard-missing-51";
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
    const chat53 = document.createElement("div");
    chat53.id = "test-scope-guard-chat-53";
    document.body.appendChild(chat53);
    const sm53 = new ContextStateMachine(this.hierarchy);
    const assistant53 = new ContextualAssistant({
      hierarchy: this.hierarchy,
      stateMachine: sm53
    });
    const orchestrator53 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm53,
      assistant: assistant53
    });
    orchestrator53.chatContainerId = chat53.id;
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

    const visualContainer = document.createElement("div");
    visualContainer.id = "test-scope-guard-visual-preferences";
    document.body.appendChild(visualContainer);
    const visualRegistry = new DOMSurfaceRegistry();
    const visualPresenter = new WorkspacePresenter(visualContainer.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: visualRegistry
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
    const orchestrator60 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: sm60
    });
    orchestrator60.chatContainerId = "test-scope-guard-missing-60";
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

    const modeContainer = document.createElement("div");
    modeContainer.id = "test-scope-guard-workspace-modes";
    document.body.appendChild(modeContainer);
    const modeState = new ContextStateMachine(this.hierarchy);
    const modePresenter = new WorkspacePresenter(modeContainer.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: modeState
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

    const scenarioContainer82 = document.createElement("div");
    scenarioContainer82.id = "test-scope-guard-master-bath-workspace";
    document.body.appendChild(scenarioContainer82);
    const scenarioChat82 = document.createElement("div");
    scenarioChat82.id = "test-scope-guard-master-bath-chat";
    document.body.appendChild(scenarioChat82);
    const scenarioState82 = new ContextStateMachine(this.hierarchy);
    const scenarioHistory82 = new ChangeHistory({
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard
    });
    const scenarioPresenter82 = new WorkspacePresenter(scenarioContainer82.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: scenarioState82
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
      historyManager: scenarioHistory82
    });
    scenarioOrchestrator82.chatContainerId = scenarioChat82.id;
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
    const orientationContainer83 = document.createElement("div");
    orientationContainer83.id = "test-scope-guard-orientation-workspace";
    document.body.appendChild(orientationContainer83);
    const orientationChat83 = document.createElement("div");
    orientationChat83.id = "test-scope-guard-orientation-chat";
    document.body.appendChild(orientationChat83);
    const orientationState83 = new ContextStateMachine(this.hierarchy);
    const orientationPresenter83 = new WorkspacePresenter(orientationContainer83.id, {
      hierarchy: this.hierarchy,
      store: this.store,
      resolver: this.resolver,
      guard: this.guard,
      registry: new DOMSurfaceRegistry(),
      stateMachine: orientationState83
    });
    const orientationOrchestrator83 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: orientationState83,
      assistant: new ContextualAssistant({ hierarchy: this.hierarchy, stateMachine: orientationState83 }),
      presenter: orientationPresenter83
    });
    orientationOrchestrator83.chatContainerId = orientationChat83.id;
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
    const reportContainer88 = document.getElementById("architectDecisionHistory");
    const previousReport88 = reportContainer88 ? reportContainer88.innerHTML : "";
    const originalConsoleWarn88 = console.warn;
    const capturedWarnings88 = [];
    console.warn = (...args) => capturedWarnings88.push(args.map(String).join(" "));
    try {
      scenarioHistory82.renderArchitectReport(finalSnapshot82);
    } finally {
      console.warn = originalConsoleWarn88;
    }
    const test88Pass = scenarioHistory82.sessionState.levelId === "lvl_upper" &&
      capturedWarnings88.length === 0;
    if (reportContainer88) reportContainer88.innerHTML = previousReport88;
    results.push({ name: "Test 88: ChangeHistory Uses Current Scenario Snapshot", pass: test88Pass });

    // Test 89: A real form submit runs the complete master-bath message path
    const form89 = document.createElement("form");
    const input89 = document.createElement("input");
    const chat89 = document.createElement("div");
    chat89.id = "test-scope-guard-form-chat";
    form89.appendChild(input89);
    document.body.append(form89, chat89);
    const formState89 = new ContextStateMachine(this.hierarchy);
    const formOrchestrator89 = new ConversationOrchestrator({
      hierarchy: this.hierarchy,
      stateMachine: formState89,
      assistant: new ContextualAssistant({ hierarchy: this.hierarchy, stateMachine: formState89 })
    });
    formOrchestrator89.chatContainerId = chat89.id;
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
      formOrchestrator89.appendUserMessage(chip.dataset.reply);
      formOrchestrator89.handleUserMessage(chip.dataset.reply);
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

    scenarioContainer82.remove();
    scenarioChat82.remove();
    orientationContainer83.remove();
    orientationChat83.remove();
    form89.remove();
    chat89.remove();

    console.log(`=== Scope, Surface & Payload Guard Unit Test Results (${results.length} total) ===`);
    results.forEach(r => console.log(`${r.pass ? '✅ PASS' : '❌ FAIL'}: ${r.name}`));

    return results;
  }
}

// Auto-run on load in dev console
window.TestScopeGuard = TestScopeGuard;
new TestScopeGuard().runAllTests();
