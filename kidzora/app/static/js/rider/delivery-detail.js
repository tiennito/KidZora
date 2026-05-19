/**
 * KidZora – Rider Panel / Delivery Detail
 * Handles the embedded Rider ↔ Seller AJAX chat and quick-message buttons.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    /* ── Quick-message pill buttons ─────────────────────── */
    document.querySelectorAll('.quick-msg').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var input = document.getElementById('msgInput');
        if (input) { input.value = btn.dataset.msg; input.focus(); }
      });
    });

    /* ── AJAX Chat ──────────────────────────────────────── */
    var form     = document.getElementById('msgForm');
    var chatBox  = document.getElementById('chatBox');
    var input    = document.getElementById('msgInput');
    var typingEl = document.getElementById('chatTyping');

    if (!form || !chatBox || !input) return;

    var sendUrl   = form.dataset.sendUrl;
    var pollUrl   = form.dataset.pollUrl;
    var typingUrl = form.dataset.typingUrl;
    var myId      = form.dataset.myId;
    var lastTs    = form.dataset.lastTs || '';

    /* ── Helpers ── */
    function scrollBottom() {
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    function timeStr(iso) {
      try { return iso.substring(11, 16); } catch (e) { return ''; }
    }

    function escHtml(s) {
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    function clearEmpty() {
      var el = chatBox.querySelector('.kzc-empty');
      if (el) el.remove();
    }

    function addBubble(msg) {
      var isMine = (msg.sender_id === myId);
      var wrap = document.createElement('div');
      wrap.className = 'd-flex justify-content-' + (isMine ? 'end' : 'start') + ' mb-2';
      wrap.dataset.id = msg.id || '';
      wrap.innerHTML =
        '<div>' +
        '<div class="msg-bubble ' + (isMine ? 'sent' : 'received') + '">' +
        escHtml(msg.content) +
        '</div>' +
        '<div class="text-muted mt-1 ' + (isMine ? 'text-end' : 'text-start') +
        '" style="font-size:.68rem;">' +
        timeStr(msg.created_at || '') +
        '</div>' +
        '</div>';
      if (typingEl && chatBox.contains(typingEl)) {
        chatBox.insertBefore(wrap, typingEl);
      } else {
        chatBox.appendChild(wrap);
      }
      if (msg.created_at && lastTs < msg.created_at) lastTs = msg.created_at;
    }

    /* ── Initial scroll ── */
    scrollBottom();

    /* ── Send ── */
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = input.value.trim();
      if (!text || !sendUrl) return;
      input.value = '';
      input.disabled = true;

      fetch(sendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ content: text }),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok && d.msg) {
            clearEmpty();
            addBubble(d.msg);
            scrollBottom();
          }
        })
        .catch(function () {})
        .finally(function () {
          input.disabled = false;
          input.focus();
        });
    });

    /* ── Typing indicator ── */
    var typingTimer = null;
    input.addEventListener('input', function () {
      clearTimeout(typingTimer);
      if (!typingUrl) return;
      fetch(typingUrl, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      typingTimer = setTimeout(function () {}, 3000);
    });

    /* ── Poll for new messages every 3 s ── */
    function poll() {
      if (!pollUrl) return;
      var url = pollUrl + (lastTs ? '?since=' + encodeURIComponent(lastTs) : '');
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok && d.messages && d.messages.length) {
            var atBottom =
              chatBox.scrollTop + chatBox.clientHeight >= chatBox.scrollHeight - 20;
            d.messages.forEach(function (m) {
              if (!chatBox.querySelector('[data-id="' + m.id + '"]')) {
                clearEmpty();
                addBubble(m);
              }
            });
            if (atBottom) scrollBottom();
          }
          if (typingEl) {
            typingEl.style.visibility = d.typing ? 'visible' : 'hidden';
          }
        })
        .catch(function () {});
    }

    if (pollUrl) {
      setInterval(poll, 3000);
      poll();
    }
  });
})();
