/* ══════════════════════════════════════════════════════════════
   kidzora-empty-states.js
   Utility functions for managing empty-state visibility and interactions
═══════════════════════════════════════════════════════════════ */

/**
 * Show empty state container, hide content
 * @param {string|Element} containerId - Container ID or element
 * @example showEmptyState('wishlist-container');
 */
window.showEmptyState = function (containerId) {
  var container = typeof containerId === 'string'
    ? document.getElementById(containerId)
    : containerId;

  if (!container) return;

  var emptyState = container.querySelector('[data-empty-state]');
  var content = container.querySelector('[data-empty-content]');

  if (emptyState) {
    emptyState.classList.remove('d-none');
    emptyState.classList.add('d-flex');
  }
  if (content) {
    content.classList.add('d-none');
  }
};

/**
 * Hide empty state container, show content
 * @param {string|Element} containerId - Container ID or element
 * @example hideEmptyState('wishlist-container');
 */
window.hideEmptyState = function (containerId) {
  var container = typeof containerId === 'string'
    ? document.getElementById(containerId)
    : containerId;

  if (!container) return;

  var emptyState = container.querySelector('[data-empty-state]');
  var content = container.querySelector('[data-empty-content]');

  if (emptyState) {
    emptyState.classList.add('d-none');
    emptyState.classList.remove('d-flex');
  }
  if (content) {
    content.classList.remove('d-none');
  }
};

/**
 * Toggle empty state visibility
 * @param {string|Element} containerId - Container ID or element
 * @param {boolean} show - Whether to show empty state
 * @example setEmptyState('orders-container', true);
 */
window.setEmptyState = function (containerId, show) {
  if (show) {
    window.showEmptyState(containerId);
  } else {
    window.hideEmptyState(containerId);
  }
};

/**
 * Show empty states for multiple containers at once
 * @param {string|Element} ...containers - Container IDs or elements
 * @example showEmptyStatesBy('.wishlist-item'); // Show all empty states with class
 */
window.showEmptyStatesBy = function (selector) {
  var elements = document.querySelectorAll(selector);
  elements.forEach(function (el) {
    window.showEmptyState(el);
  });
};

/**
 * Hide empty states for multiple containers at once
 * @param {string|Element} ...containers - Container IDs or elements
 * @example hideEmptyStatesBy('.wishlist-item');
 */
window.hideEmptyStatesBy = function (selector) {
  var elements = document.querySelectorAll(selector);
  elements.forEach(function (el) {
    window.hideEmptyState(el);
  });
};

/**
 * Show/hide based on item count
 * @param {string|Element} containerId - Container ID or element
 * @param {number} itemCount - Number of items
 * @example setEmptyStateByCount('orders-container', orders.length);
 */
window.setEmptyStateByCount = function (containerId, itemCount) {
  window.setEmptyState(containerId, itemCount === 0);
};

/**
 * Wrap async operation with empty state management
 * @param {string|Element} containerId - Container ID or element
 * @param {Function} asyncOperation - Promise-returning function
 * @example withEmptyState('wishlist', fetchWishlist());
 */
window.withEmptyState = function (containerId, asyncOperation) {
  window.showEmptyState(containerId);

  return Promise.resolve(asyncOperation)
    .then(function (result) {
      window.hideEmptyState(containerId);
      return result;
    })
    .catch(function (error) {
      window.showEmptyState(containerId);
      console.error('Error in withEmptyState:', error);
      throw error;
    });
};

/**
 * Show empty state, auto-hide after duration
 * @param {string|Element} containerId - Container ID or element
 * @param {number} duration - Time in milliseconds before hiding
 * @example showEmptyStateFor('notifications', 3000);
 */
window.showEmptyStateFor = function (containerId, duration) {
  window.showEmptyState(containerId);
  if (duration && duration > 0) {
    setTimeout(function () {
      window.hideEmptyState(containerId);
    }, duration);
  }
};

/**
 * Set empty state for multiple containers with one call
 * @param {boolean} show - Show or hide
 * @param {string|Element} ...containers - Container IDs or elements
 * @example setEmptyStates(true, 'orders', 'notifications', 'inbox');
 * @example setEmptyStates(false, 'cart-container', 'wishlist-container');
 */
window.setEmptyStates = function (show) {
  // Get all arguments after the first (show parameter)
  var containers = Array.prototype.slice.call(arguments, 1);

  containers.forEach(function (containerId) {
    window.setEmptyState(containerId, show);
  });
};

/**
 * Update empty state message dynamically
 * @param {string|Element} containerId - Container ID or element
 * @param {string} title - New empty state title
 * @param {string} description - New empty state description
 * @example updateEmptyStateMessage('search-results', 'No results found', 'Try adjusting your filters');
 */
window.updateEmptyStateMessage = function (containerId, title, description) {
  var container = typeof containerId === 'string'
    ? document.getElementById(containerId)
    : containerId;

  if (!container) return;

  var emptyState = container.querySelector('[data-empty-state]');
  if (!emptyState) return;

  var titleEl = emptyState.querySelector('.empty-state__title');
  var descEl = emptyState.querySelector('.empty-state__description');

  if (titleEl && title) {
    titleEl.textContent = title;
  }
  if (descEl && description) {
    descEl.textContent = description;
  }
};

/**
 * Toggle empty state visibility for multiple items based on condition
 * @param {Array} items - Array to check
 * @param {string} containerId - Container ID for empty state
 * @param {boolean} [showIfEmpty=true] - Show empty state if array is empty
 * @example checkAndToggleEmptyState(wishlistItems, 'wishlist-container');
 */
window.checkAndToggleEmptyState = function (items, containerId, showIfEmpty) {
  showIfEmpty = showIfEmpty !== false; // Default to true

  if (items && Array.isArray(items)) {
    window.setEmptyState(containerId, showIfEmpty && items.length === 0);
  }
};

/* ══════════════════════════════════════════════════════════════
   Usage Pattern:
   
   HTML Structure:
   <div id="orders-container">
     <div data-empty-state class="empty-state d-none">
       <div class="empty-state__icon">...</div>
       <h2 class="empty-state__title">No Orders Yet</h2>
       <p class="empty-state__description">Start shopping...</p>
     </div>
     <div data-empty-content><!-- Real content here --></div>
   </div>

   JavaScript Usage:
   window.showEmptyState('orders-container');
   window.hideEmptyState('orders-container');
   window.setEmptyState('orders-container', true);
   window.setEmptyStateByCount('orders-container', orders.length);
═════════════════════════════════════════════════════════════ */
