/* ══════════════════════════════════════════════
   rider/payouts.js
   Payouts/withdrawals page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Payout method selection ───────────────────────────────── */
  function togglePayoutMethodFields() {
    var methodSelect = document.getElementById('rpoMethod');
    if (!methodSelect) return;

    var method = methodSelect.value;
    var bankFields = document.querySelectorAll('[data-method="bank"]');
    var walletFields = document.querySelectorAll('[data-method="wallet"]');
    var mobileFields = document.querySelectorAll('[data-method="mobile"]');

    // Hide all fields initially
    [bankFields, walletFields, mobileFields].forEach(function (fields) {
      fields.forEach(function (field) {
        field.style.display = 'none';
      });
    });

    // Show relevant fields based on selection
    if (method === 'bank') {
      bankFields.forEach(function (field) { field.style.display = 'block'; });
    } else if (method === 'wallet') {
      walletFields.forEach(function (field) { field.style.display = 'block'; });
    } else if (method === 'mobile') {
      mobileFields.forEach(function (field) { field.style.display = 'block'; });
    }
  }

  var methodSelect = document.getElementById('rpoMethod');
  if (methodSelect) {
    methodSelect.addEventListener('change', togglePayoutMethodFields);
    // Initialize on load
    togglePayoutMethodFields();
  }

  /* ── Request amount validation ─────────────────────────────── */
  var amountInput = document.getElementById('rpoAmount');
  if (amountInput) {
    amountInput.addEventListener('change', function () {
      var amount = parseFloat(this.value);
      if (amount < 100) {
        this.classList.add('is-invalid');
        var feedback = this.parentElement.querySelector('.invalid-feedback');
        if (feedback) feedback.textContent = 'Minimum withdrawal is ₱100';
      } else {
        this.classList.remove('is-invalid');
      }
    });
  }

})();
