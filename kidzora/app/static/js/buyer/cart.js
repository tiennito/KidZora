/* ══════════════════════════════════════════════
   buyer/cart.js
   Cart page interactions: quantity controls
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Quantity decrease button ───────────────────────────────── */
  document.querySelectorAll('.cart-qty-group button:first-child').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var form = btn.closest('form');
      var input = form.querySelector('input[name="qty"]');
      var newVal = Math.max(1, parseInt(input.value, 10) - 1);
      input.value = newVal;
    });
  });

  /* ── Quantity increase button ───────────────────────────────── */
  document.querySelectorAll('.cart-qty-group button:last-child').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var form = btn.closest('form');
      var input = form.querySelector('input[name="qty"]');
      var maxStock = parseInt(btn.dataset.stock, 10);
      var newVal = Math.min(maxStock, parseInt(input.value, 10) + 1);
      input.value = newVal;
    });
  });

})();
