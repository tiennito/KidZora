/* ══════════════════════════════════════════════
   rider/dashboard.js
   Dashboard page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Availability toggle feedback ──────────────────────────── */
  var dashBtn = document.getElementById('kzDashAvailBtn');
  if (dashBtn) {
    dashBtn.addEventListener('click', function () {
      this.disabled = true;
      var isCurrentlyAvailable = this.dataset.available === 'true';
      var newState = !isCurrentlyAvailable;
      
      fetch('/rider/toggle-availability', { method: 'POST' })
        .then(function () {
          this.disabled = false;
        }.bind(this))
        .catch(function () {
          this.disabled = false;
        }.bind(this));
    });
  }

})();
