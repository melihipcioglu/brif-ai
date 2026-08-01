/**
 * BRIF.AI — Scope-Driven Workspace Resolver (v6.1.4 Platform Architecture)
 *
 * Resolves candidate documents for active context based on specificity priority:
 * entity -> zone -> level -> building -> project.
 * Calculates natural Turkish context transition copy with zero template artifacts.
 */

class WorkspaceScopeResolver {
  constructor(hierarchy, store) {
    this.hierarchy = hierarchy || new EntityHierarchy();
    this.store = store || new ScopedDocumentStore();
  }

  resolveDocument(activeContext, documentType) {
    const candidates = this.store.findCandidateDocuments(activeContext, documentType);
    if (!candidates || candidates.length === 0) return null;

    // Specificity Priority: entity > zone > level > building > project
    const priorityOrder = ['entity', 'zone', 'level', 'building', 'project'];

    for (const scope of priorityOrder) {
      const match = candidates.find(c => c.scopeType === scope);
      if (match) return match;
    }

    return candidates[0];
  }

  // Helper to clean project names by removing trailing 'Projesi' / 'projesi'
  cleanProjectName(name) {
    if (!name) return "";
    return name.replace(/\s+(projesi|Projesi)$/i, "").trim();
  }

  // First Divergence Hierarchy Level Calculation (Requirement 4)
  calculateDivergence(oldContext, newContext) {
    if (!oldContext || !newContext) return null;

    // 1. Check Project Divergence
    if (oldContext.projectId && newContext.projectId && oldContext.projectId !== newContext.projectId) {
      const oldProj = this.hierarchy.findEntity(oldContext.projectId);
      const newProj = this.hierarchy.findEntity(newContext.projectId);

      const oldName = oldProj ? this.cleanProjectName(oldProj.name) : "";
      const newName = newProj ? this.cleanProjectName(newProj.name) : "";

      let msg = "";
      if (oldName && newName) {
        msg = `Önceki konuşmanız ${oldName} kapsamındaydı. Şu anda ${newName} projesini inceliyorsunuz.`;
      } else if (newName) {
        msg = `Şu anda ${newName} projesini inceliyorsunuz.`;
      } else {
        msg = `Proje kapsamı güncellendi.`;
      }

      return {
        level: "project",
        oldName: oldName || "Önceki Proje",
        newName: newName || "Yeni Proje",
        message: msg
      };
    }

    // 2. Check Building/Tower/Block Divergence
    if (oldContext.buildingId && newContext.buildingId && oldContext.buildingId !== newContext.buildingId) {
      const oldBldg = this.hierarchy.findEntity(oldContext.buildingId);
      const newBldg = this.hierarchy.findEntity(newContext.buildingId);
      const oldBName = oldBldg ? oldBldg.name : "Önceki Yapı";
      const newBName = newBldg ? newBldg.name : "Yeni Yapı";

      return {
        level: "building",
        oldName: oldBName,
        newName: newBName,
        message: `Önceki konuşmanız ${oldBName} kapsamındaydı. Şu anda ${newBName} inceleniyor.`
      };
    }

    // 3. Check Level/Floor Divergence
    if (oldContext.levelId && newContext.levelId && oldContext.levelId !== newContext.levelId) {
      const oldLvl = this.hierarchy.findEntity(oldContext.levelId);
      const newLvl = this.hierarchy.findEntity(newContext.levelId);
      const oldLName = oldLvl ? oldLvl.name : "Önceki Kat";
      const newLName = newLvl ? newLvl.name : "Yeni Kat";

      return {
        level: "level",
        oldName: oldLName,
        newName: newLName,
        message: `Önceki konuşmanız ${oldLName} kapsamındaydı. Şu anda ${newLName} inceleniyor.`
      };
    }

    // 4. Check Zone Divergence
    if (oldContext.zoneId && newContext.zoneId && oldContext.zoneId !== newContext.zoneId) {
      const oldZn = this.hierarchy.findEntity(oldContext.zoneId);
      const newZn = this.hierarchy.findEntity(newContext.zoneId);
      const oldZName = oldZn ? oldZn.name : "Önceki Zon";
      const newZName = newZn ? newZn.name : "Yeni Zon";

      return {
        level: "zone",
        oldName: oldZName,
        newName: newZName,
        message: `Önceki konuşmanız ${oldZName} kapsamındaydı. Şu anda ${newZName} inceleniyor.`
      };
    }

    // 5. Check Entity/Space Divergence
    if (oldContext.entityId && newContext.entityId && oldContext.entityId !== newContext.entityId) {
      const oldEnt = this.hierarchy.findEntity(oldContext.entityId);
      const newEnt = this.hierarchy.findEntity(newContext.entityId);
      const oldEName = oldEnt ? oldEnt.name : "Önceki Varlık";
      const newEName = newEnt ? newEnt.name : "Yeni Varlık";

      return {
        level: "entity",
        oldName: oldEName,
        newName: newEName,
        message: `Önceki konuşmanız ${oldEName} kapsamındaydı. Şu anda ${newEName} inceleniyor.`
      };
    }

    return null;
  }
}

// Global Export
window.WorkspaceScopeResolver = WorkspaceScopeResolver;
