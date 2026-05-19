"""
app/services/notifications.py
─────────────────────────────
Shared notification utilities for fetching and marking notifications as read.
Used by both API endpoints and page routes to avoid duplication.
"""

import json
from flask import current_app
from app.extensions import supabase_admin as supabase


def fetch_notifications(user_id, limit=100, since=None, unread_only=False):
    """
    Fetch notifications for a user.

    Args:
        user_id (str): The user's ID
        limit (int): Maximum number of rows to return (default 100, max 100)
        since (str): ISO-8601 timestamp — only return rows created_at > since
        unread_only (bool): If True, only fetch unread notifications

    Returns:
        list: Notification dicts with _url extracted from data JSON
    """
    try:
        limit = min(int(limit), 100)
    except (TypeError, ValueError):
        limit = 100

    try:
        q = (supabase.table('notifications')
             .select('id, type, title, body, is_read, data, created_at')
             .eq('user_id', user_id)
             .order('created_at', desc=True)
             .limit(limit))

        if since:
            q = q.gt('created_at', since)

        if unread_only:
            q = q.eq('is_read', False)

        rows = q.execute().data or []
    except Exception as exc:
        current_app.logger.error(f'[fetch_notifications] error: {exc}')
        return []

    # Pre-extract URL from data so template/response never has to parse a dict
    for r in rows:
        d = r.get('data') or {}
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception:
                d = {}
        r['_url'] = d.get('url', '') if isinstance(d, dict) else ''

    return rows


def mark_all_read(user_id):
    """
    Mark all unread notifications for a user as read.

    Args:
        user_id (str): The user's ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        (supabase.table('notifications')
         .update({'is_read': True})
         .eq('user_id', user_id)
         .eq('is_read', False)
         .execute())
        return True
    except Exception as exc:
        current_app.logger.error(f'[mark_all_read] error: {exc}')
        return False


def mark_notifications_read(user_id, notification_ids):
    """
    Mark specific notifications as read.

    Args:
        user_id (str): The user's ID
        notification_ids (list): List of notification IDs to mark as read

    Returns:
        bool: True if successful, False otherwise
    """
    if not notification_ids:
        return True

    try:
        (supabase.table('notifications')
         .update({'is_read': True})
         .eq('user_id', user_id)
         .in_('id', notification_ids)
         .execute())
        return True
    except Exception as exc:
        current_app.logger.error(f'[mark_notifications_read] error: {exc}')
        return False
