/**
 * KidZora – Admin Base Layout JS
 * Sidebar toggle for mobile & dropdown menus.
 */
(function () {
  'use strict';
  
  // Mobile sidebar toggle
  var btn = document.getElementById('sidebarToggle');
  var sb  = document.getElementById('adminSidebar');
  if (btn && sb) {
    btn.addEventListener('click', function () { sb.classList.toggle('open'); });
  }

  // Sidebar dropdown menus
  var dropdownToggles = document.querySelectorAll('.sidebar-dropdown-toggle');
  dropdownToggles.forEach(function (toggle) {
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      var dropdown = toggle.closest('.sidebar-dropdown');
      if (dropdown) {
        dropdown.classList.toggle('expanded');
      }
    });
  });
})();
