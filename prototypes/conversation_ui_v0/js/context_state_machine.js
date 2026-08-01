/**
 * BRIF.AI — Centralized Context State Machine & Reducer (v6.2 Platform Architecture)
 *
 * Universal state machine creating an immutable ActiveContextSnapshot on every transition:
 * { projectId, projectType, buildingId, levelId, zoneId, entityId, workspaceMode,
 *   conversationScope, capabilities, generationId, contextFingerprint, timestamp }
 */

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
      activeStage: 4,
      scenarioId: null,
      decisionId: null,
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
    this.listeners.forEach(fn => fn(this.activeSnapshot));
  }

  getContext() {
    return { ...this.activeSnapshot };
  }

  getSnapshot() {
    return { ...this.activeSnapshot };
  }

  createFingerprint(ctx) {
    if (!ctx) return "none";
    return `${ctx.projectId || 'none'}|${ctx.buildingId || 'none'}|${ctx.levelId || 'none'}|${ctx.zoneId || 'none'}|${ctx.entityId || 'none'}`;
  }

  createSnapshot(ctx) {
    this.generationId++;
    const ancestors = this.hierarchy.getAncestors(ctx.entityId || ctx.levelId || ctx.buildingId || ctx.projectId);
    const capabilities = this.hierarchy.getActiveCapabilities(ctx);
    const fingerprint = this.createFingerprint(ctx);

    return {
      projectId: ctx.projectId,
      projectType: ancestors.project ? ancestors.project.type : 'project',
      buildingId: ctx.buildingId || (ancestors.building ? ancestors.building.id : null),
      levelId: ctx.levelId || (ancestors.level ? ancestors.level.id : null),
      zoneId: ctx.zoneId || (ancestors.zone ? ancestors.zone.id : null),
      entityId: ctx.entityId || (ancestors.entity ? ancestors.entity.id : null),
      entityType: ctx.entityType || 'space',
      viewMode: ctx.viewMode || 'plan',
      activeStage: ctx.activeStage || 4,
      scenarioId: ctx.scenarioId || null,
      decisionId: ctx.decisionId || null,
      workspaceScope: {
        projectId: ctx.projectId,
        buildingId: ctx.buildingId || (ancestors.building ? ancestors.building.id : null),
        levelId: ctx.levelId || (ancestors.level ? ancestors.level.id : null)
      },
      conversationScope: {
        entityId: ctx.entityId || (ancestors.entity ? ancestors.entity.id : null),
        levelId: ctx.levelId || (ancestors.level ? ancestors.level.id : null)
      },
      suspendedContext: ctx.suspendedContext || null,
      capabilities: capabilities,
      generationId: this.generationId,
      contextFingerprint: fingerprint,
      timestamp: new Date().toISOString()
    };
  }

  // Central Atomic Transition Function (Requirement 1)
  transitionToContext(partialContext) {
    if (!partialContext) return this.activeSnapshot;

    const current = { ...this.activeContext };

    // 1. Project transition
    if (partialContext.projectId && partialContext.projectId !== current.projectId) {
      current.projectId = partialContext.projectId;
      current.buildingId = partialContext.buildingId || null;
      current.levelId = partialContext.levelId || null;
      current.zoneId = partialContext.zoneId || null;
      current.entityId = partialContext.entityId || null;
    }

    // 2. Building transition
    if (partialContext.buildingId !== undefined) {
      current.buildingId = partialContext.buildingId;
      // Auto-resolve default level for building if not specified
      if (!partialContext.levelId) {
        const bldg = this.hierarchy.findEntity(current.buildingId);
        if (bldg && bldg.levels) {
          const firstLvl = Object.values(bldg.levels)[0];
          current.levelId = firstLvl ? firstLvl.id : null;
        } else {
          current.levelId = null;
        }
      } else {
        current.levelId = partialContext.levelId;
      }
      current.zoneId = null;
      current.entityId = null;
    }

    // 3. Level transition
    if (partialContext.levelId !== undefined && partialContext.levelId !== current.levelId) {
      current.levelId = partialContext.levelId;
      current.zoneId = null;
      current.entityId = null;
    }

    // 4. Zone / Entity transition
    if (partialContext.zoneId !== undefined) current.zoneId = partialContext.zoneId;
    if (partialContext.entityId !== undefined) {
      current.entityId = partialContext.entityId;
      if (partialContext.entityType) current.entityType = partialContext.entityType;
    }

    // 5. Stage / View / Scenario transition
    if (partialContext.activeStage !== undefined) current.activeStage = partialContext.activeStage;
    if (partialContext.viewMode !== undefined) current.viewMode = partialContext.viewMode;
    if (partialContext.scenarioId !== undefined) current.scenarioId = partialContext.scenarioId;
    if (partialContext.decisionId !== undefined) current.decisionId = partialContext.decisionId;
    if (partialContext.suspendedContext !== undefined) current.suspendedContext = partialContext.suspendedContext;

    // Resolve full ancestors to ensure no orphaned building/level/zone IDs remain
    const ancestors = this.hierarchy.getAncestors(current.entityId || current.levelId || current.buildingId || current.projectId);
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
    return this.activeSnapshot;
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
          entityId: payload.entityId
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

      case "SCENARIO_STARTED":
        this.transitionToContext({
          scenarioId: payload.scenarioId,
          decisionId: payload.decisionId || null,
          entityId: payload.targetEntityId || this.activeContext.entityId
        });
        break;

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
            suspendedContext: null
          });
        }
        break;

      case "ARCHITECT_VIEW_OPENED":
        this.transitionToContext({
          viewMode: "architect_report"
        });
        break;

      default:
        break;
    }
  }
}

// Global Export
window.ContextStateMachine = ContextStateMachine;
