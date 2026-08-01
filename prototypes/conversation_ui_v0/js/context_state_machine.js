/**
 * BRIF.AI — Centralized Context State Machine & Reducer (v6.1.2 Platform Architecture)
 *
 * Universal state machine handling context transitions and preventing
 * fragmented JS files from directly mutating visible context text.
 */

class ContextStateMachine {
  constructor(hierarchy) {
    this.hierarchy = hierarchy || new EntityHierarchy();

    // Generic ActiveContext Model (Requirement 2)
    this.activeContext = {
      projectId: "proj_house_2story",
      buildingId: "bldg_main",
      levelId: "lvl_ground",
      zoneId: "zone_living",
      entityId: "space_study",
      entityType: "space",
      viewMode: "plan",
      scenarioId: null,
      decisionId: null,
      workspaceScope: { levelId: "lvl_ground", buildingId: "bldg_main", projectId: "proj_house_2story" },
      conversationScope: { entityId: "space_study", levelId: "lvl_ground" },
      suspendedContext: null
    };

    this.listeners = [];
  }

  subscribe(listener) {
    this.listeners.push(listener);
  }

  notify() {
    this.listeners.forEach(fn => fn(this.activeContext));
  }

  getContext() {
    return { ...this.activeContext };
  }

  // Central Event Reducer
  dispatch(action) {
    const type = action.type;
    const payload = action.payload || {};

    switch (type) {
      case "PROJECT_SELECTED":
        this.activeContext.projectId = payload.projectId;
        this.activeContext.buildingId = payload.buildingId || null;
        this.activeContext.levelId = payload.levelId || null;
        this.activeContext.zoneId = payload.zoneId || null; // Reset zoneId on project switch
        this.activeContext.entityId = payload.entityId || null;
        this.activeContext.workspaceScope = { projectId: payload.projectId, levelId: payload.levelId, buildingId: payload.buildingId };
        break;

      case "LEVEL_SELECTED":
        this.activeContext.levelId = payload.levelId;
        this.activeContext.zoneId = null; // Reset zoneId on level switch
        this.activeContext.workspaceScope.levelId = payload.levelId;
        break;

      case "BUILDING_SELECTED":
        this.activeContext.buildingId = payload.buildingId;
        this.activeContext.levelId = null;
        this.activeContext.zoneId = null;
        this.activeContext.workspaceScope.buildingId = payload.buildingId;
        break;

      case "ENTITY_SELECTED":
        this.activeContext.entityId = payload.entityId;
        this.activeContext.entityType = payload.entityType || "space";
        this.activeContext.conversationScope = { entityId: payload.entityId, levelId: this.activeContext.levelId };
        break;

      case "VIEW_CHANGED":
        this.activeContext.viewMode = payload.viewMode;
        this.activeContext.workspaceScope.viewMode = payload.viewMode;
        break;

      case "SCENARIO_STARTED":
        this.activeContext.scenarioId = payload.scenarioId;
        this.activeContext.decisionId = payload.decisionId || null;
        if (payload.targetEntityId) {
          this.activeContext.conversationScope.entityId = payload.targetEntityId;
        }
        break;

      case "SCENARIO_SUSPENDED":
        this.activeContext.suspendedContext = {
          scenarioId: this.activeContext.scenarioId,
          entityId: this.activeContext.entityId,
          levelId: this.activeContext.levelId,
          reason: payload.reason || "Kapsam Değişikliği"
        };
        this.activeContext.scenarioId = null;
        break;

      case "SCENARIO_RESUMED":
        if (this.activeContext.suspendedContext) {
          const suspended = this.activeContext.suspendedContext;
          this.activeContext.scenarioId = suspended.scenarioId;
          this.activeContext.entityId = suspended.entityId;
          this.activeContext.levelId = suspended.levelId;
          this.activeContext.workspaceScope.levelId = suspended.levelId;
          this.activeContext.suspendedContext = null;
        }
        break;

      case "ARCHITECT_VIEW_OPENED":
        this.activeContext.viewMode = "architect_report";
        break;

      default:
        break;
    }

    this.notify();
  }
}

// Global Export
window.ContextStateMachine = ContextStateMachine;
