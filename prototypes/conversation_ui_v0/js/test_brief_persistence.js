/**
 * BRIF.AI — JS Unit Tests for Brief Persistence V0 & Browser Lifecycle
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

if (typeof window === 'undefined') {
  global.window = {};
}

const LocalLLMGateway = require('./local_llm_gateway.js');
const ConversationOrchestrator = require('./conversation_orchestrator.js');

const demoSnapshotsFilePath = path.join(__dirname, '../data/brief_snapshots.demo.json');
const demoSnapshots = JSON.parse(fs.readFileSync(demoSnapshotsFilePath, 'utf8'));

class MockEntityHierarchy {
  constructor() {
    this.projects = {
      proj_house_2story: { id: 'proj_house_2story', name: 'Müstakil Ev' },
      proj_tower_50floor: { id: 'proj_tower_50floor', name: 'Finans Kulesi' }
    };
  }
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
  dispatch(action) {
    if (action.type === 'PROJECT_SELECTED') {
      this.ctx.projectId = action.payload.projectId;
      this.ctx.contextFingerprint = `${action.payload.projectId}|fp`;
      this.listeners.forEach(fn => fn(this.ctx));
    }
    return this.ctx;
  }
}

class MockStore {}
class MockResolver {}
class MockAssistant {}
class MockPresenter { render() {} }

function createOrchestrator(fetchFn = null) {
  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine();
  const orchestrator = new ConversationOrchestrator({
    hierarchy,
    stateMachine,
    store: new MockStore(),
    resolver: new MockResolver(),
    assistant: new MockAssistant(),
    presenter: new MockPresenter(),
    briefSnapshotsByProject: {}
  });
  orchestrator.demoBriefSnapshotsSeed = demoSnapshots;
  const gateway = new LocalLLMGateway({
    stateMachine,
    hierarchy,
    orchestrator,
    fetchFn: fetchFn || (async () => ({}))
  });
  orchestrator.setLocalLLMGateway(gateway);
  return { orchestrator, gateway, stateMachine };
}

async function runTests() {
  console.log('Running Brief Persistence JS Unit Tests...');

  // 1. Gateway fetchProjectBrief success
  {
    const fetchFn = async (url) => {
      if (url.includes('/api/v1/projects/proj_house_2story/brief')) {
        return {
          status: 200,
          json: async () => ({ project_id: 'proj_house_2story', brief_version: 5, space_requests: [] })
        };
      }
      return { status: 404, json: async () => ({}) };
    };
    const { orchestrator } = createOrchestrator(fetchFn);
    const loaded = await orchestrator.loadProjectBrief('proj_house_2story');
    assert.strictEqual(loaded, true);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 5);
    console.log('✓ 1. Gateway fetchProjectBrief returns server snapshot');
  }

  // 2. Demo initialization fallback ONLY for 404 uninitialized demo project
  {
    let initCalled = false;
    let initPayload = null;
    const fetchFn = async (url, options) => {
      if (url.includes('/api/v1/projects/proj_house_2story/brief/initialize')) {
        initCalled = true;
        initPayload = JSON.parse(options.body);
        return {
          status: 200,
          json: async () => ({ ...initPayload, brief_version: 1 })
        };
      }
      if (url.includes('/api/v1/projects/proj_house_2story/brief')) {
        return { status: 404, json: async () => ({ detail: 'Not found' }) };
      }
      return { status: 404, json: async () => ({}) };
    };

    const { orchestrator } = createOrchestrator(fetchFn);
    const loaded = await orchestrator.loadProjectBrief('proj_house_2story');
    assert.strictEqual(loaded, true);
    assert.strictEqual(initCalled, true);
    assert.strictEqual(initPayload.project_id, 'proj_house_2story');
    console.log('✓ 2. Demo initialization fallback works ONLY for 404');
  }

  // 3. Server 500 or 409 error surfaces error state; does NOT fall back to demo seed
  {
    let initCalled = false;
    const fetchFn = async (url) => {
      if (url.includes('/api/v1/projects/proj_house_2story/brief/initialize')) {
        initCalled = true;
      }
      if (url.includes('/api/v1/projects/proj_house_2story/brief')) {
        return { status: 500, json: async () => ({ detail: 'Internal Server Error' }) };
      }
      return { status: 500, json: async () => ({}) };
    };

    const { orchestrator } = createOrchestrator(fetchFn);
    const loaded = await orchestrator.loadProjectBrief('proj_house_2story');
    assert.strictEqual(loaded, false);
    assert.strictEqual(initCalled, false);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot(), null);
    console.log('✓ 3. Server 500 error does NOT trigger demo reinitialization');
  }

  // 4. Approval request includes expected_brief_version
  {
    let sentBody = null;
    const fetchFn = async (url, options) => {
      if (url.includes('/api/v1/brief/mutations/approve')) {
        sentBody = JSON.parse(options.body);
        return {
          status: 200,
          json: async () => ({
            success: true,
            resulting_snapshot: { project_id: 'proj_house_2story', brief_version: 2 }
          })
        };
      }
      return { status: 200, json: async () => ({}) };
    };

    const { orchestrator } = createOrchestrator(fetchFn);
    orchestrator.replaceActiveBriefSnapshot({ project_id: 'proj_house_2story', brief_version: 1 });
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_exp', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'X', space_function: 'OTHER' } }]
      },
      'house|main',
      1
    );

    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    await orchestrator.approveProposalById(pendingId);

    assert.strictEqual(sentBody.expected_brief_version, 1);
    assert.strictEqual(sentBody.current_project_id, 'proj_house_2story');
    console.log('✓ 4. Approval request includes expected_brief_version');
  }

  console.log('\nAll Brief Persistence JS Unit Tests Passed Successfully!');
}

runTests().catch(err => {
  console.error('JS Test Failure:', err);
  process.exit(1);
});
