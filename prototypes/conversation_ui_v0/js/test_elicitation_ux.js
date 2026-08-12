/**
 * Unit tests for Elicitation V1 JS Orchestrator behavior and safety invariants.
 */

const assert = require('assert');
const path = require('path');
const jsDir = __dirname;

// Mock browser globals
if (typeof window === 'undefined') {
  global.window = {};
}

class MockEntityHierarchy {
  constructor() {
    this.projects = {
      proj_house_2story: {
        id: 'proj_house_2story',
        name: 'Müstakil Ev',
        buildings: {}
      }
    };
  }
  getScopeTitle() { return 'Scope'; }
}

class MockStateMachine {
  constructor() {
    this.ctx = {
      projectId: 'proj_house_2story',
      contextFingerprint: 'house|main',
      generationId: 1
    };
    this.listeners = [];
  }
  getSnapshot() { return { ...this.ctx }; }
  getContext() { return { ...this.ctx }; }
  subscribe(fn) { this.listeners.push(fn); }
  dispatch() { return this.ctx; }
}

class MockDocumentStore {}
class MockScopeResolver {}
class MockAssistant { processUserMessage() { return { aiResponseText: 'Ok' }; } }
class MockPresenter { render() {} }

const LocalLLMGateway = require('./local_llm_gateway.js');
const ConversationOrchestrator = require('./conversation_orchestrator.js');

function createOrchestrator() {
  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine();
  const orchestrator = new ConversationOrchestrator({
    hierarchy,
    stateMachine,
    store: new MockDocumentStore(),
    resolver: new MockScopeResolver(),
    assistant: new MockAssistant(),
    presenter: new MockPresenter(),
    briefSnapshotsByProject: {}
  });
  const gateway = new LocalLLMGateway({
    stateMachine,
    hierarchy,
    orchestrator,
    fetchFn: async () => ({})
  });
  orchestrator.setLocalLLMGateway(gateway);
  return { orchestrator, gateway, stateMachine };
}

async function testMultiplePendingProposalsTextSafety() {
  const { orchestrator } = createOrchestrator();

  // Mock DOM elements for test container
  global.document = {
    createElement: () => ({
      appendChild: () => {},
      classList: { add: () => {}, remove: () => {} },
      dataset: {},
      setAttribute: () => {}
    }),
    getElementById: () => null
  };

  orchestrator.appendAssistantMessage = function(text) {
    this.lastAssistantMessage = text;
  };

  // Add 2 mock pending proposals
  orchestrator.pendingProposals.set('prop_1', {
    id: 'prop_1',
    proposal_status: 'pending',
    contextFingerprint: 'house|main',
    generationId: 1,
    briefMutation: { briefItem: { normalized_statement: '4 kişilik aile' } }
  });
  orchestrator.pendingProposals.set('prop_2', {
    id: 'prop_2',
    proposal_status: 'pending',
    contextFingerprint: 'house|main',
    generationId: 1,
    briefMutation: { briefItem: { normalized_statement: 'Tek katlı ev' } }
  });

  const res = await orchestrator.handlePendingProposalCommand('onayla');

  assert.strictEqual(
    res.status,
    'multiple_pending_requires_explicit_choice',
    'Status must be multiple_pending_requires_explicit_choice'
  );
  assert.strictEqual(
    orchestrator.pendingProposals.get('prop_1').proposal_status,
    'pending',
    'pending[0] must remain pending (untouched)'
  );
  assert.strictEqual(
    orchestrator.pendingProposals.get('prop_2').proposal_status,
    'pending',
    'pending[1] must remain pending (untouched)'
  );
  assert.strictEqual(
    orchestrator.lastAssistantMessage.includes('Birden fazla brief önerisi bekliyor'),
    true,
    'Assistant message must clarify multiple pending proposals'
  );

  console.log('✔ testMultiplePendingProposalsTextSafety passed');
}

async function testSinglePendingProposalTextApproval() {
  const { orchestrator } = createOrchestrator();
  orchestrator.appendAssistantMessage = function() {};
  orchestrator.approveProposalById = async function(id) {
    const prop = this.pendingProposals.get(id);
    if (prop) prop.proposal_status = 'approved';
    return prop;
  };

  orchestrator.pendingProposals.set('prop_1', {
    id: 'prop_1',
    proposal_status: 'pending',
    contextFingerprint: 'house|main',
    generationId: 1,
    briefMutation: { briefItem: { normalized_statement: '4 kişilik aile' } }
  });

  const res = await orchestrator.handlePendingProposalCommand('onayla');

  assert.strictEqual(res.status, 'approved', 'Status must be approved for single pending proposal');
  assert.strictEqual(
    orchestrator.pendingProposals.get('prop_1').proposal_status,
    'approved',
    'Single proposal must be approved'
  );

  console.log('✔ testSinglePendingProposalTextApproval passed');
}

async function run() {
  await testMultiplePendingProposalsTextSafety();
  await testSinglePendingProposalTextApproval();
}

run().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
