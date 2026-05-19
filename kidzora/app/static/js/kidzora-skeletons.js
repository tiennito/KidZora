/* ══════════════════════════════════════════════════════════════
   kidzora-skeletons.js
   Utility functions for managing loading skeleton screens
   Simple API for showing/hiding skeletons with content
══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /**
   * Show skeleton placeholder, hide content
   * @param {string|HTMLElement} containerId - Container ID or element
   */
  window.showSkeleton = function (containerId) {
    var container = typeof containerId === 'string' 
      ? document.getElementById(containerId) 
      : containerId;
    
    if (!container) return;

    var skeleton = container.querySelector('[data-skeleton]');
    var content = container.querySelector('[data-skeleton-content]');

    if (skeleton) {
      skeleton.classList.remove('skeleton-hidden');
      skeleton.classList.add('skeleton-visible');
    }

    if (content) {
      content.classList.remove('skeleton-visible');
      content.classList.add('skeleton-hidden');
    }
  };

  /**
   * Hide skeleton placeholder, show content
   * @param {string|HTMLElement} containerId - Container ID or element
   */
  window.hideSkeleton = function (containerId) {
    var container = typeof containerId === 'string' 
      ? document.getElementById(containerId) 
      : containerId;
    
    if (!container) return;

    var skeleton = container.querySelector('[data-skeleton]');
    var content = container.querySelector('[data-skeleton-content]');

    if (skeleton) {
      skeleton.classList.add('skeleton-hidden');
      skeleton.classList.remove('skeleton-visible');
    }

    if (content) {
      content.classList.add('skeleton-visible');
      content.classList.remove('skeleton-hidden');
    }
  };

  /**
   * Toggle skeleton visibility
   * @param {string|HTMLElement} containerId - Container ID or element
   * @param {boolean} show - Show skeleton if true, hide if false
   */
  window.setSkeleton = function (containerId, show) {
    if (show) {
      window.showSkeleton(containerId);
    } else {
      window.hideSkeleton(containerId);
    }
  };

  /**
   * Show multiple skeletons by selector
   * @param {string} selector - CSS selector for elements
   */
  window.showSkeletonsBy = function (selector) {
    document.querySelectorAll(selector).forEach(function (el) {
      window.showSkeleton(el);
    });
  };

  /**
   * Hide multiple skeletons by selector
   * @param {string} selector - CSS selector for elements
   */
  window.hideSkeletonsBy = function (selector) {
    document.querySelectorAll(selector).forEach(function (el) {
      window.hideSkeleton(el);
    });
  };

  /**
   * Create a promise-based skeleton wrapper for async operations
   * @param {string|HTMLElement} containerId - Container ID or element
   * @param {Promise} asyncOperation - Promise to wrap
   * @returns {Promise} Original promise chain
   */
  window.withSkeleton = function (containerId, asyncOperation) {
    window.showSkeleton(containerId);
    
    return asyncOperation
      .then(function (result) {
        window.hideSkeleton(containerId);
        return result;
      })
      .catch(function (error) {
        window.hideSkeleton(containerId);
        throw error;
      });
  };

  /**
   * Show skeleton for time duration then automatically hide
   * Useful for placeholder timing during development
   * @param {string|HTMLElement} containerId - Container ID or element
   * @param {number} duration - Duration in milliseconds (default 2000)
   */
  window.showSkeletonFor = function (containerId, duration) {
    duration = duration || 2000;
    window.showSkeleton(containerId);
    
    setTimeout(function () {
      window.hideSkeleton(containerId);
    }, duration);
  };

  /**
   * Batch show/hide operations for multiple containers
   * @param {Array<string>|Array<HTMLElement>} containers - Array of container IDs or elements
   * @param {boolean} show - Show skeleton if true, hide if false
   */
  window.setSkeletons = function (show) {
    var containers = Array.prototype.slice.call(arguments, 1);
    
    containers.forEach(function (containerId) {
      window.setSkeleton(containerId, show);
    });
  };

  /* ══════════════════════════════════════════════════════════════
     Usage Examples:
     
     HTML:
     <div id="chart-container">
       <div data-skeleton>
         <div class="skeleton-chart"></div>
       </div>
       <div data-skeleton-content style="display: none;">
         <canvas id="myChart"></canvas>
       </div>
     </div>
     
     JavaScript:
     // Show skeleton while loading
     showSkeleton('chart-container');
     
     // Hide skeleton when data arrives
     hideSkeleton('chart-container');
     
     // Promise-based approach
     withSkeleton('chart-container', 
       fetch('/api/data').then(r => r.json())
     );
     
     // Auto-hide after duration
     showSkeletonFor('chart-container', 3000);
     
     // Batch operations
     setSkeletons(true, 'chart-1', 'chart-2', 'table-1');
     
  ══════════════════════════════════════════════════════════════ */

})();
