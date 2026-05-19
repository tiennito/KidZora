/* ============================================================
   KidZora – Seller Orders JS
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

  // ── Status update modal ────────────────────────────────
  const statusModal = document.getElementById('statusModal');
  if (statusModal) {
    statusModal.addEventListener('show.bs.modal', function (e) {
      const btn = e.relatedTarget;
      const orderId     = btn.getAttribute('data-order-id');
      const orderRef    = btn.getAttribute('data-order-ref');
      const currentStatus = btn.getAttribute('data-status');
      document.getElementById('statusOrderRef').textContent = '#' + orderRef;
      document.getElementById('updateStatusForm').action =
        '/seller/orders/PLACEHOLDER/status'.replace('PLACEHOLDER', orderId);
      const sel = document.getElementById('newStatus');
      if (sel) sel.value = currentStatus || 'pending';
    });
  }

  // ── Filter by status (client-side) ────────────────────
  const filterBtns = document.querySelectorAll('.order-filter-btn');
  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      filterBtns.forEach(b => b.classList.remove('active', 'btn-primary'));
      filterBtns.forEach(b => b.classList.add('btn-outline-primary'));
      this.classList.add('active', 'btn-primary');
      this.classList.remove('btn-outline-primary');

      const status = this.getAttribute('data-status');
      document.querySelectorAll('.order-row').forEach(function (row) {
        if (status === 'all' || row.getAttribute('data-status') === status) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });

  // ── Search orders ──────────────────────────────────────
  const searchInput = document.getElementById('orderSearch');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      document.querySelectorAll('.order-row').forEach(function (row) {
        const ref = (row.getAttribute('data-ref') || '').toLowerCase();
        row.style.display = ref.includes(q) ? '' : 'none';
      });
    });
  }

});
