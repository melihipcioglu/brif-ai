/**
 * BRIF.AI — Node & JS Unit Test Suite for Brief Conversation Approval E2E
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock browser globals if needed
if (typeof window === 'undefined') {
  global.window = {};
}

const LocalLLMGateway = require('./local_llm_gateway.js');
const ConversationOrchestrator = require('./conversation_orchestrator.js');

// Load demo snapshot seeds from single source of truth file
const demoSnapshotsFilePath = path.join(__dirname, '../data/brief_snapshots.demo.json');
const demoSnapshots = JSON.parse(fs.readFileSync(demoSnapshotsFilePath, 'utf8'));

// Mock dependencies for testing orchestrator in node
class MockEntityHierarchy {
  constructor() {
    this.projects = {
      proj_house_2story: {
        id: 'proj_house_2story',
        name: 'Müstakil Ev',
        buildings: {
          bldg_main: {
            id: 'bldg_main',
            levels: {
              lvl_ground: {
                id: 'lvl_ground',
                zones: {
                  zone_living: {
                    id: 'zone_living',
                    spaces: {
                      space_study: { id: 'space_study', type: 'space', name: 'Çalışma Odası' }
                    }
                  }
                }
              }
            }
          }
        }
      },
      proj_tower_50floor: {
        id: 'proj_tower_50floor',
        name: 'Finans Kulesi',
        buildings: {}
      },
      proj_campus_multiblock: {
        id: 'proj_campus_multiblock',
        name: 'AR-GE Kampüsü',
        buildings: {}
      }
    };
  }
  getScopeTitle() { return 'Scope'; }
}

class MockStateMachine {
  constructor(hierarchy) {
    this.ctx = {
      projectId: 'proj_house_2story',
      buildingId: 'bldg_main',
      levelId: 'lvl_ground',
      zoneId: 'zone_living',
      entityId: 'space_study',
      contextFingerprint: 'house|main|ground|living|study',
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

class MockDocumentStore {}
class MockScopeResolver {}
class MockAssistant { processUserMessage() { return { aiResponseText: 'Ok' }; } }
class MockPresenter { render() {} }

function createOrchestrator(fetchFn = null) {
  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine(hierarchy);
  const orchestrator = new ConversationOrchestrator({
    hierarchy,
    stateMachine,
    store: new MockDocumentStore(),
    resolver: new MockScopeResolver(),
    assistant: new MockAssistant(),
    presenter: new MockPresenter(),
    briefSnapshotsByProject: demoSnapshots
  });
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
  console.log('Running Brief Conversation Approval JS Unit Tests...');

  // 17. Gateway accepts valid proposed_brief_mutations
  {
    const { gateway } = createOrchestrator();
    const validResult = {
      assistant_message: 'Mutfak talebinizi aldım.',
      intent: 'gather_requirement',
      target: { entity_id: null },
      proposed_actions: [],
      proposed_brief_mutations: [
        {
          mutation_id: 'mut_1',
          mutation_type: 'ADD_SPACE_REQUEST',
          space_request: { display_name: 'Mutfak', space_function: 'COOKING' }
        }
      ],
      needs_user_confirmation: true,
      confidence: 0.9
    };
    assert.strictEqual(gateway.isValidatedResult(validResult, { visible_entities: [] }), true);
    console.log('✓ 17. Gateway accepts valid proposed_brief_mutations');
  }

  // 18. Gateway rejects mutation type/payload mismatch
  {
    const { gateway } = createOrchestrator();
    const mismatchResult = {
      assistant_message: 'Test',
      intent: 'gather_requirement',
      proposed_actions: [],
      proposed_brief_mutations: [
        {
          mutation_id: 'mut_1',
          mutation_type: 'ADD_SPACE_REQUEST',
          brief_item: { kind: 'NEED', normalized_statement: 'X', priority: 'MUST' }
        }
      ],
      needs_user_confirmation: true,
      confidence: 0.9
    };
    assert.strictEqual(gateway.isValidatedResult(mismatchResult, { visible_entities: [] }), false);
    console.log('✓ 18. Gateway rejects mutation type/payload mismatch');
  }

  // 19. Gateway rejects multiple mutation payloads in single item
  {
    const { gateway } = createOrchestrator();
    const hybridResult = {
      assistant_message: 'Test',
      intent: 'gather_requirement',
      proposed_actions: [],
      proposed_brief_mutations: [
        {
          mutation_id: 'mut_1',
          mutation_type: 'ADD_SPACE_REQUEST',
          space_request: { display_name: 'Mutfak', space_function: 'COOKING' },
          brief_item: { kind: 'NEED', normalized_statement: 'X', priority: 'MUST' }
        }
      ],
      needs_user_confirmation: true,
      confidence: 0.9
    };
    assert.strictEqual(gateway.isValidatedResult(hybridResult, { visible_entities: [] }), false);
    console.log('✓ 19. Gateway rejects multiple mutation payloads');
  }

  // 20. Compare result with mutation is rejected
  {
    const { gateway } = createOrchestrator();
    const compareWithMutation = {
      assistant_message: 'Alternatif 1...',
      intent: 'compare_alternatives',
      proposed_actions: [],
      proposed_brief_mutations: [
        {
          mutation_id: 'mut_1',
          mutation_type: 'ADD_SPACE_REQUEST',
          space_request: { display_name: 'Mutfak', space_function: 'COOKING' }
        }
      ],
      needs_user_confirmation: true,
      confidence: 0.9
    };
    assert.strictEqual(gateway.isValidatedResult(compareWithMutation, { visible_entities: [] }), false);
    console.log('✓ 20. Compare result with mutation is rejected');
  }

  // 21. Orchestrator stores brief pending proposal separately from plan action
  {
    const { orchestrator } = createOrchestrator();
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Öneri sunuldu.',
        proposed_actions: [{ action_type: 'suggest_space_resize', description: 'Genişlet', requires_user_confirmation: true }],
        proposed_brief_mutations: [{ mutation_id: 'mut_1', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'Teras', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pending = Array.from(orchestrator.pendingProposals.values());
    assert.strictEqual(pending.length, 2);
    assert.strictEqual(pending[0].action !== null, true);
    assert.strictEqual(pending[0].briefMutation, null);
    assert.strictEqual(pending[1].action, null);
    assert.strictEqual(pending[1].briefMutation !== null, true);
    console.log('✓ 21. Orchestrator stores brief pending proposal separately from plan action');
  }

  // 22. Action-only pending proposal still works
  {
    const { orchestrator } = createOrchestrator();
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Plan önerisi.',
        proposed_actions: [{ action_type: 'suggest_space_resize', description: 'Plan düzenle', requires_user_confirmation: true }],
        proposed_brief_mutations: []
      },
      'house|main|ground|living|study',
      1
    );
    const pending = Array.from(orchestrator.pendingProposals.values());
    assert.strictEqual(pending.length, 1);
    assert.strictEqual(pending[0].action.description, 'Plan düzenle');
    console.log('✓ 22. Action-only pending proposal still works');
  }

  // 23. Brief-only PendingProposalContext serialization is correct
  {
    const { orchestrator } = createOrchestrator();
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Brief önerisi.',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_b1', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'Teras', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const ctx = orchestrator.getPendingProposalContext();
    assert.strictEqual(ctx.length, 1);
    assert.strictEqual(ctx[0].action, null);
    assert.strictEqual(ctx[0].brief_mutation.mutation_id, 'mut_b1');
    console.log('✓ 23. Brief-only PendingProposalContext serialization is correct');
  }

  // 24. Original user message/source reference retained
  {
    const { orchestrator } = createOrchestrator();
    orchestrator.lastUserMessageText = 'Bahçeli bir ev istiyorum.';
    orchestrator.lastUserMessageRef = 'chatmsg_99';

    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Bahçe eklensin mi?',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_m1', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'Bahçe', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pending = Array.from(orchestrator.pendingProposals.values())[0];
    assert.strictEqual(pending.userMessageText, 'Bahçeli bir ev istiyorum.');
    assert.strictEqual(pending.userMessageRef, 'chatmsg_99');
    console.log('✓ 24. Original user message/source reference retained');
  }

  // 25. Brief approval calls approval API and includes current_project_id
  {
    let apiCalled = false;
    let sentPayload = null;
    const fetchFn = async (url, options) => {
      if (url.includes('/api/v1/brief/mutations/approve')) {
        apiCalled = true;
        sentPayload = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            success: true,
            resulting_snapshot: {
              project_id: 'proj_house_2story',
              schema_version: 'brief.v0',
              brief_version: 2,
              space_requests: [{ display_name: 'Bahçe' }]
            },
            approval_record: { proposal_status: 'user_approved', resulting_brief_version: 2 }
          })
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const { orchestrator } = createOrchestrator(fetchFn);
    orchestrator.lastUserMessageText = 'Bahçe olsun.';
    orchestrator.lastUserMessageRef = 'chatmsg_100';

    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Bahçe ekleyelim mi?',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_app1', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'Bahçe', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    await orchestrator.approveProposalById(pendingId);

    assert.strictEqual(apiCalled, true);
    assert.strictEqual(sentPayload.current_project_id, 'proj_house_2story');
    assert.strictEqual(sentPayload.user_message, 'Bahçe olsun.');
    assert.strictEqual(sentPayload.source_reference, 'chatmsg_100');
    console.log('✓ 25. Brief approval calls approval API with current_project_id');
  }

  // 26. Successful approval replaces snapshot rather than mutating in place
  {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({
        success: true,
        resulting_snapshot: {
          project_id: 'proj_house_2story',
          schema_version: 'brief.v0',
          brief_version: 2,
          space_requests: [{ display_name: 'Balkon' }]
        }
      })
    });
    const { orchestrator } = createOrchestrator(fetchFn);
    const initialSnap = orchestrator.getActiveBriefSnapshot();
    assert.strictEqual(initialSnap.brief_version, 1);

    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Balkon?',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_repl', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'Balkon', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    await orchestrator.approveProposalById(pendingId);

    const newSnap = orchestrator.getActiveBriefSnapshot();
    assert.notStrictEqual(newSnap, initialSnap);
    assert.strictEqual(newSnap.brief_version, 2);
    assert.strictEqual(newSnap.space_requests.length, 1);
    console.log('✓ 26. Successful approval replaces snapshot');
  }

  // 27. Successful approval removes pending mutation
  {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({
        success: true,
        resulting_snapshot: { project_id: 'proj_house_2story', brief_version: 2 }
      })
    });
    const { orchestrator } = createOrchestrator(fetchFn);
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_rem', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'X', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    assert.strictEqual(orchestrator.pendingProposals.size, 1);
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    await orchestrator.approveProposalById(pendingId);
    assert.strictEqual(orchestrator.pendingProposals.size, 0);
    console.log('✓ 27. Successful approval removes pending mutation');
  }

  // 28. Successful approval marks UI state as brief-added
  {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({
        success: true,
        resulting_snapshot: { project_id: 'proj_house_2story', brief_version: 2 }
      })
    });
    const { orchestrator } = createOrchestrator(fetchFn);
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_ui', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'X', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    await orchestrator.approveProposalById(pendingId);
    const assistantMsg = orchestrator.allChatMessages[orchestrator.allChatMessages.length - 2];
    assert.strictEqual(assistantMsg.proposedActions[0].status, 'approved');
    console.log('✓ 28. Successful approval marks UI state as brief-added');
  }

  // 29. Failed approval leaves snapshot and pending proposal unchanged
  {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({
        success: false,
        error: 'Stale context'
      })
    });
    const { orchestrator } = createOrchestrator(fetchFn);
    const initialSnap = orchestrator.getActiveBriefSnapshot();

    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_fail', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'X', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    await orchestrator.approveProposalById(pendingId);

    assert.strictEqual(orchestrator.getActiveBriefSnapshot(), initialSnap);
    assert.strictEqual(orchestrator.pendingProposals.size, 1);
    console.log('✓ 29. Failed approval leaves snapshot and pending proposal unchanged');
  }

  // 30. Dismissal leaves snapshot/version unchanged
  {
    const { orchestrator } = createOrchestrator();
    const initialSnap = orchestrator.getActiveBriefSnapshot();

    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_dism', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'X', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    orchestrator.dismissProposalById(pendingId);

    assert.strictEqual(orchestrator.getActiveBriefSnapshot(), initialSnap);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 1);
    assert.strictEqual(orchestrator.pendingProposals.size, 0);
    console.log('✓ 30. Dismissal leaves snapshot/version unchanged');
  }

  // 31. Project switch selects correct project brief snapshot
  {
    const { orchestrator, stateMachine } = createOrchestrator();
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().project_id, 'proj_house_2story');

    stateMachine.dispatch({
      type: 'PROJECT_SELECTED',
      payload: { projectId: 'proj_tower_50floor' }
    });
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().project_id, 'proj_tower_50floor');
    console.log('✓ 31. Project switch selects correct project brief snapshot');
  }

  // 32. Next interpret request contains newly approved brief snapshot/version
  {
    let capturedRequestBody = null;
    const fetchFn = async (url, options) => {
      if (url.includes('/api/v1/conversation/interpret')) {
        capturedRequestBody = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            success: true,
            llm_enabled: true,
            context_fingerprint: 'house|main|ground|living|study',
            generation_id: 1,
            result: { assistant_message: 'Response', confidence: 0.9, proposed_actions: [] }
          })
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const { orchestrator, gateway } = createOrchestrator(fetchFn);
    orchestrator.replaceActiveBriefSnapshot({
      project_id: 'proj_house_2story',
      brief_version: 5,
      space_requests: [{ display_name: 'Teras' }]
    });

    await gateway.interpret('Sonraki mesaj');
    assert.strictEqual(capturedRequestBody.brief_snapshot !== undefined, true);
    assert.strictEqual(capturedRequestBody.brief_snapshot.brief_version, 5);
    console.log('✓ 32. Next interpret request contains newly approved brief snapshot/version');
  }

  // 33. Fallback/summary code works with brief-only pending proposals
  {
    const { orchestrator } = createOrchestrator();
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_sum', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'Çalışma', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    const summary = orchestrator.getConversationSummary();
    assert.strictEqual(summary.includes('Çalışma'), true);
    console.log('✓ 33. Fallback/summary code works with brief-only pending proposals');
  }

  // 34. Existing plan proposal approval tests remain green
  {
    const { orchestrator } = createOrchestrator();
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Plan eylemi.',
        proposed_actions: [{ action_type: 'suggest_space_resize', description: 'Odayı büyüt', requires_user_confirmation: true }],
        proposed_brief_mutations: []
      },
      'house|main|ground|living|study',
      1
    );
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    const record = await orchestrator.approveProposalById(pendingId);
    assert.strictEqual(record !== null, true);
    assert.strictEqual(record.proposed_action.description, 'Odayı büyüt');
    console.log('✓ 34. Existing plan proposal approval tests remain green');
  }

  // Requirement 2 Tests: Hardened browser snapshot replacement
  // 35. Active house project rejects tower snapshot replacement
  {
    const { orchestrator } = createOrchestrator();
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().project_id, 'proj_house_2story');
    const towerSnapshot = {
      project_id: 'proj_tower_50floor',
      schema_version: 'brief.v0',
      brief_version: 10
    };
    const replaced = orchestrator.replaceActiveBriefSnapshot(towerSnapshot);
    assert.strictEqual(replaced, false);
    console.log('✓ 35. Active house project rejects tower snapshot replacement');
  }

  // 36. House snapshot remains unchanged after rejection
  {
    const { orchestrator } = createOrchestrator();
    const initialHouseSnap = orchestrator.getActiveBriefSnapshot();
    const towerSnapshot = { project_id: 'proj_tower_50floor', brief_version: 10 };
    orchestrator.replaceActiveBriefSnapshot(towerSnapshot);
    const currentHouseSnap = orchestrator.getActiveBriefSnapshot();
    assert.strictEqual(currentHouseSnap.brief_version, initialHouseSnap.brief_version);
    console.log('✓ 36. House snapshot remains unchanged after rejection');
  }

  // 37. Tower stored snapshot remains unchanged after rejection
  {
    const { orchestrator, stateMachine } = createOrchestrator();
    const towerSnapshot = { project_id: 'proj_tower_50floor', brief_version: 99 };
    orchestrator.replaceActiveBriefSnapshot(towerSnapshot);

    stateMachine.dispatch({
      type: 'PROJECT_SELECTED',
      payload: { projectId: 'proj_tower_50floor' }
    });
    const activeTowerSnap = orchestrator.getActiveBriefSnapshot();
    assert.strictEqual(activeTowerSnap.brief_version, 1);
    console.log('✓ 37. Tower stored snapshot remains unchanged after rejection');
  }

  // 38. Valid same-project replacement succeeds
  {
    const { orchestrator } = createOrchestrator();
    const validHouseUpdate = {
      project_id: 'proj_house_2story',
      schema_version: 'brief.v0',
      brief_version: 3,
      space_requests: [{ display_name: 'Veranda' }]
    };
    const replaced = orchestrator.replaceActiveBriefSnapshot(validHouseUpdate);
    assert.strictEqual(replaced, true);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().brief_version, 3);
    console.log('✓ 38. Valid same-project replacement succeeds');
  }

  // 39. Successful brief approval with a wrong-project API result is treated as failure and does not remove pending proposal
  {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({
        success: true,
        resulting_snapshot: {
          project_id: 'proj_tower_50floor', // Mismatched project returned from API!
          brief_version: 2
        }
      })
    });
    const { orchestrator } = createOrchestrator(fetchFn);
    orchestrator.handleStructuredLLMResponse(
      {
        assistant_message: 'Test',
        proposed_actions: [],
        proposed_brief_mutations: [{ mutation_id: 'mut_wrong_res', mutation_type: 'ADD_SPACE_REQUEST', space_request: { display_name: 'X', space_function: 'OTHER' } }]
      },
      'house|main|ground|living|study',
      1
    );
    assert.strictEqual(orchestrator.pendingProposals.size, 1);
    const pendingId = Array.from(orchestrator.pendingProposals.keys())[0];
    const record = await orchestrator.approveProposalById(pendingId);

    assert.strictEqual(record, null);
    assert.strictEqual(orchestrator.pendingProposals.size, 1);
    assert.strictEqual(orchestrator.getActiveBriefSnapshot().project_id, 'proj_house_2story');
    console.log('✓ 39. Approval with wrong-project API result is treated as failure');
  }

  console.log('\nAll 23 JS Unit Tests Passed Successfully!');
}

runTests().catch(err => {
  console.error('JS Test Failure:', err);
  process.exit(1);
});
