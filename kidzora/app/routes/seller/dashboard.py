"""Seller dashboard route."""
from flask import render_template
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from .utils import seller_bp, seller_required


@seller_bp.route('/dashboard')
@login_required
@seller_required
def dashboard():
    from flask_login import current_user

    # ── Stats ──────────────────────────────────────────────────────────────────
    try:
        r = supabase.table('products').select('id', count='exact').eq('seller_id', current_user.id).execute()
        total_products = r.count or 0
    except Exception:
        total_products = 0

    try:
        r = supabase.table('orders').select('id', count='exact').eq('seller_id', current_user.id).execute()
        total_orders = r.count or 0
    except Exception:
        total_orders = 0

    try:
        r = (supabase.table('orders').select('total_amount')
             .eq('seller_id', current_user.id).eq('status', 'completed').execute())
        total_revenue = sum(float(o.get('total_amount', 0)) for o in (r.data or []))
    except Exception:
        total_revenue = 0.0

    try:
        r = (supabase.table('orders').select('id', count='exact')
             .eq('seller_id', current_user.id).eq('status', 'pending').execute())
        pending_orders = r.count or 0
    except Exception:
        pending_orders = 0

    # ── Recent rows ────────────────────────────────────────────────────────────
    try:
        r = (supabase.table('orders').select('*')
             .eq('seller_id', current_user.id).order('created_at', desc=True).limit(5).execute())
        recent_orders = r.data or []
    except Exception:
        recent_orders = []

    try:
        r = (supabase.table('products').select('*')
             .eq('seller_id', current_user.id).order('created_at', desc=True).limit(4).execute())
        recent_products = r.data or []
    except Exception:
        recent_products = []

    return render_template(
        'seller/dashboard.html',
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        recent_orders=recent_orders,
        recent_products=recent_products,
    )
