/* ============================================================
   KidZora – Seller Products JS
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

  // ── Delete confirmation modal ──────────────────────────
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (e) {
      const btn = e.relatedTarget;
      const productId   = btn.getAttribute('data-product-id');
      const productName = btn.getAttribute('data-product-name');
      document.getElementById('deleteProductName').textContent = productName;
      document.getElementById('deleteForm').action =
        '/seller/products/PLACEHOLDER/delete'.replace('PLACEHOLDER', productId);
    });
  }

  // ── Toggle active/inactive ─────────────────────────────
  document.querySelectorAll('.toggle-active').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const productId = this.getAttribute('data-product-id');
      const currentState = this.getAttribute('data-active') === 'true';
      fetch('/seller/products/' + productId + '/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          const row = document.getElementById('product-row-' + productId);
          if (row) {
            const badge = row.querySelector('.active-badge');
            if (badge) {
              if (data.is_active) {
                badge.className = 'status-pill status-completed active-badge';
                badge.textContent = 'Active';
              } else {
                badge.className = 'status-pill status-cancelled active-badge';
                badge.textContent = 'Inactive';
              }
            }
            this.setAttribute('data-active', data.is_active.toString());
            this.innerHTML = data.is_active
              ? '<i class="fas fa-eye-slash"></i>'
              : '<i class="fas fa-eye"></i>';
            this.title = data.is_active ? 'Deactivate' : 'Activate';
          }
        }
      })
      .catch(console.error);
    });
  });

  // ── Image upload preview  (product_form.html) ─────────
  const uploadZone  = document.getElementById('uploadZone');
  const fileInput   = document.getElementById('productImages');
  const previewGrid = document.getElementById('imagePreviewGrid');

  // Rebuild DataTransfer from DOM order — called after reorder or remove
  function rebuildDtFromDom() {
    var newDt = new DataTransfer();
    Array.from(previewGrid.querySelectorAll('.image-preview-item')).forEach(function (el) {
      if (el._kzFile) newDt.items.add(el._kzFile);
    });
    fileInput.files = newDt.files;
  }
  // Expose for product-form.js sortable callback
  window.kzRebuildDt = rebuildDtFromDom;

  function addFilesToQueue(files) {
    files.forEach(function (file) {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = function (e) {
        const wrapper = document.createElement('div');
        wrapper.className = 'image-preview-item';
        wrapper.draggable = true;
        wrapper._kzFile = file;              // store file reference on element
        wrapper.innerHTML = `
          <img src="${e.target.result}" alt="preview">
          <button type="button" class="remove-img">&times;</button>`;
        previewGrid.appendChild(wrapper);
        rebuildDtFromDom();                  // sync input after append
        wrapper.querySelector('.remove-img').addEventListener('click', function () {
          wrapper.remove();
          rebuildDtFromDom();
        });
      };
      reader.readAsDataURL(file);
    });
  }

  if (uploadZone && fileInput) {
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', function (e) {
      e.preventDefault();
      this.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', function () {
      this.classList.remove('dragover');
    });
    uploadZone.addEventListener('drop', function (e) {
      e.preventDefault();
      this.classList.remove('dragover');
      addFilesToQueue(Array.from(e.dataTransfer.files));  // drag-drop → into input
    });

    fileInput.addEventListener('change', function () {
      addFilesToQueue(Array.from(this.files));             // click-select → into input
    });
  }

  // ── Search / filter table ──────────────────────────────
  const searchInput = document.getElementById('productSearch');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      document.querySelectorAll('.product-row').forEach(function (row) {
        const name = row.getAttribute('data-name') || '';
        row.style.display = name.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  // ── Bulk select ────────────────────────────────────────
  const selectAll  = document.getElementById('selectAllProducts');
  const toolbar    = document.getElementById('bulkToolbar');
  const bulkCount  = document.getElementById('bulkCount');

  function getCheckedBoxes() {
    return Array.from(document.querySelectorAll('.product-check:checked'));
  }

  function updateToolbar() {
    const checked = getCheckedBoxes();
    if (!toolbar || !bulkCount) return;
    bulkCount.textContent = checked.length;
    if (checked.length > 0) {
      toolbar.classList.remove('d-none');
      toolbar.classList.add('d-flex');
    } else {
      toolbar.classList.add('d-none');
      toolbar.classList.remove('d-flex');
      if (selectAll) selectAll.checked = false;
    }
  }

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      document.querySelectorAll('.product-check').forEach(function (cb) {
        // Only check visible rows
        const row = cb.closest('.product-row');
        if (!row || row.style.display === 'none') return;
        cb.checked = selectAll.checked;
      });
      updateToolbar();
    });
  }

  document.addEventListener('change', function (e) {
    if (e.target && e.target.classList.contains('product-check')) {
      updateToolbar();
      // If any unchecked, deselect the select-all header checkbox
      const total   = document.querySelectorAll('.product-check').length;
      const checked = getCheckedBoxes().length;
      if (selectAll) selectAll.checked = checked === total && total > 0;
    }
  });

  function bulkAction(action) {
    const ids = getCheckedBoxes().map(cb => cb.getAttribute('data-product-id'));
    if (!ids.length) return;

    fetch('/seller/products/bulk-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ action, ids }),
    })
    .then(r => r.json())
    .then(data => {
      if (!data.success) { alert('Bulk action failed: ' + (data.error || 'unknown error')); return; }

      ids.forEach(function (pid) {
        const row = document.getElementById('product-row-' + pid);
        if (!row) return;

        if (action === 'activate' || action === 'deactivate') {
          const isActive = action === 'activate';
          const badge = row.querySelector('.active-badge');
          if (badge) {
            badge.className = isActive ? 'status-pill status-completed active-badge' : 'status-pill status-cancelled active-badge';
            badge.textContent = isActive ? 'Active' : 'Inactive';
          }
          const toggleBtn = row.querySelector('.toggle-active');
          if (toggleBtn) {
            toggleBtn.setAttribute('data-active', isActive.toString());
            toggleBtn.innerHTML = isActive ? '<i class="fas fa-eye-slash"></i>' : '<i class="fas fa-eye"></i>';
            toggleBtn.title = isActive ? 'Deactivate' : 'Activate';
          }
          row.dataset.active = isActive ? 'active' : 'inactive';
        } else if (action === 'archive') {
          // Remove rows from non-archived view
          row.remove();
        } else if (action === 'restore') {
          row.remove();
        }
      });

      // Clear all checkboxes and hide toolbar
      document.querySelectorAll('.product-check').forEach(cb => { cb.checked = false; });
      if (selectAll) selectAll.checked = false;
      updateToolbar();
    })
    .catch(console.error);
  }

  const bulkActivate   = document.getElementById('bulkActivate');
  const bulkDeactivate = document.getElementById('bulkDeactivate');
  const bulkArchive    = document.getElementById('bulkArchive');
  const bulkRestore    = document.getElementById('bulkRestore');
  const bulkClear      = document.getElementById('bulkClear');

  if (bulkActivate)   bulkActivate.addEventListener('click',   () => bulkAction('activate'));
  if (bulkDeactivate) bulkDeactivate.addEventListener('click', () => bulkAction('deactivate'));
  if (bulkArchive)    bulkArchive.addEventListener('click',    () => bulkAction('archive'));
  if (bulkRestore)    bulkRestore.addEventListener('click',    () => bulkAction('restore'));
  if (bulkClear) {
    bulkClear.addEventListener('click', function () {
      document.querySelectorAll('.product-check').forEach(cb => { cb.checked = false; });
      if (selectAll) selectAll.checked = false;
      updateToolbar();
    });
  }

});

/* ── Category / status select filters (called from onchange) ── */
function filterByCategory(cat) {
  document.querySelectorAll('.product-row').forEach(function (row) {
    row.style.display = (!cat || row.dataset.category === cat) ? '' : 'none';
  });
}

function filterByStatus(status) {
  document.querySelectorAll('.product-row').forEach(function (row) {
    row.style.display = (!status || row.dataset.active === status) ? '' : 'none';
  });
}

function filterByStockStatus(stock) {
  document.querySelectorAll('.product-row').forEach(function (row) {
    if (!stock) { row.style.display = ''; return; }
    const s = row.dataset.stockStatus;
    row.style.display = (
      stock === 'alert' ? (s === 'oos' || s === 'low') : s === stock
    ) ? '' : 'none';
  });
}
