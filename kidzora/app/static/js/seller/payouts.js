/**
 * KidZora – Seller / Payouts Page
 */
document.addEventListener('DOMContentLoaded', function () {
  toggleMethodFields();
});

function toggleMethodFields() {
  var method   = document.getElementById('poMethod');
  var accLabel = document.getElementById('poAccLabel');
  var numLabel = document.getElementById('poNumLabel');
  if (!method) return;
  if (method.value === 'gcash') {
    if (accLabel) accLabel.textContent = 'GCash Registered Name';
    if (numLabel) numLabel.textContent = 'GCash Number';
  } else {
    if (accLabel) accLabel.textContent = 'Account Holder Name';
    if (numLabel) numLabel.textContent = 'Account Number';
  }
}
window.toggleMethodFields = toggleMethodFields;
