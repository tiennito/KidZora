/**
 * KidZora – Admin / Users Pending Page
 * Requires window.KZ_ADMIN_PENDING to be set by the template:
 *   window.KZ_ADMIN_PENDING = {
 *     approveUserUrl: '<url with PLACEHOLDER>',
 *     rejectUserUrl:  '<url with PLACEHOLDER>'
 *   };
 */
(function () {
  'use strict';

  /* ── Bootstrap URL config from data element ─────────────── */
  var _cfgEl = document.getElementById('kz-pending-cfg');
  window.KZ_ADMIN_PENDING = _cfgEl ? {
    approveUserUrl: _cfgEl.dataset.approveUrl || '',
    rejectUserUrl:  _cfgEl.dataset.rejectUrl  || ''
  } : {};

  function fileCard(label, url, icon) {
    if (!url) {
      return '<div class="col-md-4 mb-3">' +
               '<div class="card border-warning h-100">' +
                 '<div class="card-body text-center py-3">' +
                   '<i class="fas ' + icon + ' fa-2x text-warning mb-2"></i>' +
                   '<p class="mb-1 fw-bold">' + label + '</p>' +
                   '<span class="badge bg-warning text-dark">Not uploaded</span>' +
                 '</div>' +
               '</div>' +
             '</div>';
    }
    var isImg   = /\.(png|jpg|jpeg|gif|webp)(\?|$)/i.test(url);
    var preview = isImg
      ? '<img src="' + url + '" class="img-fluid rounded mb-2" style="max-height:120px;object-fit:cover;" alt="' + label + '">'
      : '<i class="fas fa-file-pdf fa-3x text-danger mb-2"></i>';
    return '<div class="col-md-4 mb-3">' +
             '<div class="card border-success h-100">' +
               '<div class="card-body text-center py-3">' +
                 preview +
                 '<p class="mb-1 fw-bold">' + label + '</p>' +
                 '<a href="' + url + '" target="_blank" class="btn btn-sm btn-outline-primary me-1"><i class="fas fa-eye me-1"></i>View</a>' +
                 '<a href="' + url + '" download class="btn btn-sm btn-outline-secondary"><i class="fas fa-download me-1"></i>Download</a>' +
               '</div>' +
             '</div>' +
           '</div>';
  }

  /* ── Approve modal ───────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var approveModal = document.getElementById('approveModal');
    if (approveModal) {
      approveModal.addEventListener('show.bs.modal', function (event) {
        var button   = event.relatedTarget;
        var userId   = button.getAttribute('data-user-id');
        var userName = button.getAttribute('data-user-name');
        var cfg      = window.KZ_ADMIN_PENDING || {};

        document.getElementById('approveUserName').textContent = userName;
        this.querySelector('form').action = (cfg.approveUserUrl || '').replace('PLACEHOLDER', userId);
      });
    }

    /* ── Reject modal ──────────────────────────────────────── */
    var rejectModal = document.getElementById('rejectModal');
    if (rejectModal) {
      rejectModal.addEventListener('show.bs.modal', function (event) {
        var button   = event.relatedTarget;
        var userId   = button.getAttribute('data-user-id');
        var userName = button.getAttribute('data-user-name');
        var userRole = button.getAttribute('data-user-role') || 'seller';
        var cfg      = window.KZ_ADMIN_PENDING || {};
        var isRider  = (userRole === 'rider');
        var isBuyer  = (userRole === 'buyer');
        var isSoftReject = isRider || isBuyer;

        // Populate name in both notices
        var nameEl       = document.getElementById('rejectUserName');
        var nameSellEl   = document.getElementById('rejectUserNameSeller');
        if (nameEl)     nameEl.textContent     = userName;
        if (nameSellEl) nameSellEl.textContent = userName;

        // Toggle which notice is visible and whether confirmation checkbox is needed
        var riderNotice  = document.getElementById('rejectRiderNotice');
        var sellerNotice = document.getElementById('rejectSellerNotice');
        var confirmWrap  = document.getElementById('rejectConfirmWrap');
        var btnLabel     = document.getElementById('rejectBtnLabel');
        var submitBtn    = document.getElementById('rejectSubmitBtn');

        if (isSoftReject) {
          if (riderNotice)  riderNotice.classList.remove('d-none');
          if (sellerNotice) sellerNotice.classList.add('d-none');
          if (confirmWrap)  confirmWrap.style.display = 'none';
          if (btnLabel)     btnLabel.textContent = isBuyer ? 'Reject & Notify Buyer' : 'Reject & Notify Rider';
          if (submitBtn)    submitBtn.disabled = false;
        } else {
          if (riderNotice)  riderNotice.classList.add('d-none');
          if (sellerNotice) sellerNotice.classList.remove('d-none');
          if (confirmWrap)  confirmWrap.style.display = '';
          if (btnLabel)     btnLabel.textContent = 'Reject permanently';
          if (submitBtn)    submitBtn.disabled = true;
        }

        this.querySelector('form').action = (cfg.rejectUserUrl || '').replace('PLACEHOLDER', userId);
        var confirmChk = document.getElementById('rejectConfirm');
        if (confirmChk) confirmChk.checked = false;
        document.getElementById('rejectReason').value = '';
      });
    }

    /* ── View modal ────────────────────────────────────────── */
    var viewModal = document.getElementById('viewModal');
    if (viewModal) {
      viewModal.addEventListener('show.bs.modal', function (event) {
        var button   = event.relatedTarget;
        var userId   = button.getAttribute('data-user-id');
        var userType = button.getAttribute('data-user-type');
        var content  = document.getElementById('viewModalContent');
        var footer   = document.getElementById('viewModalFooter');

        content.innerHTML =
          '<div class="text-center py-5">' +
            '<div class="spinner-border text-primary" role="status"></div>' +
            '<p class="mt-2 text-muted">Loading details...</p>' +
          '</div>';
        footer.innerHTML = '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>';

        var apiUrl = userType === 'rider'
          ? '/admin/api/rider-details/' + userId
          : userType === 'buyer'
            ? '/admin/api/buyer-details/' + userId
            : '/admin/api/seller-details/' + userId;

        var modalTitle = document.getElementById('viewModalTitle');
        modalTitle.innerHTML = userType === 'rider'
          ? '<i class="fas fa-motorcycle me-2"></i>Rider Application Details'
          : userType === 'buyer'
            ? '<i class="fas fa-id-card me-2"></i>Buyer Verification Details'
            : '<i class="fas fa-store me-2"></i>Seller Application Details';

        fetch(apiUrl)
          .then(function (r) { return r.json(); })
          .then(function (resp) {
            if (!resp.success) {
              content.innerHTML = '<div class="alert alert-danger">Failed to load details: ' + resp.message + '</div>';
              return;
            }
            var d = resp.data;

            var personalCard =
              '<div class="col-md-6">' +
                '<div class="card h-100">' +
                  '<div class="card-header bg-light"><i class="fas fa-user me-2"></i><strong>Personal Information</strong></div>' +
                  '<div class="card-body">' +
                    '<table class="table table-sm mb-0">' +
                      '<tr><th>Full Name</th><td>' + d.full_name + '</td></tr>' +
                      '<tr><th>Email</th><td><a href="mailto:' + d.email + '">' + d.email + '</a></td></tr>' +
                      '<tr><th>Phone</th><td>' + (d.phone || '—') + '</td></tr>' +
                      '<tr><th>Registered</th><td>' + (d.created_at ? d.created_at.substring(0, 10) : '—') + '</td></tr>' +
                      '<tr><th>Status</th><td><span class="badge bg-warning text-dark">Pending Approval</span></td></tr>' +
                    '</table>' +
                  '</div>' +
                '</div>' +
              '</div>';

            var addressCard =
              '<div class="col-md-6">' +
                '<div class="card h-100">' +
                  '<div class="card-header bg-light"><i class="fas fa-map-marker-alt me-2"></i><strong>Address</strong></div>' +
                  '<div class="card-body">' +
                    '<table class="table table-sm mb-0">' +
                      '<tr><th>Building/Unit</th><td>' + (d.building_number || '—') + '</td></tr>' +
                      '<tr><th>Street</th><td>' + (d.street_name || '—') + '</td></tr>' +
                      '<tr><th>Barangay</th><td>' + (d.barangay || '—') + '</td></tr>' +
                      '<tr><th>City</th><td>' + (d.city || '—') + '</td></tr>' +
                      '<tr><th>Province</th><td>' + (d.province || '—') + '</td></tr>' +
                      '<tr><th>Region</th><td>' + (d.region || '—') + '</td></tr>' +
                      '<tr><th>Postal Code</th><td>' + (d.postal_code || '—') + '</td></tr>' +
                      '<tr><th>Country</th><td>' + (d.country || 'Philippines') + '</td></tr>' +
                    '</table>' +
                  '</div>' +
                '</div>' +
              '</div>';

            if (userType === 'buyer') {
              document.getElementById('viewModalContent').innerHTML =
                '<div class="row g-3">' +
                  personalCard +
                  addressCard +
                  '<div class="col-12">' +
                    '<div class="card">' +
                      '<div class="card-header bg-light"><i class="fas fa-id-card me-2"></i><strong>Submitted Valid ID</strong></div>' +
                      '<div class="card-body"><div class="row">' +
                        fileCard('Government-Issued Valid ID', d.valid_id_url, 'fa-id-card') +
                      '</div></div>' +
                    '</div>' +
                  '</div>' +
                '</div>';
            } else if (userType === 'rider') {
              document.getElementById('viewModalContent').innerHTML =
                '<div class="row g-3">' +
                  personalCard +
                  addressCard +
                  '<div class="col-12">' +
                    '<div class="card">' +
                      '<div class="card-header bg-light"><i class="fas fa-paperclip me-2"></i><strong>Rider Documents</strong></div>' +
                      '<div class="card-body"><div class="row">' +
                        fileCard("Driver's License / Licensed ID", d.licensed_id_url, 'fa-id-card') +
                        fileCard('Official Receipt (OR)',            d.original_receipt_url, 'fa-receipt') +
                        fileCard('Certificate of Registration (CR)', d.certificate_of_registration_url, 'fa-file-alt') +
                      '</div></div>' +
                    '</div>' +
                  '</div>' +
                '</div>';
            } else {
              var bizTypeLabels = {
                individual: 'Individual', corporation: 'Corporation',
                partnership: 'Partnership', sole_proprietorship: 'Sole Proprietorship'
              };
              var idTypeLabels = {
                passport: 'Passport', drivers_license: "Driver's License",
                national_id: 'National ID', umid: 'UMID',
                philhealth_id: 'PhilHealth ID', sss_id: 'SSS ID', tin_id: 'TIN ID'
              };
              content.innerHTML =
                '<div class="row g-3">' +
                  personalCard +
                  addressCard +
                  '<div class="col-12">' +
                    '<div class="card">' +
                      '<div class="card-header bg-light"><i class="fas fa-store me-2"></i><strong>Business Information</strong></div>' +
                      '<div class="card-body"><div class="row">' +
                        '<div class="col-md-3"><strong>Business Name</strong><br>' + (d.business_name || '—') + '</div>' +
                        '<div class="col-md-3"><strong>Business Type</strong><br>' + (bizTypeLabels[d.business_type] || d.business_type || '—') + '</div>' +
                        '<div class="col-md-3"><strong>ID Type</strong><br>' + (idTypeLabels[d.seller_id_type] || d.seller_id_type || '—') + '</div>' +
                        '<div class="col-md-3"><strong>ID Number</strong><br>' + (d.seller_id_number || '—') + '</div>' +
                      '</div></div>' +
                    '</div>' +
                  '</div>' +
                  '<div class="col-12">' +
                    '<div class="card">' +
                      '<div class="card-header bg-light"><i class="fas fa-paperclip me-2"></i><strong>Attached Documents</strong></div>' +
                      '<div class="card-body"><div class="row">' +
                        fileCard('Government ID',   d.seller_id_file,       'fa-id-card') +
                        fileCard('Business Permit', d.business_permit_file, 'fa-file-alt') +
                        fileCard('BIR Certificate', d.bir_file,             'fa-file-invoice') +
                      '</div></div>' +
                    '</div>' +
                  '</div>' +
                '</div>';
            }

            footer.innerHTML =
              '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>' +
              '<button type="button" class="btn btn-danger" data-bs-dismiss="modal"' +
                ' onclick="triggerReject(\'' + d.id + '\',\'' + d.full_name + '\',\'' + d.role + '\')">' +
                '<i class="fas fa-times me-1"></i>Reject' +
              '</button>' +
              '<button type="button" class="btn btn-success" data-bs-dismiss="modal"' +
                ' onclick="triggerApprove(\'' + d.id + '\',\'' + d.full_name + '\')">' +
                '<i class="fas fa-check me-1"></i>Approve' +
              '</button>';
          })
          .catch(function (err) {
            content.innerHTML =
              '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>Error loading details: ' +
              (err.message || err) + '</div>';
            console.error(err);
          });
      });
    }
  });

  /* ── Programmatic approve / reject triggers ─────────────── */
  function triggerApprove(userId, userName) {
    var cfg = window.KZ_ADMIN_PENDING || {};
    document.getElementById('approveUserName').textContent = userName;
    document.querySelector('#approveModal form').action = (cfg.approveUserUrl || '').replace('PLACEHOLDER', userId);
    new bootstrap.Modal(document.getElementById('approveModal')).show();
  }
  window.triggerApprove = triggerApprove;

  function triggerReject(userId, userName, userRole) {
    var cfg = window.KZ_ADMIN_PENDING || {};
    var isSoftReject = userRole === 'buyer' || userRole === 'rider';
    document.getElementById('rejectUserName').textContent = userName;
    document.getElementById('rejectUserNameSeller').textContent = userName;
    document.querySelector('#rejectModal form').action = (cfg.rejectUserUrl || '').replace('PLACEHOLDER', userId);
    document.getElementById('rejectConfirm').checked = false;
    document.getElementById('rejectSubmitBtn').disabled = !isSoftReject;
    document.getElementById('rejectRiderNotice').classList.toggle('d-none', !isSoftReject);
    document.getElementById('rejectSellerNotice').classList.toggle('d-none', isSoftReject);
    document.getElementById('rejectConfirmWrap').style.display = isSoftReject ? 'none' : '';
    document.getElementById('rejectBtnLabel').textContent = userRole === 'buyer' ? 'Reject & Notify Buyer' : userRole === 'rider' ? 'Reject & Notify Rider' : 'Reject permanently';
    document.getElementById('rejectReason').value = '';
    new bootstrap.Modal(document.getElementById('rejectModal')).show();
  }
  window.triggerReject = triggerReject;
})();
