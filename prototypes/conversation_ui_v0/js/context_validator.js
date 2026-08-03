/**
 * BRIF.AI — Context Compatibility Validator (v6.1 Platform Engine)
 *
 * Validates scope compatibility before any render step:
 * Calculates first divergence hierarchy level between context transitions.
 */

class ContextValidator {
  constructor(hierarchy, stateMachine) {
    this.hierarchy = hierarchy || new EntityHierarchy();
    this.stateMachine = stateMachine;
    this.resolver = new WorkspaceScopeResolver(this.hierarchy);
  }

  validateActiveContext(activeContext) {
    if (!activeContext) return { isValid: true, mismatch: null };

    const workspace = activeContext.workspaceScope || {};
    const conversation = activeContext.conversationScope || {};

    // Check scope divergence using WorkspaceScopeResolver
    const div = this.resolver.calculateDivergence(conversation, workspace);

    if (div) {
      return {
        isValid: false,
        mismatch: div.level.toUpperCase() + "_MISMATCH",
        message: div.message,
        divergence: div,
        suspendedData: {
          levelId: conversation.levelId,
          entityId: conversation.entityId,
          scenarioId: activeContext.scenarioId,
          scopeTitle: `${div.oldName}`
        }
      };
    }

    return { isValid: true, mismatch: null };
  }
}

// Global Export
window.ContextValidator = ContextValidator;
