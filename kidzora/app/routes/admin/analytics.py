"""Admin analytics API + analytics page."""
import calendar
from collections import defaultdict
from datetime import datetime, timedelta

from flask import jsonify, render_template, request, current_app
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from app.utils.decorators import admin_required
from app.utils.settings import get_commission_rate as _get_commission_rate
from .utils import admin_bp


def _parse_dt(dt_str):
    """Parse ISO datetime string from Supabase, ignoring timezone."""
    if not dt_str:
        return None
    # strip timezone suffix so fromisoformat works on Py 3.7-3.10
    clean = dt_str[:19]  # "YYYY-MM-DDTHH:MM:SS"
    try:
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def _build_buckets(period, now):
    """
    Return (start_dt, labels, bucket_fn).

    daily   → today 00:00–23:00, hourly (24 buckets)
    weekly  → this week Mon–Sun, by full day name (7 buckets)
    monthly → this month day 1 to last day, "Jan 1" … (N buckets)
    yearly  → this year Jan–Dec, full month name (12 buckets)
    """
    if period == 'daily':
        # Today from midnight
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        labels = [f'{h:02d}:00' for h in range(24)]
        def bucket_fn(dt):
            return f'{dt.hour:02d}:00'

    elif period == 'weekly':
        # Monday of current week
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        start = week_start
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday']
        labels = day_names
        def bucket_fn(dt):
            return day_names[dt.weekday()]

    elif period == 'monthly':
        # First day of current month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        month_abbr = now.strftime('%b')
        labels = [f'{month_abbr} {d}' for d in range(1, days_in_month + 1)]
        def bucket_fn(dt):
            return f'{dt.strftime("%b")} {dt.day}'

    else:  # yearly
        # Jan 1 of current year
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        labels = month_names
        def bucket_fn(dt):
            return month_names[dt.month - 1]

    return start, labels, bucket_fn


def _fmt_day(dt):
    """Return e.g. 'Mar 7' — compatible with both Windows and Linux."""
    return dt.strftime('%b') + ' ' + str(dt.day)


def _build_custom_buckets(start_dt, end_dt):
    """
    Build buckets for a custom date range.
    ≤ 31 days  → bucket by day   "Mar 7"
    ≤ 365 days → bucket by week  "Mar 07"
    > 365 days → bucket by month "Mar 2025"
    """
    delta = (end_dt - start_dt).days

    if delta <= 31:
        labels = [_fmt_day(start_dt + timedelta(days=i)) for i in range(delta + 1)]

        def bucket_fn(dt):
            return _fmt_day(dt)

    elif delta <= 365:
        labels = []
        d = start_dt
        while d <= end_dt:
            labels.append(d.strftime('%b %d'))
            d += timedelta(weeks=1)

        def bucket_fn(dt):
            week_offset = (dt - start_dt).days // 7
            bucket_date = start_dt + timedelta(weeks=week_offset)
            return bucket_date.strftime('%b %d')

    else:
        labels = []
        d = start_dt.replace(day=1)
        end_m = end_dt.replace(day=1)
        while d <= end_m:
            labels.append(d.strftime('%b %Y'))
            if d.month == 12:
                d = d.replace(year=d.year + 1, month=1)
            else:
                d = d.replace(month=d.month + 1)

        def bucket_fn(dt):
            return dt.strftime('%b %Y')

    return start_dt, labels, bucket_fn


