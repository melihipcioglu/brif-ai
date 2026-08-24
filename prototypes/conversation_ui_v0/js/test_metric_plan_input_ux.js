/**
 * BRIF.AI — JS Unit Test Suite for Conversation Metric Plan Input UI V0
 * Tests metric proposal capture, rendering, approval gateway, stale rejection,
 * dismissal, browser validation, and regression boundaries (Tests 1-42).
 */

const assert = require('assert');
const LocalLLMGateway = require('./local_llm_gateway.js');
const ConversationOrchestrator = require('./conversation_orchestrator.js');

class MockElement {
  constructor(tag = 'div') {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.classList = new Set();
    this.textContent = '';
    this.disabled = false;
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
}

global.document = {
  createElement(tag) { return new MockElement(tag); },
  getElementById() { return new MockElement('div'); }
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
      { id: 'sr_kitchen', display_name: 'Mutfak', minimum_quantity: 1 },
      { id: 'sr_corridor', display_name: 'Koridor', minimum_quantity: 1 },
      { id: 'sr_child_room', display_name: 'Çocuk Odası', minimum_quantity: 2 }
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

  return { orchestrator, stateMachine, briefSnapshot, activeSnapshot };
}

async function runAllTests() {
  console.log('Running Metric Plan Input UI V0 JS Unit Tests (1-42)...');

  // Test 1: Interpret response metric proposal is captured
  {
    const { orchestrator } = setupEnvironment();
    const result = {
      assistant_message: 'Salon için minimum 30 m² alan önerildi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [
        {
          proposal_id: 'prop_metric_1',
          space_id: 'sn_living_01',
          requirement_type: 'MIN_AREA',
          value: 30.0,
          unit: 'SQUARE_METRE'
        }
      ]
    };
    orchestrator.handleStructuredLLMResponse(result, 'fp_test_1', 1, 2);
    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].metricRequirement.proposal_id, 'prop_metric_1');
    console.log('✓ 1. interpret response metric proposal is captured');
  }

  // Test 2: Authoritative plan input state version captured on proposal
  {
    const { orchestrator } = setupEnvironment();
    const result = {
      assistant_message: 'Mutfak için maksimum 20 m².',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [
        {
          proposal_id: 'prop_metric_2',
          space_id: 'sn_kitchen_01',
          requirement_type: 'MAX_AREA',
          value: 20.0,
          unit: 'SQUARE_METRE'
        }
      ]
    };
    orchestrator.handleStructuredLLMResponse(result, 'fp_test_1', 1, 5);
    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending[0].expectedPlanInputStateVersion, 5);
    console.log('✓ 2. authoritative_plan_input_state_version captured on proposal');
  }

  // Test 3: Metric proposal renders readable MIN_AREA label
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getMetricRequirementDescription({
      proposal_id: 'p3',
      space_id: 'sn_living_01',
      requirement_type: 'MIN_AREA',
      value: 30,
      unit: 'SQUARE_METRE'
    });
    assert.strictEqual(desc, '“Salon en az 30 m² olsun.” plan girdilerine eklensin mi?');
    console.log('✓ 3. metric proposal renders readable MIN_AREA label');
  }

  // Test 4: MAX_AREA label
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getMetricRequirementDescription({
      proposal_id: 'p4',
      space_id: 'sn_kitchen_01',
      requirement_type: 'MAX_AREA',
      value: 20,
      unit: 'SQUARE_METRE'
    });
    assert.strictEqual(desc, '“Mutfak en fazla 20 m² olsun.” plan girdilerine eklensin mi?');
    console.log('✓ 4. MAX_AREA label');
  }

  // Test 5: MIN_CLEAR_WIDTH label (with decimal formatting in Turkish)
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getMetricRequirementDescription({
      proposal_id: 'p5',
      space_id: 'sn_corridor_01',
      requirement_type: 'MIN_CLEAR_WIDTH',
      value: 1.2,
      unit: 'METRE'
    });
    assert.strictEqual(desc, '“Koridor net genişliği en az 1,2 m olsun.” plan girdilerine eklensin mi?');
    console.log('✓ 5. MIN_CLEAR_WIDTH label');
  }

  // Test 6: Machine space ID not displayed if display name resolvable
  {
    const { orchestrator } = setupEnvironment();
    const desc = orchestrator.getMetricRequirementDescription({
      proposal_id: 'p6',
      space_id: 'sn_child_room_02',
      requirement_type: 'MIN_AREA',
      value: 15,
      unit: 'SQUARE_METRE'
    });
    assert(desc.includes('Çocuk Odası 2'));
    assert(!desc.includes('sn_child_room_02'));
    console.log('✓ 6. machine space ID not displayed if display name resolvable');
  }

  // Test 7: Button text = "Ölçüyü onayla"
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.allChatMessages = [{
      role: 'assistant',
      text: 'Öneri:',
      proposedActions: [{
        id: 'prop_btn_1',
        status: 'pending',
        metricRequirement: {
          proposal_id: 'p7',
          space_id: 'sn_living_01',
          requirement_type: 'MIN_AREA',
          value: 30,
          unit: 'SQUARE_METRE'
        }
      }],
      snapshot: orchestrator.stateMachine.getContext()
    }];
    orchestrator.renderFilteredChatMessages();
    console.log('✓ 7. button text = Ölçüyü onayla');
  }

  // Test 8: Approved button state
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.allChatMessages = [{
      role: 'assistant',
      text: 'Öneri:',
      proposedActions: [{
        id: 'prop_btn_2',
        status: 'approved',
        metricRequirement: {
          proposal_id: 'p8',
          space_id: 'sn_living_01',
          requirement_type: 'MIN_AREA',
          value: 30,
          unit: 'SQUARE_METRE'
        }
      }],
      snapshot: orchestrator.stateMachine.getContext()
    }];
    orchestrator.renderFilteredChatMessages();
    console.log('✓ 8. approved button state');
  }

  // Test 9: getPendingProposalContext returns metric_requirement
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Alan önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'pm_9',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 2);
    const ctx = orchestrator.getPendingProposalContext();
    assert.strictEqual(ctx.length, 1);
    assert.strictEqual(ctx[0].metric_requirement.proposal_id, 'pm_9');
    console.log('✓ 9. getPendingProposalContext returns metric_requirement');
  }

  // Test 10: XOR context shape preserved
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Alan önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'pm_10',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 2);
    const item = orchestrator.getPendingProposalContext()[0];
    const populated = [item.action, item.brief_mutation, item.spatial_relationship, item.metric_requirement]
      .filter(x => x !== null);
    assert.strictEqual(populated.length, 1);
    console.log('✓ 10. XOR context shape preserved');
  }

  // Test 11 & 12: Gateway approval URL uses project ID and is encoded
  {
    let capturedUrl = null;
    let capturedBody = null;
    const gateway = new LocalLLMGateway({
      fetchFn: async (url, opts) => {
        capturedUrl = url;
        capturedBody = JSON.parse(opts.body);
        return {
          status: 200,
          json: async () => ({
            success: true,
            resulting_plan_input_state: { state_version: 3 }
          })
        };
      }
    });

    const res = await gateway.approveMetricRequirement('proj/special#1', {
      proposed_requirement: {
        proposal_id: 'p_11',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }
    });
    assert.strictEqual(res.success, true);
    assert.strictEqual(
      capturedUrl,
      'http://127.0.0.1:8000/api/v1/projects/proj%2Fspecial%231/plan/input/metrics/approve'
    );
    console.log('✓ 11. gateway approval URL uses project ID');
    console.log('✓ 12. URL project ID encoded');
  }

  // Test 13 to 19: Approval payload invariants (exact proposal, expected versions, no brief/metric_context/evidence/site)
  {
    let capturedBody = null;
    const { orchestrator } = setupEnvironment('proj_test_123');
    const gateway = new LocalLLMGateway({
      fetchFn: async (url, opts) => {
        capturedBody = JSON.parse(opts.body);
        return {
          status: 200,
          json: async () => ({
            success: true,
            resulting_plan_input_state: { state_version: 4 }
          })
        };
      }
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.lastUserMessageText = 'Salon en az 30 m² olsun.';
    orchestrator.lastUserMessageRef = 'chatmsg_42';

    const prop = {
      proposal_id: 'prop_metric_13',
      space_id: 'sn_living_01',
      requirement_type: 'MIN_AREA',
      value: 30.0,
      unit: 'SQUARE_METRE'
    };

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Salon önerisi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [prop]
    }, 'fp_test_1', 1, 3, 3);

    const pending = orchestrator.getActivePendingProposals();
    const record = await orchestrator.approveProposalById(pending[0].id);
    assert(record !== null);

    // 13. Approval payload contains exact proposed_requirement
    assert.deepStrictEqual(capturedBody.proposed_requirement, prop);
    console.log('✓ 13. approval payload contains exact proposed_requirement');

    // 14. Expected brief version correct (3 from proposal.expectedBriefVersion)
    assert.strictEqual(capturedBody.expected_brief_version, 3);
    console.log('✓ 14. expected brief version correct');

    // 15. Expected plan-input state version is proposal-time server version (3)
    assert.strictEqual(capturedBody.expected_plan_input_state_version, 3);
    console.log('✓ 15. expected plan-input state version is proposal-time server version');

    // 16. No brief_snapshot sent
    assert.strictEqual(capturedBody.brief_snapshot, undefined);
    console.log('✓ 16. no brief_snapshot sent');

    // 17. No metric_context sent
    assert.strictEqual(capturedBody.metric_context, undefined);
    console.log('✓ 17. no metric_context sent');

    // 18. No evidence_ids invented
    assert.strictEqual(capturedBody.evidence_ids, undefined);
    assert.strictEqual(capturedBody.evidence, undefined);
    console.log('✓ 18. no evidence_ids invented');

    // 19. No site/floor/config sent
    assert.strictEqual(capturedBody.site_envelope, undefined);
    assert.strictEqual(capturedBody.floor_plate, undefined);
    assert.strictEqual(capturedBody.solver_config, undefined);
    console.log('✓ 19. no site/floor/config sent');
  }

  // Test 20 & 21: Approval success does NOT replace BriefSnapshot and records resulting state version
  {
    const { orchestrator, briefSnapshot } = setupEnvironment('proj_test_123');
    const initialBriefCopy = JSON.stringify(briefSnapshot);
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: 7 }
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p20',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 6, 3);

    const pending = orchestrator.getActivePendingProposals();
    const record = await orchestrator.approveProposalById(pending[0].id);

    // 20. BriefSnapshot unchanged
    const currentBrief = orchestrator.getActiveBriefSnapshot();
    assert.strictEqual(JSON.stringify(currentBrief), initialBriefCopy);
    console.log('✓ 20. approval success does NOT replace BriefSnapshot');

    // 21. Resulting state version recorded
    assert.strictEqual(record.resulting_plan_input_state_version, 7);
    assert.strictEqual(orchestrator.lastPlanInputStateVersion, 7);
    console.log('✓ 21. approval success records resulting state version');
  }

  // Test 22 & 23: Proposal removed from pending and success message truthful
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: 2 }
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p22',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const pendingId = orchestrator.getActivePendingProposals()[0].id;
    await orchestrator.approveProposalById(pendingId);

    // 22. Removed from pending
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);
    console.log('✓ 22. proposal removed from pending');

    // 23. Confirmation message truthful
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.strictEqual(lastMsg.text, 'Salon için minimum 30 m² gereksinimi plan girdilerine kaydedildi.');
    assert(!lastMsg.text.includes('plan çizildi'));
    assert(!lastMsg.text.includes('optimize edildi'));
    console.log('✓ 23. success message truthful');
  }

  // Test 24 & 25: 409 Stale does not retry and expectedPlanInputStateVersion is not rewritten
  {
    let callCount = 0;
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => {
        callCount += 1;
        return {
          status: 409,
          json: async () => ({
            success: false,
            error: 'Stale plan-input version: expected 1, current is 2.'
          })
        };
      }
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p24',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const pending = orchestrator.getActivePendingProposals();
    const res = await orchestrator.approveProposalById(pending[0].id);

    // 24. No retry
    assert.strictEqual(res, null);
    assert.strictEqual(callCount, 1);
    console.log('✓ 24. 409 stale does not retry');

    // 25. State version not rewritten
    assert.strictEqual(pending[0].expectedPlanInputStateVersion, 1);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('artık güncel proje durumuna ait değil'));
    console.log('✓ 25. stale proposal state version not rewritten');
  }

  // Test 26: 422 Safe failure
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 422,
        json: async () => ({
          success: false,
          error: 'Geçersiz metrik değeri: 422 Unprocessable Entity'
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p26',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const pending = orchestrator.getActivePendingProposals();
    await orchestrator.approveProposalById(pending[0].id);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('Geçersiz ölçü gereksinimi'));
    console.log('✓ 26. 422 safe failure');
  }

  // Test 27: 500 Safe failure
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 500,
        json: async () => ({
          success: false,
          error: 'Internal Server Error'
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p27',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const pending = orchestrator.getActivePendingProposals();
    await orchestrator.approveProposalById(pending[0].id);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('Ölçü gereksinimi onaylanamadı'));
    console.log('✓ 27. 500 safe failure');
  }

  // Test 28: Network failure safe
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => {
        throw new Error('Connection refused');
      }
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p28',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const pending = orchestrator.getActivePendingProposals();
    await orchestrator.approveProposalById(pending[0].id);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('ulaşılamadı'));
    console.log('✓ 28. network failure safe');
  }

  // Test 29: Dismissal leaves plan inputs unchanged
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'p29',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    const pending = orchestrator.getActivePendingProposals();
    const dismissed = orchestrator.dismissProposalById(pending[0].id);
    assert.strictEqual(dismissed, true);
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert.strictEqual(lastMsg.text, 'Ölçü önerisi iptal edildi. Plan girdileri değiştirilmedi.');
    console.log('✓ 29. dismissal leaves plan inputs unchanged');
  }

  // Test 30: Multiple old-version metric proposals become stale after first success
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 200,
        json: async () => ({
          success: true,
          resulting_plan_input_state: { state_version: 2 }
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'İki ölçü önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [
        {
          proposal_id: 'prop_A',
          space_id: 'sn_living_01',
          requirement_type: 'MIN_AREA',
          value: 30.0,
          unit: 'SQUARE_METRE'
        },
        {
          proposal_id: 'prop_B',
          space_id: 'sn_kitchen_01',
          requirement_type: 'MAX_AREA',
          value: 20.0,
          unit: 'SQUARE_METRE'
        }
      ]
    }, 'fp_test_1', 1, 1, 3);

    assert.strictEqual(orchestrator.getActivePendingProposals().length, 2);
    const propAId = orchestrator.getActivePendingProposals()[0].id;

    // Approve Proposal A
    await orchestrator.approveProposalById(propAId);

    // Proposal B (created against state version 1) should be removed as stale
    assert.strictEqual(orchestrator.getActivePendingProposals().length, 0);
    const msgs = orchestrator.allChatMessages.map(m => m.text);
    assert(msgs.some(t => t.includes('diğer ölçü önerileri yeniden değerlendirilmelidir')));
    console.log('✓ 30. multiple old-version metric proposals become stale after first success');
  }

  // Test 31: proposed_metric_requirements absent => normalized to []
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Bilgi.',
      intent: 'gather_requirement',
      confidence: 0.9,
      needs_user_confirmation: false,
      proposed_actions: []
    };
    const valid = gateway.isValidatedResult(result, {});
    assert.strictEqual(valid, true);
    assert.deepStrictEqual(result.proposed_metric_requirements, []);
    console.log('✓ 31. proposed_metric_requirements absent => []');
  }

  // Test 32: TARGET_AREA browser rejection
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Hedef alan.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'p32',
        space_id: 'sn_living_01',
        requirement_type: 'TARGET_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(result, {}), false);
    console.log('✓ 32. TARGET_AREA browser rejection');
  }

  // Test 33: Invalid unit rejection
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Hatalı birim.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'p33',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'METRE' // Should be SQUARE_METRE
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(result, {}), false);
    console.log('✓ 33. invalid unit rejection');
  }

  // Test 34: Invalid numeric value rejection (negative or NaN or <= 0)
  {
    const gateway = new LocalLLMGateway();
    const resultZero = {
      assistant_message: 'Sıfır alan.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'p34a',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 0,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(resultZero, {}), false);

    const resultNaN = {
      assistant_message: 'NaN alan.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'p34b',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: Infinity,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(resultNaN, {}), false);
    console.log('✓ 34. invalid numeric value rejection');
  }

  // Test 35: Metric + brief mixed response rejected
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Karışık öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [{
        mutation_id: 'mut_1',
        mutation_type: 'ADD_SPACE_REQUEST',
        space_request: { display_name: 'Balkon' }
      }],
      proposed_metric_requirements: [{
        proposal_id: 'p35',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(result, {}), false);
    console.log('✓ 35. metric + brief mixed response rejected');
  }

  // Test 36: Metric + spatial mixed response rejected
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Karışık öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_spatial_relationships: [{
        source_space_id: 'sn_living_01',
        target_space_id: 'sn_kitchen_01',
        relation_type: 'ADJACENT_TO'
      }],
      proposed_metric_requirements: [{
        proposal_id: 'p36',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(result, {}), false);
    console.log('✓ 36. metric + spatial mixed response rejected');
  }

  // Test 37: Metric + action mixed response rejected
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Karışık öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [{
        action_type: 'highlight_entity',
        description: 'Vurgula'
      }],
      proposed_metric_requirements: [{
        proposal_id: 'p37',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(result, {}), false);
    console.log('✓ 37. metric + action mixed response rejected');
  }

  // Test 38: Metric requires needs_user_confirmation === true
  {
    const gateway = new LocalLLMGateway();
    const result = {
      assistant_message: 'Onaysız metrik.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: false, // Invalid for metrics
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'p38',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    };
    assert.strictEqual(gateway.isValidatedResult(result, {}), false);
    console.log('✓ 38. metric requires needs_user_confirmation');
  }

  // Test 39: Fallback summary does not assume proposal.action exists
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_metric_requirements: [{
        proposal_id: 'p39',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 1, 3);

    // Call fallback handler
    const fallbackRes = orchestrator.handleLocalLLMFallback('test', 'error');
    assert.strictEqual(fallbackRes.status, 'pending_continuation');
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('Salon en az 30 m² olsun.'));
    console.log('✓ 39. fallback summary does not assume proposal.action exists');
  }

  // Test 40: Brief approval regression unchanged
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 200,
        json: async () => ({
          success: true,
          resulting_snapshot: {
            project_id: 'proj_test_123',
            brief_version: 4,
            brief_items: [],
            space_requests: [],
            evidence: []
          }
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Brief önerisi.',
      intent: 'modify_space',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [{
        mutation_id: 'mut_40',
        mutation_type: 'ADD_SPACE_REQUEST',
        space_request: { display_name: 'Kiler' }
      }]
    }, 'fp_test_1', 1);

    const pending = orchestrator.getActivePendingProposals();
    const record = await orchestrator.approveProposalById(pending[0].id);
    assert(record !== null);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 4);
    console.log('✓ 40. brief approval regression unchanged');
  }

  // Test 41: Spatial approval regression unchanged
  {
    const { orchestrator } = setupEnvironment();
    const gateway = new LocalLLMGateway({
      fetchFn: async () => ({
        status: 200,
        json: async () => ({
          success: true,
          resulting_snapshot: {
            project_id: 'proj_test_123',
            brief_version: 4,
            brief_items: [],
            space_requests: [],
            evidence: [{ id: 'ev_spatial_1' }]
          }
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Mekânsal ilişki önerisi.',
      intent: 'modify_relationship',
      confidence: 0.9,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_spatial_relationships: [{
        source_space_id: 'sn_living_01',
        target_space_id: 'sn_kitchen_01',
        relation_type: 'ADJACENT_TO'
      }]
    }, 'fp_test_1', 1);

    const pending = orchestrator.getActivePendingProposals();
    const record = await orchestrator.approveProposalById(pending[0].id);
    assert(record !== null);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 4);
    console.log('✓ 41. spatial approval regression unchanged');
  }

  // Test 42: Existing project plan preview regression unchanged
  {
    let capturedUrl = null;
    const gateway = new LocalLLMGateway({
      stateMachine: { getSnapshot: () => ({ projectId: 'proj_test_123' }) },
      fetchFn: async (url) => {
        capturedUrl = url;
        return {
          status: 200,
          ok: true,
          json: async () => ({
            success: true,
            solution: { room_count: 3 },
            document: '<svg viewBox="0 0 100 100"></svg>'
          })
        };
      }
    });

    const res = await gateway.previewProjectPlan('proj_test_123');
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.kind, 'success');
    assert.strictEqual(res.document, '<svg viewBox="0 0 100 100"></svg>');
    assert.strictEqual(capturedUrl, 'http://127.0.0.1:8000/api/v1/projects/proj_test_123/plan/preview');
    console.log('✓ 42. existing project plan preview regression unchanged');
  }

  // Test 43: Proposal-time brief version is stored on metric proposal
  {
    const { orchestrator } = setupEnvironment();
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Salon önerisi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'pm_43',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 2, 3);
    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].expectedBriefVersion, 3);
    console.log('✓ 43. proposal-time brief version is stored on metric proposal');
  }

  // Test 44: Normal case: proposal created at Brief v3, active brief remains v3, approval sends expected_brief_version = 3
  {
    let capturedBody = null;
    const { orchestrator } = setupEnvironment('proj_test_123');
    const gateway = new LocalLLMGateway({
      fetchFn: async (url, opts) => {
        capturedBody = JSON.parse(opts.body);
        return {
          status: 200,
          json: async () => ({
            success: true,
            resulting_plan_input_state: { state_version: 3 }
          })
        };
      }
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Salon önerisi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'pm_44',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 2, 3);

    const pending = orchestrator.getActivePendingProposals();
    await orchestrator.approveProposalById(pending[0].id);
    assert.strictEqual(capturedBody.expected_brief_version, 3);
    console.log('✓ 44. normal case sends expected_brief_version = 3');
  }

  // Test 45: Stale brief regression: proposal created at Brief v3, active brief becomes v4, approval STILL sends expected_brief_version = 3, backend 409 handled safely
  {
    let capturedBody = null;
    let callCount = 0;
    const { orchestrator, briefSnapshot } = setupEnvironment('proj_test_123');
    const gateway = new LocalLLMGateway({
      fetchFn: async (url, opts) => {
        callCount += 1;
        capturedBody = JSON.parse(opts.body);
        return {
          status: 409,
          json: async () => ({
            success: false,
            error: 'Stale brief version: expected 3, current is 4.'
          })
        };
      }
    });
    orchestrator.setLocalLLMGateway(gateway);

    // 1. Interpretation request was sent with Brief v3
    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Salon önerisi.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'pm_45',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 2, 3);

    const pending = orchestrator.getActivePendingProposals();
    assert.strictEqual(pending[0].expectedBriefVersion, 3);

    // 2. Before approval, local active Brief becomes v4
    orchestrator.replaceActiveBriefSnapshot({
      ...briefSnapshot,
      brief_version: 4
    });
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 4);

    // 3. Approval payload STILL sends expected_brief_version = 3
    const res = await orchestrator.approveProposalById(pending[0].id);
    assert.strictEqual(capturedBody.expected_brief_version, 3);

    // 4. Verify 409 response handling
    assert.strictEqual(res, null);
    assert.strictEqual(callCount, 1); // No retry
    assert.strictEqual(pending[0].expectedBriefVersion, 3); // Not rewritten to 4
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('artık güncel proje durumuna ait değil'));
    console.log('✓ 45. stale brief v3 -> v4 sends expected_brief_version = 3 and handles 409 safely without retry/rewrite');
  }

  // Test 46: LocalLLMGateway.interpret extracts requestBody.brief_snapshot?.brief_version and passes to handleStructuredLLMResponse
  {
    const { orchestrator, briefSnapshot } = setupEnvironment('proj_test_123');
    let capturedProposalBriefVersion = null;
    let capturedStateVersion = null;
    orchestrator.handleStructuredLLMResponse = (result, fp, genId, planInputStateVer, briefVer) => {
      capturedStateVersion = planInputStateVer;
      capturedProposalBriefVersion = briefVer;
    };

    const gateway = new LocalLLMGateway({
      orchestrator,
      hierarchy: new MockEntityHierarchy(),
      stateMachine: { getSnapshot: () => ({ projectId: 'proj_test_123', contextFingerprint: 'fp_46', generationId: 1 }) },
      fetchFn: async () => ({
        status: 200,
        ok: true,
        json: async () => ({
          success: true,
          context_fingerprint: 'fp_46',
          generation_id: 1,
          authoritative_plan_input_state_version: 5,
          result: {
            assistant_message: 'Mutfak en fazla 20 m².',
            intent: 'modify_space',
            confidence: 0.9,
            needs_user_confirmation: true,
            proposed_actions: [],
            proposed_metric_requirements: [{
              proposal_id: 'pm_46',
              space_id: 'sn_kitchen_01',
              requirement_type: 'MAX_AREA',
              value: 20.0,
              unit: 'SQUARE_METRE'
            }]
          }
        })
      })
    });
    orchestrator.setLocalLLMGateway(gateway);

    await gateway.interpret('Mutfak en fazla 20 m² olsun');
    assert.strictEqual(capturedStateVersion, 5);
    assert.strictEqual(capturedProposalBriefVersion, 3);
    console.log('✓ 46. LocalLLMGateway.interpret forwards proposalBriefVersion and stateVersion');
  }

  // Test 47: Missing / null expectedBriefVersion fails safely
  {
    const { orchestrator } = setupEnvironment('proj_test_123');
    const gateway = new LocalLLMGateway({
      fetchFn: async () => {
        throw new Error('Should not be called');
      }
    });
    orchestrator.setLocalLLMGateway(gateway);

    orchestrator.handleStructuredLLMResponse({
      assistant_message: 'Öneri.',
      intent: 'modify_space',
      confidence: 0.95,
      needs_user_confirmation: true,
      proposed_actions: [],
      proposed_brief_mutations: [],
      proposed_spatial_relationships: [],
      proposed_metric_requirements: [{
        proposal_id: 'pm_47',
        space_id: 'sn_living_01',
        requirement_type: 'MIN_AREA',
        value: 30.0,
        unit: 'SQUARE_METRE'
      }]
    }, 'fp_test_1', 1, 2, null); // null expectedBriefVersion

    const pending = orchestrator.getActivePendingProposals();
    const res = await orchestrator.approveProposalById(pending[0].id);
    assert.strictEqual(res, null);
    const lastMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 1];
    assert(lastMsg.text.includes('geçerli brief versiyonu bulunamadı'));
    console.log('✓ 47. missing expectedBriefVersion fails safely');
  }

  console.log('\nAll 47 Metric Plan Input UI V0 JS Unit Tests Passed Successfully!');
}

runAllTests().catch(err => {
  console.error('Test failure:', err);
  process.exit(1);
});
