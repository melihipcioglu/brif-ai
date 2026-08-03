/**
 * BRIF.AI — DOM Surface Registry & Generation Token Manager (v6.1.3 Platform Architecture)
 *
 * Core architectural module tracking all mounted workspace surfaces and enforcing:
 * "No stale or foreign workspace payload may survive an active-scope transition."
 */

class DOMSurfaceRegistry {
  constructor() {
    this.currentGenerationId = 0;
    this.currentFingerprint = "";
    this.mountedSurfaces = new Map();
  }

  // Generate new render token on scope transition
  nextGeneration(activeContext) {
    this.currentGenerationId++;
    this.currentFingerprint = this.getScopeFingerprint(activeContext);
    return {
      generationId: this.currentGenerationId,
      fingerprint: this.currentFingerprint
    };
  }

  getScopeFingerprint(ctx) {
    if (!ctx) return "none";
    return `${ctx.projectId || 'none'}|${ctx.buildingId || 'none'}|${ctx.levelId || 'none'}|${ctx.zoneId || 'none'}|${ctx.entityId || 'none'}`;
  }

  // Check if render token is valid and fresh
  isValidGeneration(generationId, activeContext) {
    if (generationId !== this.currentGenerationId) return false;
    const fp = this.getScopeFingerprint(activeContext);
    return fp === this.currentFingerprint;
  }

  // Register mounted surface
  mountSurface(surfaceInfo) {
    const key = surfaceInfo.containerId || surfaceInfo.surfaceId;
    this.mountedSurfaces.set(key, {
      ...surfaceInfo,
      generationId: this.currentGenerationId,
      status: 'mounted',
      mountedAt: new Date().toISOString()
    });
  }

  // Unmount surfaces incompatible with current activeContext
  unmountIncompatibleSurfaces(activeContext) {
    const activeProj = activeContext ? activeContext.projectId : null;

    this.mountedSurfaces.forEach((surface, key) => {
      if (surface.projectId && activeProj && surface.projectId !== activeProj) {
        const container = document.getElementById(surface.containerId);
        if (container) {
          container.innerHTML = '';
        }
        this.mountedSurfaces.delete(key);
      }
    });
  }

  // Clear all mounted surfaces
  clearAll() {
    this.mountedSurfaces.forEach((surface) => {
      const container = document.getElementById(surface.containerId);
      if (container) container.innerHTML = '';
    });
    this.mountedSurfaces.clear();
  }

  getMountedSurfacesForProject(projectId) {
    const list = [];
    this.mountedSurfaces.forEach((surface) => {
      if (surface.projectId === projectId) list.push(surface);
    });
    return list;
  }
}

// Global Export
window.DOMSurfaceRegistry = DOMSurfaceRegistry;
