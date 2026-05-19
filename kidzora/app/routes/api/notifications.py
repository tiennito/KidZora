"""
app/routes/api/notifications.py
────────────────────────────────
Lightweight polling API used by the frontend to fetch new notifications
and mark them read.  Requires the user to be logged in.

Endpoints:
    GET  /api/v1/notifications/poll          → list of recent notifications
    POST /api/v1/notifications/mark-read     → mark specific IDs as read
    POST /api/v1/notifications/mark-all-read → mark all as read
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.services.notifications import fetch_notifications, mark_all_read, mark_notifications_read

notif_api_bp = Blueprint('notif_api', __name__)


# ── Poll ──────────────────────────────────────────────────────────────────────

@notif_api_bp.route('/poll')
@login_required
def poll():
    """
    Return the 30 most recent notifications for the logged-in user.

    Query params:
        since  ISO-8601 timestamp — only return rows created_at > since
               (omit to get the latest 30 regardless of timestamp)
        limit  int, default 30, max 50
    """
    since       = request.args.get('since', '')
    unread_only = request.args.get('unread_only', '0') in ('1', 'true')
    try:
        limit = min(int(request.args.get('limit', 30)), 50)
    except (TypeError, ValueError):
        limit = 30

    rows = fetch_notifications(
        user_id=current_user.id,
        limit=limit,
        since=since if since else None,
        unread_only=unread_only
    )
    return jsonify({'notifications': rows})


# ── Mark read ─────────────────────────────────────────────────────────────────

@notif_api_bp.route('/mark-read', methods=['POST'])
@login_required
def mark_read():
    """Body: { "ids": ["uuid1", "uuid2", ...] }"""
    ids = (request.get_json(silent=True) or {}).get('ids', [])
    if not ids:
        return jsonify({'ok': True})

    success = mark_notifications_read(current_user.id, ids)
    return jsonify({'ok': success})


@notif_api_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read_route():
    """Marks every unread notification for the current user as read."""
    success = mark_all_read(current_user.id)
    return jsonify({'ok': success})


# ── Web Push ──────────────────────────────────────────────────────────────────

@notif_api_bp.route('/vapid-public-key')
@login_required
def vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    from flask import current_app
    key = current_app.config.get('VAPID_PUBLIC_KEY', '')
    return jsonify({'key': key})


@notif_api_bp.route('/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    """Save a Web Push subscription for the current user.

    Body: { "endpoint": str, "p256dh": str, "auth": str }
    """
    data     = request.get_json(silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    p256dh   = (data.get('p256dh')   or '').strip()
    auth     = (data.get('auth')      or '').strip()

    if not endpoint or not p256dh or not auth:
        return jsonify({'ok': False, 'error': 'Missing fields'}), 400

    try:
        (supabase.table('push_subscriptions')
         .upsert({
             'user_id':  current_user.id,
             'endpoint': endpoint,
             'p256dh':   p256dh,
             'auth':     auth,
         }, on_conflict='user_id,endpoint')
         .execute())
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500

    return jsonify({'ok': True})


@notif_api_bp.route('/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    """Remove a Web Push subscription for the current user.

    Body: { "endpoint": str }
    """
    data     = request.get_json(silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()

    if not endpoint:
        return jsonify({'ok': False, 'error': 'Missing endpoint'}), 400

    try:
        (supabase.table('push_subscriptions')
         .delete()
         .eq('user_id', current_user.id)
         .eq('endpoint', endpoint)
         .execute())
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500

    return jsonify({'ok': True})
