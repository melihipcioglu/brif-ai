/**
 * BRIF.AI — Context Compatibility Validator (v6.0 Platform Engine)
 *
 * Validates scope compatibility before any render step:
 * - Is selected entity within active project/building/level?
 * - Is active scenario target entity within active workspace scope?
 * - Is conversation scope compatible with workspace scope?
 */

class ContextValidator {
  constructor(hierarchy, stateMachine) {
    this.hierarchy = hierarchy || new EntityHierarchy();
    this.stateMachine = stateMachine;
  }

  validateActiveContext(activeContext) {
    if (!activeContext) return { isValid: true, mismatch: null };

    const workspace = activeContext.workspaceScope || {};
    const conversation = activeContext.conversationScope || {};

    // 1. Check Level Scope Mismatch (e.g. Master Bath on Upper Level vs Workspace set to Ground Level)
    if (conversation.levelId && workspace.levelId && conversation.levelId !== workspace.levelId) {
      const convAncestors = this.hierarchy.getAncestors(conversation.entityId || conversation.levelId);
      const workAncestors = this.hierarchy.getAncestors(workspace.levelId);

      const convName = convAncestors.level ? convAncestors.level.name : conversation.levelId;
      const workName = workAncestors.level ? workAncestors.level.name : workspace.levelId;
      const entityName = convAncestors.entity ? convAncestors.entity.name : 'Seçili Varlık';

      return {
        isValid: false,
        mismatch: "LEVEL_MISMATCH",
        message: `Önceki konu (${convName} / ${entityName}) başka bir kat kapsamındaydı. Bu görünümde ${workName} inceleniyor.`,
        suspendedData: {
          levelId: conversation.levelId,
          entityId: conversation.entityId,
          scenarioId: activeContext.scenarioId,
          scopeTitle: `${convName} / ${entityName}`
        }
      };
    }

    // 2. Check Building/Tower Mismatch (e.g. Tower A Level 18 vs Tower B)
    if (conversation.buildingId && workspace.buildingId && conversation.buildingId !== workspace.buildingId) {
      const convAncestors = this.hierarchy.getAncestors(conversation.buildingId);
      const workAncestors = this.hierarchy.getAncestors(workspace.buildingId);

      return {
        isValid: false,
        mismatch: "BUILDING_MISMATCH",
        message: `Önceki konu (${convAncestors.building ? convAncestors.building.name : conversation.buildingId}) başka bir kule/blok kapsamındaydı.`,
        suspendedData: {
          buildingId: conversation.buildingId,
          scenarioId: activeContext.scenarioId
        }
      };
    }

    return { isValid: true, mismatch: null };
  }
}

// Global Export
window.ContextValidator = ContextValidator;
