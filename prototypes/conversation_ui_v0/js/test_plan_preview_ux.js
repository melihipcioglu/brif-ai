/**
 * BRIF.AI — Plan Preview UI V0 JS Unit Test Suite
 *
 * Tests:
 * 1. Gateway sends POST /api/v1/plan/preview
 * 2. Exact fixture payload is sent
 * 3. Success response normalized correctly
 * 4. Error response normalized correctly (409, 422, 500, 503)
 * 5. Timeout/network failure handled and distinguished
 * 6. Planı Göster action calls gateway with explicit payload
 * 7. Loading state displayed
 * 8. Valid SVG rendered
 * 9. Both Kitchen and Living Room visible
 * 10. Metadata room count, status, grid step correct
 * 11. Invalid/non-SVG document rejected
 * 12. Script-containing SVG, foreignObject, and event handlers rejected
 * 13. Error state rendered safely with Turkish messages
 * 14. No LLM call occurs for plan preview
 * 15. No brief mutation occurs
 * 16. Repeated preview does not duplicate UI containers
 * 17. Existing conversation UX tests still pass
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
  parseFromString(str, mimeType) {
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

const demoFixturePath = path.join(__dirname, '../data/plan_preview_request.demo.json');
const demoFixture = JSON.parse(fs.readFileSync(demoFixturePath, 'utf8'));

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
  dispatch(action) { return this.ctx; }
}

function createTestHarness(customFetch = null) {
  if (global.document && global.document._registry) {
    global.document._registry.clear();
  }
  const hierarchy = new MockEntityHierarchy();
  const stateMachine = new MockStateMachine();
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
  return { orchestrator, gateway, stateMachine };
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
  console.log('Running Plan Preview UI V0 JS Unit Tests...\n');

  // Test 1: Gateway sends POST /api/v1/plan/preview
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

    const res = await gateway.previewPlan(demoFixture);
    assert.strictEqual(requestedUrl, 'http://127.0.0.1:8000/api/v1/plan/preview', 'Must call /api/v1/plan/preview');
    assert.strictEqual(requestedMethod, 'POST', 'Must use POST method');
    console.log('✓ 1. gateway sends POST /api/v1/plan/preview');
  }

  // Test 2: Exact fixture payload is sent
  {
    let receivedBody = null;
    const { gateway } = createTestHarness(async (url, opts) => {
      receivedBody = JSON.parse(opts.body);
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

    await gateway.previewPlan(demoFixture);
    assert.deepStrictEqual(receivedBody, demoFixture, 'Must send exact fixture payload without mutations');
    console.log('✓ 2. exact fixture payload is sent');
  }

  // Test 3: Success response normalized correctly
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

    const res = await gateway.previewPlan(demoFixture);
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.status, 200);
    assert.deepStrictEqual(res.solution, mockSuccessSolution);
    assert.deepStrictEqual(res.document, mockSuccessSvgDocument);
    console.log('✓ 3. success response normalized correctly');
  }

  // Test 4: Error response normalized correctly (409, 422, 500, 503) and user-facing messages asserted
  {
    for (const [code, expectedSubstr] of [
      [409, 'Plan girdileri birbiriyle uyuşmuyor.'],
      [422, 'Plan girdileri bu sürümde çözülemiyor.'],
      [503, 'Plan çözücü şu anda sonuç üretemedi.'],
      [500, 'Plan önizlemesi oluşturulamadı.']
    ]) {
      const { gateway, orchestrator } = createTestHarness(async () => ({
        ok: false,
        status: code,
        json: async () => ({
          success: false,
          error: `HTTP ${code} Traceback: internal server error`
        })
      }));

      const res = await gateway.previewPlan(demoFixture);
      assert.strictEqual(res.ok, false);
      assert.strictEqual(res.status, code);
      assert.strictEqual(res.error, expectedSubstr, `Gateway must map status ${code} to "${expectedSubstr}"`);

      // Verify orchestrator renders the safe status-mapped Turkish message
      orchestrator.renderPlanPreviewResult(res, demoFixture);
      const contentEl = global.document.getElementById('planPreviewContent');
      const errBox = contentEl.querySelector('.plan-preview-error');
      assert(errBox, `Error box must be rendered for HTTP ${code}`);
      const renderedMsg = errBox.querySelector('.error-message')?.textContent;
      assert.strictEqual(renderedMsg, expectedSubstr, `UI must display mapped message for HTTP ${code}`);
      assert(!renderedMsg.includes('Traceback'), 'UI must never display raw server traceback');
    }
    console.log('✓ 4. error response normalized and asserted for 409, 422, 500, 503');
  }

  // Test 5: Raw backend error/traceback is never displayed in UI
  {
    const { orchestrator } = createTestHarness();
    const rawErrorResult = {
      ok: false,
      status: 500,
      error: 'Traceback: internal solver exception in RoomGeometrySolver at line 42: CP-SAT failed'
    };
    orchestrator.renderPlanPreviewResult(rawErrorResult, demoFixture);
    const contentEl = global.document.getElementById('planPreviewContent');
    const errBox = contentEl.querySelector('.plan-preview-error');
    assert(errBox, 'Error box must be rendered');
    const renderedMsg = errBox.querySelector('.error-message')?.textContent;
    assert.strictEqual(renderedMsg, 'Plan önizlemesi oluşturulamadı.', 'Must display safe status 500 mapped message');
    assert(!renderedMsg.includes('Traceback'), 'Must NEVER leak raw traceback to UI');
    assert(!renderedMsg.includes('RoomGeometrySolver'), 'Must NEVER leak internal class names to UI');
    console.log('✓ 5. raw backend traceback is never displayed in UI');
  }

  // Test 6: Timeout and network failure handled and distinguished
  {
    const { gateway: netGateway, orchestrator: netOrchestrator } = createTestHarness(async () => {
      throw new Error('Failed to fetch');
    });
    const netRes = await netGateway.previewPlan(demoFixture);
    assert.strictEqual(netRes.ok, false);
    assert.strictEqual(netRes.status, 0);
    assert.strictEqual(netRes.error, 'Plan servisine ulaşılamadı.');

    netOrchestrator.renderPlanPreviewResult(netRes, demoFixture);
    const netContentEl = global.document.getElementById('planPreviewContent');
    const netErrMsg = netContentEl.querySelector('.error-message')?.textContent;
    assert.strictEqual(netErrMsg, 'Plan servisine ulaşılamadı.');

    const { gateway: timeoutGateway, orchestrator: timeoutOrchestrator } = createTestHarness(async () => {
      const err = new Error('The operation was aborted');
      err.name = 'AbortError';
      throw err;
    });
    const timeoutRes = await timeoutGateway.previewPlan(demoFixture);
    assert.strictEqual(timeoutRes.ok, false);
    assert.strictEqual(timeoutRes.status, 0);
    assert.strictEqual(timeoutRes.error, 'Plan isteği zaman aşımına uğradı.');

    timeoutOrchestrator.renderPlanPreviewResult(timeoutRes, demoFixture);
    const timeoutContentEl = global.document.getElementById('planPreviewContent');
    const timeoutErrMsg = timeoutContentEl.querySelector('.error-message')?.textContent;
    assert.strictEqual(timeoutErrMsg, 'Plan isteği zaman aşımına uğradı.');
    console.log('✓ 6. timeout and network failure handled and distinguished');
  }

  // Test 7: Planı Göster action calls gateway with explicit payload
  {
    let previewCalledWith = null;
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewPlan = async (payload) => {
      previewCalledWith = payload;
      return { ok: true, status: 200, solution: mockSuccessSolution, document: mockSuccessSvgDocument };
    };

    await orchestrator.requestPlanPreview(demoFixture);
    assert.deepStrictEqual(previewCalledWith, demoFixture, 'Orchestrator must forward explicit payload');

    let threw = false;
    try {
      await orchestrator.requestPlanPreview(null);
    } catch (e) {
      threw = true;
    }
    assert.strictEqual(threw, true, 'requestPlanPreview without payload must throw');
    console.log('✓ 7. Planı Göster action calls gateway with explicit payload');
  }

  // Test 8: Loading state displayed
  {
    let checkedLoadingInFlight = false;
    const { orchestrator } = createTestHarness();
    const contentEl = global.document.getElementById('planPreviewContent');

    orchestrator.localLLMGateway.previewPlan = async (payload) => {
      const spinner = contentEl.querySelector('.plan-preview-loading');
      if (spinner || contentEl.textContent.includes('hesaplanıyor')) {
        checkedLoadingInFlight = true;
      }
      return { ok: true, status: 200, solution: mockSuccessSolution, document: mockSuccessSvgDocument };
    };

    await orchestrator.requestPlanPreview(demoFixture);
    assert.strictEqual(checkedLoadingInFlight, true, 'Loading state must be visible during request');
    console.log('✓ 8. loading state displayed');
  }

  // Test 9: Valid SVG rendered
  {
    const { orchestrator } = createTestHarness();
    const result = {
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    };

    orchestrator.renderPlanPreviewResult(result, demoFixture);
    const contentEl = global.document.getElementById('planPreviewContent');
    const svgEl = contentEl.querySelector('svg');
    assert(svgEl, 'Must render SVG element in DOM');
    assert.strictEqual(svgEl.localName, 'svg', 'Root node must be SVG');
    console.log('✓ 9. valid SVG rendered');
  }

  // Test 10: Both Kitchen and Living Room visible in rendered SVG
  {
    const { orchestrator } = createTestHarness();
    orchestrator.renderPlanPreviewResult({
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    }, demoFixture);

    const contentEl = global.document.getElementById('planPreviewContent');
    const text = contentEl.textContent;
    assert(text.includes('Living Room') || contentEl.innerHTML.includes('Living Room'), 'Living Room must be in preview');
    assert(text.includes('Kitchen') || contentEl.innerHTML.includes('Kitchen'), 'Kitchen must be in preview');
    console.log('✓ 10. both Kitchen and Living Room visible in rendered SVG');
  }

  // Test 11: Metadata room count, status, grid step correctly rendered
  {
    const { orchestrator } = createTestHarness();
    orchestrator.renderPlanPreviewResult({
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    }, demoFixture);

    const contentEl = global.document.getElementById('planPreviewContent');
    const metaBar = contentEl.querySelector('.plan-preview-meta-bar');
    assert(metaBar, 'Metadata bar must be rendered');
    const metaText = metaBar.textContent;
    assert(metaText.includes('FEASIBLE'), 'Must show solver status FEASIBLE');
    assert(metaText.includes('2'), 'Must show 2 rooms');
    assert(metaText.includes('0.1'), 'Must show grid step 0.1');
    console.log('✓ 11. metadata room count, status, grid step correctly rendered');
  }

  // Test 12: Demo provenance notice and architectural disclaimer rendered
  {
    const { orchestrator } = createTestHarness();
    orchestrator.renderPlanPreviewResult({
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    }, demoFixture);

    const contentEl = global.document.getElementById('planPreviewContent');
    const demoNotice = contentEl.querySelector('.plan-preview-demo-notice');
    assert(demoNotice, 'Demo provenance notice must be rendered');
    assert(demoNotice.textContent.includes('Demo önizleme'), 'Must mention demo önizleme');
    assert(demoNotice.textContent.includes('mevcut sohbetinizden otomatik üretilmemiştir'), 'Must clarify not auto-generated from current chat');

    const disclaimer = contentEl.querySelector('.plan-preview-disclaimer');
    assert(disclaimer, 'Architectural disclaimer must be rendered');
    assert(disclaimer.textContent.includes('şematik yerleşimdir'), 'Must clarify schematic layout');
    assert(disclaimer.textContent.includes('Resmî mimari uygulama projesi değildir'), 'Must state not official project');
    console.log('✓ 12. demo provenance notice and architectural disclaimer rendered');
  }

  // Test 13: Invalid/non-SVG document rejected
  {
    const { orchestrator } = createTestHarness();
    const invalidDoc = {
      schema_version: 'wrong_version.v0',
      svg: '<div>not svg</div>'
    };
    const res = {
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: invalidDoc
    };

    orchestrator.renderPlanPreviewResult(res, demoFixture);
    const contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'Invalid document must not render SVG');
    assert(contentEl.querySelector('.plan-preview-error'), 'Must render error state for invalid SVG document');
    console.log('✓ 13. invalid/non-SVG document rejected');
  }

  // Test 14: Script-containing SVG, foreignObject, and event handlers rejected
  {
    const { orchestrator } = createTestHarness();

    const scriptDoc = {
      schema_version: 'svg_plan_document.v0',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect/></svg>'
    };
    orchestrator.renderPlanPreviewResult({ ok: true, status: 200, solution: mockSuccessSolution, document: scriptDoc }, demoFixture);
    let contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'Script-containing SVG must be rejected');

    const foreignDoc = {
      schema_version: 'svg_plan_document.v0',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><iframe></iframe></foreignObject></svg>'
    };
    orchestrator.renderPlanPreviewResult({ ok: true, status: 200, solution: mockSuccessSolution, document: foreignDoc }, demoFixture);
    contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'foreignObject-containing SVG must be rejected');

    const eventDoc = {
      schema_version: 'svg_plan_document.v0',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><rect onclick="alert(1)"/></svg>'
    };
    orchestrator.renderPlanPreviewResult({ ok: true, status: 200, solution: mockSuccessSolution, document: eventDoc }, demoFixture);
    contentEl = global.document.getElementById('planPreviewContent');
    assert(!contentEl.querySelector('svg'), 'Event handler attribute in SVG must be rejected');
    console.log('✓ 14. script-containing SVG, foreignObject, and event handlers rejected');
  }

  // Test 15: Error state rendered safely with Turkish messages
  {
    const { orchestrator } = createTestHarness();
    orchestrator.renderPlanPreviewResult({
      ok: false,
      status: 409,
      error: 'Plan girdileri birbiriyle uyuşmuyor.'
    }, demoFixture);

    const contentEl = global.document.getElementById('planPreviewContent');
    const errorEl = contentEl.querySelector('.plan-preview-error');
    assert(errorEl, 'Must render error element');
    assert(errorEl.textContent.includes('Plan girdileri birbiriyle uyuşmuyor.'), 'Must display Turkish 409 error message');
    console.log('✓ 15. error state rendered safely with Turkish messages');
  }

  // Test 16: No LLM call occurs for plan preview
  {
    let llmInterpretCalled = false;
    const { orchestrator, gateway } = createTestHarness();
    gateway.interpret = async () => {
      llmInterpretCalled = true;
      return { status: 'success' };
    };
    gateway.previewPlan = async () => ({
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    });

    await orchestrator.requestPlanPreview(demoFixture);
    assert.strictEqual(llmInterpretCalled, false, 'Plan preview must never call LLM interpret endpoint');
    console.log('✓ 16. no LLM call occurs for plan preview');
  }

  // Test 17: No brief mutation occurs
  {
    const { orchestrator } = createTestHarness();
    const initialBrief = orchestrator.getActiveBriefSnapshot();
    const initialBriefCopy = JSON.stringify(initialBrief);

    orchestrator.localLLMGateway.previewPlan = async () => ({
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    });

    await orchestrator.requestPlanPreview(demoFixture);
    const afterBrief = orchestrator.getActiveBriefSnapshot();
    assert.strictEqual(JSON.stringify(afterBrief), initialBriefCopy, 'Brief snapshot must remain completely untouched');
    console.log('✓ 17. no brief mutation occurs');
  }

  // Test 18: Repeated preview does not duplicate UI containers
  {
    const { orchestrator } = createTestHarness();
    orchestrator.localLLMGateway.previewPlan = async () => ({
      ok: true,
      status: 200,
      solution: mockSuccessSolution,
      document: mockSuccessSvgDocument
    });

    await orchestrator.requestPlanPreview(demoFixture);
    await orchestrator.requestPlanPreview(demoFixture);

    const contentEl = global.document.getElementById('planPreviewContent');
    const svgElements = contentEl.querySelectorAll('svg');
    assert.strictEqual(svgElements.length, 1, 'Only one SVG element should exist after repeated previews');
    console.log('✓ 18. repeated preview does not duplicate UI containers');
  }

  console.log('\nAll 18 Focused Plan Preview UI V0 JS Unit Tests Passed Successfully!');
}

if (require.main === module) {
  runTests().catch((err) => {
    console.error('Test Suite Failed:', err);
    process.exit(1);
  });
}

module.exports = { runTests };