@admin_bp.route('/analytics/data')
@login_required
@admin_required
def analytics_data():
    period = request.args.get('period', 'weekly')
    now    = datetime.utcnow()

    # ── Custom date range ─────────────────────────────────────────────────────
    if period == 'custom':
        start_str = request.args.get('start', '')
        end_str   = request.args.get('end', '')
        try:
            start_dt = datetime.fromisoformat(start_str)
        except Exception:
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            end_dt = datetime.fromisoformat(end_str).replace(
                hour=23, minute=59, second=59)
        except Exception:
            end_dt = now
        start, labels, bucket_fn = _build_custom_buckets(start_dt, end_dt)
    else:
        start, labels, bucket_fn = _build_buckets(period, now)

    # ── Fetch ALL orders in range (for order counts + status distribution) ────
    try:
        all_orders = (
            supabase.table('orders')
            .select('id, total_amount, commission, status, seller_id, created_at, updated_at')
            .gte('created_at', start.isoformat())
            .execute().data or []
        )
    except Exception:
        all_orders = []

    # ── Fetch COMPLETED orders in range (for revenue + commission, matches
    #    /admin/commission which filters status=completed + updated_at) ───────
    try:
        completed_orders = (
            supabase.table('orders')
            .select('id, total_amount, commission, seller_earnings, seller_id, updated_at')
            .eq('status', 'completed')
            .gte('updated_at', start.isoformat())
            .execute().data or []
        )
    except Exception:
        completed_orders = []

    # ── Aggregate ────────────────────────────────────────────────────────────
    revenue_map    = defaultdict(float)
    commission_map = defaultdict(float)
    order_cnt_map  = defaultdict(int)
    status_map     = defaultdict(int)
    seller_rev     = defaultdict(float)
    new_users_map  = defaultdict(int)

    # Order counts + status distribution: ALL orders by created_at
    for o in all_orders:
        dt = _parse_dt(o.get('created_at'))
        if dt is None:
            continue
        b = bucket_fn(dt)
        order_cnt_map[b] += 1
        status_map[o.get('status', 'unknown')] += 1

    # Revenue + commission: COMPLETED orders by updated_at (aligns with commission page)
    for o in completed_orders:
        dt = _parse_dt(o.get('updated_at') or o.get('created_at'))
        if dt is None:
            continue
        b   = bucket_fn(dt)
        amt = float(o.get('total_amount') or 0)
        com = float(o.get('commission') or 0) or round(amt * _get_commission_rate(), 2)

        revenue_map[b]    += amt
        commission_map[b] += com
        if o.get('seller_id'):
            seller_rev[o['seller_id']] += amt

    # ── New users per bucket ─────────────────────────────────────────────────
    try:
        users = (
            supabase.table('profiles')
            .select('id, created_at')
            .gte('created_at', start.isoformat())
            .execute().data or []
        )
    except Exception:
        users = []

    for u in users:
        dt = _parse_dt(u.get('created_at'))
        if dt:
            new_users_map[bucket_fn(dt)] += 1

    # ── Top sellers (resolve shop names) ────────────────────────────────────
    top_raw = sorted(seller_rev.items(), key=lambda x: x[1], reverse=True)[:5]
    top_ids = [s[0] for s in top_raw]
    shop_name_map = {}
    if top_ids:
        try:
            seller_rows = (
                supabase.table('sellers')
                .select('id, shop_name')
                .in_('id', top_ids)
                .execute().data or []
            )
            shop_name_map = {r['id']: r['shop_name'] for r in seller_rows}
        except Exception:
            pass
    top = [(shop_name_map.get(sid, sid[:8]), rev) for sid, rev in top_raw]

    # ── Summary KPIs ─────────────────────────────────────────────────────────
    total_revenue    = round(sum(revenue_map.values()), 2)
    total_commission = round(sum(commission_map.values()), 2)
    total_orders     = sum(order_cnt_map.values())
    total_new_users  = sum(new_users_map.values())

    return jsonify({
        'labels':       labels,
        'revenue':      [round(revenue_map.get(l, 0), 2)    for l in labels],
        'commission':   [round(commission_map.get(l, 0), 2) for l in labels],
        'order_counts': [order_cnt_map.get(l, 0)            for l in labels],
        'new_users':    [new_users_map.get(l, 0)            for l in labels],
        'status_dist':  dict(status_map),
        'top_sellers': {
            'labels': [s[0] for s in top],
            'data':   [round(s[1], 2) for s in top],
        },
        'kpis': {
            'revenue'   : total_revenue,
            'commission': total_commission,
            'orders':     total_orders,
            'new_users':  total_new_users,
            'completed':  status_map.get('completed', 0),
            'cancelled':  status_map.get('cancelled', 0),
        },
    })


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics_page():
    """Dedicated full-screen analytics/charts page."""
    return render_template('admin/analytics.html')
