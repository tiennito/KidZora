/**
 * KidZora – Seller / Product Form
 * Handles existing image removal and variant row management.
 * Image upload / drag-drop preview is handled by products.js (shared).
 */
(function () {
  'use strict';

  /* ── Remove existing saved image ────────────────────────── */
  function removeExistingImage(url, btn) {
    var input    = document.getElementById('removeImagesInput');
    var existing = input.value ? input.value.split(',') : [];
    existing.push(url);
    input.value = existing.join(',');
    btn.closest('.image-preview-item').remove();
  }
  window.removeExistingImage = removeExistingImage;

  /* ── Variant count helpers ───────────────────────────────── */
  function _variantCount() {
    return parseInt(document.getElementById('variantCount').value) || 0;
  }

  function _setVariantCount(n) {
    document.getElementById('variantCount').value = n;
  }

  /* ── Recalculate total stock from variant inputs ─────────── */
  function recalcTotal() {
    var inputs  = document.querySelectorAll('.variant-stock-input');
    var stockEl = document.getElementById('stockQtyInput');
    var noteEl  = document.getElementById('stockAutoNote');
    if (!stockEl) return;

    if (inputs.length === 0) {
      stockEl.readOnly = false;
      stockEl.classList.remove('bg-light');
      if (noteEl) noteEl.classList.add('d-none');
      return;
    }

    var total = 0;
    inputs.forEach(function (i) { total += parseInt(i.value) || 0; });
    stockEl.value    = total;
    stockEl.readOnly = true;
    stockEl.classList.add('bg-light');
    if (noteEl) noteEl.classList.remove('d-none');
  }
  window.recalcTotal = recalcTotal;

  /* ── Preview a newly selected variant image ──────────────── */
  function previewVariantImage(input, idx) {
    var preview = document.getElementById('varPreview' + idx);
    if (!preview || !input.files || !input.files[0]) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.classList.remove('d-none');
    };
    reader.readAsDataURL(input.files[0]);
  }
  window.previewVariantImage = previewVariantImage;

  /* ── Clear a variant image (edit mode) ───────────────────── */
  function clearVariantImage(idx) {
    var keepInput = document.getElementById('varKeepImg' + idx);
    if (keepInput) keepInput.value = '';
    var preview = document.getElementById('varPreview' + idx);
    if (preview) { preview.src = ''; preview.classList.add('d-none'); }
  }
  window.clearVariantImage = clearVariantImage;

  /* ── Add a new variant row dynamically ───────────────────── */
  function addVariantRow() {
    var idx  = _variantCount();
    var list = document.getElementById('variantsList');
    var div  = document.createElement('div');
    div.className    = 'variant-row card border rounded p-3 mb-2';
    div.dataset.index = idx;
    div.innerHTML =
      '<input type="hidden" name="variant_id_' + idx + '" value="">' +
      '<input type="hidden" name="variant_keep_image_' + idx + '" id="varKeepImg' + idx + '" value="">' +
      '<div class="row g-2 align-items-end">' +
        '<div class="col-md-4">' +
          '<label class="form-label small mb-1">Variant Name <span class="text-danger">*</span></label>' +
          '<input type="text" class="form-control form-control-sm" name="variant_name_' + idx + '"' +
                 ' placeholder="e.g. Red, Large" required>' +
        '</div>' +
        '<div class="col-md-3">' +
          '<label class="form-label small mb-1">Price Modifier (₱)</label>' +
          '<input type="number" class="form-control form-control-sm" name="variant_price_' + idx + '"' +
                 ' value="0" step="0.01" placeholder="0.00">' +
        '</div>' +
        '<div class="col-md-2">' +
          '<label class="form-label small mb-1">Stock</label>' +
          '<input type="number" class="form-control form-control-sm variant-stock-input"' +
                 ' name="variant_stock_' + idx + '" value="0" min="0" placeholder="0"' +
                 ' oninput="recalcTotal()">' +
        '</div>' +
        '<div class="col-md-3 text-end">' +
          '<button type="button" class="btn btn-sm btn-outline-danger" onclick="removeVariantRow(this)">' +
            '<i class="fas fa-trash me-1"></i>Remove' +
          '</button>' +
        '</div>' +
      '</div>' +
      '<div class="mt-2">' +
        '<img src="" class="rounded d-none mb-1" style="width:56px;height:56px;object-fit:cover;"' +
             ' id="varPreview' + idx + '" alt="variant image">' +
        '<input type="file" class="form-control form-control-sm variant-image-input"' +
               ' name="variant_image_' + idx + '" accept="image/*"' +
               ' onchange="previewVariantImage(this,' + idx + ')">' +
      '</div>';
    list.appendChild(div);
    _setVariantCount(idx + 1);
    recalcTotal();
  }
  window.addVariantRow = addVariantRow;

  /* ── Remove a variant row ────────────────────────────────── */
  function removeVariantRow(btn) {
    btn.closest('.variant-row').remove();
    recalcTotal();
  }
  window.removeVariantRow = removeVariantRow;

  /* ── Sale price live preview ─────────────────────────────── */
  function updateSalePreview() {
    var regInput  = document.querySelector('[name="price"]');
    var saleInput = document.getElementById('salePriceInput');
    var preview   = document.getElementById('salePreview');
    if (!regInput || !saleInput || !preview) return;
    var reg  = parseFloat(regInput.value) || 0;
    var sale = parseFloat(saleInput.value) || 0;
    if (sale > 0 && sale < reg) {
      document.getElementById('salePreviewPrice').textContent = '₱' + sale.toFixed(2);
      document.getElementById('salePreviewOrig').textContent  = '₱' + reg.toFixed(2);
      preview.classList.remove('d-none');
    } else {
      preview.classList.add('d-none');
    }
  }

  /* ── Sortable image grid (HTML5 Drag and Drop) ───────────── */
  function _initSortableGrid(gridEl, afterSort) {
    if (!gridEl) return;
    var dragged = null;

    gridEl.addEventListener('dragstart', function (e) {
      dragged = e.target.closest('.image-preview-item');
      if (!dragged) return;
      dragged.classList.add('kz-dragging');
      e.dataTransfer.effectAllowed = 'move';
    });

    gridEl.addEventListener('dragend', function () {
      if (dragged) dragged.classList.remove('kz-dragging');
      gridEl.querySelectorAll('.image-preview-item').forEach(function (el) {
        el.classList.remove('kz-drag-over');
      });
      dragged = null;
      if (afterSort) afterSort();
    });

    gridEl.addEventListener('dragover', function (e) {
      e.preventDefault();
      if (!dragged) return;
      var target = e.target.closest('.image-preview-item');
      if (!target || target === dragged) return;
      gridEl.querySelectorAll('.image-preview-item').forEach(function (el) {
        el.classList.remove('kz-drag-over');
      });
      target.classList.add('kz-drag-over');
      var rect = target.getBoundingClientRect();
      if (e.clientX < rect.left + rect.width / 2) {
        gridEl.insertBefore(dragged, target);
      } else {
        gridEl.insertBefore(dragged, target.nextSibling);
      }
    });
  }

  /* Serialize the existing-images grid order into the hidden input */
  function _serializeExistingOrder() {
    var grid  = document.getElementById('currentImages');
    var input = document.getElementById('imagesOrderInput');
    if (!grid || !input) return;
    var urls = Array.from(grid.querySelectorAll('.image-preview-item img'))
      .map(function (img) { return img.getAttribute('src'); })
      .filter(Boolean);
    input.value = urls.join(',');
  }

  /* ── Init ────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    recalcTotal();
    var salePriceInput = document.getElementById('salePriceInput');
    var regPriceInput  = document.querySelector('[name="price"]');
    if (salePriceInput) {
      salePriceInput.addEventListener('input', updateSalePreview);
      if (regPriceInput) regPriceInput.addEventListener('input', updateSalePreview);
      updateSalePreview(); // run once on load (edit mode)
    }

    // Sortable: existing saved images
    var currentImagesGrid = document.getElementById('currentImages');
    _initSortableGrid(currentImagesGrid, _serializeExistingOrder);
    _serializeExistingOrder(); // set initial order on page load

    // Sortable: newly-added images (product-form.js runs after products.js)
    var newImagesGrid = document.getElementById('imagePreviewGrid');
    _initSortableGrid(newImagesGrid, function () {
      if (typeof window.kzRebuildDt === 'function') window.kzRebuildDt();
    });
  });
})();
