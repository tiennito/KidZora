"""Buyer notifications page."""
from flask import render_template
from flask_login import login_required, current_user

from app.services.notifications import fetch_notifications, mark_all_read
from .utils import buyer_bp


@buyer_bp.route('/notifications')
@login_required
def notifications():
    """Show all notifications for the logged-in buyer, mark unread as read."""
    rows = fetch_notifications(user_id=current_user.id, limit=100)
    unread_count = len([r for r in rows if not r.get('is_read')])
    
    if unread_count > 0:
        mark_all_read(current_user.id)

    return render_template('buyer/notifications.html',
                           notifications=rows,
                           unread_count=unread_count)
