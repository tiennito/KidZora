"""Rider notifications page."""
from flask import render_template
from flask_login import login_required, current_user

from app.services.notifications import fetch_notifications, mark_all_read
from .utils import rider_bp, rider_required


@rider_bp.route('/notifications')
@login_required
@rider_required
def notifications():
    """Show all notifications for the logged-in rider, mark unread as read."""
    rows = fetch_notifications(user_id=current_user.id, limit=100)
    unread_count = len([r for r in rows if not r.get('is_read')])
    
    if unread_count > 0:
        mark_all_read(current_user.id)

    return render_template('rider/notifications.html',
                           notifications=rows,
                           unread_count=unread_count)

