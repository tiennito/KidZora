/**
 * KidZora – Buyer / Checkout
 * Reads config from window.KZ_CHECKOUT set by the template:
 *   window.KZ_CHECKOUT = {
 *     subtotal        : Number,
 *     initialDeliveryFee: Number,
 *     sellerIds       : Array,
 *     deliveryFeeUrl  : String,
 *     applyCouponUrl  : String,
 *     addrUrl         : String,
 *   };
 */
(function () {
  'use strict';

  /* ── Config ──────────────────────────────────────────────── */
  var cfg            = window.KZ_CHECKOUT || {};
  var SUBTOTAL       = parseFloat(cfg.subtotal)    || 0;
  var INITIAL_FEE    = parseFloat(cfg.initialDeliveryFee);
  var SELLER_IDS     = cfg.sellerIds               || [];
  var FEE_URL        = cfg.deliveryFeeUrl          || '';
  var COUPON_URL     = cfg.applyCouponUrl          || '';

  var currentDeliveryFee = isNaN(INITIAL_FEE) ? 120 : INITIAL_FEE;
  var currentDiscount    = 0;
  var pendingCoupon      = null;   // highlighted in modal, not yet confirmed
  var appliedCoupon      = null;   // confirmed coupon

  /* ── Helpers ─────────────────────────────────────────────── */
  function formatMoney(n) {
    return '\u20B1' + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  /* ── Delivery fee ────────────────────────────────────────── */
  function updateDeliveryFee(fee) {
    currentDeliveryFee = fee;
    var hFee = document.getElementById('hiddenDeliveryFee');
    var dFee = document.getElementById('displayDeliveryFee');
    if (hFee) hFee.value = fee.toFixed(2);
    if (dFee) dFee.textContent = formatMoney(fee);

    // Free-delivery coupon tracks the current shipping cost
    if (appliedCoupon && appliedCoupon.discount_type === 'free_delivery') {
      currentDiscount = fee;
      var hDisc = document.getElementById('hiddenDiscount');
      var dDisc = document.getElementById('displayDiscount');
      if (hDisc) hDisc.value = fee.toFixed(2);
      if (dDisc) dDisc.textContent = '-' + formatMoney(fee);
    }
    recalcTotal();
  }

  function readLocation() {
    return {
      region:   (document.querySelector('[name="region"]') || {}).value || '',
      province: (document.querySelector('[name="province"]') || {}).value || '',
      city:     (document.querySelector('[name="city"]') || {}).value || ''
    };
  }

  function fetchDeliveryFee() {
    var location = readLocation();
    if (!FEE_URL || !(location.city || location.province || location.region)) return;
    fetch(FEE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(location)
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.fee !== undefined) updateDeliveryFee(data.fee);
      var match = document.getElementById('displayDeliveryMatch');
      if (match) {
        match.textContent = data.matched && data.locationName
          ? data.locationName
          : 'Default rate';
      }
    });
  }

  /* ── Coupon modal ────────────────────────────────────────── */
  function openCouponModal() {
    pendingCoupon = appliedCoupon;
    renderCouponHighlight();
    var btn = document.getElementById('confirmCouponBtn');
    if (btn) btn.style.display = pendingCoupon ? '' : 'none';
    new bootstrap.Modal(document.getElementById('couponModal')).show();
  }
  window.openCouponModal = openCouponModal;

  function selectCoupon(coupon) {
    pendingCoupon = (pendingCoupon && pendingCoupon.code === coupon.code) ? null : coupon;
    renderCouponHighlight();
    var btn = document.getElementById('confirmCouponBtn');
    if (btn) btn.style.display = pendingCoupon ? '' : 'none';
  }
  window.selectCoupon = selectCoupon;

  function renderCouponHighlight() {
    document.querySelectorAll('.coupon-card[data-coupon]').forEach(function (card) {
      var check = card.querySelector('.coupon-check');
      var code  = '';
      try { code = JSON.parse(card.dataset.coupon).code; } catch (e) {}
      var selected = pendingCoupon && code === pendingCoupon.code;
      card.style.borderColor = selected ? 'var(--bs-primary)' : '';
      card.style.boxShadow   = selected ? '0 0 0 2px rgba(var(--bs-primary-rgb),.25)' : '';
      if (check) check.style.display = selected ? '' : 'none';
    });
  }

  function confirmCoupon() {
    if (!pendingCoupon || !COUPON_URL) return;
    fetch(COUPON_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code         : pendingCoupon.code,
        subtotal     : SUBTOTAL,
        seller_ids   : SELLER_IDS,
        delivery_fee : currentDeliveryFee
      })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      bootstrap.Modal.getInstance(document.getElementById('couponModal')).hide();
      if (data.success) {
        appliedCoupon = pendingCoupon;
        currentDiscount = parseFloat(data.discount) || 0;

        var ac   = document.getElementById('appliedCouponCode');
        var hd   = document.getElementById('hiddenDiscount');
        var dl   = document.getElementById('discountLabel');
        var dd   = document.getElementById('displayDiscount');
        var dr   = document.getElementById('discountRow');
        var cbl  = document.getElementById('couponBtnLabel');
        var cpb  = document.getElementById('couponPickerBtn');
        var acd  = document.getElementById('appliedCouponDesc');
        var aci  = document.getElementById('appliedCouponInfo');

        if (ac)  ac.value = appliedCoupon.code;
        if (hd)  hd.value = currentDiscount.toFixed(2);
        if (dl)  dl.textContent = data.description || appliedCoupon.code;
        if (dd)  dd.textContent = '-' + formatMoney(currentDiscount);
        if (dr)  dr.style.display = 'flex';
        if (cbl) cbl.textContent = appliedCoupon.code + ' applied';
        if (cpb) cpb.classList.replace('btn-outline-primary', 'btn-primary');
        if (acd) acd.textContent = data.description || data.message;
        if (aci) aci.style.display = '';
      } else {
        appliedCoupon = null;
        pendingCoupon = null;
        removeCoupon();
        alert(data.message || 'Voucher is no longer valid.');
      }
      recalcTotal();
    });
  }
  window.confirmCoupon = confirmCoupon;

  function removeCoupon() {
    appliedCoupon   = null;
    pendingCoupon   = null;
    currentDiscount = 0;

    var ac  = document.getElementById('appliedCouponCode');
    var hd  = document.getElementById('hiddenDiscount');
    var dr  = document.getElementById('discountRow');
    var aci = document.getElementById('appliedCouponInfo');
    var cbl = document.getElementById('couponBtnLabel');
    var cpb = document.getElementById('couponPickerBtn');

    if (ac)  ac.value = '';
    if (hd)  hd.value = '0';
    if (dr)  dr.style.display = 'none';
    if (aci) aci.style.display = 'none';
    if (cbl) cbl.textContent = 'Select a Voucher';
    if (cpb) cpb.classList.replace('btn-primary', 'btn-outline-primary');
    recalcTotal();
  }
  window.removeCoupon = removeCoupon;

  /* ── Grand total ─────────────────────────────────────────── */
  function recalcTotal() {
    var grand = Math.max(0, SUBTOTAL + currentDeliveryFee - currentDiscount);
    var dt = document.getElementById('displayTotal');
    if (dt) dt.textContent = formatMoney(grand);
  }

  /* ── Delegate click on dynamically-rendered coupon cards ── */
  document.addEventListener('click', function (e) {
    var card = e.target.closest('.coupon-card[data-coupon]');
    if (card) {
      try { selectCoupon(JSON.parse(card.dataset.coupon)); } catch (err) {}
    }
  });

  /* ── Init ────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    ['region', 'province', 'city'].forEach(function (fieldName) {
      var input = document.querySelector('[name="' + fieldName + '"]');
      if (!input) return;
      input.addEventListener('blur', fetchDeliveryFee);
      input.addEventListener('change', fetchDeliveryFee);
    });
    fetchDeliveryFee();
    recalcTotal();
  });

})();

/* ============================================================
   Saved Address Picker
   Reads addrUrl from window.KZ_CHECKOUT.addrUrl
   ============================================================ */
