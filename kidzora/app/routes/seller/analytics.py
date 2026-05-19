"""Seller analytics page + data API."""
import calendar
from collections import defaultdict
from datetime import datetime, timedelta

from flask import jsonify, render_template, request, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.utils.settings import get_commission_rate
from .utils import seller_bp, seller_required, _get_seller_id


# ── Shared helpers (mirrors admin/analytics.py) ────────────────────────────

def _parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str[:19])
    except Exception:
        return None


def _fmt_day(dt):
    return dt.strftime('%b') + ' ' + str(dt.day)


def _build_buckets(period, now):
    if period == 'daily':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        labels = [f'{h:02d}:00' for h in range(24)]
        def bucket_fn(dt): return f'{dt.hour:02d}:00'

    elif period == 'weekly':
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday']
        labels = day_names
        def bucket_fn(dt): return day_names[dt.weekday()]

    elif period == 'monthly':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days = calendar.monthrange(now.year, now.month)[1]
        abbr = now.strftime('%b')
        labels = [f'{abbr} {d}' for d in range(1, days + 1)]
        def bucket_fn(dt): return f'{dt.strftime("%b")} {dt.day}'

    else:  # yearly
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        labels = month_names
        def bucket_fn(dt): return month_names[dt.month - 1]

    return start, labels, bucket_fn


def _build_custom_buckets(start_dt, end_dt):
    delta = (end_dt - start_dt).days
    if delta <= 31:
        labels = [_fmt_day(start_dt + timedelta(days=i)) for i in range(delta + 1)]
        def bucket_fn(dt): return _fmt_day(dt)
    elif delta <= 365:
        labels = []
        d = start_dt
        while d <= end_dt:
            labels.append(d.strftime('%b %d'))
            d += timedelta(weeks=1)
        def bucket_fn(dt):
            offset = (dt - start_dt).days // 7
            return (start_dt + timedelta(weeks=offset)).strftime('%b %d')
    else:
        labels = []
        d = start_dt.replace(day=1)
        end_m = end_dt.replace(day=1)
        while d <= end_m:
            labels.append(d.strftime('%b %Y'))
            d = d.replace(month=d.month + 1) if d.month < 12 else d.replace(year=d.year + 1, month=1)
        def bucket_fn(dt): return dt.strftime('%b %Y')
    return start_dt, labels, bucket_fn


# ── Analytics data API ─────────────────────────────────────────────────────

