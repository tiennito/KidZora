/* ══════════════════════════════════════════════
   buyer/returns.js
   Returns & refunds page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Initialize return request rows ────────────────────────── */
  var returnRows = document.querySelectorAll('tbody tr');
  
  returnRows.forEach(function (row) {
    var statusBadge = row.querySelector('.badge');
    var linkBtn = row.querySelector('a[href*="/returns/"]');
    
    if (statusBadge) {
      // Add visual feedback on hover
      row.addEventListener('mouseenter', function () {
        row.style.backgroundColor = 'rgba(0,0,0,0.02)';
      });
      row.addEventListener('mouseleave', function () {
        row.style.backgroundColor = '';
      });
    }
  });

})();
