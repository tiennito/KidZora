/* ══════════════════════════════════════════════
   rider/available.js
   Available pickups page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Availability button on available page ─────────────────── */
  var pageBtn = document.getElementById('kzAvailPageBtn');
  if (pageBtn) {
    pageBtn.addEventListener('click', function () {
      this.disabled = true;
      fetch('/rider/toggle-availability', { method: 'POST' })
        .then(function () {
          this.disabled = false;
          // Status should update via navbar, but refresh in 1s to be safe
          setTimeout(function () { window.location.reload(); }, 500);
        }.bind(this))
        .catch(function () {
          this.disabled = false;
        }.bind(this));
    });
  }

  /* ── Accept delivery confirmation dialog ────────────────────── */
  var acceptForms = document.querySelectorAll('form[action*="/accept_order"]');
  acceptForms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      var orderNum = this.action.match(/\/(\w+)$/)?.[1] || 'Unknown';
      var confirmed = confirm('Are you sure you want to accept this delivery? You can view details after accepting.');
      if (!confirmed) {
        e.preventDefault();
      }
    });
  });

  /* ── Delivery card hover effects ───────────────────────────── */
  var deliveryCards = document.querySelectorAll('.delivery-card');
  deliveryCards.forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      this.style.boxShadow = '0 8px 16px rgba(0,0,0,0.12)';
      this.style.transform = 'translateY(-2px)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.boxShadow = '';
      this.style.transform = '';
    });
  });

})();
