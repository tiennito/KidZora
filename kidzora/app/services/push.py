"""
app/services/push.py
────────────────────
Web Push (VAPID) delivery service.

Sends browser push notifications to all registered subscriptions for a user.
Transparently prunes expired (HTTP 410) subscriptions from the database.

Usage:
    from app.services.push import send_push

    send_push(
        user_id='uuid...',
        title='New Pickup Available',
        body='Order #ABC123 is ready at KidZora Shop.',
        url='/rider/available',
    )

Prerequisites:
    pip install pywebpush

    Set these environment variables (or config.py equivalents):
        VAPID_PRIVATE_KEY  — base64url-encoded DER private key
        VAPID_PUBLIC_KEY   — base64url-encoded uncompressed EC public key
        VAPID_MAILTO       — mailto: contact for VAPID sub claim

    Generate a key pair once with:
        python - <<EOF
        from pywebpush import Vapid
        v = Vapid()
        v.generate_keys()
        print("PRIVATE:", v.private_key.decode())
        print("PUBLIC: ", v.public_key.decode())
        EOF

If VAPID_PRIVATE_KEY is not set the function returns immediately without error.
If pywebpush is not installed the function returns immediately without error.
"""

from __future__ import annotations

import json
import traceback
from typing import Optional

from app.extensions import supabase_admin as _supa


def _cfg(key: str, default: str = '') -> str:
    """Read a config value from the current Flask app context, or fall back to os.environ."""
    try:
        from flask import current_app
        return current_app.config.get(key) or default
    except RuntimeError:
        import os
        return os.environ.get(key, default) or default


def send_push(
    user_id: str,
    title: str,
    body: str = '',
    url: str = '',
    icon: str = '/static/img/icon-192.png',
) -> None:
    """
    Deliver a Web Push notification to every active subscription for *user_id*.

    Silently no-ops if:
      - VAPID_PRIVATE_KEY is not configured
      - pywebpush is not installed
      - The user has no registered subscriptions
    """
    private_key = _cfg('VAPID_PRIVATE_KEY')
    if not private_key:
        return  # VAPID not configured

    try:
        from pywebpush import webpush, WebPushException  # type: ignore
    except ImportError:
        return  # pywebpush not installed

    mailto = _cfg('VAPID_MAILTO', 'mailto:admin@kidzora.com')

    # ── Fetch all subscriptions for this user ─────────────────────────────
    try:
        rows = (
            _supa.table('push_subscriptions')
            .select('id, endpoint, p256dh, auth')
            .eq('user_id', user_id)
            .execute().data or []
        )
    except Exception:
        return

    payload = json.dumps({
        'title': title,
        'body':  body,
        'url':   url,
        'icon':  icon,
    })

    stale_ids: list[str] = []

    for sub in rows:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub['endpoint'],
                    'keys': {
                        'p256dh': sub['p256dh'],
                        'auth':   sub['auth'],
                    },
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={'sub': mailto},
                content_encoding='aesgcm',
            )
        except Exception as exc:
            err = str(exc)
            # HTTP 410 Gone or 404 = push subscription has expired
            if '410' in err or '404' in err or 'Gone' in err:
                stale_ids.append(sub['id'])
            else:
                traceback.print_exc()

    # ── Prune expired subscriptions ───────────────────────────────────────
    if stale_ids:
        try:
            (_supa.table('push_subscriptions')
             .delete()
             .in_('id', stale_ids)
             .execute())
        except Exception:
            pass
