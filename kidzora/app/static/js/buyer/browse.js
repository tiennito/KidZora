/* ══════════════════════════════════════════════
   buyer/browse.js
   JavaScript for buyer/browse.html
   Config injected via: <script id="kz-browse-data" type="application/json">
   Keys:
     hasFilter   (bool)  – true if any filter/search is currently active
     activeCount (int)   – number of active filter slots
══════════════════════════════════════════════ */
(function () {
  'use strict';

  var cfg   = JSON.parse(document.getElementById('kz-browse-data').textContent);
  var panel = document.getElementById('browseFilterPanel');
  var btn   = document.getElementById('browseFilterToggle');

  /* Only relevant on mobile – on md+ CSS keeps the panel always visible */
  if (!panel || !btn) return;

  /* ── Helpers ─────────────────────────────────────────────── */
  function isOpen() { return panel.classList.contains('is-open'); }

  function updateBtn() {
    var badge = cfg.activeCount > 0
      ? ' <span class="badge bg-primary ms-1">' + cfg.activeCount + '</span>'
      : '';
    btn.innerHTML = isOpen()
      ? '<i class="fas fa-times me-1"></i>Hide Filters'
      : '<i class="fas fa-sliders-h me-1"></i>Filters' + badge;
    btn.setAttribute('aria-expanded', String(isOpen()));
  }

  function open()  { panel.classList.add('is-open');    sessionStorage.setItem('kzBrowseFilterOpen', '1'); }
  function close() { panel.classList.remove('is-open'); sessionStorage.setItem('kzBrowseFilterOpen', '0'); }

  /* ── Initial state ───────────────────────────────────────── */
  /* Auto-open when filters are active so user can see/edit them.
     Otherwise honour the last explicit open/close they chose. */
  if (cfg.hasFilter) {
    open();
  } else if (sessionStorage.getItem('kzBrowseFilterOpen') === '1') {
    open();
  }

  /* ── Toggle button ───────────────────────────────────────── */
  btn.addEventListener('click', function () {
    if (isOpen()) { close(); } else { open(); }
    updateBtn();
  });

  /* ── Keep open after "Apply" submit ─────────────────────── */
  var filterForm = document.getElementById('browseFilterForm');
  if (filterForm) {
    filterForm.addEventListener('submit', function () {
      sessionStorage.setItem('kzBrowseFilterOpen', '1');
    });
  }

  /* ── Clear session state when "Reset" is clicked ────────── */
  var resetLink = document.getElementById('browseFilterReset');
  if (resetLink) {
    resetLink.addEventListener('click', function () {
      sessionStorage.removeItem('kzBrowseFilterOpen');
    });
  }

  updateBtn();
}());
