/**
 * BRIF.AI — Universal Architectural Entity Hierarchy (v6.0 Platform Architecture)
 *
 * Universal data model supporting:
 * Project -> Building / Block / Tower -> Level / Floor -> Zone / Department -> Space -> Architectural Element
 */

class EntityHierarchy {
  constructor() {
    this.projects = {
      // TEST A: Two-Story Residence
      proj_house_2story: {
        id: "proj_house_2story",
        type: "project",
        name: "İki Katlı Müstakil Konut Projesi",
        buildings: {
          bldg_main: {
            id: "bldg_main",
            type: "building",
            parentId: "proj_house_2story",
            name: "Ana Konut Yapısı",
            levels: {
              lvl_ground: {
                id: "lvl_ground",
                type: "level",
                parentId: "bldg_main",
                name: "Zemin Kat",
                zones: {
                  zone_living: {
                    id: "zone_living",
                    type: "zone",
                    parentId: "lvl_ground",
                    name: "Ortak Yaşam Zonu",
                    spaces: {
                      space_living: { id: "space_living", type: "space", parentId: "zone_living", name: "Salon & Yaşam Alanı", area: 34 },
                      space_kitchen: { id: "space_kitchen", type: "space", parentId: "zone_living", name: "Mutfak", area: 16 },
                      space_study: { id: "space_study", type: "space", parentId: "zone_living", name: "Çalışma Odası", area: 12 }
                    }
                  }
                }
              },
              lvl_upper: {
                id: "lvl_upper",
                type: "level",
                parentId: "bldg_main",
                name: "Üst Kat",
                zones: {
                  zone_private: {
                    id: "zone_private",
                    type: "zone",
                    parentId: "lvl_upper",
                    name: "Özel Gece Zonu",
                    spaces: {
                      space_master_suite: { id: "space_master_suite", type: "space", parentId: "zone_private", name: "Ebeveyn Süiti", area: 24 },
                      space_master_bath: { id: "space_master_bath", type: "space", parentId: "zone_private", name: "Ebeveyn Banyosu", area: 7 },
                      space_child1: { id: "space_child1", type: "space", parentId: "zone_private", name: "1. Çocuk Odası", area: 14 }
                    }
                  }
                }
              }
            }
          }
        }
      },

      // TEST B: 50-Story Commercial Tower
      proj_tower_50floor: {
        id: "proj_tower_50floor",
        type: "project",
        name: "50 Katlı Finans Kulesi Projesi",
        buildings: {
          tower_a: {
            id: "tower_a",
            type: "building",
            parentId: "proj_tower_50floor",
            name: "A Kulesi",
            levels: {
              lvl_18: {
                id: "lvl_18",
                type: "level",
                parentId: "tower_a",
                name: "18. Kat (Yönetim Katı)",
                zones: {
                  zone_exec_18: {
                    id: "zone_exec_18",
                    type: "zone",
                    parentId: "lvl_18",
                    name: "Yönetici Deparmanı",
                    spaces: {
                      space_meeting_18a: { id: "space_meeting_18a", type: "space", parentId: "zone_exec_18", name: "18A Yönetim Toplantı Odası", area: 45 }
                    }
                  }
                }
              },
              lvl_32: {
                id: "lvl_32",
                type: "level",
                parentId: "tower_a",
                name: "32. Kat (Operasyon Katı)",
                zones: {
                  zone_ops_32: {
                    id: "zone_ops_32",
                    type: "zone",
                    parentId: "lvl_32",
                    name: "Yazılım & IT Zonu",
                    spaces: {
                      space_open_office_32: { id: "space_open_office_32", type: "space", parentId: "zone_ops_32", name: "32B Açık Ofis Alanı", area: 180 }
                    }
                  }
                }
              }
            }
          }
        }
      },

      // TEST C: Multi-Block Campus
      proj_campus_multiblock: {
        id: "proj_campus_multiblock",
        type: "project",
        name: "Çok Bloklu Teknoloji Kampüsü",
        buildings: {
          block_a_r_d: {
            id: "block_a_r_d",
            type: "building",
            parentId: "proj_campus_multiblock",
            name: "Blok A (AR-GE Binası)",
            levels: {
              lvl_2_block_a: {
                id: "lvl_2_block_a",
                type: "level",
                parentId: "block_a_r_d",
                name: "2. Kat (Laboratuvar Katı)",
                zones: {
                  zone_lab: {
                    id: "zone_lab",
                    type: "zone",
                    parentId: "lvl_2_block_a",
                    name: "Prototip Laboratuvar Zonu",
                    spaces: {
                      space_robotics_lab: { id: "space_robotics_lab", type: "space", parentId: "zone_lab", name: "Robotik Araştırma Laboratuvarı", area: 120 }
                    }
                  }
                }
              }
            }
          },
          block_b_admin: {
            id: "block_b_admin",
            type: "building",
            parentId: "proj_campus_multiblock",
            name: "Blok B (İdari Bina)",
            levels: {
              lvl_2_block_b: {
                id: "lvl_2_block_b",
                type: "level",
                parentId: "block_b_admin",
                name: "2. Kat (İnsan Kaynakları Katı)",
                zones: {
                  zone_hr: {
                    id: "zone_hr",
                    type: "zone",
                    parentId: "lvl_2_block_b",
                    name: "İK Görüşme Zonu",
                    spaces: {
                      space_interview_b2: { id: "space_interview_b2", type: "space", parentId: "zone_hr", name: "B2 Mülakat Odası", area: 25 }
                    }
                  }
                }
              }
            }
          }
        }
      }
    };
  }

