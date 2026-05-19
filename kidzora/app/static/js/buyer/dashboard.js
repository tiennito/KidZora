/**
 * Buyer Dashboard Interactions
 * Wishlist & Follow functionality
 */

document.addEventListener('DOMContentLoaded', function() {
  setupWishlistButtons();
  setupFollowButtons();
});

/**
 * ─────────────────────────────────────────────────────────────────────
 * WISHLIST FUNCTIONALITY
 * ─────────────────────────────────────────────────────────────────────
 */

function setupWishlistButtons() {
  const buttons = document.querySelectorAll('.wishlist-btn');

  buttons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const productId = this.dataset.productId;
      const isWishlisted = this.dataset.wishlisted === 'true';

      // Toggle visual state immediately
      this.dataset.wishlisted = isWishlisted ? 'false' : 'true';
      this.classList.toggle('active');

      // Send to server
      fetch('/buyer/wishlist/toggle/' + productId, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        }
      })
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            // Revert on error
            this.dataset.wishlisted = isWishlisted ? 'true' : 'false';
            alert('Error: ' + (data.message || 'Could not update wishlist'));
          }
        })
        .catch(err => {
          console.error('[WISHLIST ERROR]', err);
          this.dataset.wishlisted = isWishlisted ? 'true' : 'false';
        });
    });
  });
}

/**
 * ─────────────────────────────────────────────────────────────────────
 * FOLLOW FUNCTIONALITY
 * ─────────────────────────────────────────────────────────────────────
 */

function setupFollowButtons() {
  const buttons = document.querySelectorAll('.follow-btn');

  buttons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const sellerId = this.dataset.sellerId;
      const isFollowing = this.classList.contains('following');

      // Update button state
      const originalText = this.innerHTML;
      this.disabled = true;
      this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processing...';

      // Send to server
      fetch(`/buyer/shop/${sellerId}/follow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: isFollowing ? 'unfollow' : 'follow'
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            // Update button visual state
            this.classList.toggle('following');
            if (isFollowing) {
              this.innerHTML = '<i class="fas fa-plus me-1"></i> Follow';
            } else {
              this.innerHTML = '<i class="fas fa-check me-1"></i> Following';
            }
          } else {
            alert('Error: ' + (data.message || 'Could not update follow status'));
            this.innerHTML = originalText;
          }
        })
        .catch(err => {
          console.error('[FOLLOW ERROR]', err);
          this.innerHTML = originalText;
        })
        .finally(() => {
          this.disabled = false;
        });
    });
  });
}

/**
 * ─────────────────────────────────────────────────────────────────────
 * SMOOTH SCROLL & PAGE TRANSITIONS
 * ─────────────────────────────────────────────────────────────────────
 */

// Add smooth scroll behavior for internal links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const href = this.getAttribute('href');
    if (href !== '#' && document.querySelector(href)) {
      e.preventDefault();
      document.querySelector(href).scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});

/**
 * ─────────────────────────────────────────────────────────────────────
 * PRODUCT CARD INTERACTIONS
 * ─────────────────────────────────────────────────────────────────────
 */

// Add loading state to product links
document.querySelectorAll('.product-card a[href]').forEach(link => {
  link.addEventListener('click', function() {
    // Log recently viewed product
    const productId = this.closest('.product-card')?.dataset?.productId;
    if (productId && window.location.href.includes('/dashboard')) {
      // Optional: Send to server if needed
    }
  });
});

/**
 * ─────────────────────────────────────────────────────────────────────
 * STORE CARD INTERACTIONS
 * ─────────────────────────────────────────────────────────────────────
 */

document.querySelectorAll('.store-card').forEach(card => {
  const link = card.querySelector('a');
  if (link) {
    card.addEventListener('click', function(e) {
      if (e.target.closest('.follow-btn')) {
        e.preventDefault();
        e.stopPropagation();
      } else {
        link.click();
      }
    });
  }
});

/**
 * ─────────────────────────────────────────────────────────────────────
 * LAZY LOAD IMAGES
 * ─────────────────────────────────────────────────────────────────────
 */

if ('IntersectionObserver' in window) {
  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (img.dataset.src) {
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
        }
        observer.unobserve(img);
      }
    });
  });

  document.querySelectorAll('img[data-src]').forEach(img => {
    imageObserver.observe(img);
  });
}

/**
 * ─────────────────────────────────────────────────────────────────────
 * CONSOLE LOGGING (Development)
 * ─────────────────────────────────────────────────────────────────────
 */

console.log('[DASHBOARD] Buyer dashboard loaded and interactive');
