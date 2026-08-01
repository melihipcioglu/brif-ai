/**
 * Provider-neutral browser gateway for BRIF.AI local conversation inference.
 * It sends one immutable context snapshot and rejects late responses after context changes.
 */

class LocalLLMGateway {
  constructor(options = {}) {
    this.stateMachine = options.stateMachine;
    this.hierarchy = options.hierarchy;
    this.orchestrator = options.orchestrator;
    this.baseUrl = (options.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');
    this.timeoutMs = options.timeoutMs || 120000;
  }

  async interpret(message) {
    const requestSnapshot = Object.freeze({ ...this.stateMachine.getSnapshot() });
    const requestBody = this.buildRequest(message, requestSnapshot);
    this.orchestrator.appendAssistantMessage('Talebinizi mimari açıdan değerlendiriyorum…');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/conversation/interpret`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });
      const payload = await this.readResponse(response);

      if (!payload.llm_enabled) {
        this.orchestrator.appendAssistantMessage(
          payload.error || 'Yerel yapay zekâ bağlantısı devre dışı. Demo konuşma modu kullanılıyor.'
        );
        this.orchestrator.handleDemoUserMessage(message);
        return { status: 'demo', payload };
      }

      if (!response.ok || !payload.success) {
        this.orchestrator.appendAssistantMessage(
          payload.error || 'Yerel yapay zekâ isteği tamamlanamadı.'
        );
        return { status: 'error', payload };
      }

      if (!this.isCurrentResponse(payload, requestSnapshot)) {
        this.orchestrator.appendAssistantMessage(
          'Bağlam değiştiği için önceki yerel yapay zekâ cevabı kullanılmadı.'
        );
        return { status: 'stale', payload };
      }

      if (!this.isValidatedResult(payload.result, requestBody)) {
        this.orchestrator.appendAssistantMessage(
          'Yerel model doğrulanabilir bir mimari niyet yanıtı üretmedi.'
        );
        return { status: 'invalid', payload };
      }

      this.orchestrator.handleStructuredLLMResponse(payload.result, payload.context_fingerprint);
      return { status: 'success', payload };
    } catch (error) {
      if (error && error.name === 'AbortError') {
        this.orchestrator.appendAssistantMessage('Yerel yapay zekâ isteği zaman aşımına uğradı.');
        return { status: 'timeout' };
      }
      this.orchestrator.appendAssistantMessage(
        'Yerel yapay zekâ servisine ulaşılamadı. Ollamanın çalıştığını kontrol edin.'
      );
      return { status: 'unreachable' };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  buildRequest(message, snapshot) {
    return {
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
      current_decisions: this.orchestrator.getCurrentDecisions()
    };
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
    if (result.proposed_actions.length > 0 && !result.needs_user_confirmation) return false;

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

  async readResponse(response) {
    try {
      return await response.json();
    } catch (_error) {
      return {
        success: false,
        llm_enabled: true,
        error: 'Yerel yapay zekâ servisi geçersiz bir yanıt döndürdü.'
      };
    }
  }
}

window.LocalLLMGateway = LocalLLMGateway;
