/**
 * KidZora – Admin / Users List Page
 */
(function () {
  'use strict';

  /* ── Helper: render a document thumbnail or link ─────────── */
  function docCell(url, label) {
    if (!url) return '<span class="text-muted small">Not uploaded</span>';
    var isImg = /\.(jpg|jpeg|png|gif|webp)(\?|$)/i.test(url);
    return isImg
      ? '<a href="' + url + '" target="_blank">' +
          '<img src="' + url + '" alt="' + label + '" style="max-height:80px;max-width:160px;border-radius:6px;border:1px solid #ddd;">' +
        '</a>'
      : '<a href="' + url + '" target="_blank" class="btn btn-sm btn-outline-secondary">' +
          '<i class="fas fa-file-alt me-1"></i>' + label +
        '</a>';
  }

  /* ── View user details modal ─────────────────────────────── */
  function viewUser(userId, role) {
    var content = document.getElementById('userModalContent');
    content.innerHTML =
      '<div class="text-center py-4">' +
        '<div class="spinner-border text-primary" role="status"></div>' +
        '<p class="mt-2 text-muted">Loading...</p>' +
      '</div>';

    // Show/hide Message buttons — admins can\'t be messaged
    var msgButtons = [
      document.getElementById('userModalMessageBtn'),
      document.getElementById('userModalHeaderMessageBtn')
    ];
    msgButtons.forEach(function (btn) {
      if (!btn) return;
      if (role !== 'admin') {
        btn.href = '/admin/chat/' + userId;
        btn.style.display = '';
      } else {
        btn.style.display = 'none';
      }
    });

    new bootstrap.Modal(document.getElementById('userModal')).show();

    var endpoint = (role === 'rider')
      ? '/admin/api/rider-details/' + userId
      : '/admin/api/seller-details/' + userId;

    fetch(endpoint)
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success) {
          content.innerHTML = '<div class="alert alert-danger">Failed to load user details.</div>';
          return;
        }
        var d = resp.data;
        var roleBadgeMap = { admin: 'danger', seller: 'success', buyer: 'primary', rider: 'warning' };
        var roleBadge    = roleBadgeMap[d.role] || 'secondary';
        var statusBadge  = d.is_banned
          ? '<span class="badge bg-danger">Suspended</span>'
          : '<span class="badge bg-success">Active</span>';
        var approvedBadge = (d.role === 'seller' || d.role === 'rider')
          ? (d.is_approved
              ? '<span class="badge bg-success">Approved</span>'
              : '<span class="badge bg-warning text-dark">Pending</span>')
          : '<span class="text-muted">N/A</span>';

        var docsHtml = '';
        if (d.role === 'seller') {
          docsHtml =
            '<hr>' +
            '<h6 class="text-primary"><i class="fas fa-store me-1"></i>Seller Details</h6>' +
            '<div class="row g-2 mb-3">' +
              '<div class="col-6"><strong>Business Name:</strong><br>' + (d.business_name || '—') + '</div>' +
              '<div class="col-6"><strong>Business Type:</strong><br>' + (d.business_type || '—') + '</div>' +
              '<div class="col-6"><strong>ID Type:</strong><br>' + (d.seller_id_type || '—') + '</div>' +
              '<div class="col-6"><strong>ID Number:</strong><br>' + (d.seller_id_number || '—') + '</div>' +
            '</div>' +
            '<h6 class="text-secondary"><i class="fas fa-paperclip me-1"></i>Uploaded Documents</h6>' +
            '<div class="row g-3">' +
              '<div class="col-md-4 text-center">' +
                '<div class="small fw-semibold mb-1">Valid ID</div>' +
                docCell(d.seller_id_file, 'Valid ID') +
              '</div>' +
              '<div class="col-md-4 text-center">' +
                '<div class="small fw-semibold mb-1">Business Permit</div>' +
                docCell(d.business_permit_file, 'Business Permit') +
              '</div>' +
              '<div class="col-md-4 text-center">' +
                '<div class="small fw-semibold mb-1">BIR Certificate</div>' +
                docCell(d.bir_file, 'BIR Certificate') +
              '</div>' +
            '</div>';
        } else if (d.role === 'rider') {
          docsHtml =
            '<hr>' +
            '<h6 class="text-primary"><i class="fas fa-motorcycle me-1"></i>Rider Details</h6>' +
            '<div class="row g-2 mb-3">' +
              '<div class="col-6"><strong>Vehicle Type:</strong><br>' + (d.vehicle_type || '—') + '</div>' +
              '<div class="col-6"><strong>Plate Number:</strong><br>' + (d.vehicle_plate || '—') + '</div>' +
            '</div>' +
            '<h6 class="text-secondary"><i class="fas fa-paperclip me-1"></i>Uploaded Documents</h6>' +
            '<div class="row g-3">' +
              '<div class="col-md-4 text-center">' +
                '<div class="small fw-semibold mb-1">Licensed ID</div>' +
                docCell(d.licensed_id_url, 'Licensed ID') +
              '</div>' +
              '<div class="col-md-4 text-center">' +
                '<div class="small fw-semibold mb-1">Original Receipt</div>' +
                docCell(d.original_receipt_url, 'Original Receipt') +
              '</div>' +
              '<div class="col-md-4 text-center">' +
                '<div class="small fw-semibold mb-1">Certificate of Registration</div>' +
                docCell(d.certificate_of_registration_url, 'COR') +
              '</div>' +
            '</div>';
        }

        var addressParts = [
          d.building_number, d.street_name, d.barangay, d.city,
          d.province, d.region, d.postal_code, d.country
        ].filter(Boolean);

        content.innerHTML =
          '<div class="row g-3">' +
            '<div class="col-md-6">' +
              '<h6 class="text-primary"><i class="fas fa-user me-1"></i>Personal Information</h6>' +
              '<p class="mb-1"><strong>Full Name:</strong> ' + (d.full_name || '—') + '</p>' +
              '<p class="mb-1"><strong>Email:</strong> ' + (d.email || '—') + '</p>' +
              '<p class="mb-1"><strong>Phone:</strong> ' + (d.phone || '—') + '</p>' +
              '<p class="mb-1"><strong>Registered:</strong> ' + ((d.created_at || '').slice(0, 10) || '—') + '</p>' +
            '</div>' +
            '<div class="col-md-6">' +
              '<h6 class="text-primary"><i class="fas fa-id-card me-1"></i>Account Status</h6>' +
              '<p class="mb-1"><strong>Role:</strong> <span class="badge bg-' + roleBadge + '">' + (d.role || '—') + '</span></p>' +
              '<p class="mb-1"><strong>Status:</strong> ' + statusBadge + '</p>' +
              '<p class="mb-1"><strong>Approved:</strong> ' + approvedBadge + '</p>' +
            '</div>' +
            '<div class="col-12">' +
              '<h6 class="text-primary"><i class="fas fa-key me-1"></i>User ID (UUID)</h6>' +
              '<div class="input-group input-group-sm">' +
                '<input type="text" id="uuidInput" class="form-control font-monospace" value="' + (d.id || 'N/A') + '" readonly>' +
                '<button class="btn btn-outline-secondary" type="button" id="copyUuidBtn">' +
                  '<i class="fas fa-copy me-1"></i>Copy' +
                '</button>' +
              '</div>' +
            '</div>' +
            '<div class="col-12">' +
              '<h6 class="text-primary"><i class="fas fa-map-marker-alt me-1"></i>Address</h6>' +
              '<p class="mb-0">' + (d.full_address || addressParts.join(', ') || '—') + '</p>' +
            '</div>' +
          '</div>' +
          docsHtml;
        
        // Add copy button functionality
        setTimeout(function() {
          var copyBtn = document.getElementById('copyUuidBtn');
          var uuidInput = document.getElementById('uuidInput');
          if (copyBtn && uuidInput) {
            copyBtn.addEventListener('click', function() {
              uuidInput.select();
              document.execCommand('copy');
              copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
              setTimeout(function() {
                copyBtn.innerHTML = '<i class="fas fa-copy me-1"></i>Copy';
              }, 2000);
            });
          }
        }, 100);
      })
      .catch(function () {
        content.innerHTML = '<div class="alert alert-danger">Error loading user details. Please try again.</div>';
      });
  }
  window.viewUser = viewUser;

  /* ── Export users ────────────────────────────────────────── */
  function exportUsers() {
    alert('Export functionality would download a CSV file with user data');
  }
  window.exportUsers = exportUsers;

  /* ── Open ban modal ──────────────────────────────────────── */
  function triggerBan(userId, userName) {
    document.getElementById('banForm').action = '/admin/users/' + userId + '/ban';
    document.getElementById('banUserName').textContent = userName;
    document.querySelector('#banModal textarea[name="reason"]').value = '';
    new bootstrap.Modal(document.getElementById('banModal')).show();
  }
  window.triggerBan = triggerBan;
})();

/* ── Filter form & client-side search ──────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  var form   = document.getElementById('filterForm');
  var search = document.getElementById('searchFilter');
  if (!form) return;

  ['roleFilter', 'statusFilter'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('change', function () { form.submit(); });
  });

  if (search) {
    search.addEventListener('input', function () {
      var q    = this.value.toLowerCase();
      var rows = document.querySelectorAll('table tbody tr');
      rows.forEach(function (row) {
        var name  = (row.cells[0] ? row.cells[0].textContent : '').toLowerCase();
        var email = (row.cells[1] ? row.cells[1].textContent : '').toLowerCase();
        row.style.display = (!q || name.includes(q) || email.includes(q)) ? '' : 'none';
      });
    });
  }
});
