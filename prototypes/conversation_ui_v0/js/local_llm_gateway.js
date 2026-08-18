/**
 * Provider-neutral browser gateway for BRIF.AI local conversation inference.
 * It sends one immutable context snapshot and rejects late responses after context changes.
 */

class LocalLLMGateway {
  static DEFAULT_TIMEOUT_MS = 330000;

  constructor(options = {}) {
    this.stateMachine = options.stateMachine;
    this.hierarchy = options.hierarchy;
    this.orchestrator = options.orchestrator;
    this.baseUrl = (options.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');
    this.timeoutMs = options.timeoutMs || LocalLLMGateway.DEFAULT_TIMEOUT_MS;
    this.fetchFn = options.fetchFn || ((...args) => fetch(...args));
  }

  async interpret(message, options = {}) {
    const requestSnapshot = Object.freeze({ ...this.stateMachine.getSnapshot() });
    const requestBody = this.buildRequest(message, requestSnapshot);
    const signal = options.signal;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    if (signal) {
      if (signal.aborted) {
        clearTimeout(timeoutId);
        this.runFallback(message, 'canceled');
        return { status: 'canceled' };
      }
      signal.addEventListener('abort', () => controller.abort(), { once: true });
    }

    try {
      const response = await this.fetchFn(`${this.baseUrl}/api/v1/conversation/interpret`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });
      const payload = await this.readResponse(response);

      if (signal && signal.aborted) {
        this.runFallback(message, 'canceled');
        return { status: 'canceled' };
      }

      // HTTP failures must be classified before inspecting the success
      // envelope. A 409/404 response may not contain llm_enabled and must
      // never be mistaken for an intentionally disabled LLM.
      if (!response.ok) {
        const failureStatus = this.classifyFailure(response, payload);
        this.runFallback(message, failureStatus);
        return { status: failureStatus, payload };
      }

      if (payload.llm_enabled === false) {
        this.runFallback(message, 'disabled');
        return { status: 'demo', payload };
      }

      if (!payload.success) {
        const failureStatus = this.classifyFailure(response, payload);
        this.runFallback(message, failureStatus);
        return { status: failureStatus, payload };
      }

      if (!this.isCurrentResponse(payload, requestSnapshot)) {
        this.orchestrator.appendAssistantMessage(
          'Bağlam değiştiği için önceki yerel yapay zekâ cevabı kullanılmadı.'
        );
        return { status: 'stale', payload };
      }

      if (!this.isValidatedResult(payload.result, requestBody)) {
        // Handle pre-LLM skip: result is null but resulting_brief_snapshot is present
        if (payload.result === null && payload.resulting_brief_snapshot) {
          this.orchestrator.replaceActiveBriefSnapshot(payload.resulting_brief_snapshot);
          this.orchestrator.appendAssistantMessage('Anladım, bu soruyu geçiyoruz.');
          return { status: 'skipped', payload };
        }
        this.runFallback(message, 'invalid');
        return { status: 'invalid', payload };
      }

      this.orchestrator.handleStructuredLLMResponse(
        payload.result,
        payload.context_fingerprint,
        payload.generation_id
      );

      // Sync resulting_brief_snapshot from server if present
      if (payload.resulting_brief_snapshot) {
        this.orchestrator.replaceActiveBriefSnapshot(payload.resulting_brief_snapshot);
      }

      return { status: 'success', payload };
    } catch (error) {
      if (signal && signal.aborted) {
        this.runFallback(message, 'canceled');
        return { status: 'canceled' };
      }
      if (error && error.name === 'AbortError') {
        this.runFallback(message, 'timeout');
        return { status: 'timeout' };
      }
      this.runFallback(message, 'unreachable');
      return { status: 'unreachable' };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  classifyFailure(response, payload) {
    const errorText = typeof payload.error === 'string' ? payload.error : '';
    if (
      payload.invalid_response === true ||
      response.status === 422 ||
      /geçersiz|doğrulanabilir/i.test(errorText)
    ) {
      return 'invalid';
    }
    return 'error';
  }

  runFallback(message, status) {
    this.orchestrator.handleLocalLLMFallback(message, status);
  }

  buildRequest(message, snapshot) {
    const activeBrief = this.orchestrator && typeof this.orchestrator.getActiveBriefSnapshot === 'function'
      ? this.orchestrator.getActiveBriefSnapshot()
      : null;
    const req = {
      message,
      active_context: {
        project_id: snapshot.projectId,
        building_id: snapshot.buildingId || null,
        level_id: snapshot.levelId || null,
        zone_id: snapshot.zoneId || null,
        entity_id: snapshot.entityId || null,
        context_fingerprint: snapshot.contextFingerprint,
        generation_id: snapshot.generationId
      },
      visible_entities: this.collectVisibleEntities(snapshot),
      conversation_summary: this.orchestrator.getConversationSummary(),
      current_decisions: this.orchestrator.getCurrentDecisions(),
      pending_proposals: this.orchestrator.getPendingProposalContext(snapshot)
    };
    if (activeBrief && activeBrief.project_id === snapshot.projectId) {
      req.brief_snapshot = activeBrief;
    }
    return req;
  }

  collectVisibleEntities(snapshot) {
    const project = this.hierarchy.projects[snapshot.projectId];
    if (!project) return [];
    const building = project.buildings[snapshot.buildingId];
    if (!building) return [];
    const level = building.levels[snapshot.levelId];
    if (!level) return [];

    const entities = [];
    Object.values(level.zones || {}).forEach(zone => {
      Object.values(zone.spaces || {}).forEach(entity => {
        entities.push({
          entity_id: entity.id,
          entity_type: entity.type,
          name: entity.name,
          project_id: project.id,
          building_id: building.id,
          level_id: level.id,
          zone_id: zone.id
        });
      });
    });
    return entities;
  }

  isCurrentResponse(payload, requestSnapshot) {
    const currentSnapshot = this.stateMachine.getSnapshot();
    return payload.context_fingerprint === requestSnapshot.contextFingerprint
      && payload.context_fingerprint === currentSnapshot.contextFingerprint
      && payload.generation_id === requestSnapshot.generationId
      && payload.generation_id === currentSnapshot.generationId;
  }

  isValidatedResult(result, requestBody) {
    if (!result || typeof result !== 'object') return false;
    if (typeof result.assistant_message !== 'string' || !result.assistant_message.trim()) return false;
    const allowedIntents = new Set([
      'gather_requirement',
      'modify_space',
      'modify_relationship',
      'explain_plan',
      'compare_alternatives',
      'inspect_constraint',
      'request_visual_preference',
      'unknown'
    ]);
    const allowedActions = new Set([
      'highlight_entity',
      'focus_entity',
      'explain_plan',
      'request_clarification',
      'suggest_space_resize',
      'suggest_relationship_change',
      'suggest_orientation_change',
      'compare_alternatives',
      'inspect_constraint'
    ]);
    const planChangeActions = new Set([
      'suggest_space_resize',
      'suggest_relationship_change',
      'suggest_orientation_change'
    ]);
    if (!allowedIntents.has(result.intent)) return false;
    if (typeof result.confidence !== 'number'
      || result.confidence < 0
      || result.confidence > 1) return false;
    if (result.needs_follow_up
      && (typeof result.follow_up_question !== 'string'
        || !result.follow_up_question.trim())) return false;
    if (!Array.isArray(result.proposed_actions)) return false;
    if (!Array.isArray(result.proposed_brief_mutations)) {
      result.proposed_brief_mutations = [];
    }
    if (!Array.isArray(result.proposed_spatial_relationships)) {
      result.proposed_spatial_relationships = [];
    }
    const briefMutations = result.proposed_brief_mutations;
    const spatialRels = result.proposed_spatial_relationships;
    if ((result.proposed_actions.length > 0 || briefMutations.length > 0 || spatialRels.length > 0) && !result.needs_user_confirmation) return false;
    if (result.intent === 'compare_alternatives' && (briefMutations.length > 0 || spatialRels.length > 0)) return false;

    const validMutationTypes = new Set(['ADD_BRIEF_ITEM', 'ADD_SPACE_REQUEST', 'ADD_USAGE_SCENARIO']);
    const isValidBriefMutation = (mutation) => {
      if (!mutation || typeof mutation !== 'object') return false;
      if (typeof mutation.mutation_id !== 'string' || !mutation.mutation_id.trim()) return false;
      if (!validMutationTypes.has(mutation.mutation_type)) return false;

      const hasItem = mutation.brief_item && typeof mutation.brief_item === 'object';
      const hasSpace = mutation.space_request && typeof mutation.space_request === 'object';
      const hasUsage = mutation.usage_scenario && typeof mutation.usage_scenario === 'object';

      const count = (hasItem ? 1 : 0) + (hasSpace ? 1 : 0) + (hasUsage ? 1 : 0);
      if (count !== 1) return false;

      if (mutation.mutation_type === 'ADD_BRIEF_ITEM') {
        if (!hasItem) return false;
        if (typeof mutation.brief_item.normalized_statement !== 'string' || !mutation.brief_item.normalized_statement.trim()) return false;
      } else if (mutation.mutation_type === 'ADD_SPACE_REQUEST') {
        if (!hasSpace) return false;
        if (typeof mutation.space_request.display_name !== 'string' || !mutation.space_request.display_name.trim()) return false;
      } else if (mutation.mutation_type === 'ADD_USAGE_SCENARIO') {
        if (!hasUsage) return false;
        if (typeof mutation.usage_scenario.title !== 'string' || !mutation.usage_scenario.title.trim()) return false;
      }
      return true;
    };

    if (!briefMutations.every(isValidBriefMutation)) return false;

    const visibleIds = new Set(
      (requestBody.visible_entities || []).map(entity => entity.entity_id)
    );
    if (result.target && result.target.entity_id
      && !visibleIds.has(result.target.entity_id)) return false;
    return result.proposed_actions.every(action => {
      if (!action || !allowedActions.has(action.action_type)) return false;
      if (typeof action.description !== 'string' || !action.description.trim()) return false;
      if (action.target_entity_id && !visibleIds.has(action.target_entity_id)) return false;
      if (planChangeActions.has(action.action_type)
        && action.requires_user_confirmation !== true) return false;
      return true;
    });
  }

  async fetchProjectBrief(projectId) {
    try {
      const response = await this.fetchFn(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/brief`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      if (response.status === 200) {
        const snapshot = await response.json();
        return { ok: true, snapshot };
      }
      return { ok: false, status: response.status, error: `HTTP ${response.status}` };
    } catch (error) {
      return { ok: false, status: 0, error: error.message };
    }
  }

  async initializeProjectBrief(projectId, snapshot) {
    try {
      const response = await this.fetchFn(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/brief/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(snapshot)
      });
      if (response.status === 200) {
        const result = await response.json();
        return { ok: true, snapshot: result };
      }
      return { ok: false, status: response.status, error: `HTTP ${response.status}` };
    } catch (error) {
      return { ok: false, status: 0, error: error.message };
    }
  }

  async approveBriefMutation(payload, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchFn(`${this.baseUrl}/api/v1/brief/mutations/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      return await this.readResponse(response);
    } catch (error) {
      return {
        success: false,
        error: error && error.name === 'AbortError'
          ? 'Brief onay isteği zaman aşımına uğradı.'
          : 'Brief onay servisine ulaşılamadı.'
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async approveSpatialRelationship(payload, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchFn(`${this.baseUrl}/api/v1/spatial/relationships/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      return await this.readResponse(response);
    } catch (error) {
      return {
        success: false,
        error: error && error.name === 'AbortError'
          ? 'Mekânsal ilişki onay isteği zaman aşımına uğradı.'
          : 'Mekânsal ilişki onay servisine ulaşılamadı.'
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async readResponse(response) {
    try {
      return await response.json();
    } catch (_error) {
      return {
        success: false,
        llm_enabled: true,
        invalid_response: true,
        error: 'Yerel yapay zekâ servisi geçersiz bir yanıt döndürdü.'
      };
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = LocalLLMGateway;
}
if (typeof window !== 'undefined') {
  window.LocalLLMGateway = LocalLLMGateway;
}
