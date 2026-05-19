/* ══════════════════════════════════════════════
   buyer/profile.js
   JavaScript for buyer/profile.html
   Config injected via: <script id="kz-profile-data" type="application/json">
   Keys: addrAddUrl, addrDefaultUrl (contains "_ID_" placeholder), addrDeleteUrl (contains "_ID_" placeholder)
══════════════════════════════════════════════ */
(function () {
  'use strict';

  var cfg = JSON.parse(document.getElementById('kz-profile-data').textContent);
  var ADDR_ADD     = cfg.addrAddUrl;
  var ADDR_DEFAULT = cfg.addrDefaultUrl;   /* contains "_ID_" */
  var ADDR_DELETE  = cfg.addrDeleteUrl;    /* contains "_ID_" */

  /* ── Avatar preview ─────────────────────────────────────────── */
  document.getElementById('avatarInput').addEventListener('change', function () {
    var file = this.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      var wrap = document.getElementById('avatarPreviewWrap');
      wrap.innerHTML = '<img id="avatarPreview" src="' + e.target.result +
        '" class="profile-avatar-img" alt="Profile photo">';
    };
    reader.readAsDataURL(file);
  });

  /* ── Saved address management ───────────────────────────────── */
  window.saveNewAddress = function () {
    var data = {
      label:       document.getElementById('na_label').value.trim() || 'Home',
      full_name:   document.getElementById('na_full_name').value.trim(),
      phone:       document.getElementById('na_phone').value.trim(),
      region:      document.getElementById('na_region').value.trim(),
      province:    document.getElementById('na_province').value.trim(),
      city:        document.getElementById('na_city').value.trim(),
      barangay:    document.getElementById('na_barangay').value.trim(),
      street_name: document.getElementById('na_street_name').value.trim(),
      postal_code: document.getElementById('na_postal_code').value.trim(),
      is_default:  document.getElementById('na_is_default').checked,
    };
    if (!data.full_name || !data.region) {
      alert('Please fill in at least Full Name and Region.');
      return;
    }
    fetch(ADDR_ADD, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    .then(function (r) { return r.json(); })
    .then(function (d) { if (d.error) { alert('Error: ' + d.error); } else { location.reload(); } })
    .catch(function () { alert('Error saving address.'); });
  };

  window.setDefaultAddr = function (id) {
    fetch(ADDR_DEFAULT.replace('_ID_', id), { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d.error) { alert('Error: ' + d.error); } else { location.reload(); } });
  };

  window.deleteAddr = function (id) {
    if (!confirm('Delete this saved address?')) return;
    fetch(ADDR_DELETE.replace('_ID_', id), { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d.error) { alert('Error: ' + d.error); } else { location.reload(); } });
  };
}());
