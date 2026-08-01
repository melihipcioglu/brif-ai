/**
 * BRIF.AI — Scoped Document Store (v6.1.2 Platform Architecture)
 *
 * Central registry holding generic workspace documents for all project types.
 * Matches documents ONLY via entity relationships and scope fields — NEVER room names.
 * Caches workspace demo packages and scoped actions.
 */

class ScopedDocumentStore {
  constructor() {
    this.documents = [];
    this.packages = {};
    this.isLoaded = false;
  }

  async initialize() {
    try {
      const files = [
        'data/workspaces/house_2story.workspace.demo.json',
        'data/workspaces/tower_50floor.workspace.demo.json',
        'data/workspaces/campus_multiblock.workspace.demo.json'
      ];

      for (const file of files) {
        const res = await fetch(file);
        if (res.ok) {
          const pkg = await res.json();
          if (pkg.projectId) {
            this.packages[pkg.projectId] = pkg;
          }
          if (pkg.documents) {
            this.documents.push(...pkg.documents);
          }
        }
      }
      this.isLoaded = true;
    } catch (err) {
      console.error('ScopedDocumentStore initialization error:', err);
    }
  }

  getWorkspacePackage(projectId) {
    return this.packages[projectId] || null;
  }

  addDocument(doc) {
    this.documents.push(doc);
  }

  // Find candidate documents compatible with activeContext and documentType
  findCandidateDocuments(activeContext, documentType) {
    if (!activeContext || !documentType) return [];

    return this.documents.filter(doc => {
      // 1. Must match documentType
      if (doc.documentType !== documentType) return false;

      // 2. Status must be available
      if (doc.status !== 'available') return false;

      // 3. Project ID must match
      if (doc.projectId !== activeContext.projectId) return false;

      // 4. If buildingId is defined on doc, must match activeContext or workspaceScope
      if (doc.buildingId && activeContext.buildingId && doc.buildingId !== activeContext.buildingId) {
        return false;
      }

      // 5. If levelId is defined on doc, must match activeContext or workspaceScope
      if (doc.levelId && activeContext.levelId && doc.levelId !== activeContext.levelId) {
        return false;
      }

      // 6. If zoneId is defined on doc, must match activeContext
      if (doc.zoneId && activeContext.zoneId && doc.zoneId !== activeContext.zoneId) {
        return false;
      }

      // 7. If entityId is defined on doc, must match activeContext.entityId
      if (doc.entityId && activeContext.entityId && doc.entityId !== activeContext.entityId) {
        return false;
      }

      return true;
    });
  }
}

// Global Export
window.ScopedDocumentStore = ScopedDocumentStore;
