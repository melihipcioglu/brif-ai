/**
 * BRIF.AI - Conversation UI Prototype v0 Interaction Script (Revised)
 *
 * NOTE: Standalone frontend UX prototype for BRIF.AI.
 * All conversation dynamics and dynamic panel updates run client-side.
 * Contains NO real backend, database, API, or AI model calls.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Element References
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

  let isArchitectView = false;
  let isExtraRoutineExpanded = false;

  // --------------------------------------------------------------------------
  // 1. Collapsible Extra Findings Toggle
  // --------------------------------------------------------------------------
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

  // --------------------------------------------------------------------------
  // 2. Suggestion Chip Quick-Reply Handling
  // --------------------------------------------------------------------------
  if (suggestionChips) {
    suggestionChips.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip-btn');
      if (!chip) return;

      const replyText = chip.dataset.reply || chip.textContent.trim();
      handleUserSendMessage(replyText);
    });
  }

  // --------------------------------------------------------------------------
  // 3. Chat Form Submit Handling
  // --------------------------------------------------------------------------
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

  // Voice Button Demo Toast
  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      alert('🎤 Sesli yanıt alma demosu: Konuşmanız simüle edilmektedir...');
      userInput.value = 'Eşim gün boyu online toplantılar yapıyor, tam ses izolasyonu çok kritik.';
    });
  }

  // --------------------------------------------------------------------------
  // 4. User Message Processing & Sound AI Response Simulation
  // --------------------------------------------------------------------------
  function handleUserSendMessage(messageText) {
    // Hide old chips
    if (suggestionChips) {
      suggestionChips.style.display = 'none';
    }

    // Append User Message to Chat
    appendMessage('user', 'Siz', 'MK', messageText);

    // Scroll chat to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate AI response delay
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
    } else if (userText.includes('yazım') || userText.includes('odaklanma')) {
      aiReply = 'Görsel ve zihinsel odaklanma ihtiyacını not aldım. Bu alanın günün hangi saatlerinde en yoğun kullanıldığını netleştirelim. Benzer şekilde, gündüz doğal ışık alma düzeyi sizin için ne derece belirleyici?';
      
      newCard = {
        group: 'routine',
        title: 'Odaklanma ağırlıklı bireysel çalışma ritmi',
        badge: 'Kullanıcı söyledi',
        badgeClass: 'badge-user-said',
        rationale: `"${userText}"`
      };
    } else if (userText.includes('16:00') || userText.includes('çocuk')) {
      aiReply = 'Öğleden sonra 16:00 sonrasındaki zaman dilimi çakışmasını anlıyorum. Bu saatlerde çalışma alanının çocukların ortak kullanım alanlarıyla ilişkisini ve ses geçişini değerlendireceğiz. Bu çakışma hafta içi her gün yaşanıyor mu?';
      
      newCard = {
        group: 'interpretation',
        title: 'Saat 16:00 sonrası ses ve kullanım çakışması tespiti',
        badge: 'Sistem yorumu',
        badgeClass: 'badge-system',
        rationale: `"${userText}" beyanından çıkarılan sistem yorumu.`
      };
    } else {
      aiReply = `İfade ettiğiniz konuyu not aldım: "${userText}". Bu durumun hane içi diğer kullanım alışkanlıklarıyla uyumunu değerlendireceğiz. Yatak odaları ve genel yaşam alanlarının gündüz ilişkisi hakkında ne düşünürsünüz?`;
      
      newCard = {
        group: 'routine',
        title: 'Kullanıcı beyanı eklendi',
        badge: 'Kullanıcı söyledi',
        badgeClass: 'badge-user-said',
        rationale: `"${userText}"`
      };
    }

    // Append AI reply to chat stream
    appendMessage('ai', 'BRIF.AI Mimari Danışman', 'B', aiReply);

    // Update Right Panel with ONLY findings derived from this message
    if (newCard) {
      addGroundedCard(newCard);
    }
  }

  function addGroundedCard(cardData) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'insight-card';
    if (cardData.badgeClass === 'badge-system') {
      cardDiv.classList.add('highlight-system');
    }

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
  // 5. View Toggle (Client Understanding View vs Architect Brief View)
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
  // 6. Confirmation Box Interactivity (Doğru / Düzenle / Yanlış Anladın)
  // --------------------------------------------------------------------------
  if (confirmCorrectBtn) {
    confirmCorrectBtn.addEventListener('click', () => {
      confirmationText.style.backgroundColor = '#E6F4EA';
      confirmationText.style.borderColor = '#137333';
      confirmationText.innerHTML = '✅ <strong>Kullanıcı Doğruladı:</strong> ' + confirmationText.textContent.replace('✅ Kullanıcı Doğruladı: ', '').replace(/^"|"$/g, '');
      confirmationActions.style.display = 'none';

      // Update system interpretation card badge to "Kullanıcı doğruladı"
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

      // Update badge to "Kullanıcı söyledi"
      const systemBadge = interpretationCards.querySelector('.badge-system');
      if (systemBadge) {
        systemBadge.className = 'badge badge-user-said';
        systemBadge.textContent = 'Kullanıcı söyledi';
      }
    });
  }

  // Utility Function: Escape HTML to prevent script injection
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
