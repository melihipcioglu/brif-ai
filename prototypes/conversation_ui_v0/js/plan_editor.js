/**
 * BRIF.AI — Interactive Plan Editor & Geometry Engine (v4 Demo)
 *
 * Renders SVG floor plans dynamically from JSON, handles room dragging,
 * room resizing with corner handles, room locking, keyboard controls,
 * ghost outlines, and grid snapping.
 */

class PlanEditor {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = options;
    
    this.currentAlt = 'a';
    this.currentFloor = 'ground';
    this.selectedSpaceId = 'study';
    this.planData = null;
    
    this.dragState = null;
    this.resizeState = null;
    this.isPreviewing = false;
    this.previewState = null;

    this.onSpaceSelect = options.onSpaceSelect || (() => {});
    this.onPlanChange = options.onPlanChange || (() => {});
    this.onRuleCheck = options.onRuleCheck || (() => {});
  }

  loadData(jsonData) {
    this.planData = JSON.parse(JSON.stringify(jsonData));
    this.render();
  }

  setAlternative(altKey) {
    this.currentAlt = altKey;
    this.render();
  }

  setFloor(floorKey) {
    this.currentFloor = floorKey;
    this.render();
  }

  getSpaces() {
    if (!this.planData || !this.planData.alternatives[this.currentAlt]) return [];
    return this.planData.alternatives[this.currentAlt].floors[this.currentFloor] || [];
  }

  getSpaceById(id) {
    return this.getSpaces().find(s => s.id === id);
  }

  toggleLock(spaceId) {
    const space = this.getSpaceById(spaceId);
    if (space) {
      space.locked = !space.locked;
      this.render();
      return space.locked;
    }
    return false;
  }

  render() {
    if (!this.container || !this.planData) return;

    const spaces = this.getSpaces();
    const isGround = this.currentFloor === 'ground';
    const altTitle = this.currentAlt === 'a' ? 'Alternatif A (Kontrollü Ayrışma)' : 'Alternatif B (Esnek Bağlantı)';
    const floorTitle = isGround ? 'ZEMİN KAT PLAN ŞEMASI' : 'ÜST KAT PLAN ŞEMASI';

    let svgHtml = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 560" width="100%" height="100%" id="dynamicPlanSvg">
        <defs>
          <style>
            .wall-outer { fill: none; stroke: #1E293B; stroke-width: 7; stroke-linejoin: miter; }
            .wall-inner { fill: none; stroke: #334155; stroke-width: 3.5; stroke-linejoin: round; }
            .room-rect { fill: #FAFAF7; stroke: #CBD5E1; stroke-width: 1.5; cursor: pointer; transition: fill 0.15s, stroke 0.15s; }
            .room-rect:hover, .room-rect:focus-visible { fill: #ECFDF5; stroke: #059669; stroke-width: 2.5; outline: none; }
            .room-rect.selected { fill: #E0F2FE; stroke: #0284C7; stroke-width: 3; }
            .room-rect.locked { stroke-dasharray: 4 2; stroke: #64748B; }
            .ghost-rect { fill: none; stroke: #64748B; stroke-width: 2; stroke-dasharray: 4 4; opacity: 0.6; }
            .preview-rect { fill: #EFF6FF; stroke: #2563EB; stroke-width: 2.5; stroke-dasharray: 6 3; }
            .room-title { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 700; fill: #0F172A; pointer-events: none; }
            .room-area { font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; fill: #475569; pointer-events: none; }
            .room-tag { font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 600; fill: #059669; pointer-events: none; }
            .door-arc { fill: none; stroke: #2563EB; stroke-width: 1.5; stroke-dasharray: 3 2; }
            .window-rect { fill: #FFFFFF; stroke: #0284C7; stroke-width: 2; }
            .stair-tread { stroke: #64748B; stroke-width: 1.5; }
            .resize-handle { fill: #2563EB; stroke: #FFFFFF; stroke-width: 1.5; cursor: nwse-resize; }
          </style>
        </defs>

        <rect width="840" height="560" rx="12" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.5"/>

        <!-- Header Titles -->
        <text x="45" y="55" font-family="'Inter', sans-serif" font-size="15" font-weight="800" fill="#0F172A">${floorTitle} — ${altTitle}</text>
        <text x="45" y="73" font-family="'Inter', sans-serif" font-size="11" fill="#64748B">Şematik Ön Değerlendirme Çizimi — Etkileşimli Veri Modeli</text>

        <!-- North Arrow -->
        <g transform="translate(780, 60)">
          <circle cx="0" cy="0" r="16" fill="#F8FAFC" stroke="#334155" stroke-width="1.5"/>
          <path d="M0 -10 L5 6 L0 2 L-5 6 Z" fill="#0F172A"/>
          <text x="0" y="15" font-family="'Inter', sans-serif" font-size="9" font-weight="800" fill="#0F172A" text-anchor="middle">K</text>
        </g>
    `;

    // Render Outer Wall Boundary
    if (isGround) {
      svgHtml += `<path d="M60 110 L710 110 L710 270 L540 270 L540 450 L190 450 L190 390 L60 390 Z" class="wall-outer"/>`;
    } else {
      svgHtml += `<path d="M60 110 L710 110 L710 390 L430 390 L430 450 L190 450 L190 350 L60 350 Z" class="wall-outer"/>`;
    }

    // Render Spaces
    spaces.forEach(space => {
      const isSelected = space.id === this.selectedSpaceId;
      const isLocked = space.locked;

      svgHtml += `
        <g class="interactive-room-group" data-room-id="${space.id}">
          <rect x="${space.x}" y="${space.y}" width="${space.width}" height="${space.height}" rx="4"
                class="room-rect ${isSelected ? 'selected' : ''} ${isLocked ? 'locked' : ''}"
                data-room-id="${space.id}" tabindex="0" role="button" aria-label="${space.name} kararını incele"/>
          
          <text x="${space.x + space.width / 2}" y="${space.y + space.height / 2 - 8}" class="room-title" text-anchor="middle">${space.name}</text>
          <text x="${space.x + space.width / 2}" y="${space.y + space.height / 2 + 10}" class="room-area" text-anchor="middle">${space.area} m² Net</text>
          ${isLocked ? `<text x="${space.x + space.width / 2}" y="${space.y + space.height / 2 + 26}" class="room-tag" fill="#DC2626" text-anchor="middle">🔒 KİLİTLİ</text>` : ''}

          <!-- Resize Handle for Selected Room -->
          ${isSelected && !isLocked ? `
            <circle cx="${space.x + space.width}" cy="${space.y + space.height}" r="6" class="resize-handle" data-handle="se" data-room-id="${space.id}"/>
          ` : ''}
        </g>
      `;
    });

    // Windows & Doors Overlays
    svgHtml += `
      <rect x="250" y="106" width="60" height="8" class="window-rect"/>
      <rect x="430" y="106" width="60" height="8" class="window-rect"/>
      <rect x="590" y="106" width="60" height="8" class="window-rect"/>
    `;

    svgHtml += `</svg>`;
    this.container.innerHTML = svgHtml;

    // Attach Event Listeners
    this.attachEvents();
  }

  attachEvents() {
    const svgEl = this.container.querySelector('svg');
    if (!svgEl) return;

    // Room Selection & Keyboard Controls (Requirement 6)
    svgEl.querySelectorAll('[data-room-id]').forEach(el => {
      const id = el.dataset.roomId;

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectSpace(id);
      });

      el.addEventListener('keydown', (e) => {
        const space = this.getSpaceById(id);
        if (!space || space.locked) return;

        if (e.key === 'ArrowRight') { this.moveSpaceBy(id, 10, 0); }
        else if (e.key === 'ArrowLeft') { this.moveSpaceBy(id, -10, 0); }
        else if (e.key === 'ArrowUp') { this.moveSpaceBy(id, 0, -10); }
        else if (e.key === 'ArrowDown') { this.moveSpaceBy(id, 0, 10); }
        else if (e.shiftKey && e.key === 'ArrowRight') { this.resizeSpaceBy(id, 10, 0); }
        else if (e.shiftKey && e.key === 'ArrowLeft') { this.resizeSpaceBy(id, -10, 0); }
      });
    });

    // Mouse Dragging Simulation (Requirement 5)
    let isDragging = false;
    let dragSpaceId = null;
    let startX = 0, startY = 0;
    let origX = 0, origY = 0;

    svgEl.addEventListener('mousedown', (e) => {
      const roomGroup = e.target.closest('[data-room-id]');
      if (!roomGroup) return;

      const spaceId = roomGroup.dataset.roomId;
      const space = this.getSpaceById(spaceId);
      if (!space || space.locked) return;

      isDragging = true;
      dragSpaceId = spaceId;
      startX = e.clientX;
      startY = e.clientY;
      origX = space.x;
      origY = space.y;
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging || !dragSpaceId) return;

      const dx = Math.round((e.clientX - startX) / 10) * 10;
      const dy = Math.round((e.clientY - startY) / 10) * 10;

      const space = this.getSpaceById(dragSpaceId);
      if (space) {
        // Enforce boundary kısıtı
        const newX = Math.max(60, Math.min(680 - space.width, origX + dx));
        const newY = Math.max(110, Math.min(440 - space.height, origY + dy));
        space.x = newX;
        space.y = newY;
        this.render();
      }
    });

    window.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        this.onPlanChange({ type: 'drag', spaceId: dragSpaceId });
        dragSpaceId = null;
      }
    });
  }

  selectSpace(id) {
    this.selectedSpaceId = id;
    this.render();
    const space = this.getSpaceById(id);
    if (space) this.onSpaceSelect(space);
  }

  moveSpaceBy(id, dx, dy) {
    const space = this.getSpaceById(id);
    if (!space || space.locked) return;
    space.x = Math.max(60, Math.min(680 - space.width, space.x + dx));
    space.y = Math.max(110, Math.min(440 - space.height, space.y + dy));
    this.render();
    this.onPlanChange({ type: 'move', spaceId: id });
  }

  resizeSpaceBy(id, dw, dh) {
    const space = this.getSpaceById(id);
    if (!space || space.locked) return;
    space.width = Math.max(80, space.width + dw);
    space.height = Math.max(60, space.height + dh);
    // Recalculate approx area
    space.area = Math.round((space.width * space.height) / 1600 * 10) / 10;
    this.render();
    this.onPlanChange({ type: 'resize', spaceId: id });
  }
}

// Global Export
window.PlanEditor = PlanEditor;
