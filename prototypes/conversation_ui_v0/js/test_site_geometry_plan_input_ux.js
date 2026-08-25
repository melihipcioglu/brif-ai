/**
 * BRIF.AI — JS Unit Test Suite for Conversation Site Geometry Plan Input UI V0
 * Tests site geometry proposal capture, rendering, approval gateway, stale rejection,
 * dismissal, browser validation, payload security, replay hardening, cross-invalidation,
 * and regression boundaries (Tests 1-65).
 */

const assert = require('assert');
const LocalLLMGateway = require('./local_llm_gateway.js');
const ConversationOrchestrator = require('./conversation_orchestrator.js');

class MockElement {
  constructor(tag = 'div') {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this._classList = new Set();
    this.textContent = '';
    this.disabled = false;
  }
  get className() {
    return Array.from(this._classList).join(' ');
  }
  set className(val) {
    this._classList.clear();
    String(val || '').split(/\s+/).filter(Boolean).forEach(c => this._classList.add(c));
  }
  get classList() {
    return {
      add: (...cls) => cls.forEach(c => this._classList.add(c)),
      remove: (...cls) => cls.forEach(c => this._classList.delete(c)),
      has: (c) => this._classList.has(c),
      contains: (c) => this._classList.has(c)
    };
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  append(...children) {
    this.children.push(...children);
  }
  setAttribute(k, v) { this[k] = v; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  closest() { return null; }
}

const domElements = new Map();
global.document = {
  createElement(tag) { return new MockElement(tag); },
  getElementById(id) {
    if (!domElements.has(id)) {
      domElements.set(id, new MockElement('div'));
    }
    return domElements.get(id);
  }
};

class MockEntityHierarchy {
  constructor() {
    this.projects = {
      'proj_test_123': {
        id: 'proj_test_123',
        name: 'Test Project',
        buildings: {}
      },
      'proj/special#1': {
        id: 'proj/special#1',
        name: 'Special Project',
        buildings: {}
      }
    };
  }
  getScopeTitle() { return 'Scope'; }
}

class MockStateMachine {
  constructor(ctx) { this.ctx = ctx; this.listeners = []; }
  getSnapshot() { return { ...this.ctx }; }
  getContext() { return { ...this.ctx }; }
  subscribe(fn) { this.listeners.push(fn); }
}

class MockDocumentStore {}
class MockScopeResolver {}
class MockAssistant { processUserMessage() { return { aiResponseText: 'Ok' }; } }
class MockPresenter { render() {} }

function setupEnvironment(projectId = 'proj_test_123') {
  const activeSnapshot = {
    projectId,
    buildingId: 'bldg_main',
    levelId: 'lvl_1',
    contextFingerprint: 'fp_test_1',
    generationId: 1
  };

  const briefSnapshot = {
    project_id: projectId,
    brief_version: 3,
    brief_items: [],
    space_requests: [
      { id: 'sr_living', display_name: 'Salon', minimum_quantity: 1 },
      { id: 'sr_kitchen', display_name: 'Mutfak', minimum_quantity: 1 }
    ],
    evidence: []
  };

  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine(activeSnapshot);

  const orchestrator = new ConversationOrchestrator({
    hierarchy,
    stateMachine,
    store: new MockDocumentStore(),
    resolver: new MockScopeResolver(),
    assistant: new MockAssistant(),
    presenter: new MockPresenter(),
    briefSnapshotsByProject: { [projectId]: briefSnapshot }
  });

  const createGateway = (fetchFn) => new LocalLLMGateway({
    stateMachine,
    hierarchy,
    orchestrator,
    fetchFn
  });

  return { orchestrator, stateMachine, hierarchy, briefSnapshot, activeSnapshot, createGateway };
}

async function runAllTests() {
  console.log('Running Site Geometry Plan Input UI V0 JS Unit Tests (1-65)...');

  // =========================================================================
  // Group A: Proposal Capture & Deduplication (Tests 1-7)
  // =========================================================================

  // Test 1: PARCEL_BOUNDARY captured
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel sınırı önerisi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [
          { x_m: 0, y_m: 0 },
          { x_m: 20, y_m: 0 },
          { x_m: 20, y_m: 30 },
          { x_m: 0, y_m: 30 }
        ],
        rationale: 'Kullanıcı parsel sınırı'
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel mesajı', 'chatmsg_1');

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].siteGeometry.role, 'PARCEL_BOUNDARY');
    assert.strictEqual(pending[0].siteGeometry.vertices.length, 4);
    console.log('✓ 1. PARCEL_BOUNDARY proposal is captured');
  }

  // Test 2: BUILDABLE_ENVELOPE captured
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Yapılaşma zarfı önerisi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_e1',
        role: 'BUILDABLE_ENVELOPE',
        vertices: [
          { x_m: 2, y_m: 2 },
          { x_m: 18, y_m: 2 },
          { x_m: 18, y_m: 28 },
          { x_m: 2, y_m: 28 }
        ],
        rationale: 'Kullanıcı yapılaşma zarfı'
      }]
    }, 'fp_test_1', 1, 1, 3, 'Zarf mesajı', 'chatmsg_1');

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].siteGeometry.role, 'BUILDABLE_ENVELOPE');
    console.log('✓ 2. BUILDABLE_ENVELOPE proposal is captured');
  }

  // Test 3: Exact deep-copy preserved
  {
    const { orchestrator } = setupEnvironment();
    const originalSite = {
      proposal_id: 'prop_p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
    };
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [originalSite]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    originalSite.vertices[0].x_m = 999;
    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending[0].siteGeometry.vertices[0].x_m, 0);
    console.log('✓ 3. exact deep-copy preserved');
  }

  // Test 4: expectedBriefVersion captured from proposalBriefVersion
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    }, 'fp_test_1', 1, null, 7, 'Parsel', 'chatmsg_1');

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending[0].expectedBriefVersion, 7);
    console.log('✓ 4. expected brief version captured');
  }

  // Test 5: expectedPlanInputStateVersion captured from authoritativePlanInputStateVersion
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    }, 'fp_test_1', 1, 4, 3, 'Parsel', 'chatmsg_1');

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending[0].expectedPlanInputStateVersion, 4);
    console.log('✓ 5. expected plan-input version captured');
  }

  // Test 6: null plan-input version preserved when uninitialized
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending[0].expectedPlanInputStateVersion, null);
    console.log('✓ 6. null plan-input version preserved');
  }

  // Test 7: Sibling deduplication reuses existing pending proposal
  {
    const { orchestrator } = setupEnvironment();
    const siteObj = {
      proposal_id: 'prop_p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
    };

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'İlk öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [siteObj]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    assert.strictEqual(orchestrator.getActivePendingProposals().length, 1);
    const firstId = orchestrator.getActivePendingProposals()[0].id;

    // Second response with identical context, generation, and exact site geometry
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Aynı öneri tekrarı.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [siteObj]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    assert.strictEqual(orchestrator.getActivePendingProposals().length, 1);
    assert.strictEqual(orchestrator.getActivePendingProposals()[0].id, firstId);
    console.log('✓ 7. deduplication reuses existing pending proposal');
  }

  // =========================================================================
  // Group B: Readable Description & Formatting (Tests 8-13)
  // =========================================================================

  // Test 8: PARCEL_BOUNDARY readable description
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getSiteGeometryDescription({
      proposal_id: 'p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [
        { x_m: 0, y_m: 0 },
        { x_m: 20, y_m: 0 },
        { x_m: 20, y_m: 30 },
        { x_m: 0, y_m: 30 }
      ]
    });
    assert.strictEqual(desc, '“Parsel sınırı: (0;0), (20;0), (20;30), (0;30).” plan girdilerine eklensin mi?');
    console.log('✓ 8. PARCEL_BOUNDARY readable description');
  }

  // Test 9: BUILDABLE_ENVELOPE readable description
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getSiteGeometryDescription({
      proposal_id: 'e1',
      role: 'BUILDABLE_ENVELOPE',
      vertices: [
        { x_m: 3, y_m: 5 },
        { x_m: 17, y_m: 5 },
        { x_m: 17, y_m: 27 },
        { x_m: 3, y_m: 27 }
      ]
    });
    assert.strictEqual(desc, '“Yapılaşma zarfı: (3;5), (17;5), (17;27), (3;27).” plan girdilerine eklensin mi?');
    console.log('✓ 9. BUILDABLE_ENVELOPE readable description');
  }

  // Test 10: Turkish decimal comma formatting
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getSiteGeometryDescription({
      proposal_id: 'p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [
        { x_m: 0, y_m: 0 },
        { x_m: 20.5, y_m: 0 },
        { x_m: 20.5, y_m: 30.75 },
        { x_m: 0, y_m: 30.75 }
      ]
    });
    assert.strictEqual(desc, '“Parsel sınırı: (0;0), (20,5;0), (20,5;30,75), (0;30,75).” plan girdilerine eklensin mi?');
    console.log('✓ 10. Turkish decimal comma in coordinates');
  }

  // Test 11: Vertex order strictly preserved
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getSiteGeometryDescription({
      proposal_id: 'p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [
        { x_m: 10, y_m: 20 },
        { x_m: 5, y_m: 15 },
        { x_m: 0, y_m: 0 }
      ]
    });
    assert(desc.includes('(10;20), (5;15), (0;0)'));
    console.log('✓ 11. vertex order strictly preserved');
  }

  // Test 12: No inferred closing vertex added
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getSiteGeometryDescription({
      proposal_id: 'p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [
        { x_m: 0, y_m: 0 },
        { x_m: 10, y_m: 0 },
        { x_m: 10, y_m: 10 }
      ]
    });
    // Should contain exactly 3 pairs, not 4
    const matches = desc.match(/\([^)]+\)/g);
    assert.strictEqual(matches.length, 3);
    console.log('✓ 12. no inferred closing vertex added');
  }

  // Test 13: Machine enum not shown unnecessarily
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getSiteGeometryDescription({
      proposal_id: 'p1',
      role: 'PARCEL_BOUNDARY',
      vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
    });
    assert(!desc.includes('PARCEL_BOUNDARY'));
    console.log('✓ 13. machine enum not shown');
  }

  // =========================================================================
  // Group C: Button Labels & Rendering (Tests 14-17)
  // =========================================================================

  // Test 14: Pending PARCEL_BOUNDARY button text is "Parseli onayla"
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);
    assert.strictEqual(buttons.length, 1);
    assert.strictEqual(buttons[0].textContent, 'Parseli onayla');
    console.log('✓ 14. pending PARCEL_BOUNDARY button text is "Parseli onayla"');
  }

  // Test 15: Pending BUILDABLE_ENVELOPE button text is "Yapılaşma zarfını onayla"
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Zarf.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_e1',
        role: 'BUILDABLE_ENVELOPE',
        vertices: [{ x_m: 2, y_m: 2 }, { x_m: 18, y_m: 2 }, { x_m: 18, y_m: 28 }, { x_m: 2, y_m: 28 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Zarf', 'chatmsg_1');

    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);
    assert.strictEqual(buttons.length, 1);
    assert.strictEqual(buttons[0].textContent, 'Yapılaşma zarfını onayla');
    console.log('✓ 15. pending BUILDABLE_ENVELOPE button text is "Yapılaşma zarfını onayla"');
  }

  // Test 16: Approved button text is "Plan girdisine eklendi" and disabled
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    // Mark approved
    orchestrator.allChatMessages.forEach(m => {
      (m.proposedActions || []).forEach(p => { p.status = 'approved'; });
    });

    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);
    assert.strictEqual(buttons.length, 1);
    assert.strictEqual(buttons[0].textContent, 'Plan girdisine eklendi');
    assert.strictEqual(buttons[0].disabled, true);
    assert(buttons[0].classList.has('proposal-approved'));
    console.log('✓ 16. approved button text and disabled state');
  }

  // Test 17: Proposal uses .proposal-approve-btn generic delegation
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);
    assert.strictEqual(buttons.length, 1);
    assert.strictEqual(buttons[0].dataset.proposalId, 'proposal_1');
    console.log('✓ 17. generic .proposal-approve-btn delegation preserved');
  }

  // =========================================================================
  // Group D: Browser Validation & Anti-Injection Defenses (Tests 18-31)
  // =========================================================================

  const gateway = new LocalLLMGateway();

  // Test 18: Valid PARCEL_BOUNDARY accepted
  {
    const validResult = {
      assistant_message: 'Parsel sınırı önerildi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [
          { x_m: 0, y_m: 0 },
          { x_m: 20, y_m: 0 },
          { x_m: 20, y_m: 30 },
          { x_m: 0, y_m: 30 }
        ]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(validResult, {}), true);
    console.log('✓ 18. valid PARCEL_BOUNDARY accepted');
  }

  // Test 19: Valid BUILDABLE_ENVELOPE accepted
  {
    const validResult = {
      assistant_message: 'Yapılaşma zarfı önerildi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_e1',
        role: 'BUILDABLE_ENVELOPE',
        vertices: [
          { x_m: 2, y_m: 2 },
          { x_m: 18, y_m: 2 },
          { x_m: 18, y_m: 28 },
          { x_m: 2, y_m: 28 }
        ]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(validResult, {}), true);
    console.log('✓ 19. valid BUILDABLE_ENVELOPE accepted');
  }

  // Test 20: Missing proposed_site_geometries defaults safely to []
  {
    const res = {
      assistant_message: 'Merhaba.',
      intent: 'gather_requirement',
      confidence: 0.8,
      needs_user_confirmation: false,
      proposed_actions: []
    };
    assert.strictEqual(gateway.isValidatedResult(res, {}), true);
    assert(Array.isArray(res.proposed_site_geometries));
    assert.strictEqual(res.proposed_site_geometries.length, 0);
    console.log('✓ 20. missing proposed_site_geometries normalized to []');
  }

  // Test 21: Unsupported role rejected
  {
    const invalidResult = {
      assistant_message: 'Geçersiz rol.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_x1',
        role: 'ZONING_RESTRICTION',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    console.log('✓ 21. unsupported role rejected');
  }

  // Test 22: Fewer than 3 vertices rejected
  {
    const invalidResult = {
      assistant_message: 'Yetersiz köşe.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_x1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    console.log('✓ 22. fewer than 3 vertices rejected');
  }

  // Test 23: Non-finite coordinate rejected
  {
    ['NaN', NaN, Infinity, -Infinity, null, '20'].forEach(val => {
      const invalidResult = {
        assistant_message: 'Geçersiz koordinat.',
        intent: 'modify_space',
        confidence: 0.9,
        needs_user_confirmation: true,
        proposed_actions: [],
        proposed_site_geometries: [{
          proposal_id: 'prop_x1',
          role: 'PARCEL_BOUNDARY',
          vertices: [{ x_m: val, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
        }]
      };
      assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    });
    console.log('✓ 23. non-finite coordinate rejected');
  }

  // Test 24: Missing/empty proposal_id rejected
  {
    const invalidResult = {
      assistant_message: 'Eksik proposal_id.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: '',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    console.log('✓ 24. missing proposal_id rejected');
  }

  // Test 25: Multiple site proposals rejected
  {
    const invalidResult = {
      assistant_message: 'Çift geometri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [
        {
          proposal_id: 'p1',
          role: 'PARCEL_BOUNDARY',
          vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
        },
        {
          proposal_id: 'e1',
          role: 'BUILDABLE_ENVELOPE',
          vertices: [{ x_m: 1, y_m: 1 }, { x_m: 9, y_m: 1 }, { x_m: 9, y_m: 9 }]
        }
      ]
    };
    assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    console.log('✓ 25. multiple site proposals rejected');
  }

  // Test 26: Site proposal + metric requirement mixed rejected
  {
    const mixed = {
      assistant_message: 'Karma öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }],
      proposed_metric_requirements: [{
        proposal_id: 'm1',
        space_id: 'sr_living',
        requirement_type: 'MIN_AREA',
        value: 30,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(mixed, {}), false);
    console.log('✓ 26. site + metric mixed response rejected');
  }

  // Test 27: Site proposal + brief mutation mixed rejected
  {
    const mixed = {
      assistant_message: 'Karma brief.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }],
      proposed_brief_mutations: [{
        mutation_id: 'mut_1',
        mutation_type: 'ADD_BRIEF_ITEM',
        brief_item: { normalized_statement: 'test' }
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(mixed, {}), false);
    console.log('✓ 27. site + brief mixed response rejected');
  }

  // Test 28: Site proposal + spatial relationship mixed rejected
  {
    const mixed = {
      assistant_message: 'Karma ilişki.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }],
      proposed_spatial_relationships: [{
        proposal_id: 'rel_1',
        space_id_a: 's1',
        space_id_b: 's2',
        relation_type: 'ADJACENT_TO'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(mixed, {}), false);
    console.log('✓ 28. site + spatial mixed response rejected');
  }

  // Test 29: Site proposal + proposed actions mixed rejected
  {
    const mixed = {
      assistant_message: 'Karma eylem.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [{
        action_type: 'suggest_space_resize',
        description: 'resize',
        requires_user_confirmation: true
      }],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(mixed, {}), false);
    console.log('✓ 29. site + action mixed response rejected');
  }

  // Test 30: Site proposal without needs_user_confirmation rejected
  {
    const invalidResult = {
      assistant_message: 'Onaysız site.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    console.log('✓ 30. site requires needs_user_confirmation');
  }

  // Test 31: Site proposal with needs_follow_up rejected
  {
    const invalidResult = {
      assistant_message: 'Takip sorulu site.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: true,
      follow_up_question: 'Emin misiniz?',
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(invalidResult, {}), false);
    console.log('✓ 31. site with needs_follow_up rejected');
  }

  // =========================================================================
  // Group D2: Authoritative / Unknown Field Injections Rejected (Strict Key Validation)
  // =========================================================================

  // Test 31a: provenance injection rejected
  {
    const injected = {
      assistant_message: 'Injection test',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }],
        provenance: 'malicious_client_provenance'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(injected, {}), false);
    console.log('✓ 31a. provenance injection rejected');
  }

  // Test 31b: evidence_ids injection rejected
  {
    const injected = {
      assistant_message: 'Injection test',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }],
        evidence_ids: ['ev_123']
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(injected, {}), false);
    console.log('✓ 31b. evidence_ids injection rejected');
  }

  // Test 31c: id injection rejected
  {
    const injected = {
      assistant_message: 'Injection test',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        id: 'auth_geom_id_999',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(injected, {}), false);
    console.log('✓ 31c. id injection rejected');
  }

  // Test 31d: extra vertex field rejected
  {
    const injected = {
      assistant_message: 'Injection test',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      needs_follow_up: false,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [
          { x_m: 0, y_m: 0, z_m: 5 },
          { x_m: 10, y_m: 0, z_m: 5 },
          { x_m: 10, y_m: 10, z_m: 5 }
        ]
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(injected, {}), false);
    console.log('✓ 31d. extra vertex field rejected');
  }

  // =========================================================================
  // Group E: Pending Context & Five-Way XOR (Tests 32-34)
  // =========================================================================

  // Test 32: getPendingProposalContext returns site_geometry
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const ctx = orchestrator.getPendingProposalContext();
    assert.strictEqual(ctx.length, 1);
    assert(ctx[0].site_geometry !== null);
    assert.strictEqual(ctx[0].site_geometry.role, 'PARCEL_BOUNDARY');
    console.log('✓ 32. getPendingProposalContext returns site_geometry');
  }

  // Test 33: Five-way XOR preserved
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const item = orchestrator.getPendingProposalContext()[0];
    assert.strictEqual(item.action, null);
    assert.strictEqual(item.brief_mutation, null);
    assert.strictEqual(item.spatial_relationship, null);
    assert.strictEqual(item.metric_requirement, null);
    assert.notStrictEqual(item.site_geometry, null);
    console.log('✓ 33. five-way XOR context shape preserved');
  }

  // Test 34: Exact object preserved in pending context
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }],
        rationale: 'Kullanıcı talebi'
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const item = orchestrator.getPendingProposalContext()[0];
    assert.strictEqual(item.site_geometry.proposal_id, 'prop_p1');
    assert.strictEqual(item.site_geometry.rationale, 'Kullanıcı talebi');
    assert.strictEqual(item.site_geometry.vertices.length, 4);
    console.log('✓ 34. exact object preserved in pending context');
  }

  // =========================================================================
  // Group F: Approval Payload & Exact Key Set Verification (Tests 35-37)
  // =========================================================================

  // Test 35: Approval payload contains exact required fields (no extra top-level keys)
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let capturedBody = null;
    const testGateway = env.createGateway(async (url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return {
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: 1 }
        })
      };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel sınırı: (0;0), (20;0), (20;30), (0;30)', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    assert(capturedBody !== null);
    const expectedTopLevelKeys = [
      'current_fingerprint',
      'current_generation_id',
      'current_project_id',
      'expected_brief_version',
      'expected_plan_input_state_version',
      'proposal_fingerprint',
      'proposal_generation_id',
      'proposed_geometry',
      'source_reference',
      'user_message'
    ].sort();

    assert.deepStrictEqual(Object.keys(capturedBody).sort(), expectedTopLevelKeys);
    assert.strictEqual(capturedBody.current_project_id, 'proj_test_123');
    assert.strictEqual(capturedBody.expected_brief_version, 3);
    assert.strictEqual(capturedBody.expected_plan_input_state_version, null);
    assert.strictEqual(capturedBody.proposal_fingerprint, 'fp_test_1');
    assert.strictEqual(capturedBody.current_fingerprint, 'fp_test_1');
    assert.strictEqual(capturedBody.proposal_generation_id, 1);
    assert.strictEqual(capturedBody.current_generation_id, 1);
    assert.strictEqual(capturedBody.user_message, 'Parsel sınırı: (0;0), (20;0), (20;30), (0;30)');
    assert.strictEqual(capturedBody.source_reference, 'chatmsg_1');
    console.log('✓ 35. approval payload contains exact required top-level keys');
  }

  // Test 36: Approval payload strictly OMITS authoritative / forbidden fields
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let capturedBody = null;
    const testGateway = env.createGateway(async (url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return {
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: 1 }
        })
      };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel sınırı: (0;0), (20;0), (20;30), (0;30)', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    assert.strictEqual(capturedBody.brief_snapshot, undefined);
    assert.strictEqual(capturedBody.spatial_graph, undefined);
    assert.strictEqual(capturedBody.spatial_program, undefined);
    assert.strictEqual(capturedBody.site_envelope, undefined);
    assert.strictEqual(capturedBody.provenance, undefined);
    assert.strictEqual(capturedBody.evidence_ids, undefined);
    assert.strictEqual(capturedBody.authoritative_geometry_ids, undefined);
    assert.strictEqual(capturedBody.floor_plate, undefined);
    assert.strictEqual(capturedBody.solver_config, undefined);
    console.log('✓ 36. approval payload strictly omits authoritative/forbidden fields');
  }

  // Test 37: proposed_geometry in payload contains only valid keys
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let capturedBody = null;
    const testGateway = env.createGateway(async (url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return {
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: 1 }
        })
      };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_site_1',
        role: 'PARCEL_BOUNDARY',
        vertices: [
          { x_m: 0, y_m: 0 },
          { x_m: 20, y_m: 0 },
          { x_m: 20, y_m: 30 },
          { x_m: 0, y_m: 30 }
        ],
        rationale: 'Kullanıcının verdiği parsel sınırı'
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel sınırı', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    const geom = capturedBody.proposed_geometry;
    const expectedGeomKeys = ['proposal_id', 'rationale', 'role', 'vertices'].sort();
    assert.deepStrictEqual(Object.keys(geom).sort(), expectedGeomKeys);
    assert.strictEqual(geom.provenance, undefined);
    assert.strictEqual(geom.evidence_ids, undefined);
    assert.strictEqual(geom.id, undefined);
    assert.strictEqual(geom.authoritative_geometry_ids, undefined);
    assert.strictEqual(geom.project_id, undefined);
    assert.strictEqual(geom.source_brief_version, undefined);
    assert.strictEqual(geom.created_at, undefined);
    console.log('✓ 37. proposed_geometry strictly validated without extra fields');
  }

  // =========================================================================
  // Group G: Proposal-Time Version & Real Async Source-Freeze Protection (Tests 38-40b)
  // =========================================================================

  // Test 38: Proposal-time brief version remains frozen even after active brief changes
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let capturedBody = null;
    const testGateway = env.createGateway(async (url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return {
        status: 409,
        json: async () => ({ success: false, error: 'Stale brief version' })
      };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel sınırı', 'chatmsg_1'); // Captured against brief v3

    // Active brief changes to v4
    orchestrator.replaceActiveBriefSnapshot({
      project_id: 'proj_test_123',
      brief_version: 4,
      brief_items: [],
      space_requests: [],
      evidence: []
    });

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    assert.strictEqual(capturedBody.expected_brief_version, 3);
    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('artık güncel proje durumuna ait değil')));
    console.log('✓ 38. proposal-time brief version frozen against subsequent brief changes');
  }

  // Test 39: Real Gateway Async Source-Freeze Integration Test [Requirement 2 & 3]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let capturedApprovalBody = null;
    let resolveInterpretFetch = null;

    const testGateway = env.createGateway(async (url, opts) => {
      if (url.includes('/api/v1/conversation/interpret')) {
        return new Promise(resolve => {
          resolveInterpretFetch = () => {
            resolve({
              status: 200,
              ok: true,
              json: async () => ({
                success: true,
                llm_enabled: true,
                context_fingerprint: 'fp_test_1',
                generation_id: 1,
                authoritative_brief_version: 3,
                authoritative_plan_input_state_version: 1,
                result: {
                  assistant_message: 'Parsel önerisi.',
                  intent: 'modify_space',
                  confidence: 0.9,
                  needs_user_confirmation: true,
                  needs_follow_up: false,
                  proposed_actions: [],
                  proposed_site_geometries: [{
                    proposal_id: 'prop_async_site_1',
                    role: 'PARCEL_BOUNDARY',
                    vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
                  }]
                }
              })
            });
          };
        });
      }
      if (url.includes('/plan/input/site/approve')) {
        capturedApprovalBody = JSON.parse(opts.body);
        return {
          status: 200,
          ok: true,
          json: async () => ({
            success: true,
            resulting_plan_input_state: { state_version: 2 }
          })
        };
      }
      return { status: 404, json: async () => ({}) };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    // 1. Source message/ref A is active
    const sourceMessageA = 'Parsel sınırı: (0;0), (20;0), (20;30), (0;30)';
    orchestrator.lastUserMessageText = sourceMessageA;
    orchestrator.lastUserMessageRef = 'chatmsg_A';

    // 2. Call interpret with message A
    const interpretPromise = testGateway.interpret(sourceMessageA);

    // 3. Mutate orchestrator while fetch is still unresolved
    orchestrator.lastUserMessageText = 'Başka bir mesaj';
    orchestrator.lastUserMessageRef = 'chatmsg_B';

    // 4. Resolve the interpretation response
    resolveInterpretFetch();
    await interpretPromise;

    // 5. Check proposal stored on orchestrator
    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].userMessageText, sourceMessageA);
    assert.strictEqual(pending[0].userMessageRef, 'chatmsg_A');

    // 6. Approve proposal and verify approval payload uses A/A
    await orchestrator.approveProposalById(pending[0].id);
    assert(capturedApprovalBody !== null);
    assert.strictEqual(capturedApprovalBody.user_message, sourceMessageA);
    assert.strictEqual(capturedApprovalBody.source_reference, 'chatmsg_A');
    console.log('✓ 39. real gateway async source-freeze test passed');
  }

  // Test 40: Missing proposal-time brief version aborts safely without HTTP request
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let fetchCalled = false;
    const testGateway = env.createGateway(async () => {
      fetchCalled = true;
      return { status: 200, json: async () => ({}) };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.proposalSequence += 1;
    const invalidProp = {
      id: `proposal_${orchestrator.proposalSequence}`,
      action: null,
      briefMutation: null,
      spatialRelationship: null,
      metricRequirement: null,
      siteGeometry: {
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      },
      expectedBriefVersion: null, // missing!
      expectedPlanInputStateVersion: null,
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      userMessageText: 'parsel',
      userMessageRef: 'chatmsg_1'
    };
    orchestrator.pendingProposals.set(invalidProp.id, invalidProp);

    const res = await orchestrator.approveProposalById(invalidProp.id);
    assert.strictEqual(res, null);
    assert.strictEqual(fetchCalled, false);
    console.log('✓ 40. missing expectedBriefVersion aborts safely without HTTP request');
  }

  // Test 40b: Site proposal created when source reference is missing NEVER invents "chatmsg_1" [Requirement 1]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let httpCalls = 0;
    const testGateway = env.createGateway(async () => {
      httpCalls++;
      return { status: 200, json: async () => ({}) };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    // Explicitly pass missing/null source reference
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_no_ref',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel sınırı', null);

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.notStrictEqual(pending[0].userMessageRef, 'chatmsg_1');
    assert.strictEqual(pending[0].userMessageRef, null);

    const res = await orchestrator.approveProposalById(pending[0].id);
    assert.strictEqual(res, null);
    assert.strictEqual(httpCalls, 0);
    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Kullanıcı kaynak referansı bulunamadığı için site geometrisi onaylanamadı.')));
    console.log('✓ 40b. missing source reference does not invent chatmsg_1 and aborts approval with zero HTTP requests');
  }

  // Test 40c: Site proposal does NOT fall back to mutable orchestrator state [Requirement 5 & 6]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let httpCalls = 0;
    const testGateway = env.createGateway(async () => {
      httpCalls++;
      return { status: 200, json: async () => ({}) };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.lastUserMessageText = 'UNRELATED CURRENT MESSAGE';
    orchestrator.lastUserMessageRef = 'chatmsg_unrelated';

    // Call handleStructuredLLMResponse WITHOUT explicit frozen source parameters
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_no_frozen',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 10 }]
      }]
    }, 'fp_test_1', 1, null, 3); // no frozen parameters passed

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.notStrictEqual(pending[0].userMessageText, 'UNRELATED CURRENT MESSAGE');
    assert.notStrictEqual(pending[0].userMessageRef, 'chatmsg_unrelated');
    assert.strictEqual(pending[0].userMessageText, '');
    assert.strictEqual(pending[0].userMessageRef, null);

    const res = await orchestrator.approveProposalById(pending[0].id);
    assert.strictEqual(res, null);
    assert.strictEqual(httpCalls, 0);
    console.log('✓ 40c. site proposal ignores mutable orchestrator state and aborts approval with zero HTTP calls');
  }

  // =========================================================================
  // Group H: Gateway Endpoint & HTTP Status Preservation (Tests 41-46)
  // =========================================================================

  // Test 41: Gateway calls POST /api/v1/projects/{projectId}/plan/input/site/approve
  {
    let requestedUrl = null;
    let requestedMethod = null;
    const g = new LocalLLMGateway({
      fetchFn: async (url, opts) => {
        requestedUrl = url;
        requestedMethod = opts.method;
        return {
          status: 200,
          json: async () => ({ success: true, resulting_plan_input_state: { state_version: 1 } })
        };
      }
    });

    await g.approveSiteGeometry('proj/special#1', { test: true });
    assert.strictEqual(requestedMethod, 'POST');
    assert.strictEqual(requestedUrl, 'http://127.0.0.1:8000/api/v1/projects/proj%2Fspecial%231/plan/input/site/approve');
    console.log('✓ 41. gateway approval URL uses URL-encoded project ID');
  }

  // Test 42: Gateway preserves actual HTTP status codes (200, 409, 422, 404, 500)
  {
    for (const status of [200, 409, 422, 404, 500]) {
      const g = new LocalLLMGateway({
        fetchFn: async () => ({
          status,
          json: async () => ({ success: status === 200, error: `HTTP ${status}` })
        })
      });
      const res = await g.approveSiteGeometry('proj_1', {});
      assert.strictEqual(res.httpStatus, status);
    }
    console.log('✓ 42. gateway preserves actual HTTP status codes');
  }

  // Test 43: Gateway network failure returns httpStatus: 0, failureKind: 'network'
  {
    const g = new LocalLLMGateway({
      fetchFn: async () => { throw new Error('Sensitive internal connection string failed at 192.168.1.100'); }
    });
    const res = await g.approveSiteGeometry('proj_1', {});
    assert.strictEqual(res.success, false);
    assert.strictEqual(res.httpStatus, 0);
    assert.strictEqual(res.failureKind, 'network');
    assert(!res.error.includes('192.168.1.100'));
    console.log('✓ 43. network failure returns httpStatus 0 and hides internal errors');
  }

  // Test 44: Gateway timeout failure returns httpStatus: 0, failureKind: 'timeout'
  {
    const g = new LocalLLMGateway({
      fetchFn: async () => {
        const err = new Error('The operation was aborted');
        err.name = 'AbortError';
        throw err;
      }
    });
    const res = await g.approveSiteGeometry('proj_1', {});
    assert.strictEqual(res.success, false);
    assert.strictEqual(res.httpStatus, 0);
    assert.strictEqual(res.failureKind, 'timeout');
    console.log('✓ 44. timeout failure returns httpStatus 0 and failureKind timeout');
  }

  // Test 45: Gateway rejects empty project ID
  {
    const g = new LocalLLMGateway();
    const res = await g.approveSiteGeometry('', {});
    assert.strictEqual(res.success, false);
    assert.strictEqual(res.httpStatus, 400);
    console.log('✓ 45. empty project ID rejected');
  }

  // Test 46: AbortController and signal propagation
  {
    const callerCtrl = new AbortController();
    callerCtrl.abort();
    const g = new LocalLLMGateway({
      fetchFn: async (url, opts) => {
        if (opts.signal && opts.signal.aborted) {
          const err = new Error('Aborted');
          err.name = 'AbortError';
          throw err;
        }
        return { status: 200, json: async () => ({ success: true }) };
      }
    });
    const res = await g.approveSiteGeometry('proj_1', {}, { signal: callerCtrl.signal });
    assert.strictEqual(res.httpStatus, 0);
    assert.strictEqual(res.failureKind, 'timeout');
    console.log('✓ 46. signal cancellation handled cleanly');
  }

  // =========================================================================
  // Group I: Success Handling & State Updates (Tests 47-50)
  // =========================================================================

  // Test 47: Successful approval stores record in siteGeometryProposalRecords
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 2 },
        approval_record: {
          proposal_status: 'user_approved',
          resulting_plan_input_state_version: 2
        }
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel sınırı', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    const record = await orchestrator.approveProposalById(propId);

    assert(record !== null);
    assert.strictEqual(orchestrator.siteGeometryProposalRecords.length, 1);
    assert.strictEqual(orchestrator.lastPlanInputStateVersion, 2);
    console.log('✓ 47. successful approval records resulting state version');
  }

  // Test 48: Successful approval deletes proposal from pendingProposals and marks button approved
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 1 }
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel sınırı', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);
    const approvedAction = orchestrator.allChatMessages[0].proposedActions[0];
    assert.strictEqual(approvedAction.status, 'approved');
    console.log('✓ 48. proposal removed from pending and marked approved');
  }

  // Test 49: Successful approval does NOT replace BriefSnapshot and does NOT auto-trigger preview [Requirement 8 Spy]
  {
    const env = setupEnvironment();
    const { orchestrator, briefSnapshot } = env;
    let previewCalls = 0;
    orchestrator.requestProjectPlanPreview = () => { previewCalls++; };
    orchestrator.previewProjectPlan = () => { previewCalls++; };

    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 1 }
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 3);
    assert.deepStrictEqual(orchestrator.getActiveBriefSnapshot(), briefSnapshot);
    assert.strictEqual(previewCalls, 0);
    console.log('✓ 49. approval success does NOT modify BriefSnapshot and does NOT auto-trigger preview (spy confirmed)');
  }

  // Test 50: Exact replay (HTTP 200 with same state version) accepted as success
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 1 } // state version remained 1
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    const record = await orchestrator.approveProposalById(propId);
    assert(record !== null);
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);
    console.log('✓ 50. exact replay 200 accepted as success');
  }

  // =========================================================================
  // Group J: Cross-Plan-Input Sibling Invalidation & Replay Hardening (Tests 51-54b)
  // =========================================================================

  // Test 51: State-changing Site approval (v1 -> v2) invalidates pending metric proposal created against v1 [Requirement 4A]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 2 }
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    // Site proposal created against plan input version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_site_A',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    // Metric proposal created against plan input version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Ölçü önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'prop_metric_B',
        space_id: 'sr_living',
        requirement_type: 'MIN_AREA',
        value: 30,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3, 'Salon en az 30 m² olsun.', 'chatmsg_metric_51', 'proj_test_123');

    assert.strictEqual(orchestrator.getActivePendingProposals().length, 2);
    const sitePropId = orchestrator.getActivePendingProposals().find(p => p.siteGeometry).id;
    const metricPropId = orchestrator.getActivePendingProposals().find(p => p.metricRequirement).id;

    // Approve Site proposal -> state version advances 1 -> 2
    await orchestrator.approveProposalById(sitePropId);

    // Pending proposals should now be empty (metric proposal invalidated)
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);

    // Chat message proposedActions copy is marked status = 'stale'
    const metricAction = orchestrator.allChatMessages
      .flatMap(m => m.proposedActions || [])
      .find(p => p.id === metricPropId);
    assert(metricAction !== undefined);
    assert.strictEqual(metricAction.status, 'stale');

    // Render UI and verify stale proposal button state
    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);

    const metricBtn = buttons.find(b => b.dataset.proposalId === metricPropId);
    assert(metricBtn !== undefined);
    assert.strictEqual(metricBtn.disabled, true);
    assert.strictEqual(metricBtn.textContent, 'Yeniden değerlendirilmeli');
    assert(metricBtn.classList.has('proposal-stale'));
    assert.notStrictEqual(metricBtn.textContent, 'Ölçüyü onayla');

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('diğer plan girdisi önerileri yeniden değerlendirilmelidir')));
    console.log('✓ 51. state-changing site approval invalidates pending metric proposal and marks UI button stale');
  }

  // Test 52: State-changing Metric approval (v1 -> v2) invalidates pending site proposal created against v1 [Requirement 4B]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        approval_record: {
          operation: 'replaced',
          state_changed: true,
          previous_value: 25,
          resulting_evidence_id: 'ev_metric_52',
          resulting_state_version: 2
        },
        resulting_plan_input_state: { state_version: 2 }
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    // Metric proposal created against plan input version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Ölçü önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'prop_metric_A',
        space_id: 'sr_living',
        requirement_type: 'MIN_AREA',
        value: 30,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3, 'Salon en az 30 m² olsun.', 'chatmsg_metric_52', 'proj_test_123');

    // Site proposal created against plan input version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_site_B',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    assert.strictEqual(orchestrator.getActivePendingProposals().length, 2);
    const metricPropId = orchestrator.getActivePendingProposals().find(p => p.metricRequirement).id;
    const sitePropId = orchestrator.getActivePendingProposals().find(p => p.siteGeometry).id;

    // Approve Metric proposal -> state version advances 1 -> 2
    await orchestrator.approveProposalById(metricPropId);

    // Pending proposals should now be empty (site proposal invalidated)
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);

    // Chat message proposedActions copy is marked status = 'stale'
    const siteAction = orchestrator.allChatMessages
      .flatMap(m => m.proposedActions || [])
      .find(p => p.id === sitePropId);
    assert(siteAction !== undefined);
    assert.strictEqual(siteAction.status, 'stale');

    // Render UI and verify stale proposal button state
    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);

    const siteBtn = buttons.find(b => b.dataset.proposalId === sitePropId);
    assert(siteBtn !== undefined);
    assert.strictEqual(siteBtn.disabled, true);
    assert.strictEqual(siteBtn.textContent, 'Yeniden değerlendirilmeli');
    assert(siteBtn.classList.has('proposal-stale'));
    assert.notStrictEqual(siteBtn.textContent, 'Parseli onayla');

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('diğer plan girdisi önerileri yeniden değerlendirilmelidir')));
    console.log('✓ 52. state-changing metric approval invalidates pending site proposal and marks UI button stale');
  }

  // Test 53a: Replay Case A: Site exact replay (v1 -> v1) preserves pending Metric proposal [Requirement 4C, 6 & 7]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 1 } // Exact replay: returns 1
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    // Site proposal against version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_site_S',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    // Metric proposal against version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Ölçü önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'prop_metric_M',
        space_id: 'sr_living',
        requirement_type: 'MIN_AREA',
        value: 30,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const siteProp = orchestrator.getActivePendingProposals().find(p => p.siteGeometry);
    const metricProp = orchestrator.getActivePendingProposals().find(p => p.metricRequirement);
    await orchestrator.approveProposalById(siteProp.id);

    // Metric M must REMAIN pending because state version did not change
    const remainingPending = orchestrator.getActivePendingProposals();
    assert.strictEqual(remainingPending.length, 1);
    assert(remainingPending[0].metricRequirement !== null);
    assert.strictEqual(remainingPending[0].metricRequirement.proposal_id, 'prop_metric_M');

    // Chat message proposedActions copy is NOT stale
    const metricAction = orchestrator.allChatMessages
      .flatMap(m => m.proposedActions || [])
      .find(p => p.id === metricProp.id);
    assert.notStrictEqual(metricAction.status, 'stale');

    // Render UI and verify metric button remains enabled
    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);

    const metricBtn = buttons.find(b => b.dataset.proposalId === metricProp.id);
    assert(metricBtn !== undefined);
    assert.strictEqual(metricBtn.disabled, false);
    assert.strictEqual(metricBtn.textContent, 'Ölçüyü onayla');
    assert(!metricBtn.classList.has('proposal-stale'));
    console.log('✓ 53a. site exact replay (v1->v1) preserves pending metric proposal with enabled button');
  }

  // Test 53b: Replay Case B: Metric exact replay (v1 -> v1) preserves pending Site proposal [Requirement 4D, 6 & 7]
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        approval_record: {
          operation: 'replayed',
          state_changed: false,
          previous_value: 30,
          resulting_evidence_id: 'ev_metric_53b',
          resulting_state_version: 1
        },
        resulting_plan_input_state: { state_version: 1 } // Exact replay: returns 1
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    // Metric proposal against version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Ölçü önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'prop_metric_M2',
        space_id: 'sr_living',
        requirement_type: 'MIN_AREA',
        value: 30,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3, 'Salon en az 30 m² olsun.', 'chatmsg_metric_53b', 'proj_test_123');

    // Site proposal against version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_site_S2',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    const metricProp = orchestrator.getActivePendingProposals().find(p => p.metricRequirement);
    const siteProp = orchestrator.getActivePendingProposals().find(p => p.siteGeometry);
    await orchestrator.approveProposalById(metricProp.id);

    // Site S must REMAIN pending because state version did not change
    const remainingPending = orchestrator.getActivePendingProposals();
    assert.strictEqual(remainingPending.length, 1);
    assert(remainingPending[0].siteGeometry !== null);
    assert.strictEqual(remainingPending[0].siteGeometry.proposal_id, 'prop_site_S2');

    // Chat message proposedActions copy is NOT stale
    const siteAction = orchestrator.allChatMessages
      .flatMap(m => m.proposedActions || [])
      .find(p => p.id === siteProp.id);
    assert.notStrictEqual(siteAction.status, 'stale');

    // Render UI and verify site button remains enabled
    const container = new MockElement('div');
    global.document.getElementById = () => container;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.classList && node.classList.has('proposal-approve-btn')) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);

    const siteBtn = buttons.find(b => b.dataset.proposalId === siteProp.id);
    assert(siteBtn !== undefined);
    assert.strictEqual(siteBtn.disabled, false);
    assert.strictEqual(siteBtn.textContent, 'Parseli onayla');
    assert(!siteBtn.classList.has('proposal-stale'));
    console.log('✓ 53b. metric exact replay (v1->v1) preserves pending site proposal with enabled button');
  }

  // Test 54: Non-plan-input proposals (brief, spatial, action) are NOT invalidated by site approval
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 200,
      json: async () => ({
        success: true,
        resulting_plan_input_state: { state_version: 2 }
      })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    // Site proposal against version 1
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_site_A',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    // Brief mutation proposal
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Brief önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [{
        mutation_id: 'mut_1',
        mutation_type: 'ADD_BRIEF_ITEM',
        brief_item: { normalized_statement: 'Manzara korunsun' }
      }]
    }, 'fp_test_1', 1, null, 3);

    const sitePropId = orchestrator.getActivePendingProposals().find(p => p.siteGeometry).id;
    await orchestrator.approveProposalById(sitePropId);

    // Brief proposal remains pending
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 1);
    assert(orchestrator.getActivePendingProposals()[0].briefMutation !== null);
    console.log('✓ 54. non-plan-input proposals not invalidated');
  }

  // =========================================================================
  // Group K: Failure & Stale Rejection UI Handling (Tests 55-60)
  // =========================================================================

  // Test 55: 409 Conflict surfaces safe message, does not retry or mark approved
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let callCount = 0;
    const testGateway = env.createGateway(async () => {
      callCount += 1;
      return {
        status: 409,
        json: async () => ({ success: false, error: 'Database integrity lock failed at /var/db/plan.sqlite' })
      };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    const res = await orchestrator.approveProposalById(propId);

    assert.strictEqual(res, null);
    assert.strictEqual(callCount, 1); // exactly 1 request, no retry
    assert.strictEqual(orchestrator.allChatMessages[0].proposedActions[0].status, undefined); // not approved
    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('artık güncel proje durumuna ait değil')));
    assert(!msgs.some(t => t.includes('/var/db/plan.sqlite')));
    console.log('✓ 55. 409 stale handled safely without retry/leak');
  }

  // Test 56: 422 Unprocessable surfaces safe invalid geometry message
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 422,
      json: async () => ({ success: false, error: 'Traceback: Polygon self-intersection detected at libgeos.so:412' })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Site geometrisi geçersiz olduğu için onaylanamadı.')));
    assert(!msgs.some(t => t.includes('libgeos.so')));
    console.log('✓ 56. 422 invalid geometry surfaces safe message');
  }

  // Test 57: 404 Not Found surfaces safe message
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 404,
      json: async () => ({ success: false, error: 'Project not found in repository' })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Proje veya brief verisi bulunamadığı için site geometrisi onaylanamadı.')));
    console.log('✓ 57. 404 not found surfaces safe message');
  }

  // Test 58: 500 Internal Error surfaces safe generic message
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => ({
      status: 500,
      json: async () => ({ success: false, error: 'OSError: Permission denied at C:\\Windows\\System32\\secret.key' })
    }));
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Site geometrisi şu anda kaydedilemedi. Sunucu tarafında bir hata oluştu.')));
    assert(!msgs.some(t => t.includes('System32')));
    console.log('✓ 58. 500 server error surfaces safe message');
  }

  // Test 59: Network failure surfaces safe message
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => { throw new Error('ECONNREFUSED 127.0.0.1:8000'); });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Yerel sunucuya ulaşılamadı. Lütfen bağlantınızı kontrol edin.')));
    assert(!msgs.some(t => t.includes('ECONNREFUSED')));
    console.log('✓ 59. network failure surfaces safe message');
  }

  // Test 60: Timeout failure surfaces safe timeout message
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    const testGateway = env.createGateway(async () => {
      const err = new Error('AbortError');
      err.name = 'AbortError';
      throw err;
    });
    orchestrator.setLocalLLMGateway(testGateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(propId);

    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Site geometri onay isteği zaman aşımına uğradı. Lütfen tekrar deneyin.')));
    console.log('✓ 60. timeout surfaces safe timeout message');
  }

  // =========================================================================
  // Group L: Dismissal & Fallback Summaries (Tests 61-65)
  // =========================================================================

  // Test 61: Dismissal removes site proposal from pendingProposals with safe message
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const propId = orchestrator.getActivePendingProposals()[0].id;
    const dismissed = orchestrator.dismissProposalById(propId);

    assert.strictEqual(dismissed, true);
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);
    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('Site geometri önerisi iptal edildi. Plan girdileri değiştirilmedi.')));
    console.log('✓ 61. dismissal removes proposal and displays safe message');
  }

  // Test 62: getConversationSummary formats site_geometry using getSiteGeometryDescription
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    const summary = orchestrator.getConversationSummary();
    assert(summary.includes('Parsel sınırı: (0;0), (20;0), (20;30), (0;30).'));
    assert(!summary.includes('[object Object]'));
    console.log('✓ 62. getConversationSummary formats site_geometry correctly');
  }

  // Test 63: Existing proposalRecords-based getCurrentDecisions behavior preserved exactly
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.proposalRecords.push({
      proposal_status: 'user_approved',
      proposed_action: { description: 'Action decision' }
    });

    const decisions = orchestrator.getCurrentDecisions();
    assert.strictEqual(decisions.length, 1);
    assert.strictEqual(decisions[0], 'user_approved: Action decision');
    console.log('✓ 63. existing getCurrentDecisions behavior preserved');
  }

  // Test 64: handleLocalLLMFallback includes site_geometry description
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'prop_p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, null, 3, 'Parsel', 'chatmsg_1');

    orchestrator.handleLocalLLMFallback('Yeni istek', 'timeout');
    const msgs = orchestrator.allChatMessages.map(m => m.text);
    const lastMsg = msgs[msgs.length - 1];
    assert(lastMsg.includes('Parsel sınırı: (0;0), (20;0), (20;30), (0;30).'));
    assert(!lastMsg.includes('[object Object]'));
    console.log('✓ 64. handleLocalLLMFallback includes site_geometry description');
  }

  // Test 65: Multiple site geometry approvals accumulate in siteGeometryProposalRecords
  {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let stateVer = 1;
    const testGateway = env.createGateway(async () => {
      stateVer += 1;
      return {
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: stateVer }
        })
      };
    });
    orchestrator.setLocalLLMGateway(testGateway);

    // Approval 1: Parcel
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Parsel önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'p1',
        role: 'PARCEL_BOUNDARY',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }]
      }]
    }, 'fp_test_1', 1, 1, 3, 'Parsel', 'chatmsg_1');
    await orchestrator.approveProposalById(orchestrator.getActivePendingProposals()[0].id);

    // Approval 2: Envelope
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Zarf önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_site_geometries: [{
        proposal_id: 'e1',
        role: 'BUILDABLE_ENVELOPE',
        vertices: [{ x_m: 2, y_m: 2 }, { x_m: 18, y_m: 2 }, { x_m: 18, y_m: 28 }, { x_m: 2, y_m: 28 }]
      }]
    }, 'fp_test_1', 1, 2, 3, 'Zarf', 'chatmsg_2');
    await orchestrator.approveProposalById(orchestrator.getActivePendingProposals()[0].id);

    assert.strictEqual(orchestrator.siteGeometryProposalRecords.length, 2);
    assert.strictEqual(orchestrator.lastPlanInputStateVersion, 3);
    console.log('✓ 65. multiple site geometry approvals accumulate in siteGeometryProposalRecords');
  }

  console.log('\nAll 65 Site Geometry Plan Input UI V0 JS Unit Tests Passed Successfully!\n');
}

runAllTests().catch(err => {
  console.error('Test suite failed:', err);
  process.exit(1);
});