  // Recursive Entity Finder
  findEntity(entityId) {
    if (!entityId) return null;

    for (const projId in this.projects) {
      const proj = this.projects[projId];
      if (proj.id === entityId) return proj;

      for (const bldgId in proj.buildings) {
        const bldg = proj.buildings[bldgId];
        if (bldg.id === entityId) return bldg;

        for (const lvlId in bldg.levels) {
          const lvl = bldg.levels[lvlId];
          if (lvl.id === entityId) return lvl;

          for (const znId in lvl.zones) {
            const zn = lvl.zones[znId];
            if (zn.id === entityId) return zn;

            for (const spId in zn.spaces) {
              const sp = zn.spaces[spId];
              if (sp.id === entityId) return sp;
            }
          }
        }
      }
    }
    return null;
  }

  // Get full ancestor path for an entity
  getAncestors(entityId) {
    const ancestors = { project: null, building: null, level: null, zone: null, entity: null };
    const target = this.findEntity(entityId);
    if (!target) return ancestors;

    ancestors.entity = target;

    // Traverse upwards
    for (const projId in this.projects) {
      const proj = this.projects[projId];
      for (const bldgId in proj.buildings) {
        const bldg = proj.buildings[bldgId];
        for (const lvlId in bldg.levels) {
          const lvl = bldg.levels[lvlId];
          for (const znId in lvl.zones) {
            const zn = lvl.zones[znId];
            for (const spId in zn.spaces) {
              const sp = zn.spaces[spId];
              if (sp.id === entityId) {
                ancestors.project = proj;
                ancestors.building = bldg;
                ancestors.level = lvl;
                ancestors.zone = zn;
                return ancestors;
              }
            }
            if (zn.id === entityId) {
              ancestors.project = proj;
              ancestors.building = bldg;
              ancestors.level = lvl;
              return ancestors;
            }
          }
          if (lvl.id === entityId) {
            ancestors.project = proj;
            ancestors.building = bldg;
            return ancestors;
          }
        }
        if (bldg.id === entityId) {
          ancestors.project = proj;
          return ancestors;
        }
      }
    }
    return ancestors;
  }

  // Generate dynamic, room-name-independent Scope Title (Requirement 8)
  getScopeTitle(activeContext) {
    if (!activeContext) return "Genel Proje Bağlamı";

    const ancestors = this.getAncestors(activeContext.entityId || activeContext.levelId || activeContext.buildingId);
    const parts = [];

    if (ancestors.building && ancestors.building.name !== "Ana Konut Yapısı") {
      parts.push(ancestors.building.name);
    }
    if (ancestors.level) {
      parts.push(ancestors.level.name);
    }
    if (ancestors.zone && ancestors.zone.name !== "Ortak Yaşam Zonu" && ancestors.zone.name !== "Özel Gece Zonu") {
      parts.push(ancestors.zone.name);
    }
    if (ancestors.entity && ancestors.entity.type === "space") {
      parts.push(ancestors.entity.name);
    }

    if (parts.length === 0) {
      const proj = this.projects[activeContext.projectId];
      return proj ? proj.name : "Mimari Bağlam";
    }

    return parts.join(" / ");
  }
}

// Global Export
window.EntityHierarchy = EntityHierarchy;
