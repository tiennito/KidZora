/**
 * KidZora – Admin / Coupons Page
 * Requires window.KZ_ADMIN_COUPONS to be set by the template:
 *   window.KZ_ADMIN_COUPONS = { editCouponUrl: '<url with __ID__ placeholder>' };
 */
(function () {
  'use strict';
  /* ── Bootstrap URL config from data element ─────────────── */
  var _cfgEl = document.getElementById('kz-admin-coupons-cfg');
  window.KZ_ADMIN_COUPONS = _cfgEl ? {
    editCouponUrl: _cfgEl.dataset.editUrl || ''
  } : {};
  /* ── Toggle discount input fields based on type ─────────── */
  function toggleDiscountFields() {
    var discountType     = document.getElementById('discountType').value;
    var discountSymbol   = document.getElementById('discountSymbol');
    var maxDiscountField = document.getElementById('maxDiscountAmount');
    var discountValField = document.getElementById('discountValue');

    if (discountType === 'percentage') {
      discountSymbol.textContent  = '%';
      maxDiscountField.disabled   = false;
      discountValField.disabled   = false;
    } else if (discountType === 'free_delivery') {
      discountSymbol.textContent  = '—';
      maxDiscountField.disabled   = true;
      maxDiscountField.value      = '';
      discountValField.disabled   = true;
      discountValField.value      = '0';
    } else {
      discountSymbol.textContent  = '₱';
      maxDiscountField.disabled   = true;
      maxDiscountField.value      = '';
      discountValField.disabled   = false;
    }
  }
  window.toggleDiscountFields = toggleDiscountFields;

  /* ── Open edit modal and populate with coupon data ──────── */
  function editCoupon(couponId) {
    var modalBody = document.querySelector('#editCouponModal .modal-body');
    if (!modalBody) return;

    modalBody.innerHTML =
      '<div class="row">' +
        '<div class="col-md-6">' +
          '<div class="mb-3">' +
            '<label for="editDescription" class="form-label">Description</label>' +
            '<input type="text" class="form-control" id="editDescription" name="description" value="Sample coupon description">' +
          '</div>' +
        '</div>' +
        '<div class="col-md-6">' +
          '<div class="mb-3">' +
            '<label for="editDiscountType" class="form-label">Discount Type</label>' +
            '<select class="form-select" id="editDiscountType" name="discount_type">' +
              '<option value="percentage">Percentage</option>' +
              '<option value="fixed">Fixed Amount</option>' +
              '<option value="free_delivery">Free Delivery</option>' +
            '</select>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="row">' +
        '<div class="col-md-6">' +
          '<div class="mb-3">' +
            '<label for="editDiscountValue" class="form-label">Discount Value</label>' +
            '<input type="number" class="form-control" id="editDiscountValue" name="discount_value" value="10" min="0" step="0.01">' +
          '</div>' +
        '</div>' +
        '<div class="col-md-6">' +
          '<div class="mb-3">' +
            '<label for="editMinOrderAmount" class="form-label">Minimum Order Amount</label>' +
            '<input type="number" class="form-control" id="editMinOrderAmount" name="min_order_amount" value="100" min="0" step="0.01">' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="row">' +
        '<div class="col-md-6">' +
          '<div class="mb-3">' +
            '<label for="editUsageLimit" class="form-label">Usage Limit</label>' +
            '<input type="number" class="form-control" id="editUsageLimit" name="usage_limit" value="100" min="1">' +
          '</div>' +
        '</div>' +
        '<div class="col-md-6">' +
          '<div class="mb-3">' +
            '<label for="editExpiresAt" class="form-label">Expiry Date</label>' +
            '<input type="date" class="form-control" id="editExpiresAt" name="expires_at" value="2024-12-31">' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="row">' +
        '<div class="col-12">' +
          '<div class="form-check">' +
            '<input class="form-check-input" type="checkbox" id="editIsActive" name="is_active" checked>' +
            '<label class="form-check-label" for="editIsActive">Active</label>' +
          '</div>' +
        '</div>' +
      '</div>';

    var cfg      = window.KZ_ADMIN_COUPONS || {};
    var formEl   = document.getElementById('editCouponForm');
    if (formEl && cfg.editCouponUrl) {
      formEl.action = cfg.editCouponUrl.replace('__ID__', couponId);
    }

    new bootstrap.Modal(document.getElementById('editCouponModal')).show();
  }
  window.editCoupon = editCoupon;
})();
