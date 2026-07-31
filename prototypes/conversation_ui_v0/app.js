/**
 * BRIF.AI - Multi-Stage Architectural UX Prototype v0 Interaction Script
 *
 * NOTE: Standalone frontend UX prototype for BRIF.AI.
 * Powers Stage Navigation, Visual Preference Analysis, Space Program & Relationship Graph,
 * Draft Plan Alternatives, and Dynamic Insight Synthesis.
 * Contains NO real backend, database, API, or AI model calls.
 */

document.addEventListener('DOMContentLoaded', () => {
  // --------------------------------------------------------------------------
  // DOM Element References
  // --------------------------------------------------------------------------
  const stepNodes = document.querySelectorAll('.step-node');
  const stageViews = document.querySelectorAll('.stage-view');

  const chatMessages = document.getElementById('chatMessages');
  const suggestionChips = document.getElementById('suggestionChips');
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const voiceBtn = document.getElementById('voiceBtn');

  const toggleViewBtn = document.getElementById('toggleViewBtn');
  const toggleBtnText = document.getElementById('toggleBtnText');
  const panelTitle = document.getElementById('panelTitle');
  const panelSubtitle = document.getElementById('panelSubtitle');
  const clientView = document.getElementById('clientView');
  const architectView = document.getElementById('architectView');

  const routineCards = document.getElementById('routineCards');
  const interpretationCards = document.getElementById('interpretationCards');
  const pendingCards = document.getElementById('pendingCards');

  const toggleExtraRoutineBtn = document.getElementById('toggleExtraRoutineBtn');
  const extraRoutineItems = document.getElementById('extraRoutineItems');
  const routineCount = document.getElementById('routineCount');

  const confirmCorrectBtn = document.getElementById('confirmCorrectBtn');
  const confirmEditBtn = document.getElementById('confirmEditBtn');
  const confirmRejectBtn = document.getElementById('confirmRejectBtn');
  const confirmationText = document.getElementById('confirmationText');
  const inlineEditor = document.getElementById('inlineEditor');
  const editInput = document.getElementById('editInput');
  const cancelEditBtn = document.getElementById('cancelEditBtn');
  const saveEditBtn = document.getElementById('saveEditBtn');
  const confirmationActions = document.getElementById('confirmationActions');

  const btnNextToProgram = document.getElementById('btnNextToProgram');
  const btnAltA = document.getElementById('btnAltA');
  const btnAltB = document.getElementById('btnAltB');
  const planIframe = document.getElementById('planIframe');
  const archTendencyVal = document.getElementById('archTendencyVal');

  let isArchitectView = false;
  let isExtraRoutineExpanded = false;
  let currentStage = 1;

  // --------------------------------------------------------------------------
  // 1. Process Stepper Navigation
  // --------------------------------------------------------------------------
  stepNodes.forEach((node) => {
    node.addEventListener('click', () => {
      const targetStage = parseInt(node.dataset.stage, 10);
      switchStage(targetStage);
    });
  });

  function switchStage(stageNum) {
    currentStage = stageNum;

    // Update Stepper Nodes UI
    stepNodes.forEach((node) => {
      const num = parseInt(node.dataset.stage, 10);
      node.classList.remove('active');
      const badge = node.querySelector('.step-badge');

      if (num === stageNum) {
        node.classList.add('active');
        if (badge) {
          badge.className = 'step-badge badge-active';
          badge.textContent = 'Devam ediyor';
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
          badge.textContent = 'Henüz başlamadı';
        }
      }
    });

    // Update Stage Views Display
    stageViews.forEach((view) => {
      view.classList.add('hidden');
      view.classList.remove('active');
    });

    const activeView = document.getElementById(`stageView${stageNum}`);
    if (activeView) {
      activeView.classList.remove('hidden');
      activeView.classList.add('active');
    }
  }

  if (btnNextToProgram) {
    btnNextToProgram.addEventListener('click', () => {
      switchStage(3);
    });
  }

  // --------------------------------------------------------------------------
  // 2. Stage 1 Chat Conversation Dynamics
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

    userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  }

  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      alert('🎤 Sesli yanıt alma demosu: Konuşmanız simüle edilmektedir...');
      userInput.value = 'Eşim gün boyu online toplantılar yapıyor, tam ses izolasyonu çok kritik.';
    });
  }

  function handleUserSendMessage(messageText) {
    if (suggestionChips) suggestionChips.style.display = 'none';

    appendMessage('user', 'Siz', 'MK', messageText);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    setTimeout(() => {
      generateSoundAiResponse(messageText);
    }, 600);
  }

  function appendMessage(senderType, senderName, avatarText, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${senderType}-message`;

    msgDiv.innerHTML = `
      <div class="message-avatar ${senderType === 'user' ? 'user' : 'brif'}">${avatarText}</div>
      <div class="message-content">
        <div class="message-sender">${senderName}</div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function generateSoundAiResponse(userText) {
    let aiReply = '';
    let newCard = null;

    if (userText.includes('toplantı') || userText.includes('izolasyon') || userText.includes('ses')) {
      aiReply = 'Akustik mahremiyet ihtiyacının önemli olduğunu anlıyorum. Eşinizin toplantıları sırasında evdeki diğer seslerin çalışma alanına ulaşması mı, yoksa içerideki sesin dışarı çıkmaması mı daha öncelikli? Bu ihtiyaç ileride mimarın değerlendireceği mekânsal ve akustik kararlara dönüşebilir.';
      
      newCard = {
        group: 'routine',
        title: 'Çalışma alanında yoğun ses izolasyonu talebi',
        badge: 'Kullanıcı söyledi',
        badgeClass: 'badge-user-said',
        rationale: `"${userText}"`
      };
    } else {
      aiReply = `İfade ettiğiniz konuyu not aldım: "${userText}". Bu durumun hane içi diğer kullanım alışkanlıklarıyla uyumunu değerlendireceğiz. Ayrıntıları netleştirmek için ikinci aşamadaki Görsel Tercihler bölümüne geçebiliriz.`;
      
      newCard = {
        group: 'routine',
        title: 'Kullanıcı beyanı eklendi',
        badge: 'Kullanıcı söyledi',
        badgeClass: 'badge-user-said',
        rationale: `"${userText}"`
      };
    }

    appendMessage('ai', 'BRIF.AI Mimari Danışman', 'B', aiReply);
    if (newCard) addGroundedCard(newCard);
  }

  function addGroundedCard(cardData) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'insight-card';
    if (cardData.badgeClass === 'badge-system') cardDiv.classList.add('highlight-system');

    cardDiv.innerHTML = `
      <div class="card-top">
        <span class="card-text">${escapeHtml(cardData.title)}</span>
        <span class="badge ${cardData.badgeClass}">${escapeHtml(cardData.badge)}</span>
      </div>
      <div class="card-rationale">
        <span class="rationale-label">Dayanak:</span> ${escapeHtml(cardData.rationale)}
      </div>
    `;

    if (cardData.group === 'routine') {
      routineCards.insertBefore(cardDiv, routineCards.firstChild);
    } else if (cardData.group === 'interpretation') {
      interpretationCards.insertBefore(cardDiv, interpretationCards.firstChild);
    } else {
      pendingCards.insertBefore(cardDiv, pendingCards.firstChild);
    }
  }

  // --------------------------------------------------------------------------
  // 3. Stage 2 Visual Preference Cards Interactions
  // --------------------------------------------------------------------------
  const prefCards = document.querySelectorAll('.pref-card');
  prefCards.forEach((card) => {
    const actions = card.querySelectorAll('.pref-action-btn');
    const selector = card.querySelector('.attribute-selector');
    const title = card.querySelector('.pref-card-title').textContent.trim();

    actions.forEach((btn) => {
      btn.addEventListener('click', () => {
        actions.forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');

        const actionType = btn.dataset.action;
        if (actionType === 'like') {
          if (selector) selector.classList.remove('hidden');
          addGroundedCard({
            group: 'interpretation',
            title: `Görsel Tercih: ${title} örneği uygun bulundu`,
            badge: 'Sistem yorumu',
            badgeClass: 'badge-system',
            rationale: `Kullanıcı "${title}" örneğini "Bana uygun" olarak işaretledi.`
          });
        } else {
          if (selector) selector.classList.add('hidden');
        }
      });
    });

    // Attribute Chips
    const attrChips = card.querySelectorAll('.attr-chip');
    attrChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('selected');
        const attrVal = chip.dataset.attr;

        addGroundedCard({
          group: 'interpretation',
          title: `Mekânsal Nitelik: "${attrVal}" öne çıkarıldı`,
          badge: 'Sistem yorumu',
          badgeClass: 'badge-system',
          rationale: `Kullanıcı "${title}" görselinde "${attrVal}" özelliğini seçti.`
        });
      });
    });
  });

  // --------------------------------------------------------------------------
  // 4. Stage 3 Space Program & Relationship Diagram Interactions
  // --------------------------------------------------------------------------
  const spaceCards = document.querySelectorAll('.space-card');
  spaceCards.forEach((scard) => {
    const sbtns = scard.querySelectorAll('.space-btn');
    const sname = scard.querySelector('.space-name').textContent;

    sbtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        if (action === 'remove') {
          scard.style.opacity = '0.4';
          scard.style.textDecoration = 'line-through';
          btn.textContent = 'Çıkarılması istendi';
          addGroundedCard({
            group: 'routine',
            title: `Mekân Çıkarma Talebi: ${sname}`,
            badge: 'Kullanıcı söyledi',
            badgeClass: 'badge-user-said',
            rationale: `Kullanıcı ${sname} alanının programdan çıkarılmasını istedi.`
          });
        } else if (action === 'size-up') {
          alert(`📐 ${sname} alanı tahmini boyutu artırıldı.`);
        } else if (action === 'size-down') {
          alert(`📐 ${sname} alanı tahmini boyutu azaltıldı.`);
        }
      });
    });
  });

  // Relationship SVG Nodes Interactivity
  const relNodes = document.querySelectorAll('.rel-node');
  relNodes.forEach((rnode) => {
    rnode.addEventListener('click', () => {
      const nodeName = rnode.dataset.node;
      addGroundedCard({
        group: 'interpretation',
        title: `Mekânsal İlişki İncelemesi: ${nodeName.toUpperCase()}`,
        badge: 'Sistem yorumu',
        badgeClass: 'badge-system',
        rationale: `Diyagramda ${nodeName} odağı seçildi; diğer mekânlarla akustik ve görsel bağları analiz ediliyor.`
      });
    });
  });

  // --------------------------------------------------------------------------
  // 5. Stage 4 Draft Plan Alternatives & Preference Tracking
  // --------------------------------------------------------------------------
  if (btnAltA && btnAltB && planIframe) {
    btnAltA.addEventListener('click', () => {
      btnAltA.classList.add('active');
      btnAltB.classList.remove('active');
      planIframe.src = 'assets/plans/alternative_a.svg';
    });

    btnAltB.addEventListener('click', () => {
      btnAltB.classList.add('active');
      btnAltA.classList.remove('active');
      planIframe.src = 'assets/plans/alternative_b.svg';
    });
  }

  const tendencyBtns = document.querySelectorAll('.tendency-btn');
  tendencyBtns.forEach((tbtn) => {
    tbtn.addEventListener('click', () => {
      tendencyBtns.forEach((b) => b.classList.remove('selected'));
      tbtn.classList.add('selected');

      const val = tbtn.dataset.tendency;
      if (archTendencyVal) {
        archTendencyVal.textContent = val;
      }

      addGroundedCard({
        group: 'routine',
        title: `Plan Eğilimi Seçildi: ${val}`,
        badge: 'Kullanıcı söyledi',
        badgeClass: 'badge-user-said',
        rationale: `Kullanıcı taslak plan alternatifleri arasından "${val}" eğilimini belirtti.`
      });
    });
  });

  // --------------------------------------------------------------------------
  // 6. Right Panel View Toggle (Client Understanding vs Architect Brief View)
  // --------------------------------------------------------------------------
  if (toggleViewBtn) {
    toggleViewBtn.addEventListener('click', () => {
      isArchitectView = !isArchitectView;

      if (isArchitectView) {
        clientView.classList.add('hidden');
        architectView.classList.remove('hidden');
        toggleBtnText.textContent = 'Müşteri Görünümü';
        panelTitle.textContent = 'Mimar Sentez Raporu';
        panelSubtitle.textContent = 'Teknik mimari brief ve gereksinim analizi';
        toggleViewBtn.classList.add('active');
      } else {
        architectView.classList.add('hidden');
        clientView.classList.remove('hidden');
        toggleBtnText.textContent = 'Mimar Önizlemesi';
        panelTitle.textContent = 'Sizi nasıl anladım?';
        panelSubtitle.textContent = 'Sohbetinizden çıkarılan canlı mimari profil';
        toggleViewBtn.classList.remove('active');
      }
    });
  }

  // --------------------------------------------------------------------------
  // 7. Interactive Confirmation Actions
  // --------------------------------------------------------------------------
  if (confirmCorrectBtn) {
    confirmCorrectBtn.addEventListener('click', () => {
      confirmationText.style.backgroundColor = '#E6F4EA';
      confirmationText.style.borderColor = '#137333';
      confirmationText.innerHTML = '✅ <strong>Kullanıcı Doğruladı:</strong> ' + confirmationText.textContent.replace('✅ Kullanıcı Doğruladı: ', '').replace(/^"|"$/g, '');
      confirmationActions.style.display = 'none';

      const systemBadge = interpretationCards.querySelector('.badge-system');
      if (systemBadge) {
        systemBadge.className = 'badge badge-confirmed';
        systemBadge.textContent = 'Kullanıcı doğruladı';
      }
    });
  }

  if (confirmRejectBtn || confirmEditBtn) {
    const handleEditOpen = () => {
      inlineEditor.classList.remove('hidden');
      editInput.value = confirmationText.textContent.trim().replace(/^"|"$/g, '').replace('✅ Kullanıcı Doğruladı: ', '');
      editInput.focus();
    };

    if (confirmRejectBtn) confirmRejectBtn.addEventListener('click', handleEditOpen);
    if (confirmEditBtn) confirmEditBtn.addEventListener('click', handleEditOpen);
  }

  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', () => {
      inlineEditor.classList.add('hidden');
    });
  }

  if (saveEditBtn) {
    saveEditBtn.addEventListener('click', () => {
      const updatedText = editInput.value.trim();
      if (!updatedText) return;

      confirmationText.textContent = `"${updatedText}"`;
      confirmationText.style.backgroundColor = '#EEF3F0';
      confirmationText.style.borderColor = '#3F5E4D';
      inlineEditor.classList.add('hidden');

      const systemBadge = interpretationCards.querySelector('.badge-system');
      if (systemBadge) {
        systemBadge.className = 'badge badge-user-said';
        systemBadge.textContent = 'Kullanıcı söyledi';
      }
    });
  }

  if (toggleExtraRoutineBtn && extraRoutineItems) {
    toggleExtraRoutineBtn.addEventListener('click', () => {
      isExtraRoutineExpanded = !isExtraRoutineExpanded;
      if (isExtraRoutineExpanded) {
        extraRoutineItems.classList.remove('hidden');
        toggleExtraRoutineBtn.querySelector('span').textContent = 'Daha az göster';
        if (routineCount) routineCount.textContent = '3 Gösteriliyor';
      } else {
        extraRoutineItems.classList.add('hidden');
        toggleExtraRoutineBtn.querySelector('span').textContent = 'Diğer bulguları göster (+1)';
        if (routineCount) routineCount.textContent = '2 Gösteriliyor';
      }
    });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
