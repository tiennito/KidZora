/* ══════════════════════════════════════════════
   buyer/notifications.js
   Notifications page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Initialize empty state on page load ───────────────────── */
  var notifCards = document.querySelectorAll('.notif-container .card');
  
  // Show empty state if no notifications, hide if there are notifications
  if (notifCards.length === 0) {
    window.showEmptyState('notifications-container');
  } else {
    window.hideEmptyState('notifications-container');
  }

  /* ── Initialize notification cards ────────────────────────── */
  notifCards.forEach(function (card) {
    var viewBtn = card.querySelector('.notif-view-btn');
    var badge = card.querySelector('.notif-badge-new');
    
    // Mark as read when viewing
    if (viewBtn) {
      viewBtn.addEventListener('click', function () {
        if (badge) {
          badge.style.display = 'none';
          card.classList.remove('notif-bg-blue', 'notif-bg-sky', 'notif-bg-yellow', 'notif-bg-green', 'notif-bg-red', 'notif-bg-default');
          card.classList.add('notif-bg-subtle');
        }
      });
    }
  });

})();
