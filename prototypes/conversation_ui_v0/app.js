/**
 * BRIF.AI — Multi-Stage Architectural UX Prototype v3 Interaction Script
 *
 * Handles:
 * 1. Process Stepper Stage Navigation & Contextual Right Panel switching
 * 2. Stage 1 Chat Conversation & User Statement collection
 * 3. Stage 2 Visual Preferences (3 Comparative Rounds & Attribute Chips)
 * 4. Stage 3 Space Program (2 Floor Tabs & Spatial Relationship Graph)
 * 5. Stage 4 Draft Schematic Floor Plans (Inline SVG injection, floor views, room click reasoning)
 * 6. Qualitative Indicators, Plan Assumptions Simulation & User Inclination
 * 7. Architect View Toggle & Mobile Drawer Handling
 */

document.addEventListener('DOMContentLoaded', () => {

  // --------------------------------------------------------------------------
  // Data Repositories & State
  // --------------------------------------------------------------------------
  let currentStage = 1;
  let currentAlt = 'a'; // 'a' or 'b'
  let currentFloor = 'ground'; // 'ground' or 'upper'
  let isArchitectView = false;
  let selectedAttributes = new Set();
  let userInclination = null;

  // Cached Inline SVGs to prevent duplicate fetch calls
  const svgCache = {
    a: null,
    b: null
  };

  // Room Reasoning Knowledge Base (Requirements 5 & 8)
  const roomReasoningMap = {
    study: {
      title: 'Çalışma Odası — Neden Burada?',
      userStatement: 'Eşim evden çalışıyor, online toplantılar yapıyor.',
      visualAttr: 'Sessizlik ve gerektiğinde kapanabilmesi.',
      archInterp: 'Çalışma alanı ortak yaşama yakın ancak akustik olarak izole edilebilir olmalıdır.',
      altDiff: 'Alternatif A: Tam izole kapalı oda. Alternatif B: Kayar panelli esnek dönüşüm.',
      verifyTopic: 'Tam ayrışma ile esnek bağlantı arasındaki öncelik henüz kesinleşmedi.',
      sourceType: 'Doğrudan kullanıcı beyanı',
      sourceClass: 'user-said',
      confidence: 'Güven: Orta'
    },
    living: {
      title: 'Yaşam Alanı (Salon) — Neden Burada?',
      userStatement: 'Öğleden sonra 16:00 sonrası çocuklar okuldan gelince yoğun kullanılıyor.',
      visualAttr: 'Ferahlık, gün ışığı ve peyzaj teras teması.',
      archInterp: 'Güney cephesinde terasla bütünleşen ana aile toplanma alanı.',
      altDiff: 'Alternatif A: Çalışma alanından bağımsız. Alternatif B: Çalışma alanına kayar panelle açılan akış.',
      verifyTopic: 'Mutfak ile açık/kapı ilişkisi netleştirilecek.',
      sourceType: 'Doğrudan kullanıcı beyanı',
      sourceClass: 'user-said',
      confidence: 'Güven: Yüksek'
    },
    kitchen: {
      title: 'Mutfak ve Yemek — Neden Burada?',
      userStatement: 'Günlük aile yemekleri ve hızlı bahçe servisi ihtiyacı.',
      visualAttr: 'Görsel bağlantı & koku/ses kontrolü.',
      archInterp: 'Zemin kat servis kanadında, teras ve salona doğrudan erişim.',
      altDiff: 'Alternatif A: Yarı-kontrollü bağımsız kurgu. Alternatif B: Açık ada mutfak kurgusu.',
      verifyTopic: 'Ada mutfak çevresi sirkülasyon genişliği.',
      sourceType: 'Kullanıcının görsel tercihi',
      sourceClass: 'pref-chip',
      confidence: 'Güven: Yüksek'
    },
    master: {
      title: 'Ebeveyn Yatak Odası — Neden Burada?',
      userStatement: 'Gece kuşağında sessizlik ve özel dinlenme alanı.',
      visualAttr: 'Mahremiyet ve özel banyo konforu.',
      archInterp: 'Üst katta çocuk odalarından merdiven holü ile ayrışan özel süit.',
      altDiff: 'Her iki alternatifte üst kat korunaklı cephede konumlanmıştır.',
      verifyTopic: 'Giyinme bölümünün banyo ile ilişkisi.',
      sourceType: 'Doğrudan kullanıcı beyanı',
      sourceClass: 'user-said',
      confidence: 'Güven: Yüksek'
    },
    kids: {
      title: 'Çocuk Odaları — Neden Burada?',
      userStatement: 'Çocuklar 16:00 sonrası odalarını çalışma ve oyun için kullanıyor.',
      visualAttr: 'Gün ışığı ve ortak banyo erişimi.',
      archInterp: 'Üst kat doğu/güney-doğu cephesinde ikiz çocuk alanı.',
      altDiff: 'Her iki alternatifte ortak banyo ve merdiven holüne hizalı.',
      verifyTopic: 'Gelecekte çalışma masası büyüme ihtiyacı.',
      sourceType: 'Doğrudan kullanıcı beyanı',
      sourceClass: 'user-said',
      confidence: 'Güven: Yüksek'
    },
    entry: {
      title: 'Giriş ve Vestiyer — Neden Burada?',
      userStatement: 'Dört kişilik aile ayakkabı/mont ve okul çantası depolama.',
      visualAttr: 'Mahremiyet süzgeci ve düzen.',
      archInterp: 'Rüzgarlık ve vestiyer tamponu sağlayan ana giriş düğümü.',
      altDiff: 'Zemin kat kuzey/kuzey-doğu aksında konumlandırılmıştır.',
      verifyTopic: 'Ayakkabılık depolama hacmi yeterliliği.',
      sourceType: 'Prototip varsayımı',
      sourceClass: 'proto-assump',
      confidence: 'Güven: Yüksek'
    },
    terrace: {
      title: 'Peyzaj Terası — Neden Burada?',
      userStatement: 'Salondan bahçeye doğrudan geçiş ve dış mekân kullanımı.',
      visualAttr: 'Ferahlık ve gün ışığı.',
      archInterp: 'Salona doğrudan bağlı açık dış mekân yaşama platformu.',
      altDiff: 'Açık alandır, kapalı brüt toplama eklenmez.',
      verifyTopic: 'Teras üstü gölgelendirme elemanı tercihi.',
      sourceType: 'Kullanıcının görsel tercihi',
      sourceClass: 'pref-chip',
      confidence: 'Güven: Orta'
    }
  };

  // --------------------------------------------------------------------------
  // DOM References
  // --------------------------------------------------------------------------
  const stepNodes = document.querySelectorAll('.step-node');
  const stageViews = document.querySelectorAll('.stage-view');
  
  const toggleViewBtn = document.getElementById('toggleViewBtn');
  const toggleBtnText = document.getElementById('toggleBtnText');
  const architectStageView = document.getElementById('architectStageView');

  const panelTitle = document.getElementById('panelTitle');
  const panelSubtitle = document.getElementById('panelSubtitle');
  const panelStage1 = document.getElementById('panelStage1');
  const panelStage2 = document.getElementById('panelStage2');
  const panelStage3 = document.getElementById('panelStage3');
  const panelStage4 = document.getElementById('panelStage4');

  const drawerHandleBar = document.getElementById('drawerHandleBar');
  const contextualPanel = document.getElementById('contextualPanel');

  // Stage 1 Chat
  const chatMessages = document.getElementById('chatMessages');
  const suggestionChips = document.getElementById('suggestionChips');
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const voiceBtn = document.getElementById('voiceBtn');

  // Stage 2 Visual Preferences
  const roundTabs = document.querySelectorAll('.round-tab');
  const prefRoundContainers = document.querySelectorAll('.pref-round-container');
  const selectedChipsSummary = document.getElementById('selectedChipsSummary');
  const btnNextToProgram = document.getElementById('btnNextToProgram');

  // Stage 3 Space Program
  const floorTabGround = document.getElementById('floorTabGround');
  const floorTabUpper = document.getElementById('floorTabUpper');
  const spacesGround = document.getElementById('spacesGround');
  const spacesUpper = document.getElementById('spacesUpper');
  const stage3PanelCards = document.getElementById('stage3PanelCards');

  // Stage 4 Plan & Alternatives
  const btnAltA = document.getElementById('btnAltA');
  const btnAltB = document.getElementById('btnAltB');
  const planFloorGroundBtn = document.getElementById('planFloorGroundBtn');
  const planFloorUpperBtn = document.getElementById('planFloorUpperBtn');
  const planSvgContainer = document.getElementById('planSvgContainer');
  const openAssumptionsBtn = document.getElementById('openAssumptionsBtn');
  const assumptionsModal = document.getElementById('assumptionsModal');
  const closeAssumptionsBtn = document.getElementById('closeAssumptionsBtn');
  const assumptionsForm = document.getElementById('assumptionsForm');

  // Accordion for Past Rationale
  const togglePastRationaleBtn = document.getElementById('togglePastRationaleBtn');
  const pastRationaleContent = document.getElementById('pastRationaleContent');

  // --------------------------------------------------------------------------
  // 1. Process Stepper Navigation & Stage Switching (Requirement 1 & 8)
  // --------------------------------------------------------------------------
  stepNodes.forEach(node => {
    node.addEventListener('click', () => {
      const targetStage = parseInt(node.dataset.stage, 10);
      switchStage(targetStage);
    });
  });

  function switchStage(stageNum) {
    if (isArchitectView) {
      toggleArchitectView(false);
    }

    currentStage = stageNum;

    // Update Stepper Bar UI
    stepNodes.forEach(node => {
      const num = parseInt(node.dataset.stage, 10);
      node.classList.remove('active');
      const badge = node.querySelector('.step-badge');

      if (num === stageNum) {
        node.classList.add('active');
        if (badge) {
          badge.className = 'step-badge badge-active';
          badge.textContent = 'Aktif';
        }
      } else if (num < stageNum) {
        node.classList.add('completed');
        if (badge) {
          badge.className = 'step-badge badge-completed';
          badge.textContent = 'Tamamlandı';
        }
      } else {
        if (badge) {
          badge.className = 'step-badge badge-pending';
          badge.textContent = num === 2 ? '3 Tur' : (num === 3 ? '2 Katlı' : 'Şematik');
        }
      }
    });

    // Update Main Stage Views
    stageViews.forEach(view => {
      view.classList.add('hidden');
      view.classList.remove('active');
    });

    const activeView = document.getElementById(`stageView${stageNum}`);
    if (activeView) {
      activeView.classList.remove('hidden');
      activeView.classList.add('active');
    }

    // Update Contextual Right Panel Content & Titles (Requirements 1 & 8)
    updateRightPanelForStage(stageNum);

    // If Stage 4, load plan SVG inline
    if (stageNum === 4) {
      loadPlanSvg(currentAlt, currentFloor);
    }
  }

  function updateRightPanelForStage(stageNum) {
    // Hide all panel stage containers
    [panelStage1, panelStage2, panelStage3, panelStage4].forEach(el => el.classList.add('hidden'));

    if (stageNum === 1) {
      panelTitle.textContent = 'Sizi nasıl anladım?';
      panelSubtitle.textContent = 'Sohbetten elde edilen günlük yaşam bulguları';
      panelStage1.classList.remove('hidden');
    } else if (stageNum === 2) {
      panelTitle.textContent = 'Görsellerden ne anladım?';
      panelSubtitle.textContent = 'Seçilen mekânsal nitelikler ve tercihler';
      panelStage2.classList.remove('hidden');
    } else if (stageNum === 3) {
      panelTitle.textContent = 'Program kararlarının dayanakları';
      panelSubtitle.textContent = 'Mekân ve ilişki düğümü detayları';
      panelStage3.classList.remove('hidden');
    } else if (stageNum === 4) {
      panelTitle.textContent = 'Planı neden böyle kurduk?';
      panelSubtitle.textContent = 'Seçili mekânın mimari dayanakları';
      panelStage4.classList.remove('hidden');
    }
  }

  // --------------------------------------------------------------------------
  // 2. Stage 1 Chat Conversation Logic
  // --------------------------------------------------------------------------
  if (suggestionChips) {
    suggestionChips.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip-btn');
      if (!chip) return;
      const replyText = chip.dataset.reply || chip.textContent.trim();
      handleUserSendMessage(replyText);
    });
  }

  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = userInput.value.trim();
      if (!text) return;
      handleUserSendMessage(text);
      userInput.value = '';
    });
  }

  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      alert('🎤 Sesli yanıt simülasyonu: "Eşim evden çalışıyor, toplantılar için tam ses izolasyonu çok kritik." mesajı yazıldı.');
      userInput.value = 'Eşim evden çalışıyor, toplantılar için tam ses izolasyonu çok kritik.';
    });
  }

  function handleUserSendMessage(messageText) {
    if (suggestionChips) suggestionChips.style.display = 'none';
    appendChatMessage('user', 'Siz', 'MK', messageText);

    setTimeout(() => {
      appendChatMessage('brif', 'BRIF.AI Mimari Danışman', 'B', `Anladım: "${messageText}". Bu beyanı ve ihtiyaçlarınızı not aldım. İkinci aşamada görsel tercihler üzerinden mekan kalitelerini netleştireceğiz.`);
    }, 600);
  }

  function appendChatMessage(type, sender, avatar, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type === 'user' ? 'user-message' : 'ai-message'}`;
    msgDiv.innerHTML = `
      <div class="message-avatar ${type === 'user' ? 'user' : 'brif'}">${avatar}</div>
      <div class="message-content">
        <div class="message-sender">${sender}</div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // --------------------------------------------------------------------------
  // 3. Stage 2 Visual Preferences (3 Comparative Rounds & Attribute Chips - Requirement 2 & 9)
  // --------------------------------------------------------------------------
  roundTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const rNum = parseInt(tab.dataset.round, 10);
      switchPrefRound(rNum);
    });
  });

  function switchPrefRound(rNum) {
    roundTabs.forEach(tab => tab.classList.remove('active'));
    prefRoundContainers.forEach(cont => cont.classList.add('hidden'));

    document.getElementById(`roundTab${rNum}`).classList.add('active');
    document.getElementById(`prefRound${rNum}`).classList.remove('hidden');
  }

  // Primary Buttons & Secondary Links on Cards
  document.querySelectorAll('.pref-card-large').forEach(card => {
    const chipSection = card.querySelector('.attribute-chip-section');
    const primaryBtns = card.querySelectorAll('.pref-card-actions button');
    const dislikeLink = card.querySelector('.pref-link-dislike');

    primaryBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        card.classList.remove('selected-like', 'selected-dislike');

        if (action === 'like') {
          card.classList.add('selected-like');
        } else if (action === 'neutral') {
          // Requirement 9: "Kararsızım" selected -> system creates "Teyit gerekli"
        }

        if (chipSection) chipSection.classList.remove('hidden');
      });
    });

    if (dislikeLink) {
      dislikeLink.addEventListener('click', () => {
        card.classList.remove('selected-like');
        card.classList.add('selected-dislike');
      });
    }

    // Attribute Chips Click Listeners
    const chips = card.querySelectorAll('.attr-chip');
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('selected');
        const attrVal = chip.dataset.attr;

        if (chip.classList.contains('selected')) {
          selectedAttributes.add(attrVal);
        } else {
          selectedAttributes.delete(attrVal);
        }

        updateSelectedChipsSummary();
      });
    });
  });

  function updateSelectedChipsSummary() {
    if (!selectedChipsSummary) return;
    selectedChipsSummary.innerHTML = '';

    if (selectedAttributes.size === 0) {
      selectedChipsSummary.innerHTML = '<span class="summary-chip">Sessizlik</span><span class="summary-chip">Gerektiğinde kapanabilmesi</span>';
      return;
    }

    selectedAttributes.forEach(attr => {
      const span = document.createElement('span');
      span.className = 'summary-chip';
      span.textContent = attr;
      selectedChipsSummary.appendChild(span);
    });
  }

  if (btnNextToProgram) {
    btnNextToProgram.addEventListener('click', () => {
      switchStage(3);
    });
  }

  // --------------------------------------------------------------------------
  // 4. Stage 3 Space Program & Spatial Relationship Graph (Requirements 4 & 5)
  // --------------------------------------------------------------------------
  floorTabGround.addEventListener('click', () => {
    floorTabGround.classList.add('active');
    floorTabUpper.classList.remove('active');
    spacesGround.classList.remove('hidden');
    spacesGround.classList.add('active');
    spacesUpper.classList.add('hidden');
    spacesUpper.classList.remove('active');
  });

  floorTabUpper.addEventListener('click', () => {
    floorTabUpper.classList.add('active');
    floorTabGround.classList.remove('active');
    spacesUpper.classList.remove('hidden');
    spacesUpper.classList.add('active');
    spacesGround.classList.add('hidden');
    spacesGround.classList.remove('active');
  });

  // Space Card Clicks in Stage 3 -> Right Panel Update
  document.querySelectorAll('.space-card').forEach(card => {
    card.addEventListener('click', () => {
      const spaceId = card.dataset.spaceId;
      const spaceTitle = card.querySelector('.space-title').textContent;
      const spaceMeta = card.querySelector('.space-meta').textContent;

      if (stage3PanelCards) {
        stage3PanelCards.innerHTML = `
          <div class="insight-card highlight-card">
            <div class="insight-card-header">
              <span class="source-badge user-said">Doğrudan kullanıcı beyanı</span>
              <span class="conf-badge high">Güven: Yüksek</span>
            </div>
            <h4 class="insight-card-title">${escapeHtml(spaceTitle)}</h4>
            <p class="insight-card-desc"><strong>Metraj:</strong> ${escapeHtml(spaceMeta)}</p>
            <p class="insight-card-desc"><strong>Mimari Nitelik:</strong> Aile ritmi ve erişilebilirlik gereksinimine uygun ön değerlendirme.</p>
          </div>
        `;
      }
    });
  });

  // Spatial Relationship Diagram Node Clicks
  document.querySelectorAll('.rel-node-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const relKey = btn.dataset.rel;
      let relText = '';

      if (relKey === 'rel_work_living') {
        relText = 'Çalışma ↔ Salon: Online toplantı sessizliği için akustik ayrışma öncelikli; kayar panel seçeneğinde esnek bağlantı olası.';
      } else if (relKey === 'rel_kitchen_living') {
        relText = 'Mutfak ↔ Salon: Açık ada mutfak sosyal teması artırırken sürgülü cam kapı koku/ses kontrolü sağlar.';
      } else if (relKey === 'rel_stair_vertical') {
        relText = 'Merdiven (Zemin ↕ Üst): Zemin kat gündüz yaşama alanı ile üst kat gece mahremiyet alanı arasındaki düşey geçiş düğümü.';
      } else {
        relText = 'Ebeveyn ↔ Çocuk Odaları: Üst katta merdiven holü ile sağlanan akustik ve mahremiyet mesafesi.';
      }

      if (stage3PanelCards) {
        stage3PanelCards.innerHTML = `
          <div class="insight-card highlight-card">
            <div class="insight-card-header">
              <span class="source-badge sys-interp">Sistem yorumu</span>
              <span class="conf-badge high">Güven: Yüksek</span>
            </div>
            <h4 class="insight-card-title">İlişki Kararı Analizi</h4>
            <p class="insight-card-desc">${relText}</p>
          </div>
        `;
      }
    });
  });

  // --------------------------------------------------------------------------
  // 5. Stage 4 Plan SVGs Fetch, Inline Injection & Room Interactions (Requirements 1, 2, 6, 7)
  // --------------------------------------------------------------------------
  btnAltA.addEventListener('click', () => {
    btnAltA.classList.add('active');
    btnAltB.classList.remove('active');
    currentAlt = 'a';
    loadPlanSvg('a', currentFloor);
  });

  btnAltB.addEventListener('click', () => {
    btnAltB.classList.add('active');
    btnAltA.classList.remove('active');
    currentAlt = 'b';
    loadPlanSvg('b', currentFloor);
  });

  planFloorGroundBtn.addEventListener('click', () => {
    planFloorGroundBtn.classList.add('active');
    planFloorUpperBtn.classList.remove('active');
    currentFloor = 'ground';
    switchSvgFloorView('ground');
  });

  planFloorUpperBtn.addEventListener('click', () => {
    planFloorUpperBtn.classList.add('active');
    planFloorGroundBtn.classList.remove('active');
    currentFloor = 'upper';
    switchSvgFloorView('upper');
  });

  async function loadPlanSvg(alt, floor) {
    if (!planSvgContainer) return;

    try {
      if (!svgCache[alt]) {
        const url = alt === 'a' ? 'assets/plans/alternative_a.svg' : 'assets/plans/alternative_b.svg';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        svgCache[alt] = await res.text();
      }

      // Inject Inline SVG (Requirement 1)
      planSvgContainer.innerHTML = svgCache[alt];

      // Switch Floor View inside SVG (<g data-floor-view="ground/upper">)
      switchSvgFloorView(floor);

      // Attach Interactions to [data-room] elements (Requirement 1)
      attachRoomSvgListeners();

    } catch (err) {
      console.error('Plan SVG Yükleme Hatası:', err);
      planSvgContainer.innerHTML = `<div class="error-box">Plan yüklenemedi: ${escapeHtml(err.message)}</div>`;
    }
  }

  function switchSvgFloorView(floor) {
    const svgEl = planSvgContainer.querySelector('svg');
    if (!svgEl) return;

    const groundGroup = svgEl.querySelector('[data-floor-view="ground"]');
    const upperGroup = svgEl.querySelector('[data-floor-view="upper"]');

    if (groundGroup && upperGroup) {
      if (floor === 'ground') {
        groundGroup.style.display = 'block';
        upperGroup.style.display = 'none';
      } else {
        groundGroup.style.display = 'none';
        upperGroup.style.display = 'block';
      }
    }
  }

  function attachRoomSvgListeners() {
    const svgEl = planSvgContainer.querySelector('svg');
    if (!svgEl) return;

    const interactiveRooms = svgEl.querySelectorAll('[data-room]');

    interactiveRooms.forEach(roomEl => {
      // Accessibility attributes
      if (!roomEl.getAttribute('tabindex')) roomEl.setAttribute('tabindex', '0');
      if (!roomEl.getAttribute('role')) roomEl.setAttribute('role', 'button');

      const roomKey = roomEl.dataset.room;

      // Event listener for click
      roomEl.addEventListener('click', (e) => {
        e.stopPropagation();
        selectRoom(roomEl, roomKey);
      });

      // Keyboard navigation: Enter or Space key (Requirement 1)
      roomEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectRoom(roomEl, roomKey);
        }
      });
    });
  }

  function selectRoom(roomEl, roomKey) {
    // Remove previous selection styling
    const svgEl = planSvgContainer.querySelector('svg');
    if (svgEl) {
      svgEl.querySelectorAll('.room-shape').forEach(el => el.classList.remove('selected'));
    }

    roomEl.classList.add('selected');

    // Update Right Panel with Room Reasoning (Requirements 5 & 8)
    const reasoning = roomReasoningMap[roomKey] || roomReasoningMap['study'];

    document.getElementById('roomReasoningTitle').textContent = reasoning.title;
    document.getElementById('roomUserStatement').textContent = reasoning.userStatement;
    document.getElementById('roomVisualAttr').textContent = reasoning.visualAttr;
    document.getElementById('roomArchInterp').textContent = reasoning.archInterp;
    document.getElementById('roomAltDiff').textContent = reasoning.altDiff;
    document.getElementById('roomVerifyTopic').textContent = reasoning.verifyTopic;

    const sourceBadge = document.getElementById('roomSourceType');
    if (sourceBadge) {
      sourceBadge.textContent = reasoning.sourceType;
      sourceBadge.className = `source-badge ${reasoning.sourceClass}`;
    }

    const confBadge = document.getElementById('roomConfidence');
    if (confBadge) {
      confBadge.textContent = reasoning.confidence;
    }
  }

  // --------------------------------------------------------------------------
  // 6. Plan Assumptions Simulation Modal (Requirement 10)
  // --------------------------------------------------------------------------
  if (openAssumptionsBtn && assumptionsModal) {
    openAssumptionsBtn.addEventListener('click', () => {
      assumptionsModal.classList.remove('hidden');
    });
  }

  if (closeAssumptionsBtn && assumptionsModal) {
    closeAssumptionsBtn.addEventListener('click', () => {
      assumptionsModal.classList.add('hidden');
    });
  }

  if (assumptionsForm) {
    assumptionsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const studyPriority = document.getElementById('assumpStudy').value;

      if (studyPriority === 'flexible') {
        // Highlight Alt B
        btnAltB.click();
        alert('⚙️ Varsayım Güncellendi: Esnek dönüşüm önceliğine göre Alternatif B (Esnek Bağlantı) öne çıkarıldı.');
      } else {
        // Highlight Alt A
        btnAltA.click();
        alert('⚙️ Varsayım Güncellendi: Akustik izolasyon önceliğine göre Alternatif A (Kontrollü Ayrışma) öne çıkarıldı.');
      }

      assumptionsModal.classList.add('hidden');
    });
  }

  // User Inclination Buttons
  document.querySelectorAll('.inc-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.inc-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      userInclination = btn.dataset.inc;

      const incStatus = document.getElementById('inclinationStatus');
      if (incStatus) {
        incStatus.textContent = `Kullanıcı eğilimi kaydedildi (${btn.textContent}) — nihai tasarım kararı değildir.`;
      }
    });
  });

  // Accordion for Past Rationale
  if (togglePastRationaleBtn && pastRationaleContent) {
    togglePastRationaleBtn.addEventListener('click', () => {
      pastRationaleContent.classList.toggle('hidden');
    });
  }

  // --------------------------------------------------------------------------
  // 7. Architect View Toggle Mode
  // --------------------------------------------------------------------------
  if (toggleViewBtn) {
    toggleViewBtn.addEventListener('click', () => {
      toggleArchitectView(!isArchitectView);
    });
  }

  function toggleArchitectView(showArch) {
    isArchitectView = showArch;

    if (showArch) {
      stageViews.forEach(v => v.classList.add('hidden'));
      architectStageView.classList.remove('hidden');
      toggleBtnText.textContent = 'Müşteri Görünümüne Dön';

      panelTitle.textContent = 'Doğrulanmış brief ve güven durumu';
      panelSubtitle.textContent = 'Mimarlar için sentezlenmiş veriler';
    } else {
      architectStageView.classList.add('hidden');
      toggleBtnText.textContent = 'Mimar Önizlemesine Geç';
      switchStage(currentStage);
    }
  }

  // --------------------------------------------------------------------------
  // 8. Mobile Drawer Handle Toggle (<1024px)
  // --------------------------------------------------------------------------
  if (drawerHandleBar && contextualPanel) {
    drawerHandleBar.addEventListener('click', () => {
      contextualPanel.classList.toggle('drawer-open');
    });
  }

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------
  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, match => {
      const escapeMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      };
      return escapeMap[match];
    });
  }

});
