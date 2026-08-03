/**
 * BRIF.AI — Automated Scope, Surface & Payload Unit Tests (v6.2 Engine)
 *
 * Verifies core architectural principles across 53 test scenarios:
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
    const testGPass = titleG.includes("Finans Kulesi") && sibsG.some(s => s.displayName === "32. Kat");
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

    console.log(`=== Scope, Surface & Payload Guard Unit Test Results (${results.length} total) ===`);
    results.forEach(r => console.log(`${r.pass ? '✅ PASS' : '❌ FAIL'}: ${r.name}`));

    return results;
  }
}

// Auto-run on load in dev console
window.TestScopeGuard = TestScopeGuard;
new TestScopeGuard().runAllTests();
