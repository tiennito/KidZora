/**
 * KidZora – Rider / Profile Page
 */

document.addEventListener('DOMContentLoaded', function () {
  var input = document.getElementById('avatarInput');
  if (!input) return;

  input.addEventListener('change', function () {
    if (!this.files || !this.files[0]) return;

    var reader = new FileReader();
    reader.onload = function (e) {
      var wrap = document.getElementById('avatarPreviewWrap');
      var init = document.getElementById('avatarInitial');
      var img = document.getElementById('avatarPreview');

      if (!img) {
        img = document.createElement('img');
        img.id = 'avatarPreview';
        img.alt = 'Profile photo';
        img.className = 'rp-avatar-img';
        if (init) init.style.display = 'none';
        if (wrap) wrap.appendChild(img);
      }

      img.src = e.target.result;
    };

    reader.readAsDataURL(this.files[0]);
  });
});
