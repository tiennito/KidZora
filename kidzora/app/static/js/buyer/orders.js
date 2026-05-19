/* ══════════════════════════════════════════════
   buyer/orders.js
   Orders page interactions and utilities
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Initialize empty state on page load ───────────────────── */
  var orderCards = document.querySelectorAll('.order-card');
  
  // Show empty state if no orders, hide if there are orders
  if (orderCards.length === 0) {
    window.showEmptyState('orders-container');
  } else {
    window.hideEmptyState('orders-container');
  }

  /* ── Initialize order cards interactions ────────────────────── */
  orderCards.forEach(function (card) {
    var viewBtn = card.querySelector('a[href*="/orders/"]');
    if (viewBtn) {
      viewBtn.addEventListener('click', function (e) {
        // Optional: add analytics tracking
        // console.log('User clicked order details:', this.href);
      });
    }
  });

})();
