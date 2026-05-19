/**
 * KidZora – Rider Panel / Base
 * Sidebar mobile toggle + availability toggle — runs on every rider page.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    // ── Sidebar toggle ──────────────────────────────────────────────────────
    var toggle  = document.getElementById('sidebarToggle');
    var sidebar = document.getElementById('riderSidebar');

    if (toggle && sidebar) {
      toggle.addEventListener('click', function () {
        sidebar.classList.toggle('open');
      });

      document.addEventListener('click', function (e) {
        if (!sidebar.contains(e.target) && e.target !== toggle) {
          sidebar.classList.remove('open');
        }
      });
    }

    // ── Availability toggle ─────────────────────────────────────────────────
    var TOGGLE_URL = '/rider/toggle-availability';

    function _applyAvailability(isAvailable) {
      // Navbar button
      var navBtn   = document.getElementById('kzAvailBtn');
      var navDot   = document.getElementById('kzAvailDot');
      var navLabel = document.getElementById('kzAvailLabel');
      if (navBtn) {
        navBtn.dataset.available = isAvailable ? 'true' : 'false';
        navBtn.title = isAvailable
          ? 'You are Online — click to go Offline'
          : 'You are Offline — click to go Online';
        navBtn.className = 'btn btn-sm fw-semibold px-3 py-1 ' +
          (isAvailable ? 'btn-success' : 'btn-secondary');
        if (navDot) {
          navDot.classList.toggle('is-online', isAvailable);
          navDot.classList.toggle('is-offline', !isAvailable);
        }
        if (navLabel) navLabel.textContent        = isAvailable ? 'Online'  : 'Offline';
      }

      // Dashboard banner button (may or may not be on current page)
      var dashBtn = document.getElementById('kzDashAvailBtn');
      if (dashBtn) {
        var banner = dashBtn.closest('.alert');
        if (banner) {
          banner.className = 'alert d-flex align-items-center gap-3 py-2 mb-4 ' +
            (isAvailable ? 'alert-success' : 'alert-secondary');
          var dot  = banner.querySelector('.fa-circle');
          var text = banner.querySelector('strong');
          var sub  = banner.querySelector('.flex-grow-1');
          if (dot)  dot.style.color = isAvailable ? '#198754' : '#6c757d';
          if (text) text.textContent = isAvailable ? 'You are Online' : 'You are Offline';
          if (sub) {
            sub.innerHTML = isAvailable
              ? '<strong>You are Online</strong> — you can accept new deliveries.'
              : '<strong>You are Offline</strong> — you won\'t appear for new delivery assignments.';
          }
        }
        dashBtn.dataset.available = isAvailable ? 'true' : 'false';
        dashBtn.className = 'btn btn-sm ' + (isAvailable ? 'btn-outline-secondary' : 'btn-success');
        dashBtn.textContent = isAvailable ? 'Go Offline' : 'Go Online';
      }

      // Available page inline button
      var pageBtn = document.getElementById('kzAvailPageBtn');
      if (pageBtn) {
        pageBtn.dataset.available = isAvailable ? 'true' : 'false';
        // Reload page after going online so the order list refreshes
        if (isAvailable) {
          window.location.reload();
          return;
        }
      }
    }

    function _doToggle(btn) {
      if (!btn) return;
      btn.disabled = true;
      var oldText  = btn.innerHTML;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>…';

      fetch(TOGGLE_URL, {
        method:  'POST',
        headers: {'Content-Type': 'application/json',
                  'X-Requested-With': 'XMLHttpRequest'},
      })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btn.disabled = false;
        if (data.ok) {
          _applyAvailability(data.is_available);
        } else {
          btn.innerHTML = oldText;
          console.error('[kzAvail] toggle error:', data.error);
        }
      })
      .catch(function () {
        btn.disabled  = false;
        btn.innerHTML = oldText;
      });
    }

    // Wire all three possible toggle buttons
    ['kzAvailBtn', 'kzDashAvailBtn', 'kzAvailPageBtn'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener('click', function () { _doToggle(el); });
      }
    });
  });
})();
