/* ============================================================
   KidZora – Seller Dashboard JS
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

  // ── Mobile sidebar drawer ──────────────────────────────
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar       = document.getElementById('sellerSidebar');
  const overlay       = document.getElementById('sidebarOverlay');

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden'; // prevent body scroll while drawer open
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  function toggleSidebar() {
    sidebar && sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  }

  if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);

  // Clicking the backdrop closes the drawer
  if (overlay) overlay.addEventListener('click', closeSidebar);

  // Pressing Escape also closes it
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });

  // On resize to ≥768px: reset inline overflow lock so desktop is never broken
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 768) {
      closeSidebar();
    }
  });

  // Alerts stay until the user manually closes them (btn-close).

});
