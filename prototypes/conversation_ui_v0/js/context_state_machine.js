/**
 * BRIF.AI — Centralized Context State Machine & Reducer (v6.2 Platform Architecture)
 *
 * Universal state machine creating an immutable ActiveContextSnapshot on every transition:
 * { projectId, projectType, buildingId, levelId, zoneId, entityId, workspaceMode,
 *   conversationScope, capabilities, generationId, contextFingerprint, timestamp }
 */

function cloneContextState(value) {
  if (Array.isArray(value)) {
    return value.map(item => cloneContextState(item));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, cloneContextState(item)])
    );
  }
  return value;
}

function freezeContextState(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.values(value).forEach(item => freezeContextState(item));
  return Object.freeze(value);
}

const WorkspaceModeRegistry = Object.freeze({
  plan: null,
  stage1_dashboard: 'renderStage1Dashboard',
  stage3_program: null,
  progress: 'renderAnalysisProgress',
  options_side_by_side: 'renderMasterBathOptionsSideBySide',
  overlay: 'renderFloorOverlayMode',
  orientation: 'renderOrientationMode'
});

const ScenarioQuickReplyRegistry = Object.freeze({
  master_bath_relocation: Object.freeze([
    Object.freeze({
      label: 'Yataktan görünmesini istemiyorum',
      action: 'RECORD_MASTER_BATH_PREFERENCE',
      value: 'hidden_from_bed',
      optionId: 'master_bath_bed_visibility',
      preferenceKey: 'bed_visibility',
      preferenceValue: 'hidden_from_bed',
      scenarioId: 'master_bath_relocation',
      decisionId: 'dec_master_bath'
    }),
    Object.freeze({
      label: 'Giyinme alanından geçilsin',
      action: 'RECORD_MASTER_BATH_PREFERENCE',
      value: 'through_dressing',
      optionId: 'master_bath_dressing_access',
      preferenceKey: 'access_route',
      preferenceValue: 'through_dressing',
      scenarioId: 'master_bath_relocation',
      decisionId: 'dec_master_bath'
    }),
    Object.freeze({
      label: 'Daha mahrem olsun',
      action: 'RECORD_MASTER_BATH_PREFERENCE',
      value: 'increased_privacy',
      optionId: 'master_bath_increased_privacy',
      preferenceKey: 'privacy',
      preferenceValue: 'increased_privacy',
      scenarioId: 'master_bath_relocation',
      decisionId: 'dec_master_bath'
    })
  ])
});

class ContextStateMachine {
  constructor(hierarchy) {
    this.hierarchy = hierarchy || new EntityHierarchy();

    this.generationId = 0;

    // Initial ActiveContext Model
    this.activeContext = {
      projectId: "proj_house_2story",
      buildingId: "bldg_main",
      levelId: "lvl_ground",
      zoneId: "zone_living",
      entityId: "space_study",
      entityType: "space",
      viewMode: "plan",
      workspaceMode: "plan",
      activeStage: 4,
      scenarioId: null,
      decisionId: null,
      targetEntityId: null,
      selectedOption: null,
      decisionStatus: null,
      scenarioResponses: {},
      visualPreferencesByProject: {},
      workspaceScope: { levelId: "lvl_ground", buildingId: "bldg_main", projectId: "proj_house_2story" },
      conversationScope: { entityId: "space_study", levelId: "lvl_ground" },
      suspendedContext: null
    };

    this.listeners = [];
    this.activeSnapshot = this.createSnapshot(this.activeContext);
  }

  subscribe(listener) {
    this.listeners.push(listener);
  }

  notify() {
    this.listeners.forEach(fn => fn(this.getSnapshot()));
  }

  getContext() {
    return cloneContextState(this.activeSnapshot);
  }

  getSnapshot() {
    return cloneContextState(this.activeSnapshot);
  }

  createFingerprint(ctx) {
    if (!ctx) return "none";
    return `${ctx.projectId || 'none'}|${ctx.buildingId || 'none'}|${ctx.levelId || 'none'}|${ctx.zoneId || 'none'}|${ctx.entityId || 'none'}`;
  }

