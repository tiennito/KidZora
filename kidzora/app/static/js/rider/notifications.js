/* ══════════════════════════════════════════════
   rider/notifications.js
   Rider notifications page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Notification card interactions ────────────────────────── */
  var notifCards = document.querySelectorAll('.notif-container .card');
  
  notifCards.forEach(function (card) {
    var viewBtn = card.querySelector('.notif-view-btn');
    var badge = card.querySelector('.notif-badge-new');
    
    // Mark as read when viewing
    if (viewBtn) {
      viewBtn.addEventListener('click', function () {
        if (badge) {
          badge.style.display = 'none';
          card.classList.add('opacity-75');
        }
      });
    }

    // Card hover
    card.addEventListener('mouseenter', function () {
      this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.boxShadow = '';
    });
  });

})();
