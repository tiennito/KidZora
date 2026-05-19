/**
 * KidZora – Admin / Orders Page
 */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el, { trigger: 'hover', placement: 'top' });
  });
});