  createSnapshot(ctx) {
    this.generationId++;
    const normalized = cloneContextState(ctx);
    const targetId = normalized.entityId || normalized.zoneId || normalized.levelId ||
      normalized.buildingId || normalized.projectId;
    const ancestors = this.hierarchy.getAncestors(targetId);
    if (ancestors.project) normalized.projectId = ancestors.project.id;
    if (ancestors.building) normalized.buildingId = ancestors.building.id;
    if (ancestors.level) normalized.levelId = ancestors.level.id;
    if (ancestors.zone) normalized.zoneId = ancestors.zone.id;
    if (ancestors.entity) normalized.entityId = ancestors.entity.id;

    const capabilities = this.hierarchy.getActiveCapabilities(normalized);
    const fingerprint = this.createFingerprint(normalized);
    const snapshot = {
      projectId: normalized.projectId,
      projectType: ancestors.project ? ancestors.project.type : 'project',
      buildingId: normalized.buildingId || (ancestors.building ? ancestors.building.id : null),
      levelId: normalized.levelId || (ancestors.level ? ancestors.level.id : null),
      zoneId: normalized.zoneId || (ancestors.zone ? ancestors.zone.id : null),
      entityId: normalized.entityId || (ancestors.entity ? ancestors.entity.id : null),
      entityType: normalized.entityType || 'space',
      viewMode: normalized.viewMode || 'plan',
      workspaceMode: normalized.workspaceMode || 'plan',
      activeStage: normalized.activeStage ?? 4,
      scenarioId: normalized.scenarioId || null,
      decisionId: normalized.decisionId || null,
      targetEntityId: normalized.targetEntityId || null,
      selectedOption: normalized.selectedOption ?? null,
      decisionStatus: normalized.decisionStatus || null,
      scenarioResponses: cloneContextState(normalized.scenarioResponses || {}),
      visualPreferencesByProject: cloneContextState(normalized.visualPreferencesByProject || {}),
      workspaceScope: {
        projectId: normalized.projectId,
        buildingId: normalized.buildingId || (ancestors.building ? ancestors.building.id : null),
        levelId: normalized.levelId || (ancestors.level ? ancestors.level.id : null)
      },
      conversationScope: {
        entityId: normalized.entityId || (ancestors.entity ? ancestors.entity.id : null),
        levelId: normalized.levelId || (ancestors.level ? ancestors.level.id : null)
      },
      suspendedContext: normalized.suspendedContext || null,
      capabilities: capabilities,
      generationId: this.generationId,
      contextFingerprint: fingerprint,
      timestamp: new Date().toISOString()
    };
    return freezeContextState(snapshot);
  }

  referencesAreValid(partialContext) {
    if (
      partialContext.workspaceMode !== undefined &&
      !Object.prototype.hasOwnProperty.call(WorkspaceModeRegistry, partialContext.workspaceMode)
    ) {
      return false;
    }

    const expectedTypes = {
      projectId: 'project',
      buildingId: 'building',
      levelId: 'level',
      zoneId: 'zone'
    };

    for (const [field, expectedType] of Object.entries(expectedTypes)) {
      const value = partialContext[field];
      if (value === undefined) continue;
      if (value === null) return field !== 'projectId';
      const entity = this.hierarchy.findEntity(value);
      if (!entity || entity.type !== expectedType) return false;
    }

    if (partialContext.entityId !== undefined && partialContext.entityId !== null) {
      const entity = this.hierarchy.findEntity(partialContext.entityId);
      if (!entity) return false;
      const expectedEntityType = partialContext.entityType || 'space';
      if (entity.type !== expectedEntityType) return false;
    }

    if (partialContext.targetEntityId !== undefined && partialContext.targetEntityId !== null) {
      const targetEntity = this.hierarchy.findEntity(partialContext.targetEntityId);
      if (!targetEntity) return false;
    }

    return true;
  }

