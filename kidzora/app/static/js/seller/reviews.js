/**
 * KidZora – Seller / Reviews Page
 */
function toggleReplyForm(id) {
  var form = document.getElementById('reply-form-' + id);
  var btn  = document.getElementById('reply-btn-'  + id);
  if (!form) return;
  var showing = !form.classList.contains('d-none');
  form.classList.toggle('d-none', showing);
  if (btn) btn.classList.toggle('d-none', !showing);
  if (!showing) {
    var ta = form.querySelector('textarea');
    if (ta) ta.focus();
  }
}
window.toggleReplyForm = toggleReplyForm;
