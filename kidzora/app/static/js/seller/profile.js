/* ============================================================
   KidZora – Seller Profile JS
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

  // ── Password strength meter ────────────────────────────
  const pwInput = document.getElementById('new_password');
  const strengthBar = document.getElementById('pwStrengthBar');
  const strengthText = document.getElementById('pwStrengthText');

  if (pwInput && strengthBar) {
    pwInput.addEventListener('input', function () {
      const pw = this.value;
      let score = 0;
      if (pw.length >= 8)          score++;
      if (/[A-Z]/.test(pw))        score++;
      if (/[0-9]/.test(pw))        score++;
      if (/[^A-Za-z0-9]/.test(pw)) score++;

      const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
      const colors = ['', 'bg-danger', 'bg-warning', 'bg-info', 'bg-success'];

      strengthBar.style.width = (score * 25) + '%';
      strengthBar.className   = 'progress-bar ' + (colors[score] || '');
      if (strengthText) strengthText.textContent = labels[score] || '';
    });
  }

  // ── Confirm password match ─────────────────────────────
  const confirmPw = document.getElementById('confirm_password');
  if (confirmPw && pwInput) {
    confirmPw.addEventListener('input', function () {
      if (this.value && this.value !== pwInput.value) {
        this.classList.add('is-invalid');
      } else {
        this.classList.remove('is-invalid');
      }
    });
  }

  // ── Profile image preview ──────────────────────────────
  var avatarInputEl = document.getElementById('avatarInput');
  if (avatarInputEl) {
    avatarInputEl.addEventListener('change', function () {
      var file = this.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        var wrap = document.getElementById('avatarPreviewWrap');
        if (wrap) {
          wrap.innerHTML = '<img id="avatarPreview" src="' + e.target.result + '" style="width:100%;height:100%;object-fit:cover;object-position:center;">';
        }
      };
      reader.readAsDataURL(file);
    });
  }

  // ── Banner image preview ───────────────────────────────
  var bannerInputEl = document.getElementById('bannerInput');
  if (bannerInputEl) {
    bannerInputEl.addEventListener('change', function () {
      var file = this.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        var preview     = document.getElementById('bannerPreview');
        var placeholder = document.getElementById('bannerPlaceholder');
        if (preview) {
          preview.src             = e.target.result;
          preview.style.display   = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';
      };
      reader.readAsDataURL(file);
    });
  }

  // ── Unsaved changes warning ────────────────────────────
  let formDirty = false;
  const profileForm = document.getElementById('profileForm');
  if (profileForm) {
    profileForm.querySelectorAll('input, select, textarea').forEach(function (el) {
      el.addEventListener('change', function () { formDirty = true; });
    });
    profileForm.addEventListener('submit', function () { formDirty = false; });
  }
  window.addEventListener('beforeunload', function (e) {
    if (formDirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

});
