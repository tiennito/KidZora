/**
 * KidZora – Seller / Coupons Page
 * Requires window.KZ_SELLER_COUPONS to be set by the template:
 *   window.KZ_SELLER_COUPONS = {
 *     editCouponUrl:   '<url with __ID__ placeholder>',
 *     toggleCouponUrl: '<url with __ID__ placeholder>'
 *   };
 */
(function () {
  'use strict';

  /* ── Bootstrap URL config from data element ─────────────── */
  var _cfgEl = document.getElementById('kz-coupons-cfg');
  window.KZ_SELLER_COUPONS = _cfgEl ? {
    editCouponUrl:   _cfgEl.dataset.editUrl   || '',
    toggleCouponUrl: _cfgEl.dataset.toggleUrl || ''
  } : {};

  function handleDiscountType(valueId, selectId) {
    var type  = document.getElementById(selectId).value;
    var wrap  = document.getElementById(valueId + 'Wrap');
    var input = document.getElementById(valueId);

    if (type === 'free_delivery') {
      if (wrap) wrap.style.opacity = '0.4';
      if (input) { input.value = ''; input.disabled = true; input.required = false; }
    } else {
      if (wrap) wrap.style.opacity = '1';
      if (input) { input.disabled = false; input.required = true; }
    }
  }
  window.handleDiscountType = handleDiscountType;

  /* ── Open edit-coupon modal and populate fields ──────────── */
  function openEditModal(coupon) {
    var cfg = window.KZ_SELLER_COUPONS || {};

    document.getElementById('editCouponForm').action =
      (cfg.editCouponUrl || '').replace('__ID__', coupon.id);
    document.getElementById('editCode').value          = coupon.code;
    document.getElementById('editDescription').value   = coupon.description || '';
    document.getElementById('editDiscountType').value  = coupon.discount_type || 'percentage';
    document.getElementById('editDiscountValue').value = coupon.discount_value || '';
    document.getElementById('editMaxDiscount').value   = coupon.max_discount_amount || '';
    document.getElementById('editMinOrder').value      = coupon.min_order_amount || 0;
    document.getElementById('editUsageLimit').value    = coupon.usage_limit || '';
    document.getElementById('editExpiresAt').value     = (coupon.expires_at || '').slice(0, 10);
    document.getElementById('editIsActive').checked    = coupon.is_active;

    handleDiscountType('editDiscountValue', 'editDiscountType');
    new bootstrap.Modal(document.getElementById('editCouponModal')).show();
  }
  window.openEditModal = openEditModal;

  /* ── Toggle coupon active/inactive via fetch ─────────────── */
  function toggleCoupon(couponId, btn) {
    var cfg = window.KZ_SELLER_COUPONS || {};
    var url = (cfg.toggleCouponUrl || '').replace('__ID__', couponId);

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.success) {
        var active = data.is_active;
        btn.className = 'btn btn-sm toggle-btn' + (active ? ' btn-success' : ' btn-secondary');
        btn.innerHTML = '<i class="fas fa-' + (active ? 'check' : 'times') + '-circle me-1"></i>' +
                        (active ? 'Active' : 'Inactive');
        btn.title = active ? 'Active – click to deactivate' : 'Inactive – click to activate';
      }
    });
  }
  window.toggleCoupon = toggleCoupon;
})();
