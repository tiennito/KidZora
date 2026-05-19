/**
 * admin/inbox.js
 * ───────────────
 * Messenger-style two-pane admin inbox:
 *  – Tab filtering (All / Sellers / Buyers / Riders)
 *  – Live name search
 *  – Click conversation row → load bare chat in right-pane iframe
 */
(function () {
  'use strict';

  var tabs      = document.querySelectorAll('#kzInboxTabs .adm-tab');
  var cards     = document.querySelectorAll('#kzConvoList .adm-convo-row');
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
      cards.forEach(function (c) { c.classList.remove('adm-convo-row--active'); });
      card.classList.add('adm-convo-row--active');

      // Clear unread badge on this row immediately (optimistic UI)
      var dot = card.querySelector('.adm-unread-pill');
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

  /* ── New Chat Panel ─────────────────────────────────────────────────────── */

  var newChatPanel  = document.getElementById('kzNewChatPanel');
  var newChatToggle = document.getElementById('kzNewChatToggle');
  var newChatClose  = document.getElementById('kzNewChatClose');
  var newChatSearch = document.getElementById('kzNewChatSearch');
  var newChatRows   = document.querySelectorAll('#kzNewChatList .adm-newchat-row');
  var newChatEmpty  = document.getElementById('kzNewChatEmpty');
  var newChatIcon   = document.getElementById('kzNewChatIcon');

  function openNewChat() {
    if (!newChatPanel) return;
    newChatPanel.classList.add('open');
    if (newChatIcon) { newChatIcon.classList.remove('fa-edit'); newChatIcon.classList.add('fa-times'); }
    if (newChatSearch) { newChatSearch.value = ''; newChatSearch.focus(); filterNewChat(''); }
  }

  function closeNewChat() {
    if (!newChatPanel) return;
    newChatPanel.classList.remove('open');
    if (newChatIcon) { newChatIcon.classList.remove('fa-times'); newChatIcon.classList.add('fa-edit'); }
  }

  function filterNewChat(q) {
    q = q.toLowerCase().trim();
    var vis = 0;
    newChatRows.forEach(function (r) {
      var show = !q || (r.dataset.name || '').indexOf(q) !== -1;
      r.style.display = show ? '' : 'none';
      if (show) vis++;
    });
    if (newChatEmpty) newChatEmpty.style.display = (vis === 0 ? '' : 'none');
  }

  if (newChatToggle) {
    newChatToggle.addEventListener('click', function () {
      newChatPanel && newChatPanel.classList.contains('open') ? closeNewChat() : openNewChat();
    });
  }
  if (newChatClose) newChatClose.addEventListener('click', closeNewChat);

  if (newChatSearch) {
    newChatSearch.addEventListener('input', function () { filterNewChat(newChatSearch.value); });
  }

  // Clicking a new-chat row loads chat in the right pane (same as convo rows)
  newChatRows.forEach(function (row) {
    row.addEventListener('click', function (e) {
      e.preventDefault();
      closeNewChat();
      var href = row.getAttribute('href') || '';
      var embedUrl = href + (href.indexOf('?') === -1 ? '?' : '&') + 'embed=1';
      if (chatPH) chatPH.style.display = 'none';
      if (chatFrame) { chatFrame.style.display = 'block'; chatFrame.src = embedUrl; }
      if (window.history && window.history.pushState) { window.history.pushState({}, '', href); }
    });
  });

})();