  // Central Atomic Transition Function (Requirement 1)
  transitionToContext(partialContext) {
    if (!partialContext) return this.getSnapshot();

    const partial = cloneContextState(partialContext);
    const previousSnapshot = this.getSnapshot();
    if (!this.referencesAreValid(partial)) return previousSnapshot;

    const current = cloneContextState(this.activeContext);

    // 1. Project transition
    if (partial.projectId && partial.projectId !== current.projectId) {
      current.projectId = partial.projectId;
      current.buildingId = partial.buildingId || null;
      current.levelId = partial.levelId || null;
      current.zoneId = partial.zoneId || null;
      current.entityId = partial.entityId || null;
    }

    // 2. Building transition
    const needsDefaultLevel = partial.levelId === undefined &&
      partial.zoneId === undefined &&
      partial.entityId === undefined &&
      current.levelId === null;
    if (
      partial.buildingId !== undefined &&
      (partial.buildingId !== current.buildingId || needsDefaultLevel)
    ) {
      current.buildingId = partial.buildingId;
      if (partial.levelId === undefined && current.buildingId) {
        const building = this.hierarchy.findEntity(current.buildingId);
        const firstLevel = building && building.levels
          ? Object.values(building.levels)[0]
          : null;
        current.levelId = firstLevel ? firstLevel.id : null;
      } else if (partial.levelId !== undefined) {
        current.levelId = partial.levelId;
      }
      current.zoneId = null;
      current.entityId = null;
    }

    // 3. Level transition
    if (partial.levelId !== undefined && partial.levelId !== current.levelId) {
      current.levelId = partial.levelId;
      current.zoneId = null;
      current.entityId = null;
    }

    // 4. Zone / Entity transition
    if (partial.zoneId !== undefined && partial.zoneId !== current.zoneId) {
      current.zoneId = partial.zoneId;
      current.entityId = null;
    }
    if (partial.entityId !== undefined) {
      current.entityId = partial.entityId;
      if (partial.entityType) current.entityType = partial.entityType;
    }

    // 5. Stage / View / Scenario / Decision transition
    if (partial.activeStage !== undefined) current.activeStage = partial.activeStage;
    if (partial.viewMode !== undefined) current.viewMode = partial.viewMode;
    if (partial.workspaceMode !== undefined) current.workspaceMode = partial.workspaceMode;
    if (partial.scenarioId !== undefined) current.scenarioId = partial.scenarioId;
    if (partial.decisionId !== undefined) current.decisionId = partial.decisionId;
    if (partial.targetEntityId !== undefined) current.targetEntityId = partial.targetEntityId;
    if (partial.selectedOption !== undefined) current.selectedOption = partial.selectedOption;
    if (partial.decisionStatus !== undefined) current.decisionStatus = partial.decisionStatus;
    if (partial.scenarioResponses !== undefined) {
      current.scenarioResponses = cloneContextState(partial.scenarioResponses);
    }
    if (partial.visualPreferencesByProject !== undefined) {
      current.visualPreferencesByProject = cloneContextState(partial.visualPreferencesByProject);
    }
    if (partial.suspendedContext !== undefined) {
      current.suspendedContext = cloneContextState(partial.suspendedContext);
    }

    // The most specific target owns the full ancestor chain.
    const targetId = current.entityId || current.zoneId || current.levelId ||
      current.buildingId || current.projectId;
    const ancestors = this.hierarchy.getAncestors(targetId);
    if (!ancestors.project) return previousSnapshot;
    current.projectId = ancestors.project.id;
    if (ancestors.building) current.buildingId = ancestors.building.id;
    if (ancestors.level) current.levelId = ancestors.level.id;
    if (ancestors.zone) current.zoneId = ancestors.zone.id;

    this.activeContext = current;
    this.activeSnapshot = this.createSnapshot(this.activeContext);

    // Unmount stale surfaces from registry
    if (window.appDOMRegistry) {
      window.appDOMRegistry.unmountIncompatibleSurfaces(this.activeSnapshot);
    }

    this.notify();
    return this.getSnapshot();
  }

