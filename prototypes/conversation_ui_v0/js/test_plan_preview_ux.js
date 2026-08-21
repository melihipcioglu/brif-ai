/**
 * BRIF.AI — Plan Preview UI Project Endpoint Integration V1 JS Unit Test Suite
 *
 * Tests:
 * 1. Gateway sends POST /api/v1/projects/{projectId}/plan/preview
 * 2. Gateway request has NO body (opts.body === undefined)
 * 3. Gateway project ID is URL encoded
 * 4. HTTP 200 PlanPreviewResponse success is normalized correctly
 * 5. 409 ProjectPlanPreviewReadinessResult => kind === 'not_ready'
 * 6. Project-level blocker messages extracted correctly
 * 7. Preparation-level blocker messages extracted correctly
 * 8. related_ids and tracebacks are never surfaced as user-facing blocker text
 * 9. 409 PlanPreviewResponse failure => kind === 'execution_error' (not 'not_ready')
 * 10. 422 execution error safe mapping
 * 11. 503 execution error safe mapping
 * 12. 500 execution and readiness error safe mapping
 * 13. Timeout handling and mapping
 * 14. Network failure handling and mapping
 * 15. Cancellation handling and mapping
 * 16. Orchestrator obtains current stateMachine projectId
 * 17. Orchestrator calls previewProjectPlan(projectId)
 * 18. Orchestrator does NOT call legacy previewPlan(requestPayload)
 * 19. Orchestrator does NOT fetch plan_preview_request.demo.json
 * 20. Loading state rendered in UI
 * 21. Success SVG rendered in UI
 * 22. Success chat message contains no "Demo önizleme" and uses truthful statement
 * 23. not_ready response renders distinct blocked state in UI
 * 24. Canonical blocker messages shown in blocked state
 * 25. related_ids and raw traceback not shown in blocked UI
 * 26. server_error renders safe generic message in UI
 * 27. Repeated preview does not duplicate containers
 * 28a. Gateway stale response protection directly tested (switching project A -> B)
 * 28b. Gateway stale response protection when active project becomes null/empty
 * 28c. Orchestrator stale context protection: old SVG is not rendered and loading state is cleared
 * 29. app.js button wiring connects to requestProjectPlanPreview
 * 30. Legacy gateway previewPlan remains backward-compatible
 * 31. Invalid/non-SVG document rejected by sanitization
 * 32. Script-containing SVG, foreignObject, and event handlers rejected
 * 33. No LLM interpret call occurs
 * 34. No brief or spatial mutation occurs
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock browser globals if in Node
if (typeof window === 'undefined') {
  global.window = {};
}

// Minimal DOM implementation for Node.js test environment
class MockDOMNode {
  constructor(name = 'div', isElement = true) {
    this.localName = name.toLowerCase();
    this.tagName = name.toUpperCase();
    this.nodeName = name;
    this.isElement = isElement;
    this.children = [];
    this.childNodes = [];
    this.attributes = {};
    this.dataset = {};
    this.classList = new Set();
    this._textContent = undefined;
    this.innerHTML = '';
    this.parentElement = null;
    this.disabled = false;
  }

  get textContent() {
    if (this._textContent !== undefined) return this._textContent;
    if (this.children.length === 0) return '';
    return this.children.map(c => c.textContent).join(' ');
  }

  set textContent(val) {
    this._textContent = val;
  }

  set className(val) {
    this._className = val;
    this.classList = new Set(val ? String(val).split(/\s+/).filter(Boolean) : []);
  }

  get className() {
    return this._className || '';
  }

  getAttribute(key) {
    return this.attributes[key] !== undefined ? this.attributes[key] : null;
  }

  setAttribute(key, val) {
    this.attributes[key] = String(val);
  }

  removeAttribute(key) {
    delete this.attributes[key];
  }

  appendChild(child) {
    if (child) {
      child.parentElement = this;
      this.children.push(child);
      this.childNodes.push(child);
    }
    return child;
  }

  append(...children) {
    for (const child of children) {
      if (child) {
        if (typeof child === 'string') {
          const textNode = new MockDOMNode('#text', false);
          textNode.textContent = child;
          this.appendChild(textNode);
        } else {
          this.appendChild(child);
        }
      }
    }
  }

  replaceChildren(...nodes) {
    this.children = [];
    this.childNodes = [];
    for (const node of nodes) {
      if (node) this.appendChild(node);
    }
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  querySelectorAll(selector) {
    const results = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (matchesSelector(child, selector)) {
          results.push(child);
        }
        walk(child);
      }
    };
    walk(this);
    return results;
  }

  getElementsByTagName(tagName) {
    const target = tagName.toLowerCase();
    const results = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (target === '*' || child.localName === target) {
          results.push(child);
        }
        walk(child);
      }
    };
    walk(this);
    return results;
  }

  cloneNode(deep = true) {
    const clone = new MockDOMNode(this.localName, this.isElement);
    clone.attributes = { ...this.attributes };
    clone.textContent = this.textContent;
    clone.innerHTML = this.innerHTML;
    clone.classList = new Set(this.classList);
    clone.dataset = { ...this.dataset };
    if (deep) {
      for (const child of this.children) {
        clone.appendChild(child.cloneNode(true));
      }
    }
    return clone;
  }
}

function matchesSelector(node, selector) {
  if (selector.startsWith('#')) {
    return node.getAttribute('id') === selector.slice(1);
  }
  if (selector.startsWith('.')) {
    return node.classList.has(selector.slice(1));
  }
  if (selector === node.localName) {
    return true;
  }
  return false;
}

class SimpleXMLDoc {
  constructor(root) {
    this.documentElement = root;
  }
  getElementsByTagName(tag) {
    if (!this.documentElement) return [];
    const list = this.documentElement.getElementsByTagName(tag);
    if (tag.toLowerCase() === '*' || tag.toLowerCase() === this.documentElement.localName) {
      return [this.documentElement, ...list];
    }
    return list;
  }
  querySelector(sel) {
    if (!this.documentElement) return null;
    if (matchesSelector(this.documentElement, sel)) return this.documentElement;
    return this.documentElement.querySelector(sel);
  }
}

class MockDOMParser {
  parseFromString(str, _mimeType) {
    if (typeof str !== 'string' || !str.trim()) {
      const errNode = new MockDOMNode('parsererror');
      errNode.textContent = 'Empty or invalid XML';
      return new SimpleXMLDoc(errNode);
    }
    const trimmed = str.trim();
    if (!trimmed.startsWith('<') || !trimmed.endsWith('>')) {
      const errNode = new MockDOMNode('parsererror');
      errNode.textContent = 'Not well-formed XML';
      return new SimpleXMLDoc(errNode);
    }

    if (trimmed.includes('<parsererror')) {
      const errNode = new MockDOMNode('parsererror');
      return new SimpleXMLDoc(errNode);
    }

    const openTagMatch = trimmed.match(/^<([a-zA-Z0-9_:-]+)([^>]*)>/);
    if (!openTagMatch) {
      const errNode = new MockDOMNode('parsererror');
      return new SimpleXMLDoc(errNode);
    }
    const rootName = openTagMatch[1];
    const rootAttrs = openTagMatch[2];
    const root = new MockDOMNode(rootName);
    root.innerHTML = trimmed;
    root.textContent = trimmed.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

    const attrRegex = /([a-zA-Z0-9_:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
    let m;
    while ((m = attrRegex.exec(rootAttrs)) !== null) {
      root.setAttribute(m[1], m[2] !== undefined ? m[2] : m[3]);
    }

    const tagRegex = /<([a-zA-Z0-9_:-]+)([^>]*?)(?:\/>|>([\s\S]*?)<\/\1>)/g;
    const innerContent = trimmed.slice(openTagMatch[0].length, trimmed.lastIndexOf('</'));
    let childMatch;
    while ((childMatch = tagRegex.exec(innerContent)) !== null) {
      const cName = childMatch[1];
      const cAttrs = childMatch[2];
      const cBody = childMatch[3] || '';
      const cNode = new MockDOMNode(cName);
      cNode.textContent = cBody.replace(/<[^>]+>/g, ' ').trim();
      let am;
      while ((am = attrRegex.exec(cAttrs)) !== null) {
        cNode.setAttribute(am[1], am[2] !== undefined ? am[2] : am[3]);
      }
      root.appendChild(cNode);
    }

    return new SimpleXMLDoc(root);
  }
}

global.DOMParser = MockDOMParser;
global.document = {
  createElement: (tag) => new MockDOMNode(tag),
  getElementById: (id) => {
    if (!global.document._registry) global.document._registry = new Map();
    if (!global.document._registry.has(id)) {
      const el = new MockDOMNode('div');
      el.setAttribute('id', id);
      global.document._registry.set(id, el);
    }
    return global.document._registry.get(id);
  },
  importNode: (node, deep) => node.cloneNode(deep)
};

const LocalLLMGateway = require('./local_llm_gateway.js');
const ConversationOrchestrator = require('./conversation_orchestrator.js');

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
  constructor(initialProjectId = 'proj_house_2story') {
    this.ctx = {
      projectId: initialProjectId,
      buildingId: 'bldg_main',
      levelId: 'lvl_ground',
      zoneId: 'zone_living',
      entityId: 'space_study',
      contextFingerprint: 'fp_test',
      generationId: 1
    };
    this.listeners = [];
  }
  getSnapshot() { return { ...this.ctx }; }
  getContext() { return { ...this.ctx }; }
  subscribe(fn) { this.listeners.push(fn); }
  dispatch(_action) { return this.ctx; }
  setProjectId(newId) { this.ctx.projectId = newId; }
}

function createTestHarness(customFetch = null, initialProjectId = 'proj_house_2story') {
  if (global.document && global.document._registry) {
    global.document._registry.clear();
  }
  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine(initialProjectId);
  const orchestrator = new ConversationOrchestrator({
    hierarchy,
    stateMachine,
    store: {},
    resolver: {},
    assistant: { processUserMessage: () => ({ aiResponseText: 'ok' }) },
    presenter: { render: () => {} }
  });
  const gateway = new LocalLLMGateway({
    stateMachine,
    hierarchy,
    orchestrator,
    fetchFn: customFetch || (async () => ({}))
  });
  orchestrator.setLocalLLMGateway(gateway);
  return { orchestrator, gateway, stateMachine, hierarchy };
}

const mockSuccessSolution = {
  schema_version: 'room_geometry_solution.v0',
  status: 'FEASIBLE',
  grid_step_m: 0.1,
  rooms: [
    { space_id: 'sn_living_01', display_name: 'Living Room', x_m: 4.0, y_m: 4.0, width_m: 5.0, depth_m: 4.0, area_m2: 20.0 },
    { space_id: 'sn_kitchen_01', display_name: 'Kitchen', x_m: 4.0, y_m: 8.0, width_m: 2.5, depth_m: 4.0, area_m2: 10.0 }
  ]
};

const mockSuccessSvgDocument = {
  schema_version: 'svg_plan_document.v0',
  width_px: 560.0,
  height_px: 560.0,
  svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 560"><g class="rooms"><rect x="40" y="40" width="50" height="40"/><text>Living Room</text><rect x="40" y="80" width="25" height="40"/><text>Kitchen</text></g></svg>'
};

async function runTests() {
  console.log('Running Plan Preview UI Project Endpoint Integration V1 JS Unit Tests...\n');

  // Test 1: Gateway sends POST /api/v1/projects/{projectId}/plan/preview
  {
    let requestedUrl = null;
    let requestedMethod = null;
    const { gateway } = createTestHarness(async (url, opts) => {
      requestedUrl = url;
      requestedMethod = opts.method;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    });

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(
      requestedUrl,
      'http://127.0.0.1:8000/api/v1/projects/proj_house_2story/plan/preview',
      'Must call /api/v1/projects/{projectId}/plan/preview'
    );
    assert.strictEqual(requestedMethod, 'POST', 'Must use POST method');
    assert.strictEqual(res.ok, true);
    console.log('✓ 1. gateway sends POST /api/v1/projects/{projectId}/plan/preview');
  }

  // Test 2: Request has NO body (opts.body === undefined)
  {
    let receivedBody = null;
    let receivedOptions = null;
    const { gateway } = createTestHarness(async (_url, opts) => {
      receivedOptions = opts;
      receivedBody = opts.body;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    });

    await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(receivedBody, undefined, 'Must NOT send a request body');
    assert.strictEqual(receivedOptions.body, undefined, 'opts.body must be strictly undefined');
    console.log('✓ 2. request has NO body (opts.body === undefined)');
  }

  // Test 3: Project ID is URL encoded
  {
    let requestedUrl = null;
    const { gateway } = createTestHarness(async (url) => {
      requestedUrl = url;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    }, 'proj/special name&1');

    await gateway.previewProjectPlan('proj/special name&1');
    assert.strictEqual(
      requestedUrl,
      'http://127.0.0.1:8000/api/v1/projects/proj%2Fspecial%20name%261/plan/preview',
      'Project ID must be properly encoded with encodeURIComponent'
    );
    console.log('✓ 3. project ID is URL encoded');
  }

  // Test 4: HTTP 200 PlanPreviewResponse success is normalized correctly
  {
    const { gateway } = createTestHarness(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        solution: mockSuccessSolution,
        document: mockSuccessSvgDocument
      })
    }));

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.kind, 'success');
    assert.strictEqual(res.projectId, 'proj_house_2story');
    assert.deepStrictEqual(res.solution, mockSuccessSolution);
    assert.deepStrictEqual(res.document, mockSuccessSvgDocument);
    console.log('✓ 4. HTTP 200 PlanPreviewResponse success is normalized correctly');
  }

  // Test 5: 409 ProjectPlanPreviewReadinessResult => kind === 'not_ready'
  {
    const readinessPayload = {
      schema_version: 'project_plan_preview_readiness.v0',
      project_id: 'proj_house_2story',
      ready_for_preview: false,
      project_blockers: [
        {
          code: 'BRIEF_NOT_READY',
          message: "Brief hazır değil veya eksik onaylanmamış gereksinimler var.",
          related_ids: ['req_01', 'req_02']
        }
      ],
      preparation: {
        schema_version: 'plan_preview_readiness.v0',
        ready: false,
        blockers: [
          {
            code: 'METRIC_REQUIREMENTS_MISSING',
            message: 'Metrik mekânsal gereksinimler eksik.',
            related_ids: ['sn_living_01']
          }
        ],
        request: null
      }
    };

    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 409,
      json: async () => readinessPayload
    }));

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 409);
    assert.strictEqual(res.kind, 'not_ready');
    assert.strictEqual(res.projectId, 'proj_house_2story');
    assert.deepStrictEqual(res.readiness, readinessPayload);
    console.log('✓ 5. 409 ProjectPlanPreviewReadinessResult => kind === "not_ready"');
  }

  // Test 6: Project-level blocker messages extracted correctly
  {
    const readinessPayload = {
      schema_version: 'project_plan_preview_readiness.v0',
      project_id: 'proj_01',
      ready_for_preview: false,
      project_blockers: [
        { code: 'BRIEF_MISSING', message: 'Proje için Brief bulunamadı.', related_ids: [] },
        { code: 'SPATIAL_GRAPH_STALE', message: 'Mekânsal ilişki grafı güncel değil.', related_ids: [] }
      ],
      preparation: null
    };

    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 409,
      json: async () => readinessPayload
    }), 'proj_01');

    const res = await gateway.previewProjectPlan('proj_01');
    assert.deepStrictEqual(res.blockers, [
      'Proje için Brief bulunamadı.',
      'Mekânsal ilişki grafı güncel değil.'
    ]);
    console.log('✓ 6. project-level blocker messages extracted correctly');
  }

  // Test 7: Preparation-level blocker messages extracted correctly
  {
    const readinessPayload = {
      schema_version: 'project_plan_preview_readiness.v0',
      project_id: 'proj_01',
      ready_for_preview: false,
      project_blockers: [],
      preparation: {
        schema_version: 'plan_preview_readiness.v0',
        ready: false,
        blockers: [
          { code: 'SITE_ENVELOPE_MISSING', message: 'Arsa yapılaşma zarfı tanımlı değil.', related_ids: [] },
          { code: 'FLOOR_PLATE_INPUT_MISSING', message: 'Taban oturumu girdisi eksik.', related_ids: [] }
        ],
        request: null
      }
    };

    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 409,
      json: async () => readinessPayload
    }), 'proj_01');

    const res = await gateway.previewProjectPlan('proj_01');
    assert.deepStrictEqual(res.blockers, [
      'Arsa yapılaşma zarfı tanımlı değil.',
      'Taban oturumu girdisi eksik.'
    ]);
    console.log('✓ 7. preparation-level blocker messages extracted correctly');
  }

  // Test 8: related_ids and tracebacks are never surfaced as user-facing blocker text
  {
    const readinessPayload = {
      schema_version: 'project_plan_preview_readiness.v0',
      project_id: 'proj_01',
      ready_for_preview: false,
      project_blockers: [
        { code: 'BRIEF_NOT_READY', message: 'Brief tamamlanmadı.', related_ids: ['internal_technical_secret_id_99'] }
      ],
      preparation: {
        schema_version: 'plan_preview_readiness.v0',
        ready: false,
        blockers: [
          { code: 'SOLVER_INPUT_INVALID', message: 'Mekân boyutları uyumsuz.', related_ids: ['secret_solver_node_42'] }
        ],
        request: null
      }
    };

    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 409,
      json: async () => readinessPayload
    }), 'proj_01');

    const res = await gateway.previewProjectPlan('proj_01');
    const allBlockerText = res.blockers.join(' ');
    assert(!allBlockerText.includes('internal_technical_secret_id_99'), 'Must not contain related_ids');
    assert(!allBlockerText.includes('secret_solver_node_42'), 'Must not contain related_ids');
    assert(!allBlockerText.includes('SOLVER_INPUT_INVALID'), 'Must not contain code enum as raw message');
    console.log('✓ 8. related_ids and tracebacks are never surfaced as user-facing blocker text');
  }

  // Test 9: 409 PlanPreviewResponse failure => kind === 'execution_error' (not 'not_ready')
  {
    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 409,
      json: async () => ({
        success: false,
        solution: null,
        document: null,
        error: 'RoomGeometryInputMismatchError: Room ids do not match floor plate'
      })
    }));

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 409);
    assert.strictEqual(res.kind, 'execution_error');
    assert.strictEqual(res.error, 'Plan girdileri birbiriyle uyuşmuyor.');
    console.log('✓ 9. 409 PlanPreviewResponse failure => kind === "execution_error" (not "not_ready")');
  }

  // Test 10: 422 execution error safe mapping
  {
    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 422,
      json: async () => ({
        success: false,
        solution: null,
        document: null,
        error: 'RoomGeometryInfeasibleError: Cannot place rooms in floor plate'
      })
    }));

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 422);
    assert.strictEqual(res.kind, 'execution_error');
    assert.strictEqual(res.error, 'Plan girdileri bu sürümde çözülemiyor.');
    console.log('✓ 10. 422 execution error safe mapping');
  }

  // Test 11: 503 execution error safe mapping
  {
    const { gateway } = createTestHarness(async () => ({
      ok: false,
      status: 503,
      json: async () => ({
        success: false,
        solution: null,
        document: null,
        error: 'RoomGeometryEngineError: Solver timeout'
      })
    }));

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 503);
    assert.strictEqual(res.kind, 'execution_error');
    assert.strictEqual(res.error, 'Plan çözücü şu anda sonuç üretemedi.');
    console.log('✓ 11. 503 execution error safe mapping');
  }

  // Test 12: 500 execution and readiness error safe mapping
  {
    // 12a. 500 execution error (PlanPreviewResponse)
    const { gateway: execGateway } = createTestHarness(async () => ({
      ok: false,
      status: 500,
      json: async () => ({
        success: false,
        solution: null,
        document: null,
        error: 'SvgPlanRenderError: SVG viewBox calculation failed'
      })
    }));
    const execRes = await execGateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(execRes.ok, false);
    assert.strictEqual(execRes.status, 500);
    assert.strictEqual(execRes.kind, 'execution_error');
    assert.strictEqual(execRes.error, 'Plan önizlemesi oluşturulamadı.');

    // 12b. 500 server error (detail)
    const { gateway: srvGateway } = createTestHarness(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Kalıcı depolama hatası: Disk error' })
    }));
    const srvRes = await srvGateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(srvRes.ok, false);
    assert.strictEqual(srvRes.status, 500);
    assert.strictEqual(srvRes.kind, 'server_error');
    assert.strictEqual(srvRes.error, 'Plan önizlemesi oluşturulamadı.');
    console.log('✓ 12. 500 execution and readiness error safe mapping');
  }

  // Test 13: Timeout handling and mapping
  {
    const { gateway } = createTestHarness(async () => {
      const err = new Error('The operation was aborted');
      err.name = 'AbortError';
      throw err;
    });

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 0);
    assert.strictEqual(res.kind, 'timeout');
    assert.strictEqual(res.error, 'Plan isteği zaman aşımına uğradı.');
    console.log('✓ 13. timeout handling and mapping');
  }

  // Test 14: Network failure handling and mapping
  {
    const { gateway } = createTestHarness(async () => {
      throw new Error('Failed to fetch');
    });

    const res = await gateway.previewProjectPlan('proj_house_2story');
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 0);
    assert.strictEqual(res.kind, 'network_error');
    assert.strictEqual(res.error, 'Plan servisine ulaşılamadı.');
    console.log('✓ 14. network failure handling and mapping');
  }

  // Test 15: Cancellation handling and mapping
  {
    const controller = new AbortController();
    controller.abort();

    const { gateway } = createTestHarness(async () => ({}));
    const res = await gateway.previewProjectPlan('proj_house_2story', { signal: controller.signal });
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.status, 0);
    assert.strictEqual(res.kind, 'canceled');
    assert.strictEqual(res.error, 'Plan isteği iptal edildi.');
    console.log('✓ 15. cancellation handling and mapping');
  }

  // Test 16: Orchestrator obtains current stateMachine projectId
  {
    let calledWithProjectId = null;
    const { orchestrator } = createTestHarness(null, 'proj_custom_villa');
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => {
      calledWithProjectId = pid;
      return { ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument };
    };

    await orchestrator.requestProjectPlanPreview();
    assert.strictEqual(calledWithProjectId, 'proj_custom_villa', 'Must obtain active projectId from stateMachine');
    console.log('✓ 16. orchestrator obtains current stateMachine projectId');
  }

  // Test 17: Orchestrator calls previewProjectPlan(projectId)
  {
    let methodCalled = false;
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => {
      methodCalled = true;
      assert.strictEqual(pid, 'proj_house_2story');
      return { ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument };
    };

    await orchestrator.requestProjectPlanPreview();
    assert.strictEqual(methodCalled, true, 'previewProjectPlan must be called');
    console.log('✓ 17. orchestrator calls previewProjectPlan(projectId)');
  }

  // Test 18: Orchestrator does NOT call legacy previewPlan(requestPayload)
  {
    let legacyCalled = false;
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewPlan = async () => {
      legacyCalled = true;
      return { ok: false };
    };
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument
    });

    await orchestrator.requestProjectPlanPreview();
    assert.strictEqual(legacyCalled, false, 'Legacy previewPlan must NEVER be called by active flow');
    console.log('✓ 18. orchestrator does NOT call legacy previewPlan(requestPayload)');
  }

  // Test 19: Orchestrator does NOT fetch plan_preview_request.demo.json
  {
    const fetchedUrls = [];
    const { orchestrator } = createTestHarness(async (url) => {
      fetchedUrls.push(url);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    });

    await orchestrator.requestProjectPlanPreview();
    for (const url of fetchedUrls) {
      assert(!url.includes('plan_preview_request.demo.json'), 'Must never fetch demo JSON fixture');
    }
    console.log('✓ 19. orchestrator does NOT fetch plan_preview_request.demo.json');
  }

  // Test 20: Loading state rendered in UI
  {
    let loadingStateObserved = false;
    const { orchestrator } = createTestHarness();
    const contentEl = global.document.getElementById('planPreviewContent');

    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => {
      const spinner = contentEl.querySelector('.plan-preview-loading');
      if (spinner || contentEl.textContent.includes('hesaplanıyor')) {
        loadingStateObserved = true;
      }
      return { ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument };
    };

    await orchestrator.requestProjectPlanPreview();
    assert.strictEqual(loadingStateObserved, true, 'Loading state must be rendered during active request');
    console.log('✓ 20. loading state rendered in UI');
  }

  // Test 21: Success SVG rendered in UI
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument
    });

    await orchestrator.requestProjectPlanPreview();
    const contentEl = global.document.getElementById('planPreviewContent');
    const svgEl = contentEl.querySelector('svg');
    assert(svgEl, 'Must render SVG element in DOM');
    assert.strictEqual(svgEl.localName, 'svg', 'Root node must be SVG');
    console.log('✓ 21. success SVG rendered in UI');
  }

  // Test 22: Success chat message contains no "Demo önizleme" and uses truthful statement
  {
    let appendedMessage = null;
    const { orchestrator } = createTestHarness();
    orchestrator.appendAssistantMessage = (msg) => {
      appendedMessage = msg;
    };
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument
    });

    await orchestrator.requestProjectPlanPreview();
    assert(appendedMessage, 'Assistant message must be appended on success');
    assert(!appendedMessage.includes('Demo önizleme'), 'Must not contain "Demo önizleme" disclaimer');
    assert(
      appendedMessage.includes('sunucuda doğrulanmış proje girdileri'),
      'Must truthfully state verified project inputs were used'
    );
    console.log('✓ 22. success chat message contains no "Demo önizleme" and uses truthful statement');
  }

  // Test 23: not_ready response renders distinct blocked state in UI
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: false,
      status: 409,
      kind: 'not_ready',
      projectId: pid,
      blockers: ['Taban oturumu girdisi eksik.', 'Arsa yapılaşma zarfı tanımlı değil.']
    });

    await orchestrator.requestProjectPlanPreview();
    const contentEl = global.document.getElementById('planPreviewContent');
    const blockedBox = contentEl.querySelector('.plan-preview-blocked');
    assert(blockedBox, 'Must render distinct .plan-preview-blocked container');
    assert(!contentEl.querySelector('.plan-preview-error'), 'Must NOT render generic error container for not_ready');
    const heading = blockedBox.querySelector('.blocked-title');
    assert.strictEqual(heading?.textContent, 'Taslak plan henüz oluşturulamıyor');
    console.log('✓ 23. not_ready response renders distinct blocked state in UI');
  }

  // Test 24: Canonical blocker messages shown in blocked state
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: false,
      status: 409,
      kind: 'not_ready',
      projectId: pid,
      blockers: [
        'Metrik mekânsal gereksinimler eksik.',
        'Taban oturumu girdisi eksik.'
      ]
    });

    await orchestrator.requestProjectPlanPreview();
    const contentEl = global.document.getElementById('planPreviewContent');
    const text = contentEl.textContent;
    assert(text.includes('Metrik mekânsal gereksinimler eksik.'), 'First blocker message must be displayed');
    assert(text.includes('Taban oturumu girdisi eksik.'), 'Second blocker message must be displayed');
    console.log('✓ 24. canonical blocker messages shown in blocked state');
  }

  // Test 25: related_ids and raw traceback not shown in blocked UI
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: false,
      status: 409,
      kind: 'not_ready',
      projectId: pid,
      blockers: ['Mekânsal ilişki grafı güncel değil.']
    });

    await orchestrator.requestProjectPlanPreview();
    const contentEl = global.document.getElementById('planPreviewContent');
    const text = contentEl.textContent;
    assert(!text.includes('Traceback'), 'Blocked UI must not contain traceback');
    assert(!text.includes('related_ids'), 'Blocked UI must not contain related_ids');
    assert(!text.includes('schema_version'), 'Blocked UI must not contain raw JSON keys');
    console.log('✓ 25. related_ids and raw traceback not shown in blocked UI');
  }

  // Test 26: server_error renders safe generic message in UI
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: false,
      status: 500,
      kind: 'server_error',
      projectId: pid,
      error: 'Plan önizlemesi oluşturulamadı.'
    });

    await orchestrator.requestProjectPlanPreview();
    const contentEl = global.document.getElementById('planPreviewContent');
    const errBox = contentEl.querySelector('.plan-preview-error');
    assert(errBox, 'Error box must be rendered for server_error');
    assert.strictEqual(errBox.querySelector('.error-message')?.textContent, 'Plan önizlemesi oluşturulamadı.');
    console.log('✓ 26. server_error renders safe generic message in UI');
  }

  // Test 27: Repeated preview does not duplicate containers
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument
    });

    await orchestrator.requestProjectPlanPreview();
    await orchestrator.requestProjectPlanPreview();

    const contentEl = global.document.getElementById('planPreviewContent');
    const svgElements = contentEl.querySelectorAll('svg');
    assert.strictEqual(svgElements.length, 1, 'Only one SVG element should exist after repeated previews');
    console.log('✓ 27. repeated preview does not duplicate containers');
  }

  // Test 28a: Gateway stale response protection directly tested
  {
    const { gateway, stateMachine } = createTestHarness(async () => {
      // Simulate context switch mid-flight before fetch resolves
      stateMachine.setProjectId('proj_B');
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    }, 'proj_A');

    const res = await gateway.previewProjectPlan('proj_A');
    assert.strictEqual(res.ok, false, 'Gateway must return ok: false for stale project context');
    assert.strictEqual(res.kind, 'stale', 'Gateway must return kind: "stale"');
    assert.strictEqual(res.projectId, 'proj_A');
    assert.strictEqual(res.solution, undefined, 'Gateway must not expose solution from stale project');
    assert.strictEqual(res.document, undefined, 'Gateway must not expose document from stale project');
    assert(res.error.includes('Proje bağlamı değiştiği için'), 'Gateway must provide safe stale error message');
    console.log('✓ 28a. gateway stale response protection directly tested (switching project A -> B)');
  }

  // Test 28b: Gateway stale response protection when active project becomes null/empty
  {
    const { gateway, stateMachine } = createTestHarness(async () => {
      // Simulate active project becoming null mid-flight before fetch resolves
      stateMachine.setProjectId(null);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    }, 'proj_A');

    const res = await gateway.previewProjectPlan('proj_A');
    assert.strictEqual(res.ok, false, 'Gateway must return ok: false when project context becomes null');
    assert.strictEqual(res.kind, 'stale', 'Gateway must return kind: "stale" when project context becomes null');
    assert.strictEqual(res.projectId, 'proj_A');
    assert.strictEqual(res.solution, undefined, 'Gateway must not expose solution when project context becomes null');
    assert.strictEqual(res.document, undefined, 'Gateway must not expose document when project context becomes null');
    assert(res.error.includes('Proje bağlamı değiştiği için'), 'Gateway must provide safe stale error message');
    console.log('✓ 28b. gateway stale response protection when active project becomes null');
  }

  // Test 28c: Orchestrator stale context protection: old SVG is not rendered and loading is cleared
  {
    const { orchestrator, stateMachine } = createTestHarness(null, 'proj_A');
    const contentEl = global.document.getElementById('planPreviewContent');

    // Simulate delayed response where project switches while in flight
    orchestrator.localLLMGateway.previewProjectPlan = async (requestedPid) => {
      // User switches context mid-flight!
      stateMachine.setProjectId('proj_B');
      return {
        ok: false,
        status: 0,
        kind: 'stale',
        projectId: requestedPid,
        error: 'Proje bağlamı değiştiği için önceki plan sonucu kullanılmadı.'
      };
    };

    const res = await orchestrator.requestProjectPlanPreview();
    assert.strictEqual(res.ok, false, 'Stale result must be returned as not ok');
    assert.strictEqual(res.kind, 'stale', 'Result kind must be stale');
    assert.strictEqual(res.projectId, 'proj_A');

    // Prove old SVG was NOT rendered in project B
    const svgEl = contentEl.querySelector('svg');
    assert.strictEqual(svgEl, null, 'Old SVG for proj_A must NEVER be rendered inside proj_B context');
    assert.strictEqual(contentEl.children.length, 0, 'Loading state must be cleanly cleared upon stale context');
    console.log('✓ 28c. orchestrator stale context protection: old SVG not rendered and loading state cleared');
  }

  // Test 29: app.js button wiring connects to requestProjectPlanPreview
  {
    const appJsPath = path.join(__dirname, '../app.js');
    const appJsContent = fs.readFileSync(appJsPath, 'utf8');

    assert(!appJsContent.includes('requestDemoPlanPreview'), 'app.js must not contain requestDemoPlanPreview');
    assert(appJsContent.includes('requestProjectPlanPreview'), 'app.js must call requestProjectPlanPreview');
    assert(appJsContent.includes('btnShowPlanPreview'), 'app.js must wire btnShowPlanPreview');
    assert(appJsContent.includes('btnShowPlanPreviewEmpty'), 'app.js must wire btnShowPlanPreviewEmpty');
    console.log('✓ 29. app.js button wiring connects to requestProjectPlanPreview');
  }

  // Test 30: Legacy gateway previewPlan remains backward-compatible
  {
    let requestedUrl = null;
    let receivedPayload = null;
    const dummyPayload = { sample: 'legacy_preview' };
    const { gateway } = createTestHarness(async (url, opts) => {
      requestedUrl = url;
      receivedPayload = JSON.parse(opts.body);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          solution: mockSuccessSolution,
          document: mockSuccessSvgDocument
        })
      };
    });

    const res = await gateway.previewPlan(dummyPayload);
    assert.strictEqual(requestedUrl, 'http://127.0.0.1:8000/api/v1/plan/preview');
    assert.deepStrictEqual(receivedPayload, dummyPayload);
    assert.strictEqual(res.ok, true);
    console.log('✓ 30. legacy gateway previewPlan remains backward-compatible');
  }

  // Test 31: Invalid/non-SVG document rejected by sanitization
  {
    const { orchestrator } = createTestHarness();
    const invalidDoc = {
      schema_version: 'wrong_version.v0',
      svg: '<div>not svg</div>'
    };
    const res = {
      ok: true,
      status: 200,
      kind: 'success',
      solution: mockSuccessSolution,
      document: invalidDoc
    };

    orchestrator.renderPlanPreviewResult(res);
    const contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'Invalid document must not render SVG');
    assert(contentEl.querySelector('.plan-preview-error'), 'Must render error state for invalid SVG document');
    console.log('✓ 31. invalid/non-SVG document rejected by sanitization');
  }

  // Test 32: Script-containing SVG, foreignObject, and event handlers rejected
  {
    const { orchestrator } = createTestHarness();

    const scriptDoc = {
      schema_version: 'svg_plan_document.v0',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect/></svg>'
    };
    orchestrator.renderPlanPreviewResult({ ok: true, status: 200, kind: 'success', solution: mockSuccessSolution, document: scriptDoc });
    let contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'Script-containing SVG must be rejected');

    const foreignDoc = {
      schema_version: 'svg_plan_document.v0',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><iframe></iframe></foreignObject></svg>'
    };
    orchestrator.renderPlanPreviewResult({ ok: true, status: 200, kind: 'success', solution: mockSuccessSolution, document: foreignDoc });
    contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'foreignObject-containing SVG must be rejected');

    const eventDoc = {
      schema_version: 'svg_plan_document.v0',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><rect onclick="alert(1)"/></svg>'
    };
    orchestrator.renderPlanPreviewResult({ ok: true, status: 200, kind: 'success', solution: mockSuccessSolution, document: eventDoc });
    contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'Event handler attribute in SVG must be rejected');
    console.log('✓ 32. script-containing SVG, foreignObject, and event handlers rejected');
  }

  // Test 33: No LLM interpret call occurs
  {
    let llmInterpretCalled = false;
    const { orchestrator, gateway } = createTestHarness();
    gateway.interpret = async () => {
      llmInterpretCalled = true;
      return { status: 'success' };
    };
    gateway.previewProjectPlan = async (pid) => ({
      ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument
    });

    await orchestrator.requestProjectPlanPreview();
    assert.strictEqual(llmInterpretCalled, false, 'Plan preview must never call LLM interpret endpoint');
    console.log('✓ 33. no LLM call occurs for plan preview');
  }

  // Test 34: No brief or spatial mutation occurs
  {
    const { orchestrator } = createTestHarness();
    const initialBrief = orchestrator.getActiveBriefSnapshot();
    const initialBriefCopy = JSON.stringify(initialBrief);

    orchestrator.localLLMGateway.previewProjectPlan = async (pid) => ({
      ok: true, status: 200, kind: 'success', projectId: pid, solution: mockSuccessSolution, document: mockSuccessSvgDocument
    });

    await orchestrator.requestProjectPlanPreview();
    const afterBrief = orchestrator.getActiveBriefSnapshot();
    assert.strictEqual(JSON.stringify(afterBrief), initialBriefCopy, 'Brief snapshot must remain completely untouched');
    console.log('✓ 34. no brief or spatial mutation occurs');
  }

  console.log('\nAll 36 Project Plan Preview Integration V1 JS Unit Tests Passed Successfully!');
}

if (require.main === module) {
  runTests().catch((err) => {
    console.error('Test Suite Failed:', err);
    process.exit(1);
  });
}

module.exports = { runTests };
