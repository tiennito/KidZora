/**
 * kidzora-realtime.js
 * ───────────────────
 * Two-phase notification delivery:
 *
 *  PHASE 1 — SEED (once on page load)
 *    Fetches all unread notifications and silently pre-populates the bell panel.
 *
 *  PHASE 2 — SMART POLL (adaptive + visibility-aware)
 *    • Runs every POLL_FAST (5 s) while the tab is visible and active.
 *    • Slows to POLL_SLOW (30 s) after IDLE_ROUNDS consecutive empty polls.
 *    • Pauses completely when the tab is hidden (Page Visibility API).
 *    • Resumes + resets to fast interval the moment the tab becomes visible again.
 *    • All fetch() calls are async — zero main-thread blocking.
 *
 * Requires: kidzora-toast.js (window.Kz) loaded first.
 * Only activates when <meta name="kz-uid"> is present (user logged in).
 */

(function () {
  'use strict';

  var POLL_FAST    = 5000;              // 5 s  — active / just-got-notif
  var POLL_SLOW    = 30000;             // 30 s — idle / tab idle
  var IDLE_ROUNDS  = 3;                 // empty polls before slowing down
  var LS_SINCE     = 'kz_rt_since_v2';
  var POLL_URL     = '/api/v1/notifications/poll';
  var MARK_ALL_URL = '/api/v1/notifications/mark-all-read';

  /* ── State ──────────────────────────────────────────────────────────────── */
  var _timer       = null;   // current setTimeout handle
  var _emptyCount  = 0;      // consecutive empty-response counter
  var _running     = false;  // guard against overlapping fetches
  var _paused      = false;  // true when tab is hidden

  /* ── Helpers ──────────────────────────────────────────────────────────────── */
  function getSince()    { return localStorage.getItem(LS_SINCE) || ''; }
  function setSince(iso) { if (iso) localStorage.setItem(LS_SINCE, iso); }
  function newestTs(rows){ return (rows && rows.length && rows[0].created_at) ? rows[0].created_at : ''; }

  /* ── Type → Kz state ─────────────────────────────────────────────────────── */
  var _TYPE_STATE = {
    order_placed:       'info',
    order_confirmed:    'success',
    order_preparing:    'info',
    order_ready_pickup: 'info',
    order_out_delivery: 'warning',
    order_delivered:    'success',
    order_completed:    'success',
    order_cancelled:    'error',
    cancel_request:     'warning',
    cancel_approved:    'success',
    cancel_rejected:    'error',
    message_received:   'info',
    return_submitted:   'warning',
    return_updated:     'info',
  };
  function typeToState(type) { return _TYPE_STATE[type] || 'info'; }

  /* ── Schedule next poll ─────────────────────────────────────────────────── */
  function schedule(delay) {
    if (_timer) clearTimeout(_timer);
    _timer = setTimeout(poll, delay);
  }

  /* ── Phase 1: Seed ──────────────────────────────────────────────────────── */
  function seed() {
    fetch(POLL_URL + '?limit=50&unread_only=1', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !Array.isArray(data.notifications)) return;
        var rows = data.notifications;
        if (window.Kz && window.Kz.seed) window.Kz.seed(rows);
        var ts = newestTs(rows);
        if (ts) setSince(ts);
      })
      .catch(function () {})
      .finally(function () {
        // Start phase-2 after seed
        schedule(POLL_FAST);
      });
  }

  /* ── Phase 2: Smart poll ────────────────────────────────────────────────── */
  function poll() {
    if (_paused || _running) return;

    var since = getSince();
    if (!since) { schedule(POLL_FAST); return; }

    _running = true;
    fetch(POLL_URL + '?since=' + encodeURIComponent(since), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !Array.isArray(data.notifications)) {
          _emptyCount++;
        } else {
          var rows = data.notifications;
          if (!rows.length) {
            _emptyCount++;
          } else {
            // Got new notifications — reset to fast mode
            _emptyCount = 0;

            rows.filter(function (n) { return !n.is_read; })
                .slice().reverse()
                .forEach(function (n) {
                  if (window.Kz && window.Kz.show) {
                    var nd = (n.data && typeof n.data === 'object') ? n.data : {};
                    window.Kz.show(typeToState(n.type), n.title, n.body || '', null,
                      { data: nd, type: n.type || null });
                  }
                });

            var ts = newestTs(rows);
            if (ts) setSince(ts);
          }
        }
      })
      .catch(function () { _emptyCount++; })
      .finally(function () {
        _running = false;
        // Use slow interval after IDLE_ROUNDS consecutive empty polls
        schedule(_emptyCount >= IDLE_ROUNDS ? POLL_SLOW : POLL_FAST);
      });
  }

  /* ── Page Visibility API — pause / resume ───────────────────────────────── */
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      _paused = true;
      if (_timer) { clearTimeout(_timer); _timer = null; }
    } else {
      // Tab just became visible — snap back to fast mode immediately
      _paused = false;
      _emptyCount = 0;
      poll();
    }
  });

  /* ── Wire "Clear all" ───────────────────────────────────────────────────── */
  function wireMarkAllRead() {
    var clearBtn = document.getElementById('kz-panel-clear');
    if (!clearBtn || clearBtn._kzWired) return;
    clearBtn._kzWired = true;
    clearBtn.addEventListener('click', function () {
      fetch(MARK_ALL_URL, { method: 'POST', credentials: 'same-origin' })
        .catch(function () {});
    });
  }

  /* ── Boot ───────────────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var meta = document.querySelector('meta[name="kz-uid"]');
    if (!meta || !meta.content) return;

    wireMarkAllRead();
    setTimeout(seed, 900);   // seed runs once; schedules phase-2 when done
  });

})();

