/* ══════════════════════════════════════════════
   buyer/wishlist.js
   Wishlist (My Favorites) page interactions
══════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Initialize empty state on page load ───────────────────── */
  var productCards = document.querySelectorAll('.col .card');
  
  // Show empty state if no products, hide if there are products
  if (productCards.length === 0) {
    window.showEmptyState('wishlist-container');
  } else {
    window.hideEmptyState('wishlist-container');
  }

  /* ── Initialize wishlist product cards ─────────────────────── */
  productCards.forEach(function (card) {
    var addToCartBtn = card.querySelector('button[title*="Add to Cart"]');
    var removeBtn = card.querySelector('button[title*="Remove from Favorites"]');
    
    // Add to cart feedback
    if (addToCartBtn) {
      addToCartBtn.addEventListener('click', function () {
        var icon = this.querySelector('i');
        var originalClass = icon.className;
        // Temporary feedback
        icon.className = 'fas fa-check text-success';
        setTimeout(function () {
          icon.className = originalClass;
        }, 800);
      });
    }
    
    // Remove from favorites feedback
    if (removeBtn) {
      removeBtn.addEventListener('click', function () {
        // Fade out card before submission
        card.style.opacity = '0.5';
        card.style.pointerEvents = 'none';
      });
    }
  });

  /* ── Product card hover effects ────────────────────────────── */
  productCards.forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      this.style.transform = 'translateY(-2px)';
      this.style.boxShadow = '0 12px 24px rgba(0,0,0,0.15)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.transform = '';
      this.style.boxShadow = '';
    });
  });

})();
