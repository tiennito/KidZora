"""Buyer profile / account settings route."""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import buyer_bp, _save_avatar

_PROFILE_FIELDS = [
    'first_name', 'last_name', 'phone',
    'region', 'province', 'city', 'barangay',
    'building_number', 'street_name', 'postal_code',
]


@buyer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Redirect to dashboard account tab - profile is now integrated in dashboard."""
    return redirect(url_for('buyer.dashboard', tab='account'))
    
    # GET request - fetch current profile data
    profile_data = {}
    try:
        prof_r = supabase.table('profiles').select('*').eq('user_id', str(current_user.id)).execute()
        if prof_r.data:
            profile_data = prof_r.data[0]
    except Exception:
        pass
    
    return render_template('buyer/profile.html', profile_data=profile_data)
