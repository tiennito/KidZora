/*!
 * KidZora Real-Time Notifications v1.0
 * Supabase Realtime for live notification badge updates
 * 
 * Listens for changes to the notifications table and updates the badge
 * without requiring a page reload.
 */

(function () {
  'use strict';

  // Get current user ID from meta tag
  var currentUserId = (function () {
    var m = document.querySelector('meta[name="kz-uid"]');
    return (m && m.content) ? m.content : null;
  })();

  // Don't initialize if user not logged in
  if (!currentUserId) return;

  // Get Supabase client from window (initialized by other scripts)
  var supabase = window.supabase;
  if (!supabase) return;

  // Storage key for unread count (must match kidzora-toast.js)
  var STORAGE_KEY = 'kz_notif_v3_' + currentUserId.replace(/[^a-zA-Z0-9_-]/g, '');

  /**
   * Get current unread count from sessionStorage
   */
  function getUnreadCount() {
    try {
      var history = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]');
      return history.filter(function (n) { return !n.read; }).length;
    } catch (e) {
      return 0;
    }
  }

  /**
   * Increment unread count by 1
   */
  function incrementUnread() {
    try {
      var history = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]');
      var unreadCount = history.filter(function (n) { return !n.read; }).length;
      unreadCount++;
      updateBadgeDisplay(unreadCount);
    } catch (e) {}
  }

  /**
   * Decrement unread count by 1
   */
  function decrementUnread() {
    try {
      var history = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]');
      var unreadCount = history.filter(function (n) { return !n.read; }).length;
      if (unreadCount > 0) unreadCount--;
      updateBadgeDisplay(unreadCount);
    } catch (e) {}
  }

  /**
   * Update the badge display
   */
  function updateBadgeDisplay(count) {
    var badge = document.getElementById('kz-bell-badge');
    if (!badge) return;

    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.classList.add('kz-visible');
    } else {
      badge.textContent = '';
      badge.classList.remove('kz-visible');
    }
  }

  /**
   * Fetch unread count from API and update badge
   * (Used to sync badge on page load)
   */
  function syncUnreadCount() {
    fetch('/api/v1/notifications/poll?unread_only=1&limit=999')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var count = (data.notifications || []).length;
        updateBadgeDisplay(count);
      })
      .catch(function (e) {
        console.warn('Failed to sync unread notification count:', e);
      });
  }

  /**
   * Initialize Realtime subscription
   */
  function initializeRealtimeSubscription() {
    try {
      // Subscribe to notifications table for current user
      var channel = supabase
        .channel('notifications_' + currentUserId)
        .on(
          'postgres_changes',
          {
            event: '*', // Listen to all events (INSERT, UPDATE, DELETE)
            schema: 'public',
            table: 'notifications',
            filter: 'user_id=eq.' + currentUserId,
          },
          function (payload) {
            handleRealtimeChange(payload);
          }
        )
        .subscribe();

      console.log('✓ Real-time notification subscription initialized');
    } catch (e) {
      console.warn('Failed to initialize real-time notifications:', e);
      // Fallback: sync on page load
      syncUnreadCount();
    }
  }

  /**
   * Handle real-time changes from Supabase
   */
  function handleRealtimeChange(payload) {
    var eventType = payload.eventType; // INSERT, UPDATE, DELETE
    var newRecord = payload.new;
    var oldRecord = payload.old;

    // Ignore if the change came from current user's own session
    // (The INSERT will be handled locally by kidzora-toast.js)
    if (eventType === 'INSERT' && newRecord && newRecord.user_id === currentUserId) {
      incrementUnread();
    }

    // When notifications are marked as read via API from another tab/device
    if (eventType === 'UPDATE' && newRecord && oldRecord) {
      // If is_read changed from False to True on an unread notification
      if (oldRecord.is_read === false && newRecord.is_read === true) {
        decrementUnread();
      }
      // If is_read changed from True to False (unread action)
      else if (oldRecord.is_read === true && newRecord.is_read === false) {
        incrementUnread();
      }
    }
  }

  /**
   * On page load, sync unread count from API
   * Then initialize realtime subscription
   */
  document.addEventListener('DOMContentLoaded', function () {
    // Give kidzora-toast.js time to initialize first
    setTimeout(function () {
      syncUnreadCount();
      initializeRealtimeSubscription();
    }, 100);
  });

  // Also sync on page focus (when switching browser tabs)
  window.addEventListener('focus', function () {
    syncUnreadCount();
  });
})();
