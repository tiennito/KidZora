/**
 * KidZora – Buyer / Product Detail
 * Reads config from window.KZ_PD set by the template:
 *   window.KZ_PD = {
 *     basePrice  : Number,
 *     baseStock  : Number,
 *     helpfulUrl : String  (contains "PLACEHOLDER" for review_id)
 *   };
 */
(function () {
  'use strict';

  /* ── Config (injected by template via #pdConfig data attributes) ── */
  var _cfg   = document.getElementById('pdConfig');
  var BASE_PRICE = _cfg ? parseFloat(_cfg.dataset.basePrice) || 0 : 0;
  var BASE_STOCK = _cfg ? parseInt(_cfg.dataset.baseStock)   || 0 : 0;
  var HELPFUL_URL   = _cfg ? _cfg.dataset.helpfulUrl  : '';
  var WISHLIST_URL  = _cfg ? _cfg.dataset.wishlistUrl : '';
  var BASE_STOCK_HTML = '';
  /* legacy alias for code that still reads window.KZ_PD */
  window.KZ_PD = { basePrice: BASE_PRICE, baseStock: BASE_STOCK, helpfulUrl: HELPFUL_URL, wishlistUrl: WISHLIST_URL };

  /* ── Star-bar widths (data-pct → CSS custom property) ────── */
  document.querySelectorAll('.kz-star-bar[data-pct]').forEach(function (el) {
    el.style.setProperty('--bar-w', el.dataset.pct + '%');
  });

  /* ── Qty stepper ─────────────────────────────────────────── */
  /* ── Qty error helpers ───────────────────────────────────── */
  function showQtyError(msg) {
    var err  = document.getElementById('qtyError');
    var span = document.getElementById('qtyErrorMsg');
    var inp  = document.getElementById('qtyInput');
    if (span) span.textContent = msg;
    if (err)  err.style.display = '';
    if (inp)  inp.style.borderColor = '#dc3545';
  }
  function clearQtyError() {
    var err = document.getElementById('qtyError');
    var inp = document.getElementById('qtyInput');
    if (err) err.style.display = 'none';
    if (inp) inp.style.borderColor = '';
  }

  function adjustQty(delta) {
    var input = document.getElementById('qtyInput');
    if (!input) return;
    var val = Math.max(1, Math.min(parseInt(input.max) || 99, parseInt(input.value) + delta));
    input.value = val;
    clearQtyError();
    var ch = document.getElementById('cartQtyHidden');
    var bh = document.getElementById('buyNowQtyHidden');
    if (ch) ch.value = val;
    if (bh) bh.value = val;
  }
  window.adjustQty = adjustQty;   // called from inline onclick

  /* ── Thumbnail <-> Bootstrap carousel sync ───────────────── */
  function initCarousel() {
    var carousel = document.getElementById('productCarousel');
    var counter  = document.getElementById('imgCounter');
    var thumbs   = document.querySelectorAll('.thumb-img');
    if (!carousel || !thumbs.length) return;

    function activate(idx) {
      thumbs.forEach(function (t, i) { t.classList.toggle('active', i === idx); });
      if (counter) counter.textContent = (idx + 1) + ' / ' + thumbs.length;
    }
    thumbs.forEach(function (t) {
      t.addEventListener('click', function () {
        bootstrap.Carousel.getOrCreateInstance(carousel).to(parseInt(t.dataset.index));
      });
    });
    carousel.addEventListener('slid.bs.carousel', function (e) { activate(e.to); });
  }

  /* ── Stock helper ────────────────────────────────────────── */
  function setStock(stock) {
    var el = document.getElementById('stockInfo');
    if (el) {
      el.innerHTML = stock > 0
        ? '<i class="fas fa-check-circle text-success me-1"></i>' +
          '<span class="text-success fw-semibold">In Stock</span> ' +
          '<span class="text-muted">(' + stock + ' available)</span>'
        : '<span class="badge bg-danger">Out of Stock for this variant</span>';
    }
    var qi = document.getElementById('qtyInput');
    if (qi) {
      qi.max = stock > 0 ? stock : 1;
      if (parseInt(qi.value) > stock) qi.value = Math.max(1, stock);
    }
    var addBtn = document.getElementById('addToCartBtn');
    var bnBtn  = document.getElementById('buyNowBtn');
    if (stock > 0) {
      if (addBtn) addBtn.removeAttribute('disabled');
      if (bnBtn)  bnBtn.removeAttribute('disabled');
    } else {
      if (addBtn) addBtn.setAttribute('disabled', '');
      if (bnBtn)  bnBtn.setAttribute('disabled', '');
    }
  }

  /* ── Variant picker ──────────────────────────────────────── */
  function selectVariant(btn) {
    var vid = btn.dataset.vid;
    var selectedInput = document.getElementById('selectedVariantId');
    var isDeselect = selectedInput && selectedInput.value === vid;
    document.querySelectorAll('.variant-btn').forEach(function (b) { b.classList.remove('active'); });
    if (isDeselect) { clearVariantSelection(); return; }

    btn.classList.add('active');
    if (selectedInput) selectedInput.value = vid;

    var cv = document.getElementById('cartVariantId');
    var bv = document.getElementById('buyNowVariantId');
    if (cv) cv.value = vid;
    if (bv) bv.value = vid;

    var mod = parseFloat(btn.dataset.modifier);
    var np  = Math.max(0, BASE_PRICE + (isNaN(mod) ? 0 : mod));
    var dp  = document.getElementById('displayPrice');
    if (dp) dp.textContent = np.toFixed(2);

    var hint = document.getElementById('variantHint');
    if (hint) {
      hint.textContent = mod > 0 ? '+\u20B1' + mod.toFixed(2) + ' from base'
                       : mod < 0 ? '-\u20B1' + Math.abs(mod).toFixed(2) + ' from base'
                       : '';
    }

    var varStock = parseInt(btn.dataset.stock);
    setStock(isNaN(varStock) ? BASE_STOCK : varStock);

    if (btn.dataset.image) {
      var img = document.getElementById('variantOverlayImg');
      if (img) img.src = btn.dataset.image;
      document.getElementById('variantOverlay').classList.remove('d-none');
      document.getElementById('productGallery').classList.add('d-none');
    }
  }
  window.selectVariant = selectVariant;

  function clearVariantSelection() {
    var overlay = document.getElementById('variantOverlay');
    var gallery = document.getElementById('productGallery');
    if (overlay) overlay.classList.add('d-none');
    if (gallery) gallery.classList.remove('d-none');

    var si = document.getElementById('selectedVariantId');
    var cv = document.getElementById('cartVariantId');
    var bv = document.getElementById('buyNowVariantId');
    if (si) si.value = '';
    if (cv) cv.value = '';
    if (bv) bv.value = '';

    var dp = document.getElementById('displayPrice');
    if (dp) dp.textContent = BASE_PRICE.toFixed(2);

    var hint = document.getElementById('variantHint');
    if (hint) hint.textContent = '';

    var elStock = document.getElementById('stockInfo');
    if (elStock) elStock.innerHTML = BASE_STOCK_HTML;

    var qi = document.getElementById('qtyInput');
    if (qi) qi.max = BASE_STOCK > 0 ? BASE_STOCK : 1;

    setStock(BASE_STOCK);
    document.querySelectorAll('.variant-btn').forEach(function (b) { b.classList.remove('active'); });
  }
  window.clearVariantSelection = clearVariantSelection;

  /* ── Tab switcher ────────────────────────────────────────── */
  function initTabs() {
    document.querySelectorAll('.kz-tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.kz-tab-btn').forEach(function (b) { b.classList.remove('active'); });
        document.querySelectorAll('.kz-tab-pane').forEach(function (p) { p.classList.remove('active'); });
        btn.classList.add('active');
        var pane = document.getElementById('tab-' + btn.dataset.tab);
        if (pane) pane.classList.add('active');
      });
    });
  }

  /* ── Review filter pills ─────────────────────────────────── */
  function initFilterPills() {
    document.querySelectorAll('.kz-filter-pill').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.kz-filter-pill').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var type = btn.dataset.filterType;
        var val  = btn.dataset.filterVal;
        document.querySelectorAll('.review-card').forEach(function (card) {
          var show = true;
          if (type === 'star')     show = card.dataset.rating   === val;
          if (type === 'comments') show = card.dataset.hasBody  === '1';
          if (type === 'media')    show = card.dataset.hasMedia === '1';
          if (type === 'variant')  show = card.dataset.variant  === val;
          card.style.display = show ? '' : 'none';
        });
      });
    });
  }

  /* ── Star picker ─────────────────────────────────────────── */
  function initStarPicker() {
    var picker = document.getElementById('starPicker');
    var input  = document.getElementById('ratingInput');
    if (!picker || !input) return;
    var stars  = picker.querySelectorAll('.star-pick');

    function paint(n) {
      stars.forEach(function (s, i) {
        s.classList.toggle('fas', i < n);
        s.classList.toggle('far', i >= n);
      });
    }
    paint(parseInt(input.value) || 0);
    stars.forEach(function (s) {
      s.addEventListener('mouseover', function () { paint(parseInt(s.dataset.val)); });
      s.addEventListener('mouseleave', function () { paint(parseInt(input.value) || 0); });
      s.addEventListener('click', function () {
        input.value = s.dataset.val;
        paint(parseInt(s.dataset.val));
      });
    });
  }

  /* ── Review media file preview ───────────────────────────── */
  function previewReviewMedia(input) {
    var preview = document.getElementById('reviewMediaPreview');
    if (!preview) return;
    preview.innerHTML = '';
    Array.from(input.files).slice(0, 5).forEach(function (file) {
      var url   = URL.createObjectURL(file);
      var isVid = ['mp4','mov','avi','webm','mkv'].includes(file.name.split('.').pop().toLowerCase());
      var el    = document.createElement(isVid ? 'video' : 'img');
      el.src       = url;
      el.className = 'kz-media-thumb';
      el.title     = file.name;
      el.onclick   = function () { openMediaModal(url, isVid ? 'video' : 'image'); };
      preview.appendChild(el);
    });
  }
  window.previewReviewMedia = previewReviewMedia;

  /* ── Media lightbox ──────────────────────────────────────── */
  function openMediaModal(src, type) {
    var body = document.getElementById('mediaModalBody');
    if (!body) return;
    body.innerHTML = type === 'video'
      ? '<video src="' + src + '" class="img-fluid rounded" controls autoplay style="max-height:75vh"></video>'
      : '<img src="' + src + '" class="img-fluid rounded" style="max-height:75vh">';
    new bootstrap.Modal(document.getElementById('mediaModal')).show();
  }
  window.openMediaModal = openMediaModal;

  /* ── Helpful vote (AJAX) ─────────────────────────────────── */
  function initHelpfulButtons() {
    document.querySelectorAll('.helpful-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var rid = this.dataset.reviewId;
        var url = (HELPFUL_URL || '').replace('PLACEHOLDER', rid);
        if (!url) return;
        var self = this;
        fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.success) return;
            self.classList.toggle('active', data.voted);
            var c = self.querySelector('.helpful-count');
            if (c) c.textContent = '(' + data.count + ')';
          })
          .catch(function () {});
      });
    });
  }

  /* ── Edit review pre-fill ────────────────────────────────── */
  function openEditReview(review) {
    var card = document.getElementById('reviewFormCard');
    if (!card) return;
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });

    var titleEl = document.getElementById('reviewFormTitle');
    if (titleEl) titleEl.textContent = 'Edit Your Review';

    var ri = document.getElementById('ratingInput');
    if (ri) {
      ri.value = review.rating;
      document.querySelectorAll('#starPicker .star-pick').forEach(function (s, i) {
        s.classList.toggle('fas', i < review.rating);
        s.classList.toggle('far', i >= review.rating);
      });
    }
    var vs = document.getElementById('reviewVariantSelect');
    if (vs && review.variant_id) vs.value = review.variant_id;

    var ti = document.querySelector('#reviewForm input[name="title"]');
    if (ti) ti.value = review.title || '';

    var bo = document.querySelector('#reviewForm textarea[name="body"]');
    if (bo) bo.value = review.body || '';
  }
  window.openEditReview = openEditReview;

  /* ── Qty input live sync ─────────────────────────────────── */
  function initQtySync() {
    var qtyInput = document.getElementById('qtyInput');
    if (!qtyInput) return;

    function validate() {
      var raw  = qtyInput.value.trim();
      var max  = parseInt(qtyInput.max) || 99;
      var v    = parseInt(raw);
      var ch   = document.getElementById('cartQtyHidden');
      var bh   = document.getElementById('buyNowQtyHidden');

      if (raw === '' || isNaN(v)) {
        showQtyError('Please enter a valid quantity.');
        qtyInput.value = 1;
        v = 1;
      } else if (v < 1) {
        showQtyError('Minimum quantity is 1.');
        qtyInput.value = 1;
        v = 1;
      } else if (v > max) {
        showQtyError('Only ' + max + ' item' + (max === 1 ? '' : 's') + ' available in stock.');
        qtyInput.value = max;
        v = max;
      } else {
        clearQtyError();
      }

      if (ch) ch.value = v;
      if (bh) bh.value = v;
    }

    qtyInput.addEventListener('input',  validate);
    qtyInput.addEventListener('change', validate);  // catches paste & manual edit on blur
  }

  /* ── Wishlist toggle (AJAX) ──────────────────────────────── */
  function showFavToast(msg, isAdd) {
    var existing = document.getElementById('favToast');
    if (existing) existing.remove();
    var t = document.createElement('div');
    t.id = 'favToast';
    t.innerHTML = (isAdd ? '<i class="fas fa-heart text-danger me-2"></i>' : '<i class="far fa-heart me-2"></i>') + msg;
    Object.assign(t.style, {
      position: 'fixed', bottom: '28px', left: '50%',
      transform: 'translateX(-50%) translateY(16px)',
      background: '#1a1a1a', color: '#fff',
      padding: '10px 22px', borderRadius: '24px',
      fontSize: '.88rem', zIndex: '9999', opacity: '0',
      transition: 'opacity .22s, transform .22s',
      whiteSpace: 'nowrap', boxShadow: '0 4px 18px rgba(0,0,0,.35)',
      pointerEvents: 'none'
    });
    document.body.appendChild(t);
    requestAnimationFrame(function () {
      t.style.opacity = '1';
      t.style.transform = 'translateX(-50%) translateY(0)';
    });
    setTimeout(function () {
      t.style.opacity = '0';
      t.style.transform = 'translateX(-50%) translateY(10px)';
      setTimeout(function () { if (t.parentNode) t.remove(); }, 280);
    }, 2400);
  }

  function initWishlistButton() {
    var btn = document.getElementById('wishlistBtn');
    if (!btn) return;
    var url = WISHLIST_URL || '';

    btn.addEventListener('click', function () {
      if (!url) return;
      fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.success) return;
          var icon  = btn.querySelector('i');
          var label = btn.querySelector('.kz-wish-label');
          if (data.wishlisted) {
            btn.classList.add('active');
            if (icon)  { icon.classList.remove('far'); icon.classList.add('fas'); }
            if (label) label.textContent = 'Favorited';
            btn.title = 'Remove from Favorites';
            showFavToast('Added to Favorites', true);
          } else {
            btn.classList.remove('active');
            if (icon)  { icon.classList.remove('fas'); icon.classList.add('far'); }
            if (label) label.textContent = 'Favorite';
            btn.title = 'Add to Favorites';
            showFavToast('Removed from Favorites', false);
          }
        })
        .catch(function () {
          showFavToast('Could not update \u2014 please try again', false);
        });
    });
  }

  /* ── Review client-side pagination ─────────────────────── */
  function initReviewPagination() {
    var PER_PAGE = 5;
    var pager    = document.getElementById('reviewPager');
    var list     = document.getElementById('reviewList');
    if (!pager || !list) return;

    function visibleCards() {
      return Array.from(list.querySelectorAll('.review-card'))
                  .filter(function (c) { return c.style.display !== 'none'; });
    }

    function showPage(page) {
      var cards = visibleCards();
      var total = Math.ceil(cards.length / PER_PAGE);
      var start = (page - 1) * PER_PAGE;
      cards.forEach(function (c, i) {
        c.style.display = (i >= start && i < start + PER_PAGE) ? '' : 'none';
      });
      buildPager(page, total);
      pager.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function buildPager(cur, total) {
      pager.innerHTML = '';
      if (total <= 1) return;

      function btn(label, page, disabled, active) {
        var b = document.createElement('button');
        b.textContent    = label;
        b.className      = 'btn btn-sm ' + (active ? 'btn-primary' : 'btn-outline-secondary');
        b.style.minWidth = '36px';
        b.disabled       = disabled;
        if (!disabled) b.addEventListener('click', function () { showPage(page); });
        return b;
      }

      pager.appendChild(btn('\u2039', cur - 1, cur === 1, false));

      var lo = Math.max(1, cur - 2);
      var hi = Math.min(total, lo + 4);
      lo     = Math.max(1, hi - 4);
      for (var p = lo; p <= hi; p++) {
        pager.appendChild(btn(p, p, false, p === cur));
      }

      pager.appendChild(btn('\u203a', cur + 1, cur === total, false));
    }

    /* re-paginate when a filter pill is clicked */
    document.querySelectorAll('.kz-filter-pill').forEach(function (pill) {
      pill.addEventListener('click', function () {
        setTimeout(function () { showPage(1); }, 10);
      });
    });

    showPage(1);
  }

  /* ── Bootstrap-ready init ────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    // Capture initial stock HTML after DOM is ready
    var stockEl = document.getElementById('stockInfo');
    BASE_STOCK_HTML = stockEl ? stockEl.innerHTML : '';

    initCarousel();
    initTabs();
    initFilterPills();
    initStarPicker();
    initHelpfulButtons();
    initQtySync();
    initWishlistButton();
    initReviewPagination();
  });

})();
