/**
 * BRIF.AI — JS Unit Test Suite for Spatial Relationship Proposal Rendering & Approval
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
      proj_villa: {
        id: 'proj_villa',
        name: 'Villa',
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

function runTests() {
  console.log('Running Spatial Relationship JS Unit Tests...');

  const activeSnapshot = {
    projectId: 'proj_villa',
    buildingId: 'bldg_main',
    levelId: 'lvl_1',
    contextFingerprint: 'fp_villa_1',
    generationId: 1
  };

  const briefSnapshot = {
    project_id: 'proj_villa',
    brief_version: 1,
    brief_items: [],
    space_requests: [
      { id: 'sr_child_room', display_name: 'Çocuk Odası', minimum_quantity: 2 },
      { id: 'sr_living', display_name: 'Salon', minimum_quantity: 1 }
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
    briefSnapshotsByProject: { proj_villa: briefSnapshot }
  });

  // 1. Description formatting test
  const spatialRel = {
    source_space_id: 'sn_child_room_01',
    target_space_id: 'sn_child_room_02',
    relation_type: 'NEAR',
    provenance: 'USER_STATED',
    requires_user_confirmation: true
  };

  const desc = orchestrator.getSpatialRelationshipDescription(spatialRel);
  assert(typeof desc === 'string', 'Description must be a string');
  assert(!desc.includes('[object Object]'), 'Description must not contain [object Object]');
  assert(desc.includes('Çocuk Odası 1 ile Çocuk Odası 2 birbirine yakın olmalı.'), `Unexpected description: ${desc}`);
  console.log('✓ 1. getSpatialRelationshipDescription formats readable Turkish without [object Object]');

  // 2. Gateway isValidResponse test
  const gateway = new LocalLLMGateway({
    stateMachine,
    hierarchy,
    orchestrator,
    fetchFn: async () => ({})
  });
  orchestrator.localLLMGateway = gateway;

  const validResult = {
    assistant_message: 'Çocuk odaları birbirine yakın planlanacak.',
    intent: 'gather_requirement',
    confidence: 0.9,
    needs_user_confirmation: true,
    needs_follow_up: false,
    proposed_actions: [],
    proposed_brief_mutations: [],
    proposed_spatial_relationships: [spatialRel]
  };

  assert(gateway.isValidatedResult(validResult, {}), 'Gateway should accept valid spatial proposal');
  console.log('✓ 2. Gateway accepts valid proposed_spatial_relationships');

  // 3. Orchestrator proposal handling
  orchestrator.handleStructuredLLMResponse(
    validResult,
    activeSnapshot.contextFingerprint,
    activeSnapshot.generationId
  );

  const pending = orchestrator.getActivePendingProposals(activeSnapshot);
  assert.strictEqual(pending.length, 1, 'Should have 1 pending spatial proposal');
  assert(pending[0].spatialRelationship !== null, 'Proposal should contain spatialRelationship');
  assert.strictEqual(pending[0].spatialRelationship.relation_type, 'NEAR');
  console.log('✓ 3. Orchestrator stores spatial proposal separately');

  // 4. Pending context serialization
  const contextList = orchestrator.getPendingProposalContext(activeSnapshot);
  assert.strictEqual(contextList.length, 1);
  assert(contextList[0].spatial_relationship !== null);
  assert.strictEqual(contextList[0].action, null);
  assert.strictEqual(contextList[0].brief_mutation, null);
  console.log('✓ 4. getPendingProposalContext serializes spatial_relationship with 3-way XOR');

  // 5. Conversation summary formatting
  const summary = orchestrator.getConversationSummary();
  assert(!summary.includes('[object Object]'), 'Summary must not contain [object Object]');
  assert(summary.includes('Çocuk Odası 1 ile Çocuk Odası 2 birbirine yakın olmalı.'), 'Summary should contain spatial description');
  console.log('✓ 5. getConversationSummary formats spatial proposal without [object Object]');

  console.log('\nAll 5 Spatial Relationship JS Unit Tests Passed Successfully!');
}

runTests();
