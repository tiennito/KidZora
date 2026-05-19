"""Rider dashboard route."""
from flask import render_template
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import rider_bp, approved_rider_required, _get_rider_id


@rider_bp.route('/dashboard')
@login_required
@approved_rider_required
def dashboard():
    rider_id = _get_rider_id()

    # ── Available orders (preparing + no rider yet) ────────────────────────────
    try:
        r = supabase.table('orders').select('id', count='exact') \
            .eq('status', 'preparing').is_('rider_id', 'null').execute()
        available_count = r.count or 0
    except Exception:
        available_count = 0

    # ── Stats ──────────────────────────────────────────────────────────────────
    total_deliveries = active_deliveries = completed_deliveries = 0
    total_earnings = 0.0
    recent_deliveries = []

    if rider_id:
        try:
            r = supabase.table('orders').select('id', count='exact') \
                .eq('rider_id', rider_id).execute()
            total_deliveries = r.count or 0
        except Exception:
            pass

        try:
            r = supabase.table('orders').select('id', count='exact') \
                .eq('rider_id', rider_id).eq('status', 'out_for_delivery').execute()
            active_deliveries = r.count or 0
        except Exception:
            pass

        try:
            r = supabase.table('orders').select('id', count='exact') \
                .eq('rider_id', rider_id).in_('status', ['delivered', 'completed']).execute()
            completed_deliveries = r.count or 0
        except Exception:
            pass

        try:
            r = supabase.table('orders').select('delivery_fee') \
                .eq('rider_id', rider_id).in_('status', ['delivered', 'completed']).execute()
            total_earnings = sum(float(o.get('delivery_fee') or 0) for o in (r.data or []))
        except Exception:
            pass

        try:
            r = supabase.table('orders').select('*') \
                .eq('rider_id', rider_id) \
                .order('updated_at', desc=True).limit(5).execute()
            recent_deliveries = r.data or []
        except Exception:
            pass

    return render_template(
        'rider/dashboard.html',
        available_count=available_count,
        total_deliveries=total_deliveries,
        active_deliveries=active_deliveries,
        completed_deliveries=completed_deliveries,
        total_earnings=total_earnings,
        recent_deliveries=recent_deliveries,
    )
