/*!
 * KidZora Toast  v1.1
 * Sileo-inspired pill toasts — top-right, gooey SVG, spring physics
 * + Notification bell panel with history
 *
 * Public API:
 *   Kz.success(title [, description])
 *   Kz.error  (title [, description])
 *   Kz.warning(title [, description])
 *   Kz.info   (title [, description])
 *   Kz.show   (state, title [, description [, duration_ms]])
 *   Kz.dismiss(toastEl)
 */
(function () {
  'use strict';

  /* ── Constants ──────────────────────────────────────────── */
  var DUR            = 600;
  var TIMEOUT        = 6000;
  var EXPAND_DELAY   = 150;
  var COLLAPSE_DELAY = 150;
  var MAX_HISTORY    = 50;

  /* ── Per-user storage key ────────────────────────────────── */
  // Each logged-in user gets their own sessionStorage bucket so notifications
  // never bleed across accounts sharing the same browser.
  var _uid = (function () {
    var m = document.querySelector('meta[name="kz-uid"]');
    return (m && m.content) ? m.content.replace(/[^a-zA-Z0-9_-]/g, '') : 'guest';
  })();
  var STORAGE_KEY = 'kz_notif_v3_' + _uid;

  // Purge stale buckets from other users so sessionStorage doesn't grow unbounded
  (function () {
    try {
      var toRemove = [];
      for (var i = 0; i < sessionStorage.length; i++) {
        var k = sessionStorage.key(i);
        if (k && k.indexOf('kz_notif_v3_') === 0 && k !== STORAGE_KEY) {
          toRemove.push(k);
        }
      }
      toRemove.forEach(function (k) { sessionStorage.removeItem(k); });
    } catch (e) {}
  })();

  /* ── SVG Icons ───────────────────────────────────────────── */
  var ICONS = {
    success: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    error:   '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
    warning: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    info:    '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  };
  var CLOSE_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';

  /* ── Avatar colours (deterministic from sender id) ──────── */
  var _AV_COLORS = [
    '#e05f6a','#e87d3c','#d4a83a','#4caf72',
    '#3a9fd4','#7b64c8','#d45fa0','#3abcb2',
  ];
  function avatarColor(seed) {
    var h = 5381;
    for (var i = 0; i < seed.length; i++) h = ((h * 33) ^ seed.charCodeAt(i)) >>> 0;
    return _AV_COLORS[h % _AV_COLORS.length];
  }

  /* ── Flask category → state ──────────────────────────────── */
  var CAT_MAP = {
    success: 'success', danger: 'error', error: 'error',
    warning: 'warning', info: 'info', primary: 'info',
    secondary: 'info', light: 'info', dark: 'info',
    auth_popup: 'success',
  };

  /* ── Helpers ─────────────────────────────────────────────── */
  function esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  }

  function timeAgo(ts) {
    var diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 5)  return 'just now';
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff/60) + 'm ago';
    if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
    return Math.floor(diff/86400) + 'd ago';
  }

  /* ── Notification history (sessionStorage) ───────────────── */
  var _history = (function () {
    try { return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]'); }
    catch(e) { return []; }
  })();
  var _unreadCount = _history.filter(function(n){ return !n.read; }).length;

  function saveHistory() {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(_history)); }
    catch(e) {}
  }

  function pushHistory(state, title, desc, dbId, data, type) {
    // Deduplicate by dbId (DB notification id) so re-seeding is idempotent
    if (dbId && _history.some(function(n){ return n.dbId === dbId; })) return;
    _history.unshift({ state: state, title: title, desc: desc || null, ts: Date.now(), read: false, dbId: dbId || null, data: data || null, type: type || null });
    if (_history.length > MAX_HISTORY) _history.length = MAX_HISTORY;
    _unreadCount++;
    saveHistory();
    updateBadge();
    renderPanel();
  }

  function markAllRead() {
    _history.forEach(function(n){ n.read = true; });
    _unreadCount = 0;
    saveHistory();
    updateBadge();
    renderPanel();
  }

  function clearHistory() {
    _history.length = 0;
    _unreadCount = 0;
    saveHistory();
    updateBadge();
    renderPanel();
  }

  /* ── Bell badge ──────────────────────────────────────────── */
  function updateBadge() {
    var badge = document.getElementById('kz-bell-badge');
    if (!badge) return;
    if (_unreadCount > 0) {
      badge.textContent = _unreadCount > 99 ? '99+' : String(_unreadCount);
      badge.classList.add('kz-visible');
    } else {
      badge.textContent = '';
      badge.classList.remove('kz-visible');
    }
  }

  /* ── Panel render ────────────────────────────────────────── */
  function renderPanel() {
    var list = document.getElementById('kz-panel-list');
    var empty = document.getElementById('kz-panel-empty');
    if (!list) return;

    if (_history.length === 0) {
      list.innerHTML = '';
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';

    list.innerHTML = _history.map(function(n, idx) {
      return '<div class="kz-notif-row' + (n.read ? '' : ' kz-unread') + '" data-state="' + esc(n.state) + '" data-idx="' + idx + '">' +
        '<div class="kz-notif-dot">' + (ICONS[n.state] || ICONS.info) + '</div>' +
        '<div class="kz-notif-body">' +
          '<div class="kz-notif-title">' + esc(n.title) + '</div>' +
          '<div class="kz-notif-time">' + timeAgo(n.ts) + '</div>' +
        '</div>' +
        (n.desc ? '<div class="kz-notif-chevron">&#8250;</div>' : '') +
        '<div class="kz-notif-unread-dot"></div>' +
      '</div>';
    }).join('');
  }

  /* ── Detail view ─────────────────────────────────────────── */

  /* Reconstruct destination URL from type + stored data IDs + current user role */
  function resolveUrl(n) {
    if (n.data && n.data.url) return n.data.url;   // explicit always wins

    var d    = n.data || {};
    var type = n.type || '';
    var oid  = d.order_id || null;
    var rrId = d.rr_id    || null;

    // Infer role from current page path
    var p    = window.location.pathname || '';
    var role = p.indexOf('/seller') === 0 ? 'seller'
             : p.indexOf('/admin')  === 0 ? 'admin'
             : p.indexOf('/rider')  === 0 ? 'rider'
             : 'buyer';

    // Message received — link to the relevant chat page
    if (type === 'message_received' && d.sender_id) {
      if (role === 'seller') return '/seller/chat/' + d.sender_id;
      if (role === 'buyer')  return '/buyer/chat/'  + d.sender_id;
      if (role === 'admin')  return '/admin/chat/'  + d.sender_id;
      if (role === 'rider')  return '/rider/chat/'  + d.sender_id;
    }

    // Return / refund
    if (type === 'return_updated') {
      if (rrId) return '/buyer/returns/' + rrId;
      if (oid)  return '/buyer/orders/'  + oid;
    }
    if (type === 'return_submitted') {
      if (role === 'admin'  && rrId) return '/admin/returns/'  + rrId;
      if (role === 'seller' && rrId) return '/seller/returns/' + rrId;
      if (role === 'admin')          return '/admin/returns';
      if (role === 'seller' && oid)  return '/seller/orders/'  + oid;
    }

    // Order events
    if (oid) {
      if (type === 'order_placed' || type === 'cancel_request' || type === 'order_completed')
        return '/seller/orders/' + oid;
      if (role === 'seller') return '/seller/orders/'    + oid;
      if (role === 'rider')  return '/rider/deliveries/' + oid;
      if (role === 'admin')  return '/admin/orders/'     + oid;
      return '/buyer/orders/' + oid;
    }

    // Last-resort: if this toast fired while on an order detail page, link back to it
    var orderMatch = p.match(/\/(buyer|seller|admin|rider)\/orders\/([0-9a-f-]+)/i);
    if (!orderMatch) orderMatch = p.match(/\/(rider)\/deliveries\/([0-9a-f-]+)/i);
    if (orderMatch) return p;

    return null;
  }

  /* ── Action label by notification type ─────────────────── */
  var ACTION_LABELS = {
    order_placed:       'View Order →',
    order_confirmed:    'View Order →',
    order_preparing:    'View Order →',
    order_ready_pickup: 'View Order →',
    order_out_delivery: 'Track Order →',
    order_delivered:    'Confirm Receipt →',
    order_completed:    'View Order →',
    order_cancelled:    'View Order →',
    cancel_request:     'Review Request →',
    cancel_approved:    'View Order →',
    cancel_rejected:    'View Order →',
    return_submitted:   'View Return →',
    return_updated:     'View Return →',
    message_received:   'Open Chat →',
  };

  function openDetail(n) {
    var detail = document.getElementById('kz-panel-detail');
    var panel  = document.getElementById('kz-panel');
    var body   = document.getElementById('kz-panel-detail-body');
    if (!detail || !body) return;
    var iconHtml   = ICONS[n.state] || ICONS.info;
    var actionUrl  = resolveUrl(n);
    var actionLabel = (n.type && ACTION_LABELS[n.type]) ? ACTION_LABELS[n.type] : 'View Details \u2192';
    body.innerHTML =
      '<div class="kz-detail-header-row">' +
        '<div class="kz-detail-icon" data-state="' + esc(n.state) + '">' + iconHtml + '</div>' +
        '<div class="kz-detail-title">' + esc(n.title) + '</div>' +
      '</div>' +
      (n.desc
        ? '<div class="kz-detail-desc">'  + esc(n.desc) + '</div>'
        : '<div class="kz-detail-no-desc">No additional details.</div>') +
      '<div class="kz-detail-time">' + timeAgo(n.ts) + '</div>' +
      (actionUrl
        ? '<a class="kz-detail-action" href="' + esc(actionUrl) + '">' + actionLabel + '</a>'
        : '');
    detail.classList.add('kz-detail-open');
    if (panel) panel.classList.add('kz-panel-detail-mode');
  }

  function closeDetail() {
    var detail = document.getElementById('kz-panel-detail');
    var panel  = document.getElementById('kz-panel');
    if (detail) detail.classList.remove('kz-detail-open');
    if (panel)  panel.classList.remove('kz-panel-detail-mode');
  }

  /* ── Panel toggle ────────────────────────────────────────── */
  var _panelOpen = false;

  function openPanel() {
    var panel = document.getElementById('kz-panel');
    if (!panel) return;
    renderPanel();
    panel.classList.add('kz-panel-open');
    _panelOpen = true;
    markAllRead();
  }

  function closePanel() {
    var panel = document.getElementById('kz-panel');
    if (!panel) return;
    panel.classList.remove('kz-panel-open');
    _panelOpen = false;
  }

  function togglePanel() {
    _panelOpen ? closePanel() : openPanel();
  }

  /* ── Inject gooey filter ─────────────────────────────────── */
  function ensureGooeyFilter() {
    if (document.getElementById('kz-filter-svg')) return;
    var ns  = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.id = 'kz-filter-svg';
    svg.setAttribute('aria-hidden', 'true');
    svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none;';
    svg.innerHTML =
      '<defs><filter id="kz-gooey" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">' +
        '<feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur"/>' +
        '<feColorMatrix in="blur" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -10" result="goo"/>' +
        '<feComposite in="SourceGraphic" in2="goo" operator="atop"/>' +
      '</filter></defs>';
    document.body.appendChild(svg);
  }

  /* ── Viewport ────────────────────────────────────────────── */
  function getViewport() {
    var vp = document.getElementById('kz-viewport');
    if (!vp) {
      vp = document.createElement('div');
      vp.id = 'kz-viewport';
      vp.setAttribute('aria-live', 'polite');
      vp.setAttribute('aria-label', 'Notifications');
      document.body.appendChild(vp);
    }
    return vp;
  }

  /* ── Messenger-style message toast ─────────────────────── */
  function buildMsgToast(state, title, desc, duration, opts) {
    var timeout = (duration != null) ? duration : TIMEOUT;
    var data    = (opts && opts.data) ? opts.data : {};

    if (!(opts && opts.noHistory)) {
      pushHistory(state, title, desc, null, data, (opts && opts.type) || null);
    }

    ensureGooeyFilter();
    var vp = getViewport();

    var senderName = data.sender_name
      || (title ? title.replace(/^New message from\s*/i, '') : 'Someone');
    var avInitial  = data.avatar_initial || (senderName ? senderName.charAt(0).toUpperCase() : '?');
    var avColor    = avatarColor(data.sender_id || senderName || 'x');
    var avUrl      = (data.avatar_url && data.avatar_url.trim()) ? data.avatar_url.trim() : null;
    var msgText    = desc || '';
    var actionUrl  = resolveUrl({ data: data, type: (opts && opts.type) || '' });

    var toast = document.createElement('div');
    toast.className = 'kz-toast kz-toast--msg';
    toast.setAttribute('data-state', state);
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-label', 'Message from ' + senderName);

    var avHtml = avUrl
      ? '<img src="' + esc(avUrl) + '" class="kz-msg-av-img" alt="">'
      : '<div class="kz-msg-av" style="background:' + avColor + '">' + esc(avInitial) + '</div>';

    toast.innerHTML =
      '<div class="kz-shapes"></div>' +
      '<div class="kz-msg-row">' +
        '<div class="kz-msg-av-wrap">' + avHtml + '</div>' +
        '<div class="kz-msg-content">' +
          '<div class="kz-msg-name">' + esc(senderName) + '</div>' +
          (msgText ? '<div class="kz-msg-text">' + esc(msgText) + '</div>' : '') +
        '</div>' +
      '</div>' +
      (actionUrl
        ? '<div class="kz-actions"><a class="kz-action-btn kz-action-link kz-msg-open" href="' + esc(actionUrl) + '">Open Chat \u2192</a></div>'
        : '') +
      (timeout > 0 ? '<div class="kz-progress" style="--kz-timeout:' + (timeout / 1000) + 's"></div>' : '');

    vp.appendChild(toast);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { toast.classList.add('kz-ready'); });
    });

    var dismissTimer = null;
    function startDismissTimer() {
      if (timeout <= 0) return;
      clearTimeout(dismissTimer);
      dismissTimer = setTimeout(function () { dismiss(toast); }, timeout);
    }
    startDismissTimer();
    toast.addEventListener('mouseenter', function () { clearTimeout(dismissTimer); });
    toast.addEventListener('mouseleave', function () { startDismissTimer(); });
    toast.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('.kz-action-btn')) return;
      if (actionUrl) { window.location.href = actionUrl; }
      else { dismiss(toast); }
    });
    var swipeStartY = null;
    toast.addEventListener('touchstart', function (e) { swipeStartY = e.touches[0].clientY; }, { passive: true });
    toast.addEventListener('touchend', function (e) {
      if (swipeStartY === null) return;
      if (e.changedTouches[0].clientY - swipeStartY > 30) dismiss(toast);
      swipeStartY = null;
    }, { passive: true });

    return toast;
  }

  /* ── Core: create toast ──────────────────────────────────── */
  function createToast(state, title, desc, duration, opts) {
    // Delegate message notifications to the Messenger-style builder
    if (opts && opts.type === 'message_received') {
      return buildMsgToast(state, title, desc, duration, opts);
    }

    var timeout = (duration != null) ? duration : TIMEOUT;
    var action  = (opts && opts.action) ? opts.action : null;

    // Record in history unless explicitly suppressed (e.g. auth toasts)
    if (!(opts && opts.noHistory)) {
      pushHistory(state, title, desc, null,
        (opts && opts.data) ? opts.data : null,
        (opts && opts.type) ? opts.type : null);
    }

    ensureGooeyFilter();
    var vp = getViewport();

    var toast = document.createElement('div');
    toast.className = 'kz-toast';
    toast.setAttribute('data-state', state);
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-label', state + ': ' + title);

    // Hidden shapes layer (no-op, kept for filter compatibility)
    var shapes = document.createElement('div');
    shapes.className = 'kz-shapes';
    toast.appendChild(shapes);

    // Header: pill chip aligned to top-right
    var header = document.createElement('div');
    header.className = 'kz-header';
    var headPill = document.createElement('div');
    headPill.className = 'kz-head-pill';
    headPill.innerHTML =
      '<div class="kz-badge">' + (ICONS[state] || ICONS.info) + '</div>' +
      '<span class="kz-title">' + esc(title) + '</span>';
    header.appendChild(headPill);
    toast.appendChild(header);

    // Description (always visible)
    if (desc) {
      var descEl = document.createElement('div');
      descEl.className = 'kz-desc';
      descEl.textContent = desc;
      toast.appendChild(descEl);
    }

    // Auto-derive action from type+data if the caller didn't provide one explicitly
    if (!action && opts && opts.type) {
      var _n   = { data: opts.data || {}, type: opts.type };
      var _url = resolveUrl(_n);
      if (_url) {
        action = {
          label: ACTION_LABELS[opts.type] || 'View Details \u2192',
          url:   _url,
        };
      }
    }

    // Optional action button
    if (action) {
      var actionsEl = document.createElement('div');
      actionsEl.className = 'kz-actions';
      var actionBtn;
      if (action.url) {
        // Link-style action — navigate on click
        actionBtn = document.createElement('a');
        actionBtn.className = 'kz-action-btn kz-action-link';
        actionBtn.href = action.url;
        actionBtn.textContent = action.label || 'View \u2192';
        actionBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          dismiss(toast);
        });
      } else {
        // Callback-style action
        actionBtn = document.createElement('button');
        actionBtn.className = 'kz-action-btn';
        actionBtn.type = 'button';
        actionBtn.textContent = action.label || 'OK';
        actionBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          if (action.callback) action.callback();
          dismiss(toast);
        });
      }
      actionsEl.appendChild(actionBtn);
      toast.appendChild(actionsEl);
    }

    // Progress bar
    if (timeout > 0) {
      var progress = document.createElement('div');
      progress.className = 'kz-progress';
      progress.style.setProperty('--kz-timeout', (timeout / 1000) + 's');
      toast.appendChild(progress);
    }

    vp.appendChild(toast);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { toast.classList.add('kz-ready'); });
    });

    /* ── Timers ── */
    var dismissTimer = null;
    function startDismissTimer() {
      if (timeout <= 0) return;
      clearTimeout(dismissTimer);
      dismissTimer = setTimeout(function () { dismiss(toast); }, timeout);
    }
    startDismissTimer();

    // Pause timer on hover
    toast.addEventListener('mouseenter', function () { clearTimeout(dismissTimer); });
    toast.addEventListener('mouseleave', function () { startDismissTimer(); });

    toast.addEventListener('click', function (e) {
      // Don't dismiss if clicking action button
      if (e.target.closest && e.target.closest('.kz-action-btn')) return;
      dismiss(toast);
    });

    var swipeStartY = null;
    toast.addEventListener('touchstart', function (e) { swipeStartY = e.touches[0].clientY; }, { passive: true });
    toast.addEventListener('touchend', function (e) {
      if (swipeStartY === null) return;
      if (e.changedTouches[0].clientY - swipeStartY > 30) dismiss(toast);
      swipeStartY = null;
    }, { passive: true });

    return toast;
  }

  /* ── Dismiss ─────────────────────────────────────────────── */
  function dismiss(toast) {
    if (!toast || toast.classList.contains('kz-exit')) return;
    toast.classList.add('kz-exit');
    setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, DUR);
  }

  /* ── Public API ──────────────────────────────────────────── */
  var TYPE_STATE_MAP = {
    order_placed:      'info',    order_confirmed:   'success',
    order_preparing:   'info',    order_ready_pickup:'info',
    order_out_delivery:'warning', order_delivered:   'success',
    order_completed:   'success', order_cancelled:   'error',
    cancel_request:    'warning', cancel_approved:   'success',
    cancel_rejected:   'error',   message_received:  'info',
    return_submitted:  'warning', return_updated:    'info',
  };

  window.Kz = {
    success: function (title, desc, opts)             { return createToast('success', title, desc, null, opts); },
    error:   function (title, desc, opts)             { return createToast('error',   title, desc, null, opts); },
    warning: function (title, desc, opts)             { return createToast('warning', title, desc, null, opts); },
    info:    function (title, desc, opts)             { return createToast('info',    title, desc, null, opts); },
    show:    function (state, title, desc, dur, opts) { return createToast(state,     title, desc, dur,  opts); },
    dismiss: dismiss,
    /**
     * Silently pre-populate the bell panel from a DB notification array.
     * No toasts are shown — just the bell badge + panel entries.
     * Rows are added oldest-first so the panel is sorted newest-first.
     * Already-seen rows (by dbId) are skipped.
     *
     * @param {Array<{id,type,title,body,is_read,created_at}>} rows
     */
    seed: function (rows) {
      if (!Array.isArray(rows) || rows.length === 0) return;
      // Add oldest first so unshift produces newest-at-top order
      var sorted = rows.slice().sort(function(a,b){
        return new Date(a.created_at) - new Date(b.created_at);
      });
      var added = 0;
      sorted.forEach(function(row) {
        if (!row || !row.id) return;
        if (_history.some(function(n){ return n.dbId === row.id; })) return;
        var state = TYPE_STATE_MAP[row.type] || 'info';
        var ts    = row.created_at ? new Date(row.created_at).getTime() : Date.now();
        _history.unshift({
          state: state,
          title: row.title || '(no title)',
          desc:  row.body  || null,
          ts:    ts,
          read:  !!row.is_read,
          dbId:  row.id,
          data:  (row.data && typeof row.data === 'object') ? row.data : null,
          type:  row.type || null,
        });
        if (!row.is_read) _unreadCount++;
        added++;
      });
      if (added > 0) {
        if (_history.length > MAX_HISTORY) _history.length = MAX_HISTORY;
        saveHistory();
        updateBadge();
        renderPanel();
      }
    },
  };

  /* ── Boot: wire bell + fire flash messages ───────────────── */
  document.addEventListener('DOMContentLoaded', function () {

    /* Bell button */
    var bellBtn = document.getElementById('kz-bell-btn');
    if (bellBtn) {
      bellBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        togglePanel();
      });
    }

    /* Clear all button */
    var clearBtn = document.getElementById('kz-panel-clear');
    if (clearBtn) {
      clearBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        clearHistory();
      });
    }

    /* Row click → open detail view */
    var panelList = document.getElementById('kz-panel-list');
    if (panelList) {
      panelList.addEventListener('click', function (e) {
        var row = e.target.closest ? e.target.closest('.kz-notif-row') : null;
        if (!row) return;
        var idx = parseInt(row.getAttribute('data-idx'), 10);
        if (!isNaN(idx) && _history[idx]) openDetail(_history[idx]);
      });
    }

    /* Back button in detail view */
    var backBtn = document.getElementById('kz-panel-back');
    if (backBtn) {
      backBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        closeDetail();
      });
    }

    /* Click outside closes panel */

    document.addEventListener('click', function (e) {
      if (!_panelOpen) return;
      var panel = document.getElementById('kz-panel');
      if (panel && !panel.contains(e.target) && e.target !== bellBtn) {
        closePanel();
      }
    });

    /* Initialise badge from stored history */
    updateBadge();

    /* Flash messages */
    var node = document.getElementById('kz-flash-data');
    if (!node) return;
    var messages;
    try { messages = JSON.parse(node.textContent || node.innerText); }
    catch (e) { return; }
    if (!Array.isArray(messages)) return;
    messages.forEach(function (pair, i) {
      var cat   = pair[0];
      var state = CAT_MAP[cat] || 'info';
      var parts  = String(pair[1]).split('||');
      var title  = parts[0].trim();
      var desc   = parts.length > 1 ? parts[1].trim() : null;
      var opts   = (cat === 'auth_popup') ? { noHistory: true } : null;
      setTimeout(function () { Kz.show(state, title, desc, null, opts); }, i * 160);
    });
  });

})();
