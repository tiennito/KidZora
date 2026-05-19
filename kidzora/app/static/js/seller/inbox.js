/**
 * seller/inbox.js
 * ───────────────
 * Messenger-style two-pane inbox:
 *  – Tab filtering (All / Buyers / Riders / Admin)
 *  – Live name search
 *  – Click conversation row → load bare chat in right-pane iframe
 */
(function () {
  'use strict';

  var tabs      = document.querySelectorAll('#kzInboxTabs .kz-msgr-tab');
  var cards     = document.querySelectorAll('#kzConvoList .kz-msgr-row');
  var tabEmpty  = document.getElementById('kzTabEmpty');
  var search    = document.getElementById('kzMsgrSearch');
  var chatFrame = document.getElementById('kzChatFrame');
  var chatPH    = document.getElementById('kzChatPlaceholder');

  /* ── Tab + search filter ───────────────────────────────────────────────── */

  var activeTab = 'all';

  function filterCards(tabFilter, searchVal) {
    var q = (searchVal || '').toLowerCase().trim();
    var visible = 0;
    cards.forEach(function (c) {
      var roleOk   = (tabFilter === 'all' || c.dataset.role === tabFilter);
      var searchOk = (!q || (c.dataset.name || '').indexOf(q) !== -1);
      var show = roleOk && searchOk;
      c.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    if (tabEmpty) tabEmpty.style.display = (visible === 0 ? '' : 'none');
  }

  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      tabs.forEach(function (x) { x.classList.remove('active'); });
      t.classList.add('active');
      activeTab = t.dataset.tab;
      filterCards(activeTab, search ? search.value : '');
    });
  });

  if (search) {
    search.addEventListener('input', function () {
      filterCards(activeTab, search.value);
    });
  }

  /* ── Convo click → load iframe ─────────────────────────────────────────── */

  cards.forEach(function (card) {
    card.addEventListener('click', function (e) {
      e.preventDefault();

      // Mark active row
      cards.forEach(function (c) { c.classList.remove('kz-msgr-row--active'); });
      card.classList.add('kz-msgr-row--active');

      // Clear unread badge on this row immediately (optimistic UI)
      var dot = card.querySelector('.kz-msgr-unread-dot');
      if (dot) dot.remove();
      card.classList.remove('unread');

      // Build embed URL from the card href
      var href = card.getAttribute('href') || '';
      var embedUrl = href + (href.indexOf('?') === -1 ? '?' : '&') + 'embed=1';

      // Show iframe, hide placeholder
      if (chatPH) chatPH.style.display = 'none';
      if (chatFrame) {
        chatFrame.style.display = 'block';
        chatFrame.src = embedUrl;
      }

      // Push URL state so browser back works
      if (window.history && window.history.pushState) {
        window.history.pushState({}, '', href);
      }
    });
  });

})();
