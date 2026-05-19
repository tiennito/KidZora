/**
 * KidZora – Admin / Unban Requests Page
 */
(function () {
  'use strict';

  function openRejectModal(requestId, userName) {
    document.getElementById('rejectForm').action = '/admin/users/unban-requests/' + requestId + '/reject';
    document.getElementById('rejectUserName').textContent = userName;
    document.querySelector('#rejectModal textarea[name="admin_notes"]').value = '';
    new bootstrap.Modal(document.getElementById('rejectModal')).show();
  }
  window.openRejectModal = openRejectModal;
})();
