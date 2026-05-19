/**
 * kidzora-push.js
 * ───────────────
 * Web Push (VAPID) subscription management for the KidZora frontend.
 *
 * Behaviour:
 *  • Registers /sw.js as a Service Worker scoped to the whole origin.
 *  • Fetches the VAPID public key from /api/v1/notifications/vapid-public-key.
 *  • Subscribes the browser and POSTs the endpoint + keys to the backend.
 *  • For riders: automatically prompts for permission after 3 s on first visit
 *    (if not already asked); silently re-registers on subsequent visits when
 *    permission is already granted.
 *  • For all roles: exposes window.KzPush.subscribe() / .unsubscribe().
 *  • Provides a navbar toggle button (#kzPushToggleBtn) to enable/disable.
 *
 * Requires:
 *  • <meta name="kz-uid" content="..."> (logged-in user)
 *  • <meta name="kz-role" content="rider|buyer|seller|admin">
 *  • kidzora-toast.js loaded first (optional — used for success toast)
 *
 * If the browser does not support Service Workers or PushManager the script
 * exits silently without errors.
 */
(function () {
  'use strict';

  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

  /* ── Constants ──────────────────────────────────────────────────────── */
  var SW_URL          = '/sw.js';
  var VAPID_URL       = '/api/v1/notifications/vapid-public-key';
  var SUBSCRIBE_URL   = '/api/v1/notifications/subscribe';
  var UNSUBSCRIBE_URL = '/api/v1/notifications/unsubscribe';
  var LS_ASKED        = 'kzPushAsked_v1';

  /* ── Helpers ────────────────────────────────────────────────────────── */
  function _uid() {
    var m = document.querySelector('meta[name="kz-uid"]');
    return (m && m.content) ? m.content : null;
  }

  function _role() {
    var m = document.querySelector('meta[name="kz-role"]');
    return (m && m.content) ? m.content : '';
  }

  /** Convert a base64url string → Uint8Array for applicationServerKey */
  function _b64ToUint8(b64) {
    var padding = '='.repeat((4 - (b64.length % 4)) % 4);
    var base64  = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/');
    var raw     = atob(base64);
    var result  = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) result[i] = raw.charCodeAt(i);
    return result;
  }

  function _post(url, body) {
    return fetch(url, {
      method:      'POST',
      credentials: 'same-origin',
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function _getVapidKey() {
    return fetch(VAPID_URL, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) { return d.key || null; });
  }

  /* ── Core: register SW → get VAPID key → subscribe → POST to backend ─ */
  function _registerAndSubscribe() {
    return navigator.serviceWorker.register(SW_URL, { scope: '/' })
      .then(function (reg) {
        return _getVapidKey().then(function (key) {
          if (!key) return Promise.reject(new Error('VAPID key not configured'));
          return reg.pushManager.getSubscription().then(function (existing) {
            if (existing) return existing;
            return reg.pushManager.subscribe({
              userVisibleOnly:      true,
              applicationServerKey: _b64ToUint8(key),
            });
          });
        });
      })
      .then(function (sub) {
        var json = sub.toJSON();
        return _post(SUBSCRIBE_URL, {
          endpoint: sub.endpoint,
          p256dh:   json.keys && json.keys.p256dh,
          auth:     json.keys && json.keys.auth,
        });
      });
  }

  /* ── Update push toggle button UI ──────────────────────────────────── */
  function _updateBell(on) {
    var btn = document.getElementById('kzPushToggleBtn');
    if (!btn) return;
    if (on) {
      btn.innerHTML           = '<i class="fas fa-bell text-white" style="font-size:.9rem;"></i>';
      btn.title               = 'Push alerts ON — click to disable';
      btn.dataset.pushEnabled = 'true';
    } else {
      btn.innerHTML           = '<i class="fas fa-bell-slash" style="font-size:.9rem;opacity:.5;color:#fff;"></i>';
      btn.title               = 'Push alerts OFF — click to enable';
      btn.dataset.pushEnabled = 'false';
    }
  }

  /* ── Prompt banner ──────────────────────────────────────────────────── */
  function _showPromptBanner() {
    if (document.getElementById('kzPushBanner')) return;

    var banner = document.createElement('div');
    banner.id  = 'kzPushBanner';
    banner.setAttribute('role', 'alert');
    banner.innerHTML =
      '<div style="display:flex;align-items:center;gap:.75rem;">' +
        '<i class="fas fa-bell" style="font-size:1.2rem;flex-shrink:0;"></i>' +
        '<div style="flex:1;min-width:0;">' +
          '<strong>Enable delivery alerts</strong>' +
          '<div style="font-size:.8rem;opacity:.8;margin-top:.1rem;">' +
            'Get notified instantly when new pickups are available — even when the app is closed.' +
          '</div>' +
        '</div>' +
        '<button id="kzPushAllow" style="flex-shrink:0;background:#fff;color:#166534;border:none;' +
          'border-radius:8px;padding:.35rem .8rem;font-weight:700;font-size:.8rem;cursor:pointer;">' +
          'Enable' +
        '</button>' +
        '<button id="kzPushDismiss" style="flex-shrink:0;background:none;border:none;' +
          'color:rgba(255,255,255,.6);font-size:1.1rem;cursor:pointer;padding:0 .25rem;">' +
          '&times;' +
        '</button>' +
      '</div>';

    Object.assign(banner.style, {
      position:     'fixed',
      bottom:       '1.25rem',
      left:         '50%',
      transform:    'translateX(-50%)',
      background:   '#166534',
      color:        '#fff',
      padding:      '.85rem 1.1rem',
      borderRadius: '14px',
      boxShadow:    '0 6px 24px rgba(0,0,0,.35)',
      zIndex:       '9000',
      maxWidth:     '480px',
      width:        'calc(100% - 2rem)',
      transition:   'opacity .3s',
    });

    document.body.appendChild(banner);

    document.getElementById('kzPushAllow').addEventListener('click', function () {
      banner.style.opacity = '0';
      setTimeout(function () { if (banner.parentNode) banner.parentNode.removeChild(banner); }, 300);

      window.KzPush.subscribe()
        .then(function (res) {
          if (res && res.ok !== false) {
            _updateBell(true);
            if (window.Kz) window.Kz.success('Alerts enabled', 'You\'ll receive instant pickup notifications.');
          } else {
            _updateBell(false);
          }
        })
        .catch(function () { _updateBell(false); });
    });

    document.getElementById('kzPushDismiss').addEventListener('click', function () {
      banner.style.opacity = '0';
      setTimeout(function () { if (banner.parentNode) banner.parentNode.removeChild(banner); }, 300);
      localStorage.setItem(LS_ASKED, 'dismissed');
    });
  }

  /* ── Public API ─────────────────────────────────────────────────────── */
  window.KzPush = {
    /**
     * Request permission + subscribe. Returns a Promise<{ok: bool}>.
     * Safe to call multiple times — idempotent.
     */
    subscribe: function () {
      if (!_uid()) return Promise.reject(new Error('Not logged in'));
      return Notification.requestPermission().then(function (perm) {
        localStorage.setItem(LS_ASKED, '1');
        if (perm !== 'granted') return { ok: false, reason: 'denied' };
        return _registerAndSubscribe();
      });
    },

    /** Unsubscribe from Web Push and remove the backend record. */
    unsubscribe: function () {
      return navigator.serviceWorker.getRegistration(SW_URL)
        .then(function (reg) {
          if (!reg) return;
          return reg.pushManager.getSubscription()
            .then(function (sub) {
              if (!sub) return;
              return sub.unsubscribe().then(function () {
                return _post(UNSUBSCRIBE_URL, { endpoint: sub.endpoint });
              });
            });
        });
    },

    /** 'granted' | 'denied' | 'default' */
    permissionState: function () { return Notification.permission; },
  };

  /* ── Auto-init on DOMContentLoaded ─────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    if (!_uid()) return;

    var perm = Notification.permission;

    // Wire the push toggle button (rider navbar)
    var toggleBtn = document.getElementById('kzPushToggleBtn');
    if (toggleBtn) {
      _updateBell(perm === 'granted');
      toggleBtn.addEventListener('click', function () {
        if (toggleBtn.dataset.pushEnabled === 'true') {
          window.KzPush.unsubscribe().then(function () { _updateBell(false); }).catch(function () {});
        } else {
          window.KzPush.subscribe()
            .then(function (res) { _updateBell(res && res.ok !== false); })
            .catch(function () {});
        }
      });
    }

    // Rider auto-prompt / silent re-register
    if (_role() === 'rider') {
      if (perm === 'granted') {
        // Already granted — silently re-register so SW stays fresh
        _registerAndSubscribe().catch(function () {});
        _updateBell(true);
        return;
      }

      if (perm === 'denied') {
        _updateBell(false);
        return;
      }

      // 'default' — show prompt once (unless already dismissed)
      var asked = localStorage.getItem(LS_ASKED);
      if (!asked) {
        setTimeout(_showPromptBanner, 3000);
      }
    }
  });

})();
