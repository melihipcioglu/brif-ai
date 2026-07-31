/**
 * BRIF.AI - Conversation UI Prototype v0 Interaction Script
 *
 * NOTE: This file powers a standalone, client-side UX prototype.
 * It uses simulated conversation responses and dynamic UI state updates.
 * There are NO real backend, API, AI model, or server calls in this prototype.
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
  
  const priorityCards = document.getElementById('priorityCards');
  const routineCards = document.getElementById('routineCards');
  const pendingCards = document.getElementById('pendingCards');
  
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
  let conversationTurn = 0;

  // --------------------------------------------------------------------------
  // 1. Suggestion Chip Quick-Reply Handling
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
  // 2. Chat Form Submit Handling
  // --------------------------------------------------------------------------
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = userInput.value.trim();
      if (!text) return;

      handleUserSendMessage(text);
      userInput.value = '';
    });

    // Submit on Enter (without Shift)
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
      userInput.value = 'Eşim çalışırken sessiz ve tam konsantrasyon alanı istiyor, salonla doğrudan ses teması olmasın.';
    });
  }

  // --------------------------------------------------------------------------
  // 3. User Message Processing & AI Response Simulation
  // --------------------------------------------------------------------------
  function handleUserSendMessage(messageText) {
    // Hide old chips
    if (suggestionChips) {
      suggestionChips.style.display = 'none';
    }

    // Append User Message to Chat
    appendMessage('user', 'Siz', 'MK', messageText);

    // Increment conversation turn count
    conversationTurn++;

    // Scroll chat to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate AI thinking delay
    setTimeout(() => {
      generateAiResponse(messageText);
    }, 600);
  }

  function appendMessage(senderType, senderName, avatarText, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${senderType}-message`;

    msgDiv.innerHTML = `
      <div class="message-avatar ${senderType === 'user' ? 'user' : ''}">${avatarText}</div>
      <div class="message-content">
        <div class="message-sender">${senderName}</div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function generateAiResponse(userText) {
    let aiReply = '';
    let newInsight = null;

    if (userText.includes('Sessiz') || userText.includes('tam konsantrasyon') || userText.includes('ayrı')) {
      aiReply = 'Akustik mahremiyet ihtiyacı netleşti. Çalışma odasını ana yaşam alanından ses olarak izole ederken, doğal ışık ve havalandırma açısından kuzey-doğu cephesine konumlandırmayı düşünebiliriz. Peki, bu alanın gündüz misafir odasına dönüştürülmesi gerekir mi?';
      
      newInsight = {
        group: 'priority',
        title: 'Tam Akustik İzolasyonlu Çalışma Odası',
        badge: 'Kesinleşti',
        badgeClass: 'badge-confirmed',
        detail: 'Çalışma odası salondan bağımsız ve yüksek ses yalıtımlı kurgulanacak.'
      };
    } else if (userText.includes('Ortak alana yakın') || userText.includes('salona yakın')) {
      aiReply = 'Harika. Çalışma alanını salona veya iç avluya bakan şeffaf bir cam bölücüyle bağlayabiliriz. Böylece görsel temas korunurken toplantı sırasında kapı kapatılarak ses kontrolü sağlanır.';
      
      newInsight = {
        group: 'priority',
        title: 'Şeffaf Bölücülü Çalışma-Yaşam Entegrasyonu',
        badge: 'Kesinleşti',
        badgeClass: 'badge-confirmed',
        detail: 'Çalışma alanı ile salon arasında esnek cam panel öneriliyor.'
      };
    } else if (userText.includes('dengeli') || userText.includes('esnek')) {
      aiReply = 'Esnek kurgu mimari açıdan en nitelikli çözümleri sunar. Ahşap kayar paneller veya gizlenebilir cep kapıları ile mekan ihtiyaca göre büyüyüp küçülebilir. Mutfak ve çocuk alanıyla ilişkiniz konusunda ne düşünürsünüz?';
      
      newInsight = {
        group: 'priority',
        title: 'Gizlenebilir Panelli Esnek Mekân Kurgusu',
        badge: 'Kesinleşti',
        badgeClass: 'badge-confirmed',
        detail: 'Dönüştürülebilir duvar ve ahşap kayar panel konsepti.'
      };
    } else {
      aiReply = `Notlarımı aldım: "${userText}". Bu tercihinizi genel hane akışıyla sentezliyorum. Bir sonraki adımda yatak odaları ve ıslak hacimlerin gündüz kullanımı üzerine odaklanacağız.`;
      
      newInsight = {
        group: 'routine',
        title: 'Özel Kullanım Tercihi Eklendi',
        badge: 'Muhtemel',
        badgeClass: 'badge-probable',
        detail: userText.length > 60 ? userText.substring(0, 60) + '...' : userText
      };
    }

    // Append AI reply to chat stream
    appendMessage('ai', 'BRIF.AI Mimari Danışman', 'AI', aiReply);

    // Update Right Panel dynamically
    if (newInsight) {
      addInsightCard(newInsight);
    }
  }

  function addInsightCard(insight) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'insight-card';

    cardDiv.innerHTML = `
      <div class="card-top">
        <span class="card-text">${escapeHtml(insight.title)}</span>
        <span class="badge ${insight.badgeClass}">${escapeHtml(insight.badge)}</span>
      </div>
      <div class="card-detail">${escapeHtml(insight.detail)}</div>
    `;

    if (insight.group === 'priority') {
      priorityCards.insertBefore(cardDiv, priorityCards.firstChild);
    } else if (insight.group === 'routine') {
      routineCards.insertBefore(cardDiv, routineCards.firstChild);
    } else {
      pendingCards.insertBefore(cardDiv, pendingCards.firstChild);
    }
  }

  // --------------------------------------------------------------------------
  // 4. View Toggle (Client Understanding vs Architect Brief View)
  // --------------------------------------------------------------------------
  if (toggleViewBtn) {
    toggleViewBtn.addEventListener('click', () => {
      isArchitectView = !isArchitectView;

      if (isArchitectView) {
        clientView.classList.add('hidden');
        architectView.classList.remove('active');
        architectView.classList.remove('hidden');
        
        toggleBtnText.textContent = 'Müşteri Görünümü';
        panelTitle.textContent = 'Mimar Sentez Raporu';
        panelSubtitle.textContent = 'Teknik mimari brief ve tasarım kararları';
        toggleViewBtn.classList.add('active');
      } else {
        architectView.classList.add('hidden');
        clientView.classList.remove('hidden');
        clientView.classList.add('active');
        
        toggleBtnText.textContent = 'Mimar Önizlemesi';
        panelTitle.textContent = 'Sizi nasıl anladım?';
        panelSubtitle.textContent = 'Sohbetinizden çıkarılan canlı mimari profil';
        toggleViewBtn.classList.remove('active');
      }
    });
  }

  // --------------------------------------------------------------------------
  // 5. Interactive Confirmation Actions (Doğru / Düzenle / Yanlış Anladın)
  // --------------------------------------------------------------------------
  if (confirmCorrectBtn) {
    confirmCorrectBtn.addEventListener('click', () => {
      confirmationText.style.backgroundColor = '#E6F4EA';
      confirmationText.style.borderColor = '#137333';
      confirmationText.innerHTML = '✅ <strong>Doğrulandı:</strong> ' + confirmationText.textContent.replace('✅ Doğrulandı: ', '');
      confirmationActions.style.display = 'none';
      
      // Update pending items to confirmed
      const pendingConflictBadge = pendingCards.querySelector('.badge-conflict');
      if (pendingConflictBadge) {
        pendingConflictBadge.className = 'badge badge-confirmed';
        pendingConflictBadge.textContent = 'Kesinleşti';
      }
    });
  }

  if (confirmRejectBtn) {
    confirmRejectBtn.addEventListener('click', () => {
      inlineEditor.classList.remove('hidden');
      editInput.value = confirmationText.textContent.trim().replace(/^"|"$/g, '');
      editInput.focus();
    });
  }

  if (confirmEditBtn) {
    confirmEditBtn.addEventListener('click', () => {
      inlineEditor.classList.remove('hidden');
      editInput.value = confirmationText.textContent.trim().replace(/^"|"$/g, '');
      editInput.focus();
    });
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
      confirmationText.style.backgroundColor = '#E8F0FE';
      confirmationText.style.borderColor = '#1A73E8';
      inlineEditor.classList.add('hidden');

      // Update badge to probable
      const pendingBadge = pendingCards.querySelector('.badge-conflict');
      if (pendingBadge) {
        pendingBadge.className = 'badge badge-probable';
        pendingBadge.textContent = 'Muhtemel';
      }
    });
  }

  // Utility Function: Escape HTML to prevent injection
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
