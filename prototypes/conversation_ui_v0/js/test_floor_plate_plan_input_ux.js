/**
 * BRIF.AI — JS Unit Test Suite for Conversation Floor Plate Plan Input UI V0
 * Tests floor plate proposal capture, rendering, approval gateway, stale rejection,
 * dismissal, browser validation, payload security, replay hardening, cross-invalidation,
 * and regression boundaries (Tests 1-60+).
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
    levelId: 'lvl_ground',
    contextFingerprint: 'fp_test_1',
    generationId: 1
  };

  const briefSnapshot = {
    project_id: projectId,
    brief_version: 1,
    space_requests: [
      { id: 'sr_living', space_id: 'living_room', display_name: 'Salon' }
    ]
  };

  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine(activeSnapshot);
  const store = new MockDocumentStore();
  const resolver = new MockScopeResolver();
  const assistant = new MockAssistant();
  const presenter = new MockPresenter();

  const orchestrator = new ConversationOrchestrator({
    hierarchy,
    stateMachine,
    store,
    resolver,
    assistant,
    presenter,
    briefSnapshotsByProject: { [projectId]: briefSnapshot }
  });

  const localLLMGateway = new LocalLLMGateway({
    stateMachine,
    hierarchy,
    orchestrator,
    fetchFn: async () => ({})
  });
  orchestrator.localLLMGateway = localLLMGateway;

  orchestrator.briefSnapshot = briefSnapshot;
  orchestrator.getActiveBriefSnapshot = () => briefSnapshot;
  orchestrator.briefSnapshotsByProject = { [projectId]: briefSnapshot };

  return { orchestrator, localLLMGateway, stateMachine, hierarchy, briefSnapshot };
}

async function runTests() {
  let passed = 0;
  let failed = 0;

  async function test(name, fn) {
    try {
      await fn();
      console.log(`PASS: ${name}`);
      passed++;
    } catch (err) {
      console.error(`FAIL: ${name}`);
      console.error(err);
      failed++;
    }
  }

  console.log('--- Starting Floor Plate UI Unit Tests ---');

  // Test 1: Gateway validation parses valid proposed_floor_plates
  await test('1. Gateway validation accepts valid proposed_floor_plates', () => {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Taban oturumu önerildi.',
      intent: 'gather_requirement',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [],
      proposed_floor_plates: [
        {
          proposal_id: 'prop_fp_1',
          vertices: [
            { x_m: 0, y_m: 0 },
            { x_m: 12, y_m: 0 },
            { x_m: 12, y_m: 18 },
            { x_m: 0, y_m: 18 }
          ],
          rationale: '12x18 taban oturumu.'
        }
      ]
    };
    assert.strictEqual(gateway.isValidatedResult(result), true);
  });

  // Test 2: Gateway validation rejects floor plate with missing proposal_id
  await test('2. Gateway validation rejects floor plate with missing proposal_id', () => {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Test',
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [],
      proposed_floor_plates: [
        {
          vertices: [
            { x_m: 0, y_m: 0 },
            { x_m: 12, y_m: 0 },
            { x_m: 12, y_m: 18 },
            { x_m: 0, y_m: 18 }
          ]
        }
      ]
    };
    assert.strictEqual(gateway.isValidatedResult(result), false);
  });

  // Test 3: Gateway validation rejects floor plate with fewer than 3 vertices
  await test('3. Gateway validation rejects floor plate with fewer than 3 vertices', () => {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Test',
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [],
      proposed_floor_plates: [
        {
          proposal_id: 'prop_fp_1',
          vertices: [
            { x_m: 0, y_m: 0 },
            { x_m: 12, y_m: 0 }
          ]
        }
      ]
    };
    assert.strictEqual(gateway.isValidatedResult(result), false);
  });

  // Test 4: Gateway rejects authoritative field injection in floor plate DTO
  await test('4. Gateway rejects authoritative field injection in proposed_floor_plates', () => {
    const gateway = new LocalLLMGateway();
    const injectedFields = ['schema_version', 'project_id', 'level_id', 'provenance', 'evidence_ids', 'status'];
    for (const field of injectedFields) {
      const result = {
        assistant_message: 'Test',
        needs_user_confirmation: true,
        proposed_actions: [],
        proposed_brief_mutations: [],
        proposed_spatial_relationships: [],
        proposed_metric_requirements: [],
        proposed_site_geometries: [],
        proposed_floor_plates: [
          {
            proposal_id: 'prop_fp_1',
            vertices: [
              { x_m: 0, y_m: 0 },
              { x_m: 12, y_m: 0 },
              { x_m: 12, y_m: 18 },
              { x_m: 0, y_m: 18 }
            ],
            [field]: 'injected_untrusted_value'
          }
        ]
      };
      assert.strictEqual(gateway.isValidatedResult(result), false, `Should reject field ${field}`);
    }
  });

  // Test 5: Orchestrator captures and stores floor plate proposal with source freeze
  await test('5. Orchestrator captures floor plate proposal with source message and ref', () => {
    const { orchestrator } = setupEnvironment();
    orchestrator.lastUserMessageText = 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)';
    orchestrator.lastUserMessageRef = 'chatmsg_42';

    const llmResult = {
      assistant_message: 'Taban oturumunu onaylayabilirsiniz.',
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [],
      proposed_floor_plates: [
        {
          proposal_id: 'prop_fp_1',
          vertices: [
            { x_m: 0, y_m: 0 },
            { x_m: 12, y_m: 0 },
            { x_m: 12, y_m: 18 },
            { x_m: 0, y_m: 18 }
          ],
          rationale: 'Taban oturumu.'
        }
      ]
    };

    orchestrator.handleStructuredLLMResponse(
      llmResult,
      'fp_test_1',
      1,
      1,
      1,
      'Taban oturumu: (0;0), (12;0), (12;18), (0;18)',
      'chatmsg_42'
    );
    const proposals = orchestrator.getActivePendingProposals();
    assert.strictEqual(proposals.length, 1);
    const p = proposals[0];
    assert.strictEqual(p.userMessageText, 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)');
    assert.strictEqual(p.userMessageRef, 'chatmsg_42');
    assert.strictEqual(p.floorPlate.proposal_id, 'prop_fp_1');
  });

  // Test 6: Floor plate proposal without source reference refuses fallback to chatmsg_1
  await test('6. Floor plate proposal without source ref preserves null and does not inject chatmsg_1', () => {
    const { orchestrator } = setupEnvironment();
    orchestrator.lastUserMessageText = 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)';
    orchestrator.lastUserMessageRef = null; // Missing!

    const llmResult = {
      assistant_message: 'Öneri',
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [],
      proposed_floor_plates: [
        {
          proposal_id: 'prop_fp_1',
          vertices: [
            { x_m: 0, y_m: 0 },
            { x_m: 12, y_m: 0 },
            { x_m: 12, y_m: 18 },
            { x_m: 0, y_m: 18 }
          ]
        }
      ]
    };

    orchestrator.handleStructuredLLMResponse(
      llmResult,
      'fp_test_1',
      1,
      1,
      1,
      'Taban oturumu: (0;0), (12;0), (12;18), (0;18)',
      null
    );
    const proposals = orchestrator.getActivePendingProposals();
    assert.strictEqual(proposals.length, 1);
    assert.strictEqual(proposals[0].userMessageRef, null);
    assert.notStrictEqual(proposals[0].userMessageRef, 'chatmsg_1');
  });

  // Test 7A: Approval aborts with 0 HTTP calls if source text is null
  await test('7A. Approval aborts with zero HTTP calls if userMessageText is null', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    let httpCalled = false;
    localLLMGateway.approveFloorPlate = async () => {
      httpCalled = true;
      return { success: true };
    };

    orchestrator.pendingProposals.set('prop_fp_null_text', {
      id: 'prop_fp_null_text',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: null,
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_null_text',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const result = await orchestrator.approveProposalById('prop_fp_null_text');
    assert.strictEqual(result, null);
    assert.strictEqual(httpCalled, false);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('Kullanıcı kaynak mesajı bulunamadığı için taban oturumu onaylanamadı.'));
  });

  // Test 7B: Approval aborts with 0 HTTP calls if source text is empty string
  await test('7B. Approval aborts with zero HTTP calls if userMessageText is empty string', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    let httpCalled = false;
    localLLMGateway.approveFloorPlate = async () => {
      httpCalled = true;
      return { success: true };
    };

    orchestrator.pendingProposals.set('prop_fp_empty_text', {
      id: 'prop_fp_empty_text',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: '   ',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_empty_text',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const result = await orchestrator.approveProposalById('prop_fp_empty_text');
    assert.strictEqual(result, null);
    assert.strictEqual(httpCalled, false);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('Kullanıcı kaynak mesajı bulunamadığı için taban oturumu onaylanamadı.'));
  });

  // Test 7C: Approval aborts with 0 HTTP calls if source ref is null
  await test('7C. Approval aborts with zero HTTP calls if userMessageRef is null', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    let httpCalled = false;
    localLLMGateway.approveFloorPlate = async () => {
      httpCalled = true;
      return { success: true };
    };

    orchestrator.pendingProposals.set('prop_fp_null_ref', {
      id: 'prop_fp_null_ref',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)',
      userMessageRef: null,
      floorPlate: {
        proposal_id: 'prop_fp_null_ref',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const result = await orchestrator.approveProposalById('prop_fp_null_ref');
    assert.strictEqual(result, null);
    assert.strictEqual(httpCalled, false);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('Kullanıcı kaynak referansı bulunamadığı için taban oturumu onaylanamadı.'));
  });

  // Test 8: Real Gateway Async Source-Freeze Integration Test
  await test('8. Real gateway async interpret source-freeze test against in-flight mutations', async () => {
    const env = setupEnvironment();
    const { orchestrator } = env;
    let capturedApprovalBody = null;
    let resolveInterpretFetch = null;

    const testGateway = new LocalLLMGateway({
      stateMachine: env.stateMachine,
      hierarchy: env.hierarchy,
      orchestrator,
      fetchFn: async (url, opts) => {
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
                  authoritative_plan_input_state_version: 1,
                  result: {
                    assistant_message: 'Taban oturumu önerisi.',
                    intent: 'modify_space',
                    confidence: 0.9,
                    needs_user_confirmation: true,
                    needs_follow_up: false,
                    proposed_actions: [],
                    proposed_floor_plates: [{
                      proposal_id: 'prop_async_fp_1',
                      vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }],
                      rationale: '12x18 taban oturumu'
                    }]
                  }
                })
              });
            };
          });
        }
        if (url.includes('/plan/input/floor-plate/approve')) {
          capturedApprovalBody = JSON.parse(opts.body);
          return {
            status: 200,
            ok: true,
            json: async () => ({
              success: true,
              resulting_plan_input_state: { state_version: 2 },
              approval_record: { proposal_status: 'user_approved' }
            })
          };
        }
        return { status: 404, json: async () => ({}) };
      }
    });
    orchestrator.localLLMGateway = testGateway;

    // 1. Source message/ref A is active
    const sourceMessageA = 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)';
    orchestrator.lastUserMessageText = sourceMessageA;
    orchestrator.lastUserMessageRef = 'chatmsg_A';

    // 2. Call interpret with message A
    const interpretPromise = testGateway.interpret(sourceMessageA);

    // 3. Mutate orchestrator while fetch is still unresolved
    orchestrator.lastUserMessageText = 'İkinci alakasız mesaj B';
    orchestrator.lastUserMessageRef = 'chatmsg_B';

    // 4. Resolve the interpretation response
    resolveInterpretFetch();
    await interpretPromise;

    // 5. Check proposal stored on orchestrator
    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].userMessageText, sourceMessageA);
    assert.strictEqual(pending[0].userMessageRef, 'chatmsg_A');

    // 6. Approve proposal and verify approval payload uses message A and chatmsg_A
    await orchestrator.approveProposalById(pending[0].id);
    assert(capturedApprovalBody !== null);
    assert.strictEqual(capturedApprovalBody.user_message, sourceMessageA);
    assert.strictEqual(capturedApprovalBody.source_reference, 'chatmsg_A');
  });

  // Test 9: Exact approval payload key-set
  await test('9. Exact approval payload key-set sent to gateway', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    let capturedPayload = null;
    localLLMGateway.approveFloorPlate = async (pid, payload) => {
      capturedPayload = payload;
      return {
        success: true,
        resulting_plan_input_state: { state_version: 1 },
        approval_record: { proposal_status: 'user_approved' }
      };
    };

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri',
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [],
      proposed_site_geometries: [],
      proposed_floor_plates: [
        {
          proposal_id: 'prop_fp_1',
          vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
        }
      ]
    }, 'fp_test_1', 1, 1, 1, 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)', 'chatmsg_99');

    const proposalId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(proposalId);

    assert.ok(capturedPayload);
    const expectedKeys = [
      'proposed_floor_plate',
      'current_project_id',
      'expected_brief_version',
      'expected_plan_input_state_version',
      'proposal_fingerprint',
      'current_fingerprint',
      'proposal_generation_id',
      'current_generation_id',
      'user_message',
      'source_reference'
    ].sort();
    const actualKeys = Object.keys(capturedPayload).sort();
    assert.deepStrictEqual(actualKeys, expectedKeys);
  });

  // Cross-Type Invalidation Matrix Tests:
  // Matrix 1: FloorPlate replay N -> N preserves Metric sibling
  await test('10. Cross Matrix: FloorPlate replay N -> N preserves Metric sibling', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 1 } // Same version (replay N -> N)
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.pendingProposals.set('prop_metric_1', {
      id: 'prop_metric_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      metricRequirement: { space_id: 'living_room', requirement_type: 'MIN_AREA', value: 30 }
    });
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    await orchestrator.approveProposalById('prop_fp_1');
    assert.ok(orchestrator.pendingProposals.has('prop_metric_1'), 'Metric sibling must remain active');
  });

  // Matrix 2: FloorPlate replay N -> N preserves Site sibling
  await test('11. Cross Matrix: FloorPlate replay N -> N preserves Site sibling', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 1 }
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.pendingProposals.set('prop_site_1', {
      id: 'prop_site_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      siteGeometry: { role: 'PARCEL_BOUNDARY', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }] }
    });
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    await orchestrator.approveProposalById('prop_fp_1');
    assert.ok(orchestrator.pendingProposals.has('prop_site_1'), 'Site sibling must remain active');
  });

  // Matrix 3: Metric replay N -> N preserves FloorPlate sibling
  await test('12. Cross Matrix: Metric replay N -> N preserves FloorPlate sibling', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveMetricRequirement = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 1 }
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });
    orchestrator.pendingProposals.set('prop_metric_1', {
      id: 'prop_metric_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      metricRequirement: { space_id: 'living_room', requirement_type: 'MIN_AREA', value: 30 }
    });

    await orchestrator.approveProposalById('prop_metric_1');
    assert.ok(orchestrator.pendingProposals.has('prop_fp_1'), 'FloorPlate sibling must remain active');
  });

  // Matrix 4: Site replay N -> N preserves FloorPlate sibling
  await test('13. Cross Matrix: Site replay N -> N preserves FloorPlate sibling', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveSiteGeometry = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 1 }
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });
    orchestrator.pendingProposals.set('prop_site_1', {
      id: 'prop_site_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Parsel sınırı',
      userMessageRef: 'chatmsg_1',
      siteGeometry: { role: 'PARCEL_BOUNDARY', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }] }
    });

    await orchestrator.approveProposalById('prop_site_1');
    assert.ok(orchestrator.pendingProposals.has('prop_fp_1'), 'FloorPlate sibling must remain active');
  });

  // Matrix 5: FloorPlate mutation N -> N+1 stales Metric + Site + FloorPlate siblings
  await test('14. Cross Matrix: FloorPlate mutation N -> N+1 stales Metric, Site, and other FloorPlate siblings', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 2 } // Version advanced!
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.allChatMessages = [
      {
        id: 'msg_1',
        proposedActions: [
          { id: 'prop_fp_target', status: 'pending' },
          { id: 'prop_metric_sib', status: 'pending' },
          { id: 'prop_site_sib', status: 'pending' },
          { id: 'prop_fp_sib', status: 'pending' }
        ]
      }
    ];

    orchestrator.pendingProposals.set('prop_fp_target', {
      id: 'prop_fp_target',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu 12x18',
      userMessageRef: 'chatmsg_1',
      floorPlate: { proposal_id: 'prop_fp_target', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }] }
    });
    orchestrator.pendingProposals.set('prop_metric_sib', {
      id: 'prop_metric_sib',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      metricRequirement: { space_id: 'living_room', requirement_type: 'MIN_AREA', value: 30 }
    });
    orchestrator.pendingProposals.set('prop_site_sib', {
      id: 'prop_site_sib',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      siteGeometry: { role: 'PARCEL_BOUNDARY', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }] }
    });
    orchestrator.pendingProposals.set('prop_fp_sib', {
      id: 'prop_fp_sib',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      floorPlate: { proposal_id: 'prop_fp_sib', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 15 }, { x_m: 0, y_m: 15 }] }
    });

    await orchestrator.approveProposalById('prop_fp_target');

    assert.strictEqual(orchestrator.pendingProposals.has('prop_metric_sib'), false);
    assert.strictEqual(orchestrator.pendingProposals.has('prop_site_sib'), false);
    assert.strictEqual(orchestrator.pendingProposals.has('prop_fp_sib'), false);

    const chatActions = orchestrator.allChatMessages[0].proposedActions;
    assert.strictEqual(chatActions.find(a => a.id === 'prop_fp_target').status, 'approved');
    assert.strictEqual(chatActions.find(a => a.id === 'prop_metric_sib').status, 'stale');
    assert.strictEqual(chatActions.find(a => a.id === 'prop_site_sib').status, 'stale');
    assert.strictEqual(chatActions.find(a => a.id === 'prop_fp_sib').status, 'stale');
  });

  // Matrix 6: Metric mutation N -> N+1 stales FloorPlate sibling
  await test('15. Cross Matrix: Metric mutation N -> N+1 stales FloorPlate sibling', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveMetricRequirement = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 2 }
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.allChatMessages = [
      {
        id: 'msg_1',
        proposedActions: [
          { id: 'prop_metric_target', status: 'pending' },
          { id: 'prop_fp_sib', status: 'pending' }
        ]
      }
    ];

    orchestrator.pendingProposals.set('prop_metric_target', {
      id: 'prop_metric_target',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      metricRequirement: { space_id: 'living_room', requirement_type: 'MIN_AREA', value: 30 }
    });
    orchestrator.pendingProposals.set('prop_fp_sib', {
      id: 'prop_fp_sib',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      floorPlate: { proposal_id: 'prop_fp_sib', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 15 }, { x_m: 0, y_m: 15 }] }
    });

    await orchestrator.approveProposalById('prop_metric_target');
    assert.strictEqual(orchestrator.pendingProposals.has('prop_fp_sib'), false);
    assert.strictEqual(orchestrator.allChatMessages[0].proposedActions.find(a => a.id === 'prop_fp_sib').status, 'stale');
  });

  // Matrix 7: Site mutation N -> N+1 stales FloorPlate sibling
  await test('16. Cross Matrix: Site mutation N -> N+1 stales FloorPlate sibling', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveSiteGeometry = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 2 }
    });

    orchestrator.lastPlanInputStateVersion = 1;
    orchestrator.allChatMessages = [
      {
        id: 'msg_1',
        proposedActions: [
          { id: 'prop_site_target', status: 'pending' },
          { id: 'prop_fp_sib', status: 'pending' }
        ]
      }
    ];

    orchestrator.pendingProposals.set('prop_site_target', {
      id: 'prop_site_target',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Parsel',
      userMessageRef: 'chatmsg_1',
      siteGeometry: { role: 'PARCEL_BOUNDARY', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 20, y_m: 0 }, { x_m: 20, y_m: 30 }, { x_m: 0, y_m: 30 }] }
    });
    orchestrator.pendingProposals.set('prop_fp_sib', {
      id: 'prop_fp_sib',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedPlanInputStateVersion: 1,
      floorPlate: { proposal_id: 'prop_fp_sib', vertices: [{ x_m: 0, y_m: 0 }, { x_m: 10, y_m: 0 }, { x_m: 10, y_m: 15 }, { x_m: 0, y_m: 15 }] }
    });

    await orchestrator.approveProposalById('prop_site_target');
    assert.strictEqual(orchestrator.pendingProposals.has('prop_fp_sib'), false);
    assert.strictEqual(orchestrator.allChatMessages[0].proposedActions.find(a => a.id === 'prop_fp_sib').status, 'stale');
  });

  // Test 17: Stale proposal renders disabled button with "Yeniden değerlendirilmeli"
  await test('17. Stale floor plate proposal renders disabled button with "Yeniden değerlendirilmeli"', () => {
    const { orchestrator } = setupEnvironment();
    const messages = [
      {
        id: 'msg_1',
        role: 'assistant',
        text: 'Öneri yapıldı',
        snapshot: {
          projectId: 'proj_test_123',
          buildingId: 'bldg_main',
          levelId: 'lvl_ground'
        },
        proposedActions: [
          {
            id: 'prop_fp_stale',
            status: 'stale',
            floorPlate: {
              proposal_id: 'prop_fp_stale',
              vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
            }
          }
        ]
      }
    ];

    const container = new MockElement('div');
    global.document.getElementById = (id) => (id === 'chatMessagesContainer' ? container : new MockElement('div'));
    orchestrator.allChatMessages = messages;
    orchestrator.renderFilteredChatMessages();

    const buttons = [];
    function collectButtons(node) {
      if (node.tag === 'button' || (node.classList && node.classList.has('proposal-approve-btn'))) buttons.push(node);
      (node.children || []).forEach(collectButtons);
    }
    collectButtons(container);

    const staleBtn = buttons.find(b => b.dataset.proposalId === 'prop_fp_stale');
    assert(staleBtn !== undefined, 'Should render button for stale proposal');
    assert.strictEqual(staleBtn.disabled, true);
    assert.strictEqual(staleBtn.textContent, 'Yeniden değerlendirilmeli');
    assert(staleBtn.classList.has('proposal-stale'));
  });

  // Test 18: Explicit no-auto-preview spy verification on actual production methods
  await test('18. Floor plate approval does NOT trigger auto preview generation (requestProjectPlanPreview & previewProjectPlan call count === 0)', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    let orchestratorPreviewCalls = 0;
    let gatewayPreviewCalls = 0;

    localLLMGateway.approveFloorPlate = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 1 }
    });

    // Spy actual production preview entrypoints
    orchestrator.requestProjectPlanPreview = () => {
      orchestratorPreviewCalls++;
      throw new Error('Auto preview triggered on orchestrator!');
    };
    localLLMGateway.previewProjectPlan = async () => {
      gatewayPreviewCalls++;
      throw new Error('Auto preview triggered on gateway!');
    };
    localLLMGateway.previewPlan = async () => {
      gatewayPreviewCalls++;
      throw new Error('Auto preview plan triggered on gateway!');
    };

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu: (0;0), (12;0), (12;18), (0;18)',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(orchestratorPreviewCalls, 0, 'requestProjectPlanPreview call count must remain 0');
    assert.strictEqual(gatewayPreviewCalls, 0, 'previewProjectPlan call count must remain 0');
  });

  // Test 19: Approval handles 409 stale brief/context
  await test('19. Approval handles 409 stale version conflict gracefully', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: false,
      httpStatus: 409,
      error: 'Conflict'
    });

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(res, null);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('güncel proje durumuna ait değil'));
  });

  // Test 20: Approval handles 422 validation failure
  await test('20. Approval handles 422 validation error gracefully', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: false,
      httpStatus: 422,
      error: 'Unprocessable Entity'
    });

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(res, null);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('geçersiz olduğu için onaylanamadı'));
  });

  // Test 21: Approval handles 404 project not found
  await test('21. Approval handles 404 project not found gracefully', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: false,
      httpStatus: 404,
      error: 'Not Found'
    });

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(res, null);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('bulunamadığı için taban oturumu onaylanamadı'));
  });

  // Test 22: Approval handles 500 server error
  await test('22. Approval handles 500 server error gracefully', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: false,
      httpStatus: 500,
      error: 'Internal Server Error'
    });

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(res, null);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('Sunucu tarafında bir hata oluştu'));
  });

  // Test 23: Approval handles timeout
  await test('23. Approval handles timeout gracefully', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: false,
      httpStatus: 0,
      failureKind: 'timeout'
    });

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(res, null);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('zaman aşımına uğradı'));
  });

  // Test 24: Direct dismissal via dismissProposalById
  await test('24. Direct dismissal via dismissProposalById removes proposal and appends message', () => {
    const { orchestrator } = setupEnvironment();
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const dismissed = orchestrator.dismissProposalById('prop_fp_1');
    assert.strictEqual(dismissed, true);
    assert.strictEqual(orchestrator.pendingProposals.has('prop_fp_1'), false);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('Taban oturumu önerisi iptal edildi'));
  });

  // Test 25: Conversational rejection command ("vazgeç")
  await test('25. Conversational rejection command ("vazgeç") dismisses single proposal', async () => {
    const { orchestrator } = setupEnvironment();
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.handlePendingProposalCommand('Vazgeç');
    assert.strictEqual(res.status, 'dismissed');
    assert.strictEqual(orchestrator.pendingProposals.has('prop_fp_1'), false);
  });

  // Test 26: Conversational confirmation command ("onayla")
  await test('26. Conversational confirmation command ("onayla") approves single proposal', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    localLLMGateway.approveFloorPlate = async () => ({
      success: true,
      resulting_plan_input_state: { state_version: 1 },
      approval_record: { proposal_status: 'user_approved' }
    });

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.handlePendingProposalCommand('Onaylıyorum');
    assert.strictEqual(res.status, 'approved');
  });

  // Test 27: Floor plate description formatting
  await test('27. Floor plate description formatting with Turkish coordinates', () => {
    const { orchestrator } = setupEnvironment();
    const fp = {
      proposal_id: 'prop_fp_1',
      vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12.5, y_m: 0 }, { x_m: 12.5, y_m: 18 }, { x_m: 0, y_m: 18 }]
    };
    const desc = orchestrator.getFloorPlateDescription(fp);
    assert.ok(desc.includes('Taban oturumu'));
    assert.ok(desc.includes('(12,5;0)'));
  });

  // Test 28: Floor plate in getPendingProposalContext serialization
  await test('28. Floor plate included in getPendingProposalContext', () => {
    const { orchestrator } = setupEnvironment();
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const ctx = orchestrator.getPendingProposalContext();
    assert.strictEqual(ctx.length, 1);
    assert.ok(ctx[0].floor_plate);
    assert.strictEqual(ctx[0].floor_plate.proposal_id, 'prop_fp_1');
  });

  // Test 29: Floor plate in getConversationSummary
  await test('29. Floor plate summarized in getConversationSummary', () => {
    const { orchestrator } = setupEnvironment();
    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_test_1',
      generationId: 1,
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const summary = orchestrator.getConversationSummary();
    assert.ok(summary.includes('Taban oturumu'));
  });

  // Test 30: Context fingerprint mismatch aborts approval
  await test('30. Context fingerprint mismatch aborts approval without HTTP call', async () => {
    const { orchestrator, localLLMGateway } = setupEnvironment();
    let httpCalled = false;
    localLLMGateway.approveFloorPlate = async () => {
      httpCalled = true;
      return { success: true };
    };

    orchestrator.pendingProposals.set('prop_fp_1', {
      id: 'prop_fp_1',
      contextFingerprint: 'fp_old_diff',
      generationId: 1,
      expectedBriefVersion: 1,
      expectedPlanInputStateVersion: 1,
      userMessageText: 'Taban oturumu',
      userMessageRef: 'chatmsg_1',
      floorPlate: {
        proposal_id: 'prop_fp_1',
        vertices: [{ x_m: 0, y_m: 0 }, { x_m: 12, y_m: 0 }, { x_m: 12, y_m: 18 }, { x_m: 0, y_m: 18 }]
      }
    });

    const res = await orchestrator.approveProposalById('prop_fp_1');
    assert.strictEqual(res, null);
    assert.strictEqual(httpCalled, false);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.ok(lastMsg.text.includes('Bağlam değiştiği için bu öneri onaylanamadı'));
  });

  console.log(`--- Summary: ${passed} passed, ${failed} failed ---`);
  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch(err => {
  console.error('Unhandled error in test suite:', err);
  process.exit(1);
});
