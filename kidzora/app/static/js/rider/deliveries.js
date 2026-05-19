/* ══════════════════════════════════════════════
   rider/deliveries.js
   My deliveries page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Tab switching and state management ────────────────────── */
  var tabButtons = document.querySelectorAll('.btn-group a[href*="/deliveries?tab="]');
  tabButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      // URL navigation will handle the tab switch
      var allBtns = btn.parentElement.querySelectorAll('a');
      allBtns.forEach(function (b) {
        b.classList.remove('btn-success');
        b.classList.add('btn-outline-success');
      });
      this.classList.remove('btn-outline-success');
      this.classList.add('btn-success');
    });
  });

  /* ── Delivery card interactions ────────────────────────────── */
  var deliveryCards = document.querySelectorAll('.delivery-card');
  deliveryCards.forEach(function (card) {
    var detailBtn = card.querySelector('a[href*="/delivery_detail/"]');
    
    // Card hover effects
    card.addEventListener('mouseenter', function () {
      this.style.boxShadow = '0 8px 16px rgba(0,0,0,0.12)';
      this.style.transform = 'translateY(-2px)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.boxShadow = '';
      this.style.transform = '';
    });

    // Card click to view details (optional)
    if (detailBtn) {
      card.style.cursor = 'pointer';
      card.addEventListener('click', function (e) {
        if (e.target.closest('a[href*="/delivery_detail/"]') === detailBtn) {
          // Let the link handle it
          return;
        }
        // Optionally navigate on card click
        // detailBtn.click();
      });
    }
  });

})();
