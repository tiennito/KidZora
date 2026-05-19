/* ══════════════════════════════════════════════════════════════
   kidzora-utils.js
   Shared utility functions used across all role modules
   - Currency formatting (Philippine peso)
   - Notification type/icon/color mapping
   - Status label mapping
   - Delivery count formatting
   - Payout amount formatting
══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ──────────────────────────────────────────────────────────
     Currency Formatting
  ────────────────────────────────────────────────────────── */
  
  /**
   * Format amount as Philippine peso with thousands separator
   * @param {number} amount - Amount to format
   * @returns {string} Formatted string like "₱1,234.56"
   */
  window.formatCurrency = function (amount) {
    return '₱' + parseFloat(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  };

  /**
   * Format payout amount (alias for formatCurrency)
   * @param {number} amount - Amount to format
   * @returns {string} Formatted string like "₱1,234.56"
   */
  window.formatPayoutAmount = function (amount) {
    return window.formatCurrency(amount);
  };

  /* ──────────────────────────────────────────────────────────
     Delivery Count Formatting
  ────────────────────────────────────────────────────────── */

  /**
   * Format delivery count (ensures integer)
   * @param {number} count - Count to format
   * @returns {number} Integer count
   */
  window.formatDeliveryCount = function (count) {
    return parseInt(count, 10) || 0;
  };

  /* ──────────────────────────────────────────────────────────
     Notification Type / Icon / Color Utilities
  ────────────────────────────────────────────────────────── */

  /**
   * Get human-readable label for notification type
   * @param {string} type - Notification type code
   * @returns {string} Display label
   */
  window.getNotificationType = function (type) {
    var types = {
      'new_pickup':              'New Pickup Available',
      'order_completed':         'Order Completed',
      'delivery_assigned':       'Delivery Assigned',
      'rider_payout_approved':   'Payout Approved',
      'rider_payout_rejected':   'Payout Rejected',
      'message_received':        'New Message',
      'rating_received':         'New Rating',
      'cancel':                  'Delivery Cancelled',
      'order_placed':            'Order Placed',
      'order_confirmed':         'Order Confirmed',
      'order_preparing':         'Order Preparing',
      'out_for_delivery':        'Out for Delivery',
      'delivered':               'Delivered',
      'completed':               'Order Completed',
      'cancelled':               'Order Cancelled',
      'return':                  'Return Request',
      'message':                 'New Message',
    };
    return types[type] || (type || 'Notification').replace('_', ' ').charAt(0).toUpperCase() + (type || 'notification').slice(1).replace('_', ' ');
  };

  /**
   * Get Font Awesome icon class for notification type
   * @param {string} type - Notification type code
   * @returns {string} Font Awesome icon class
   */
  window.getNotificationIcon = function (type) {
    var icons = {
      'new_pickup':              'fas fa-box-open',
      'order_completed':         'fas fa-check-circle',
      'delivery_assigned':       'fas fa-motorcycle',
      'rider_payout_approved':   'fas fa-check-square',
      'rider_payout_rejected':   'fas fa-times-square',
      'message_received':        'fas fa-comment-dots',
      'rating_received':         'fas fa-star',
      'cancel':                  'fas fa-ban',
      'order_placed':            'fas fa-shopping-bag',
      'order_confirmed':         'fas fa-check-circle',
      'order_preparing':         'fas fa-box',
      'out_for_delivery':        'fas fa-motorcycle',
      'delivered':               'fas fa-house-user',
      'completed':               'fas fa-star',
      'cancelled':               'fas fa-times-circle',
      'return':                  'fas fa-undo-alt',
      'message':                 'fas fa-comment-dots',
    };
    return icons[type] || 'fas fa-bell';
  };

  /**
   * Get Bootstrap color/text class for notification type (buyer notifications)
   * @param {string} type - Notification type code
   * @returns {string} Bootstrap text color class
   */
  window.getNotificationColor = function (type) {
    var colors = {
      'order_placed':            'text-primary',
      'order_confirmed':         'text-info',
      'order_preparing':         'text-warning',
      'out_for_delivery':        'text-primary',
      'delivered':               'text-success',
      'completed':               'text-success',
      'cancelled':               'text-danger',
      'return':                  'text-warning',
      'message':                 'text-primary',
    };
    return colors[type] || 'text-secondary';
  };

  /* ──────────────────────────────────────────────────────────
     Status Label & Badge Utilities
  ────────────────────────────────────────────────────────── */

  /**
   * Get display label for return request status
   * @param {string} status - Status code
   * @returns {string} Human-readable status label
   */
  window.getStatusLabel = function (status) {
    var labels = {
      'pending':               'Pending Review',
      'seller_approved':       'Approved by Seller',
      'seller_rejected':       'Rejected',
      'escalated':             'Escalated to Admin',
      'admin_approved':        'Admin Approved',
      'admin_rejected':        'Admin Rejected',
    };
    return labels[status] || (status || 'Unknown').replace(/_/g, ' ').charAt(0).toUpperCase() + (status || 'unknown').slice(1).replace(/_/g, ' ');
  };

  /**
   * Get Bootstrap badge class for delivery status
   * @param {string} status - Status code
   * @returns {string} Bootstrap badge class (e.g., "badge bg-success")
   */
  window.getDeliveryStatusClass = function (status) {
    var map = {
      'out_for_delivery':  'badge bg-primary',
      'delivered':         'badge bg-success',
      'completed':         'badge bg-success',
      'cancelled':         'badge bg-danger',
    };
    return map[status] || 'badge bg-secondary';
  };

  /* ══════════════════════════════════════════════════════════════
     All utility functions are now available globally:
     - formatCurrency(amount)
     - formatPayoutAmount(amount)
     - formatDeliveryCount(count)
     - getNotificationType(type)
     - getNotificationIcon(type)
     - getNotificationColor(type)
     - getStatusLabel(status)
     - getDeliveryStatusClass(status)
  ══════════════════════════════════════════════════════════════ */

})();
