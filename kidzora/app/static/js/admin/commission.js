/**
 * KidZora – Admin / Commission Page
 */
(function () {
  'use strict';

  /* ── Open commission settings modal ─────────────────────── */
  function showCommissionSettings() {
    var modal = new bootstrap.Modal(document.getElementById('commissionSettingsModal'));
    modal.show();
  }
  window.showCommissionSettings = showCommissionSettings;

  /* ── Save commission settings ────────────────────────────── */
  function saveCommissionSettings() {
    var rate     = parseFloat(document.getElementById('commissionRate').value);
    var freq     = document.getElementById('payoutFrequency').value;
    var autodays = parseInt(document.getElementById('returnAutoApproveDays').value, 10);
    var btn      = document.querySelector('#commissionSettingsModal .btn-primary');

    if (isNaN(rate) || rate < 0 || rate > 100) {
      alert('Please enter a valid rate between 0 and 100.');
      return;
    }
    if (isNaN(autodays) || autodays < 1) {
      alert('Auto-approve days must be a positive integer.');
      return;
    }

    btn.disabled    = true;
    btn.textContent = 'Saving…';

    fetch('/admin/commission/settings', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ commission_rate: rate, payout_frequency: freq,
                                return_auto_approve_days: autodays })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.success) {
        bootstrap.Modal.getInstance(
          document.getElementById('commissionSettingsModal')
        ).hide();
        // Reload so KPI cards + label reflect new rate immediately
        window.location.reload();
      } else {
        alert('Error: ' + (data.message || 'Could not save settings.'));
      }
    })
    .catch(function () { alert('Network error — settings not saved.'); })
    .finally(function () {
      btn.disabled    = false;
      btn.textContent = 'Save Changes';
    });
  }
  window.saveCommissionSettings = saveCommissionSettings;

  /* ── Export commission data (CSV/PDF) ──────────────────── */
  function exportCommissionData(format) {
    format = format || 'csv'; // Default to CSV
    
    // Get current filter parameters from URL
    var params = new URLSearchParams(window.location.search);
    var startDate = params.get('start_date') || '';
    var endDate = params.get('end_date') || '';
    var period = params.get('period') || 'all';

    // Create form data
    var formData = new FormData();
    formData.append('start_date', startDate);
    formData.append('end_date', endDate);
    formData.append('period', period);

    // Determine endpoint
    var endpoint = format === 'pdf' 
      ? '/admin/commission/export-pdf'
      : '/admin/commission/export-csv';

    // Create a temporary form to submit the POST request
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = endpoint;
    form.style.display = 'none';

    // Add form fields
    var startDateInput = document.createElement('input');
    startDateInput.type = 'hidden';
    startDateInput.name = 'start_date';
    startDateInput.value = startDate;
    form.appendChild(startDateInput);

    var endDateInput = document.createElement('input');
    endDateInput.type = 'hidden';
    endDateInput.name = 'end_date';
    endDateInput.value = endDate;
    form.appendChild(endDateInput);

    var periodInput = document.createElement('input');
    periodInput.type = 'hidden';
    periodInput.name = 'period';
    periodInput.value = period;
    form.appendChild(periodInput);

    // Submit the form
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  }
  window.exportCommissionData = exportCommissionData;
})();
