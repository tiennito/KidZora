/* ══════════════════════════════════════════════
   rider/inbox.js
   Chat inbox page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Conversation list item selection ───────────────────────── */
  var convItems = document.querySelectorAll('[data-conversation-id]');
  convItems.forEach(function (item) {
    item.addEventListener('click', function (e) {
      if (e.target.closest('a[href*="/chat/"]')) {
        // Let the link handle navigation
        return;
      }
      // Or trigger the link if clicking anywhere else on the item
      var link = this.querySelector('a[href*="/chat/"]');
      if (link) {
        link.click();
      }
    });

    // Hover effect
    item.addEventListener('mouseenter', function () {
      this.style.backgroundColor = 'rgba(0,0,0,0.02)';
    });
    item.addEventListener('mouseleave', function () {
      this.style.backgroundColor = '';
    });
  });

  /* ── Message sending and polling ───────────────────────────── */
  var chatForm = document.getElementById('riderChatForm');
  if (chatForm) {
    var input = chatForm.querySelector('input[name="body"]');
    var submitBtn = chatForm.querySelector('button[type="submit"]');

    // Disable submit when empty
    if (input && submitBtn) {
      input.addEventListener('input', function () {
        submitBtn.disabled = !this.value.trim();
      });
      submitBtn.disabled = !input.value.trim();
    }

    // Submit handler
    chatForm.addEventListener('submit', function (e) {
      if (input && !input.value.trim()) {
        e.preventDefault();
      }
    });
  }

  /* ── Typing indicator display ──────────────────────────────── */
  window.showTypingIndicator = function () {
    var indicator = document.getElementById('typingIndicator');
    if (indicator) {
      indicator.style.display = 'block';
    }
  };

  window.hideTypingIndicator = function () {
    var indicator = document.getElementById('typingIndicator');
    if (indicator) {
      indicator.style.display = 'none';
    }
  };

})();
