/**
 * BRIF.AI — Scope-Driven Workspace Resolver (v6.1 Platform Architecture)
 *
 * Resolves candidate documents for active context based on specificity priority:
 * entity -> zone -> level -> building -> project.
 * Calculates first divergence hierarchy level between context transitions.
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

  // First Divergence Hierarchy Level Calculation (Requirement 7)
  calculateDivergence(oldContext, newContext) {
    if (!oldContext || !newContext) return null;

    // 1. Check Project Divergence
    if (oldContext.projectId !== newContext.projectId) {
      const oldProj = this.hierarchy.findEntity(oldContext.projectId);
      const newProj = this.hierarchy.findEntity(newContext.projectId);
      return {
        level: "project",
        oldName: oldProj ? oldProj.name : "Önceki Proje",
        newName: newProj ? newProj.name : "Yeni Proje",
        message: `Önceki konuşmanız ${oldProj ? oldProj.name : 'Önceki Proje'} projesine aitti. Şimdi ${newProj ? newProj.name : 'Yeni Proje'} projesini inceliyorsunuz.`
      };
    }

    // 2. Check Building/Tower/Block Divergence
    if (oldContext.buildingId !== newContext.buildingId) {
      const oldBldg = this.hierarchy.findEntity(oldContext.buildingId);
      const newBldg = this.hierarchy.findEntity(newContext.buildingId);
      return {
        level: "building",
        oldName: oldBldg ? oldBldg.name : "Önceki Yapı",
        newName: newBldg ? newBldg.name : "Yeni Yapı",
        message: `Önceki konuşmanız ${oldBldg ? oldBldg.name : 'Önceki Blok'} kapsamındaydı. Şimdi ${newBldg ? newBldg.name : 'Yeni Blok'} inceleniyor.`
      };
    }

    // 3. Check Level/Floor Divergence
    if (oldContext.levelId !== newContext.levelId) {
      const oldLvl = this.hierarchy.findEntity(oldContext.levelId);
      const newLvl = this.hierarchy.findEntity(newContext.levelId);
      return {
        level: "level",
        oldName: oldLvl ? oldLvl.name : "Önceki Kat",
        newName: newLvl ? newLvl.name : "Yeni Kat",
        message: `Önceki konuşmanız ${oldLvl ? oldLvl.name : 'Önceki Kat'} kapsamındaydı. Şimdi ${newLvl ? newLvl.name : 'Yeni Kat'} inceleniyor.`
      };
    }

    // 4. Check Zone Divergence
    if (oldContext.zoneId !== newContext.zoneId) {
      const oldZn = this.hierarchy.findEntity(oldContext.zoneId);
      const newZn = this.hierarchy.findEntity(newContext.zoneId);
      return {
        level: "zone",
        oldName: oldZn ? oldZn.name : "Önceki Zon",
        newName: newZn ? newZn.name : "Yeni Zon",
        message: `Önceki konuşmanız ${oldZn ? oldZn.name : 'Önceki Zon'} kapsamındaydı. Şimdi ${newZn ? newZn.name : 'Yeni Zon'} inceleniyor.`
      };
    }

    // 5. Check Entity/Space Divergence
    if (oldContext.entityId !== newContext.entityId) {
      const oldEnt = this.hierarchy.findEntity(oldContext.entityId);
      const newEnt = this.hierarchy.findEntity(newContext.entityId);
      return {
        level: "entity",
        oldName: oldEnt ? oldEnt.name : "Önceki Varlık",
        newName: newEnt ? newEnt.name : "Yeni Varlık",
        message: `Önceki konuşmanız ${oldEnt ? oldEnt.name : 'Önceki Varlık'} kapsamındaydı. Şimdi ${newEnt ? newEnt.name : 'Yeni Varlık'} inceleniyor.`
      };
    }

    return null;
  }
}

// Global Export
window.WorkspaceScopeResolver = WorkspaceScopeResolver;
