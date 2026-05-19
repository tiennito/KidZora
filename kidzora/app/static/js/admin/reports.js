/**
 * KidZora – Admin / Reports Page
 * Fetches real report data from /admin/reports/<id>/data and renders it.
 */
(function () {
  'use strict';

  var currentReportId = null;

  /* ─── helpers ─────────────────────────────────────────── */

  function peso(n) {
    return '₱' + Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function badge(text) {
    var map = { completed: 'success', delivered: 'success', pending: 'warning',
                confirmed: 'info', cancelled: 'danger', buyer: 'primary',
                seller: 'success', rider: 'info', admin: 'dark',
                Approved: 'success', Pending: 'warning', Banned: 'danger' };
    var cls = map[text] || 'secondary';
    return '<span class="badge bg-' + cls + '">' + text + '</span>';
  }

  /* ─── report renderers ────────────────────────────────── */

  function renderSales(d) {
    var rows = (d.rows || []).map(function (r) {
      return '<tr><td>' + r.created_at + '</td><td>' + r.order_id + '…</td><td>' +
        peso(r.amount) + '</td><td>' + peso(r.commission) + '</td><td>' +
        badge(r.status) + '</td><td>' + r.payment_method + '</td></tr>';
    }).join('');

    var statusRows = Object.entries(d.orders_by_status || {}).map(function (e) {
      return '<tr><td>' + badge(e[0]) + '</td><td>' + e[1] + '</td></tr>';
    }).join('');

    return '<div class="row mb-3">' +
      _statCard('Total Orders', d.total_orders, 'primary') +
      _statCard('Completed', d.completed_orders, 'success') +
      _statCard('Total Revenue', peso(d.total_revenue), 'info') +
      _statCard('Commission', peso(d.total_commission), 'warning') +
      _statCard('Avg Order Value', peso(d.avg_order_value), 'secondary') +
      _statCard('Cancelled', d.cancelled_orders, 'danger') +
      '</div>' +
      '<div class="row mb-3"><div class="col-md-4"><h6>Orders by Status</h6>' +
      '<table class="table table-sm table-bordered"><thead><tr><th>Status</th><th>Count</th></tr></thead>' +
      '<tbody>' + statusRows + '</tbody></table></div></div>' +
      '<h6>Order Details</h6><div class="table-responsive"><table class="table table-sm table-striped">' +
      '<thead><tr><th>Date</th><th>Order ID</th><th>Amount</th><th>Commission</th><th>Status</th><th>Payment</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="text-center text-muted">No orders in this period</td></tr>') + '</tbody></table></div>';
  }

  function renderUsers(d) {
    var rows = (d.rows || []).map(function (r) {
      return '<tr><td>' + r.registered + '</td><td>' + r.name + '</td><td>' +
        badge(r.role) + '</td><td>' + badge(r.status) + '</td></tr>';
    }).join('');

    return '<div class="row mb-3">' +
      _statCard('New Users', d.total_new_users, 'primary') +
      _statCard('Buyers', d.new_buyers, 'info') +
      _statCard('Sellers', d.new_sellers, 'success') +
      _statCard('Riders', d.new_riders, 'warning') +
      _statCard('Approved Sellers', d.approved_sellers, 'success') +
      _statCard('Pending Sellers', d.pending_sellers, 'secondary') +
      _statCard('Banned', d.banned_users, 'danger') +
      '</div>' +
      '<h6>New Registrations</h6><div class="table-responsive"><table class="table table-sm table-striped">' +
      '<thead><tr><th>Date</th><th>Name</th><th>Role</th><th>Status</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="4" class="text-center text-muted">No new users in this period</td></tr>') + '</tbody></table></div>';
  }

  function renderCommissions(d) {
    var rows = (d.transactions || []).map(function (r) {
      return '<tr><td>' + (r.created_at || '').slice(0, 10) + '</td><td>' + (r.order_id || '').slice(0, 8) + '…</td><td>' +
        peso(r.amount) + '</td><td>' + peso(r.commission_amount) + '</td><td>' + peso(r.seller_earnings) + '</td></tr>';
    }).join('');

    return '<div class="row mb-3">' +
      _statCard('Orders', d.transaction_count, 'primary') +
      _statCard('Total Commission', peso(d.total_commission), 'warning') +
      _statCard('Seller Earnings', peso(d.total_earnings), 'success') +
      '</div>' +
      '<h6>Commission Breakdown</h6><div class="table-responsive"><table class="table table-sm table-striped">' +
      '<thead><tr><th>Date</th><th>Order ID</th><th>Order Amount</th><th>Commission</th><th>Seller Earnings</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="text-center text-muted">No completed orders in this period</td></tr>') + '</tbody></table></div>';
  }

  function renderActivity(d) {
    var roleRows = Object.entries(d.new_users_by_role || {}).map(function (e) {
      return '<tr><td>' + badge(e[0]) + '</td><td>' + e[1] + '</td></tr>';
    }).join('');
    var statusRows = Object.entries(d.orders_by_status || {}).map(function (e) {
      return '<tr><td>' + badge(e[0]) + '</td><td>' + e[1] + '</td></tr>';
    }).join('');

    return '<div class="row mb-3">' +
      _statCard('Total Orders', d.total_orders, 'primary') +
      _statCard('Completed Orders', d.completed_orders, 'success') +
      _statCard('Total Revenue', peso(d.total_revenue), 'info') +
      _statCard('Commission', peso(d.total_commission), 'warning') +
      _statCard('New Users', d.total_new_users, 'secondary') +
      _statCard('Banned Users', d.banned_users, 'danger') +
      '</div>' +
      '<div class="row"><div class="col-md-5 me-3"><h6>Orders by Status</h6>' +
      '<table class="table table-sm table-bordered"><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>' +
      statusRows + '</tbody></table></div>' +
      '<div class="col-md-5"><h6>New Users by Role</h6>' +
      '<table class="table table-sm table-bordered"><thead><tr><th>Role</th><th>Count</th></tr></thead><tbody>' +
      roleRows + '</tbody></table></div></div>';
  }

  function _statCard(label, value, color) {
    return '<div class="col-md-2 col-6 mb-2"><div class="card border-' + color + '">' +
      '<div class="card-body p-2 text-center"><div class="fw-bold text-' + color + '">' + value + '</div>' +
      '<div class="small text-muted">' + label + '</div></div></div></div>';
  }

  /* ─── public functions ────────────────────────────────── */

  function viewReport(reportId) {
    currentReportId = reportId;
    var modalContent = document.getElementById('viewReportContent');
    var modalTitle   = document.querySelector('#viewReportModal .modal-title');

    // Wire up export links in the modal footer
    var csvLink = document.getElementById('modalExportCsv');
    var pdfLink = document.getElementById('modalExportPdf');
    if (csvLink) { csvLink.href = '/admin/reports/' + reportId + '/export/csv'; }
    if (pdfLink) { pdfLink.href = '/admin/reports/' + reportId + '/export/pdf'; }

    modalContent.innerHTML =
      '<div class="text-center py-4"><div class="spinner-border" role="status"></div>' +
      '<p class="mt-2 text-muted">Loading report data…</p></div>';

    var modal = new bootstrap.Modal(document.getElementById('viewReportModal'));
    modal.show();

    fetch('/admin/reports/' + reportId + '/data')
      .then(function (res) { return res.json(); })
      .then(function (resp) {
        if (resp.error) { throw new Error(resp.error); }

        var d    = resp.data || {};
        var type = resp.report_type || '';

        if (modalTitle) {
          modalTitle.textContent = resp.title + ' (' + resp.start_date + ' – ' + resp.end_date + ')';
        }

        var html = '';
        if (type === 'sales')       { html = renderSales(d); }
        else if (type === 'users')  { html = renderUsers(d); }
        else if (type === 'commissions') { html = renderCommissions(d); }
        else if (type === 'activity')    { html = renderActivity(d); }
        else {
          html = '<pre class="bg-light p-3 rounded small">' +
            JSON.stringify(d, null, 2) + '</pre>';
        }

        modalContent.innerHTML = html;
      })
      .catch(function (err) {
        modalContent.innerHTML =
          '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>' +
          'Failed to load report data: ' + err.message + '</div>';
      });
  }
  window.viewReport = viewReport;

  function downloadReport(reportId, format) {
    var fmt = format || 'csv';
    if (fmt === 'pdf') {
      window.open('/admin/reports/' + reportId + '/export/pdf', '_blank');
    } else {
      window.location.href = '/admin/reports/' + reportId + '/export/csv';
    }
  }
  window.downloadReport = downloadReport;

  function downloadCurrentReport() {
    if (currentReportId) { downloadReport(currentReportId, 'csv'); }
  }
  window.downloadCurrentReport = downloadCurrentReport;

  function deleteOldReports() {
    if (confirm('Delete all reports older than 30 days? This cannot be undone.')) {
      alert('Old-report cleanup is not yet wired to a backend route.');
    }
  }
  window.deleteOldReports = deleteOldReports;
})();