  // Central Event Reducer using transitionToContext
  dispatch(action) {
    const type = action.type;
    const payload = action.payload || {};

    switch (type) {
      case "PROJECT_SELECTED":
        this.transitionToContext({
          projectId: payload.projectId,
          buildingId: payload.buildingId,
          levelId: payload.levelId,
          entityId: payload.entityId,
          workspaceMode: payload.workspaceMode || "plan",
          scenarioId: null,
          decisionId: null,
          targetEntityId: null,
          selectedOption: null,
          decisionStatus: null,
          scenarioResponses: {}
        });
        break;

      case "BUILDING_SELECTED":
        this.transitionToContext({
          buildingId: payload.buildingId,
          levelId: payload.levelId
        });
        break;

      case "LEVEL_SELECTED":
        this.transitionToContext({
          levelId: payload.levelId
        });
        break;

      case "ENTITY_SELECTED":
        this.transitionToContext({
          entityId: payload.entityId,
          entityType: payload.entityType || "space"
        });
        break;

      case "VIEW_CHANGED":
        this.transitionToContext({
          viewMode: payload.viewMode
        });
        break;

      case "WORKSPACE_MODE_CHANGED":
        this.transitionToContext({
          workspaceMode: payload.workspaceMode
        });
        break;

      case "STAGE_CHANGED":
        this.transitionToContext({
          activeStage: payload.activeStage
        });
        break;

      case "SCENARIO_STARTED":
        this.transitionToContext({
          scenarioId: payload.scenarioId,
          decisionId: payload.decisionId || null,
          entityId: payload.targetEntityId || this.activeContext.entityId,
          targetEntityId: payload.targetEntityId || this.activeContext.targetEntityId,
          workspaceMode: payload.workspaceMode
        });
        break;

      case "SCENARIO_CONTEXT_STARTED": {
        const scenarioResponses = cloneContextState(this.activeSnapshot.scenarioResponses || {});
        if (payload.scenarioId) delete scenarioResponses[payload.scenarioId];
        this.transitionToContext({
          projectId: payload.projectId,
          buildingId: payload.buildingId,
          levelId: payload.levelId,
          entityId: payload.entityId || payload.targetEntityId,
          entityType: payload.entityType || "space",
          scenarioId: payload.scenarioId,
          decisionId: payload.decisionId || null,
          targetEntityId: payload.targetEntityId || payload.entityId || null,
          workspaceMode: payload.workspaceMode || "plan",
          selectedOption: null,
          decisionStatus: null,
          scenarioResponses
        });
        break;
      }

      case "SCENARIO_SUSPENDED":
        this.transitionToContext({
          scenarioId: null,
          suspendedContext: {
            scenarioId: this.activeSnapshot.scenarioId,
            entityId: this.activeSnapshot.entityId,
            levelId: this.activeSnapshot.levelId,
            reason: payload.reason || "Kapsam Değişikliği"
          }
        });
        break;

      case "SCENARIO_RESUMED":
        if (this.activeSnapshot.suspendedContext) {
          const suspended = this.activeSnapshot.suspendedContext;
          this.transitionToContext({
            scenarioId: suspended.scenarioId,
            entityId: suspended.entityId,
            levelId: suspended.levelId,
            suspendedContext: null,
            workspaceMode: payload.workspaceMode
          });
        }
        break;

      case "DECISION_RECORDED":
        this.transitionToContext({
          selectedOption: payload.selectedOption,
          decisionStatus: payload.decisionStatus,
          workspaceMode: payload.workspaceMode
        });
        break;

      case "SCENARIO_RESPONSE_RECORDED": {
        const active = this.activeSnapshot;
        const scenarioReplies = ScenarioQuickReplyRegistry[payload.scenarioId] || [];
        const registeredReply = scenarioReplies.find(reply =>
          reply.optionId === payload.optionId &&
          reply.preferenceKey === payload.preferenceKey &&
          reply.preferenceValue === payload.preferenceValue
        );
        const hasMasterBathEntity = active.entityId === "space_master_bath" ||
          active.targetEntityId === "space_master_bath";

        if (
          !registeredReply ||
          payload.projectId !== active.projectId ||
          payload.scenarioId !== active.scenarioId ||
          payload.decisionId !== active.decisionId ||
          active.projectId !== "proj_house_2story" ||
          active.scenarioId !== "master_bath_relocation" ||
          active.decisionId !== "dec_master_bath" ||
          !hasMasterBathEntity
        ) {
          break;
        }

        const scenarioResponses = cloneContextState(active.scenarioResponses || {});
        scenarioResponses[active.scenarioId] = {
          projectId: active.projectId,
          decisionId: active.decisionId,
          entityId: "space_master_bath",
          optionId: registeredReply.optionId,
          preferenceKey: registeredReply.preferenceKey,
          preferenceValue: registeredReply.preferenceValue,
          label: registeredReply.label
        };
        this.transitionToContext({
          scenarioResponses,
          workspaceMode: "options_side_by_side"
        });
        break;
      }

      case "VISUAL_PREFERENCE_RECORDED": {
        const projectId = payload.projectId;
        const roundId = payload.roundId;
        const cardId = payload.cardId;
        const preference = payload.preference;
        const validKey = value => typeof value === 'string' &&
          /^[a-z0-9][a-z0-9_-]{0,63}$/i.test(value);

        if (
          projectId !== this.activeSnapshot.projectId ||
          !validKey(roundId) ||
          !validKey(cardId) ||
          !['like', 'neutral'].includes(preference)
        ) {
          break;
        }

        const preferencesByProject = cloneContextState(
          this.activeSnapshot.visualPreferencesByProject || {}
        );
        const projectPreferences = cloneContextState(preferencesByProject[projectId] || {});
        const rounds = cloneContextState(projectPreferences.rounds || {});
        rounds[roundId] = { cardId, preference };
        preferencesByProject[projectId] = {
          ...projectPreferences,
          rounds
        };

        this.transitionToContext({ visualPreferencesByProject: preferencesByProject });
        break;
      }

      case "VISUAL_PREFERENCE_ROUND_SELECTED": {
        const projectId = payload.projectId;
        const roundId = payload.roundId;
        if (
          projectId !== this.activeSnapshot.projectId ||
          typeof roundId !== 'string' ||
          !/^[a-z0-9][a-z0-9_-]{0,63}$/i.test(roundId)
        ) {
          break;
        }

        const preferencesByProject = cloneContextState(
          this.activeSnapshot.visualPreferencesByProject || {}
        );
        preferencesByProject[projectId] = {
          ...cloneContextState(preferencesByProject[projectId] || {}),
          activeRoundId: roundId
        };
        this.transitionToContext({ visualPreferencesByProject: preferencesByProject });
        break;
      }

      case "ARCHITECT_VIEW_OPENED":
        this.transitionToContext({
          viewMode: "architect_report"
        });
        break;

      default:
        break;
    }

    return this.getSnapshot();
  }
}

// Global Export
window.WorkspaceModeRegistry = WorkspaceModeRegistry;
window.ScenarioQuickReplyRegistry = ScenarioQuickReplyRegistry;
window.ContextStateMachine = ContextStateMachine;
