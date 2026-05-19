"""Admin dashboard route."""
from datetime import datetime, timedelta

from flask import render_template, request
from flask_login import login_required

from app.models.profile import Profile
from app.models.transaction import Transaction
from .utils import admin_bp, admin_required


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users      = len(Profile.get_all())
    pending_sellers  = len(Profile.get_all({'role': 'seller', 'is_approved': False}))
    pending_riders   = len(Profile.get_all({'role': 'rider',  'is_approved': False}))

    # Commission filter by period
    period = request.args.get('period', 'all')
    now = datetime.utcnow()
    period_map = {
        'day':   now - timedelta(days=1),
        'week':  now - timedelta(weeks=1),
        'month': now - timedelta(days=30),
        'year':  now - timedelta(days=365),
    }
    start_date = period_map.get(period)
    commission_data = Transaction.get_commission_summary(
        start_date=start_date.isoformat() if start_date else None
    )

    recent_transactions = Transaction.get_commission_summary(
        start_date=(now - timedelta(days=7)).isoformat()
    )['transactions'][:10]

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        pending_sellers=pending_sellers,
        pending_riders=pending_riders,
        commission_data=commission_data,
        recent_transactions=recent_transactions,
        active_period=period,
    )
