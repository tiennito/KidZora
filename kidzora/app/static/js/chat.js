/**
 * KidZora Chat – chat window logic
 *
 * Requires a hidden config element in the page:
 *   <div id="chatConfig" hidden
 *        data-my-id="<user_id>"
 *        data-send-url="<send endpoint>"
 *        data-poll-url="<poll endpoint>"
 *        data-typing-url="<typing endpoint>"></div>
 */
(function () {
  'use strict';

  // ── Read config injected by the template ────────────────────
  var cfg = document.getElementById('chatConfig');
  if (!cfg) return;

  var MY_ID      = cfg.dataset.myId;
  var SEND_URL   = cfg.dataset.sendUrl;
  var POLL_URL   = cfg.dataset.pollUrl;
  var TYPING_URL = cfg.dataset.typingUrl;
  var OTHER_AV      = cfg.dataset.otherAv      || '';
  var OTHER_INITIAL = cfg.dataset.otherInitial  || '?';

  // ── DOM refs ─────────────────────────────────────────────────
  var area      = document.getElementById('msgArea');
  var form      = document.getElementById('chatForm');
  var input     = document.getElementById('msgInput');
  var sendBtn   = document.getElementById('sendBtn');
  var typingRow = document.getElementById('typingRow');

  // ── Scroll ───────────────────────────────────────────────────
  function scrollBottom(force) {
    var atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
    if (force || atBottom) area.scrollTop = area.scrollHeight;
  }
  // Initial scroll — runs at DOM-ready, then again after fonts/images settle.
  scrollBottom(true);
  window.addEventListener('load', function () {
    scrollBottom(true);
    // One extra rAF for any reflow triggered by images/fonts after 'load'
    requestAnimationFrame(function () { scrollBottom(true); });
  });

  // ── Auto-grow textarea ───────────────────────────────────────
  input.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });

  // ── Helpers ──────────────────────────────────────────────────
  function fmtTime(iso) { return iso ? iso.substring(11, 16) : ''; }

  function tickHtml(m) {
    if (m.is_read)      return '<i class="fas fa-check-double ms-1 kz-tick-seen" style="font-size:.65rem"></i>';
    if (m.is_delivered) return '<i class="fas fa-check-double ms-1 kz-tick-delivered" style="font-size:.65rem"></i>';
    return                     '<i class="fas fa-check ms-1 kz-tick-sent" style="font-size:.65rem"></i>';
  }

  function buildBubble(m) {
    var isMine = String(m.sender_id) === String(MY_ID);

    var row = document.createElement('div');
    row.className = 'kz-bubble-row ' + (isMine ? 'mine' : 'theirs');
    row.dataset.ts = m.created_at || '';
    row.dataset.id = m.id || '';

    // Peer avatar (only for their messages)
    if (!isMine) {
      var avEl = document.createElement('div');
      if (OTHER_AV) {
        avEl.className = 'kz-peer-av kz-peer-av--photo';
        var img = document.createElement('img');
        img.src = OTHER_AV;
        img.alt = '';
        avEl.appendChild(img);
      } else {
        avEl.className = 'kz-peer-av';
        avEl.textContent = OTHER_INITIAL;
      }
      row.appendChild(avEl);
    }

    var bub = document.createElement('div');
    bub.className = 'kz-bubble';
    bub.textContent = m.content;

    var time = document.createElement('span');
    time.className = 'kz-bubble-time';
    time.innerHTML = fmtTime(m.created_at) + (isMine ? ' ' + tickHtml(m) : '');

    row.appendChild(bub);
    row.appendChild(time);
    return row;
  }

  // ── Refresh tick icons on existing bubbles ───────────────────
  function refreshTicks(msgs) {
    msgs.forEach(function (m) {
      if (String(m.sender_id) !== String(MY_ID)) return;
      var row = area.querySelector('[data-id="' + m.id + '"]');
      if (!row) return;
      var timeEl = row.querySelector('.kz-bubble-time');
      if (timeEl) timeEl.innerHTML = fmtTime(m.created_at) + ' ' + tickHtml(m);
    });
  }

  // ── Latest timestamp currently rendered ─────────────────────
  function latestTs() {
    var rows = area.querySelectorAll('.kz-bubble-row[data-ts]');
    var ts = '';
    rows.forEach(function (r) { if (r.dataset.ts > ts) ts = r.dataset.ts; });
    return ts;
  }

  // ── Typing signal ────────────────────────────────────────────
  var _typingTimer = null;
  input.addEventListener('input', function () {
    clearTimeout(_typingTimer);
    fetch(TYPING_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: '{}',
    }).catch(function () {});
    _typingTimer = setTimeout(function () {}, 3000);
  });

  function showTyping(on) {
    typingRow.style.display = on ? 'flex' : 'none';
    if (on) area.scrollTop = area.scrollHeight;
  }

  // ── Send ─────────────────────────────────────────────────────
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;

    sendBtn.disabled = true;
    input.value = '';
    input.style.height = 'auto';

    fetch(SEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ content: text }),
    })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok && d.msg) {
        area.insertBefore(buildBubble(d.msg), typingRow);
        scrollBottom(true);
      }
    })
    .catch(function () {})
    .finally(function () { sendBtn.disabled = false; input.focus(); });
  });

  // Submit on Enter (Shift+Enter = new line)
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }
  });

  // ── Poll (new messages + tick refresh + typing) ──────────────
  function poll() {
    var since = latestTs();
    var url   = POLL_URL + (since ? '?since=' + encodeURIComponent(since) : '');

    fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        if (d.messages && d.messages.length) {
          d.messages.forEach(function (m) {
            // Deduplicate by message ID (not timestamp — two messages can share the same ts)
            if (area.querySelector('[data-id="' + m.id + '"]')) {
              refreshTicks([m]);
              return;
            }
            area.insertBefore(buildBubble(m), typingRow);
          });
          requestAnimationFrame(function () { scrollBottom(false); });
        }
        if (d.messages) refreshTicks(d.messages);
        showTyping(!!d.typing);
      }
    })
    .catch(function () {})
    .finally(function () { setTimeout(poll, 3000); });
  }
  setTimeout(poll, 3000);

  // ── CSRF helper ──────────────────────────────────────────────
  function getCsrf() {
    var m = document.cookie.match(/csrf_token=([^;]+)/);
    return m ? m[1] : '';
  }
}());
