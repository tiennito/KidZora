/**
 * KidZora – Rider / Ratings Page
 */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.rr-bar-fill').forEach(function (el) {
    el.style.width = (el.dataset.pct || '0') + '%';
  });
});
