/**
 * KidZora Service Worker — Web Push Notifications
 *
 * Handles incoming push events from the VAPID server and routes
 * notification click events to the correct page.
 *
 * Served at /sw.js (root scope) via a dedicated Flask route.
 */
'use strict';

/* ── Push event: show the browser notification ────────────────────────── */
self.addEventListener('push', function (event) {
  if (!event.data) return;

  var payload = {};
  try { payload = event.data.json(); } catch (e) { return; }

  var title   = payload.title || 'KidZora';
  var options = {
    body:      payload.body  || '',
    icon:      payload.icon  || '/static/img/icon-192.png',
    badge:     '/static/img/badge-72.png',
    data:      { url: payload.url || '/' },
    vibrate:   [200, 100, 200],
    tag:        'kidzora',   // collapses repeated notifications of the same type
    renotify:   true,
    requireInteraction: false,
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

/* ── Notification click: focus or open the target page ───────────────── */
self.addEventListener('notificationclick', function (event) {
  event.notification.close();

  var targetUrl = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(function (windowClients) {
        // If a tab with the same URL is already open, focus it
        for (var i = 0; i < windowClients.length; i++) {
          var client = windowClients[i];
          if (client.url === targetUrl && 'focus' in client) {
            return client.focus();
          }
        }
        // Otherwise open a new tab
        if (clients.openWindow) {
          return clients.openWindow(targetUrl);
        }
      })
  );
});

/* ── Install / activate: no caching needed (notification-only SW) ─────── */
self.addEventListener('install',  function () { self.skipWaiting(); });
self.addEventListener('activate', function (event) {
  event.waitUntil(clients.claim());
});