(function () {
  'use strict';

  var ADDR_URL = (window.KZ_CHECKOUT || {}).addrUrl || '';

  function fillField(name, value) {
    var el = document.querySelector('[name="' + name + '"]');
    if (el) el.value = value || '';
  }

  function fillForm(addr) {
    fillField('phone',       addr.phone);
    fillField('region',      addr.region);
    fillField('province',    addr.province);
    fillField('city',        addr.city);
    fillField('barangay',    addr.barangay);
    fillField('street_name', addr.street_name);
    fillField('postal_code', addr.postal_code);
    var hidId = document.getElementById('savedAddrId');
    if (hidId) hidId.value = addr.id;
    var regionEl = document.getElementById('regionInput');
    if (regionEl && addr.region) regionEl.dispatchEvent(new Event('blur'));
  }

  function clearForm() {
    ['phone', 'region', 'province', 'city', 'barangay', 'street_name', 'postal_code']
      .forEach(function (n) { fillField(n, ''); });
    var hidId = document.getElementById('savedAddrId');
    if (hidId) hidId.value = '';
  }

  function wireSaveCheckbox() {
    var saveChk = document.getElementById('saveAddressCheck');
    var lblWrap = document.getElementById('addrLabelWrap');
    if (saveChk) {
      saveChk.addEventListener('change', function () {
        if (lblWrap) lblWrap.style.display = this.checked ? '' : 'none';
      });
    }
  }

  function renderAddresses(addresses) {
    var picker  = document.getElementById('savedAddrPicker');
    var list    = document.getElementById('savedAddrList');
    var saveRow = document.getElementById('saveAddressRow');
    var saveChk = document.getElementById('saveAddressCheck');
    var lblWrap = document.getElementById('addrLabelWrap');
    if (!picker || !list) return;
    picker.style.display = '';

    var html = '';
    addresses.forEach(function (addr, i) {
      var parts   = [addr.street_name, addr.barangay, addr.city, addr.province, addr.region];
      var addrTxt = parts.filter(Boolean).join(', ');
      html += '<div class="border rounded-2 p-2 ps-3 d-flex align-items-start gap-2">'
            + '<input class="form-check-input mt-1 flex-shrink-0" type="radio" name="_saved_addr"'
            + ' id="saddr_' + i + '" value="' + addr.id + '"'
            + (addr.is_default ? ' checked' : '') + '>'
            + '<label class="flex-grow-1" for="saddr_' + i + '" style="cursor:pointer;">'
            + '<span class="fw-semibold small">' + (addr.label || 'Address') + '</span>'
            + (addr.is_default ? ' <span class="badge bg-primary" style="font-size:.6rem;">Default</span>' : '')
            + '<div class="text-muted" style="font-size:.8rem;">'
            + (addr.full_name || '') + (addr.phone ? ' &middot; ' + addr.phone : '') + '</div>'
            + '<div class="text-muted" style="font-size:.8rem;">' + addrTxt + '</div>'
            + '</label></div>';
    });
    // "Enter a new address" option
    html += '<div class="border rounded-2 p-2 ps-3 d-flex align-items-center gap-2">'
          + '<input class="form-check-input flex-shrink-0" type="radio" name="_saved_addr" id="saddr_new" value="">'
          + '<label class="small" for="saddr_new" style="cursor:pointer;">'
          + '<i class="fas fa-plus-circle me-1 text-primary"></i>Enter a new address</label></div>';
    list.innerHTML = html;

    // Pre-fill default (or first) address and hide save row
    var def = addresses.find(function (a) { return a.is_default; }) || addresses[0];
    if (def) {
      fillForm(def);
      if (saveRow) saveRow.style.display = 'none';
    }

    // Handle radio changes
    list.addEventListener('change', function (e) {
      var radio = e.target;
      if (radio.type !== 'radio') return;
      var val = radio.value;
      if (!val) {
        clearForm();
        if (saveRow) saveRow.style.display = '';
        return;
      }
      var addr = addresses.find(function (a) { return a.id === val; });
      if (addr) {
        fillForm(addr);
        if (saveRow) saveRow.style.display = 'none';
        if (saveChk) saveChk.checked = false;
        if (lblWrap) lblWrap.style.display = 'none';
      }
    });

    wireSaveCheckbox();
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!ADDR_URL) { wireSaveCheckbox(); return; }
    fetch(ADDR_URL)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (Array.isArray(data) && data.length) {
          renderAddresses(data);
        } else {
          wireSaveCheckbox();
        }
      })
      .catch(function () { wireSaveCheckbox(); });
  });

})();