@seller_bp.route('/analytics/data')
@login_required
@seller_required
def analytics_data():
    seller_id = _get_seller_id()
    if not seller_id:
        return jsonify({'error': 'Seller profile not found'}), 404

    period = request.args.get('period', 'weekly')
    now    = datetime.utcnow()

    if period == 'custom':
        try:
            start_dt = datetime.fromisoformat(request.args.get('start', ''))
        except Exception:
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            end_dt = datetime.fromisoformat(request.args.get('end', '')).replace(
                hour=23, minute=59, second=59)
        except Exception:
            end_dt = now
        start, labels, bucket_fn = _build_custom_buckets(start_dt, end_dt)
    else:
        start, labels, bucket_fn = _build_buckets(period, now)

    # ── All the seller's orders in range (by created_at) ─────────────────────
    try:
        all_orders = (supabase.table('orders')
                      .select('id, total_amount, status, created_at, updated_at')
                      .eq('seller_id', seller_id)
                      .gte('created_at', start.isoformat())
                      .execute().data or [])
    except Exception:
        all_orders = []

    # ── Completed orders (for revenue / earnings) ─────────────────────────────
    try:
        completed_orders = (supabase.table('orders')
                            .select('id, total_amount, commission, seller_earnings, updated_at')
                            .eq('seller_id', seller_id)
                            .eq('status', 'completed')
                            .gte('updated_at', start.isoformat())
                            .execute().data or [])
    except Exception:
        completed_orders = []

    # ── Order items for top-products ──────────────────────────────────────────
    all_order_ids = [o['id'] for o in all_orders]
    product_rev   = defaultdict(float)
    product_qty   = defaultdict(int)
    if all_order_ids:
        try:
            items = (supabase.table('order_items')
                     .select('product_id, quantity, price, products(name)')
                     .in_('order_id', all_order_ids)
                     .execute().data or [])
            for it in items:
                pid   = it.get('product_id')
                qty   = int(it.get('quantity') or 1)
                price = float(it.get('price') or 0)
                if pid:
                    product_rev[pid] += price * qty
                    product_qty[pid] += qty
        except Exception:
            pass

    # ── Aggregate by bucket ───────────────────────────────────────────────────
    revenue_map  = defaultdict(float)
    earnings_map = defaultdict(float)
    order_cnt    = defaultdict(int)
    status_map   = defaultdict(int)

    for o in all_orders:
        dt = _parse_dt(o.get('created_at'))
        if dt:
            order_cnt[bucket_fn(dt)] += 1
        status_map[o.get('status', 'unknown')] += 1

    for o in completed_orders:
        dt  = _parse_dt(o.get('updated_at') or o.get('created_at'))
        amt      = float(o.get('total_amount') or 0)
        # Use stored seller_earnings; fall back to computing from total_amount
        # for orders placed before the seller_earnings column was added.
        raw_earn = o.get('seller_earnings')
        raw_comm = o.get('commission')
        if raw_earn:
            earnings = float(raw_earn)
        elif raw_comm:
            earnings = max(0.0, amt - float(raw_comm))
        else:
            earnings = round(amt * (1 - get_commission_rate()), 2)
        if dt:
            b = bucket_fn(dt)
            revenue_map[b]  += amt
            earnings_map[b] += earnings

    # ── Top 5 products by revenue ─────────────────────────────────────────────
    top_prods_raw = sorted(product_rev.items(), key=lambda x: x[1], reverse=True)[:5]

    # Resolve product names
    prod_name_map = {}
    top_ids = [pid for pid, _ in top_prods_raw]
    if top_ids:
        try:
            rows = (supabase.table('products').select('id, name')
                    .in_('id', top_ids).execute().data or [])
            prod_name_map = {r['id']: r['name'] for r in rows}
        except Exception:
            pass

    top_products = [
        {'name': prod_name_map.get(pid, 'Product')[:28], 'revenue': round(rev, 2),
         'qty': product_qty.get(pid, 0)}
        for pid, rev in top_prods_raw
    ]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_revenue  = round(sum(revenue_map.values()), 2)
    total_earnings = round(sum(earnings_map.values()), 2)
    total_orders   = sum(order_cnt.values())

    # Active product count for the seller
    try:
        prod_r = (supabase.table('products')
                  .select('id', count='exact')
                  .eq('seller_id', seller_id)
                  .eq('is_active', True)
                  .execute())
        active_products = prod_r.count or 0
    except Exception:
        active_products = 0

    return jsonify({
        'labels':       labels,
        'revenue':      [round(revenue_map.get(l, 0), 2)  for l in labels],
        'earnings':     [round(earnings_map.get(l, 0), 2) for l in labels],
        'order_counts': [order_cnt.get(l, 0)              for l in labels],
        'status_dist':  dict(status_map),
        'top_products': top_products,
        'kpis': {
            'revenue':         total_revenue,
            'earnings':        total_earnings,
            'orders':          total_orders,
            'completed':       status_map.get('completed', 0),
            'cancelled':       status_map.get('cancelled', 0),
            'active_products': active_products,
        },
    })


# ── Analytics page ─────────────────────────────────────────────────────────

@seller_bp.route('/analytics')
@login_required
@seller_required
def analytics():
    commission_pct = round(get_commission_rate() * 100, 2)
    return render_template('seller/analytics.html', commission_pct=commission_pct)
