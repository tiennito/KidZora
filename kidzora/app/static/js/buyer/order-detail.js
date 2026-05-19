/**
 * KidZora – Buyer / Order Detail
 * Evidence file upload with preview, drag-and-drop, remove.
 * No template config needed — pure DOM manipulation.
 */
(function () {
  'use strict';

  var MAX_FILES  = 5;
  var IMAGE_EXTS = new Set(['png','jpg','jpeg','gif','webp']);
  var VIDEO_EXTS = new Set(['mp4','mov','avi','webm','mkv']);
  var _selectedFiles = [];   // running list of staged files

  /* ── Public: called by <input onchange> ─────────────────── */
  function previewEvidenceFiles(input) {
    var newFiles = Array.from(input.files);
    for (var i = 0; i < newFiles.length; i++) {
      if (_selectedFiles.length >= MAX_FILES) break;
      _selectedFiles.push(newFiles[i]);
    }
    renderPreviews();
  }
  window.previewEvidenceFiles = previewEvidenceFiles;

  /* ── Public: remove a staged file by index ──────────────── */
  function removeEvidenceFile(idx) {
    _selectedFiles.splice(idx, 1);
    renderPreviews();
  }
  window.removeEvidenceFile = removeEvidenceFile;

  /* ── Re-render preview grid & rebuild hidden file input ─── */
  function renderPreviews() {
    var container = document.getElementById('evidencePreview');
    if (!container) return;
    container.innerHTML = '';

    // Rebuild the native <input> files via DataTransfer
    var dt = new DataTransfer();
    _selectedFiles.forEach(function (f) { dt.items.add(f); });
    var fileInput = document.getElementById('evidenceInput');
    if (fileInput) fileInput.files = dt.files;

    _selectedFiles.forEach(function (file, idx) {
      var ext = file.name.split('.').pop().toLowerCase();
      var col = document.createElement('div');
      col.className = 'col-6 col-md-4 col-lg-3 position-relative';
      col.style.maxWidth = '150px';

      if (IMAGE_EXTS.has(ext)) {
        var url = URL.createObjectURL(file);
        col.innerHTML =
          '<img src="' + url + '" class="img-thumbnail w-100" style="height:100px;object-fit:cover;" alt="' + file.name + '">' +
          '<span class="position-absolute top-0 end-0 badge bg-secondary m-1" style="font-size:.65rem;">' + humanSize(file.size) + '</span>' +
          '<button type="button" class="btn btn-danger btn-sm w-100 mt-1 py-0" style="font-size:.7rem;" ' +
          'onclick="removeEvidenceFile(' + idx + ')"><i class="fas fa-times me-1"></i>Remove</button>';
      } else if (VIDEO_EXTS.has(ext)) {
        var vurl = URL.createObjectURL(file);
        col.innerHTML =
          '<video src="' + vurl + '" class="w-100 rounded" style="height:100px;object-fit:cover;" muted preload="metadata"></video>' +
          '<span class="d-block text-center small text-muted mt-1 text-truncate" title="' + file.name + '" style="font-size:.7rem;">' +
          '<i class="fas fa-film me-1"></i>' + file.name + '</span>' +
          '<span class="d-block text-center" style="font-size:.65rem;">' + humanSize(file.size) + '</span>' +
          '<button type="button" class="btn btn-danger btn-sm w-100 mt-1 py-0" style="font-size:.7rem;" ' +
          'onclick="removeEvidenceFile(' + idx + ')"><i class="fas fa-times me-1"></i>Remove</button>';
      }

      container.appendChild(col);
    });

    if (_selectedFiles.length > 0) {
      var info = document.createElement('div');
      info.className = 'col-12 mt-2';
      info.innerHTML = '<small class="text-muted">' + _selectedFiles.length + ' / ' + MAX_FILES + ' file(s) selected</small>';
      container.appendChild(info);
    }
  }

  /* ── Drag-and-drop on the drop zone ─────────────────────── */
  function initDropZone() {
    var zone = document.getElementById('rrDropZone');
    if (!zone) return;
    zone.addEventListener('dragover', function (e) {
      e.preventDefault();
      zone.classList.add('border-primary');
    });
    zone.addEventListener('dragleave', function () {
      zone.classList.remove('border-primary');
    });
    zone.addEventListener('drop', function (e) {
      e.preventDefault();
      zone.classList.remove('border-primary');
      previewEvidenceFiles({ files: e.dataTransfer.files });
    });
  }

  /* ── Byte size formatter ─────────────────────────────────── */
  function humanSize(bytes) {
    if (bytes < 1024)    return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

  /* ── Init ────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', initDropZone);

})();

/* ── Review modal star picker ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.modal-star-picker').forEach(function (group) {
    var pid   = group.dataset.pid;
    var stars = Array.from(group.querySelectorAll('.modal-star'));
    var input = document.getElementById('rating_' + pid);
    var extra = document.getElementById('fields_' + pid);

    function paintStars(upTo) {
      stars.forEach(function (s, i) {
        s.classList.toggle('fas', i < upTo);
        s.classList.toggle('far', i >= upTo);
      });
    }

    group.addEventListener('mouseleave', function () {
      paintStars(parseInt(input.value) || 0);
    });

    stars.forEach(function (star) {
      star.addEventListener('mouseenter', function () {
        paintStars(parseInt(this.dataset.val));
      });
      star.addEventListener('click', function () {
        var val = parseInt(this.dataset.val);
        input.value = val;
        paintStars(val);
        if (extra) { extra.style.display = 'block'; }
        star.style.transform = 'scale(1.3)';
        setTimeout(function () { star.style.transform = ''; }, 150);
      });
    });
  });
});

/* ── Rider rating star picker ─────────────────────────────────── */
function setRiderRating(val) {
  document.getElementById('riderRatingInput').value = val;
  document.querySelectorAll('.rr-star').forEach(function (s) {
    s.style.color = parseInt(s.dataset.val) <= val ? '#f59e0b' : '#d1d5db';
  });
}
document.addEventListener('DOMContentLoaded', function () {
  /* initialise colors from pre-filled hidden input (edit flow) */
  var initInput = document.getElementById('riderRatingInput');
  if (initInput && initInput.value) {
    setRiderRating(parseInt(initInput.value));
  } else {
    document.querySelectorAll('.rr-star').forEach(function (s) {
      s.style.color = '#d1d5db';
    });
  }

  document.querySelectorAll('.rr-star').forEach(function (s) {
    s.addEventListener('mouseenter', function () {
      var v = parseInt(this.dataset.val);
      document.querySelectorAll('.rr-star').forEach(function (x) {
        x.style.color = parseInt(x.dataset.val) <= v ? '#f59e0b' : '#d1d5db';
      });
    });
    s.addEventListener('mouseleave', function () {
      var cur = parseInt(document.getElementById('riderRatingInput').value) || 0;
      document.querySelectorAll('.rr-star').forEach(function (x) {
        x.style.color = parseInt(x.dataset.val) <= cur ? '#f59e0b' : '#d1d5db';
      });
    });
    s.addEventListener('click', function () {
      setRiderRating(parseInt(this.dataset.val));
    });
  });
});
