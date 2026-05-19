"""Rider earnings routes."""
import csv
import io
from calendar import monthrange
from datetime import datetime, timedelta

from flask import Response, render_template, request
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from .utils import rider_bp, approved_rider_required, _get_rider_id


def _parse_iso_date(raw_value, fallback):
    """Parse an ISO date string, falling back safely on invalid input."""
    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return fallback


def _get_earnings_filters():
    """Resolve preset/custom period filters into a normalized date range."""
    today = datetime.utcnow().date()
    default_start = today - timedelta(days=30)
    requested_period = (request.args.get('period') or 'monthly').strip().lower()

    period_map = {
        'today': 'Today',
        'weekly': 'This Week',
        'monthly': 'This Month',
        'yearly': 'This Year',
        'custom': 'Custom Range',
    }
    period = requested_period if requested_period in period_map else 'monthly'

    if period == 'today':
        start_date = end_date = today
        label = 'Today'
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        label = 'This week — Monday to Sunday'
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = today.replace(day=monthrange(today.year, today.month)[1])
        label = 'This month — 1st to last day'
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        label = 'This year — January to December'
    else:
        raw_start = request.args.get('start_date', default_start.isoformat())
        raw_end = request.args.get('end_date', today.isoformat())
        start_date = _parse_iso_date(raw_start, default_start)
        end_date = _parse_iso_date(raw_end, today)
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        label = f'Custom range — {start_date.isoformat()} to {end_date.isoformat()}'

    return {
        'period': period,
        'period_title': period_map[period],
        'period_label': label,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }


def _get_rider_earnings_data(rider_id, start_date, end_date):
    """Fetch delivery history and total earnings for the given rider/date range."""
    deliveries = []
    total_earned = 0.0

    if not rider_id:
        return deliveries, total_earned

    try:
        # Filter on delivered_at (set when rider marks order delivered);
        # this is stable and does not change when buyer later confirms receipt.
        deliveries = (supabase.table('orders')
                      .select('id, status, delivered_at, updated_at, total_amount, delivery_fee, payment_method')
                      .eq('rider_id', rider_id)
                      .in_('status', ['delivered', 'completed'])
                      .gte('delivered_at', start_date)
                      .lte('delivered_at', end_date + 'T23:59:59')
                      .order('delivered_at', desc=True)
                      .execute().data or [])
        total_earned = sum(float(d.get('delivery_fee') or 0) for d in deliveries)
    except Exception as e:
        print(f'[rider earnings] {e}')

    return deliveries, total_earned


def _build_daily_earnings_chart(start_date, end_date, deliveries, total_earned):
    """Build per-day earnings/count series for the selected period."""
    start_day = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_day = datetime.strptime(end_date, '%Y-%m-%d').date()

    labels = []
    iso_dates = []
    earnings_map = {}
    count_map = {}

    current_day = start_day
    while current_day <= end_day:
        iso_key = current_day.isoformat()
        iso_dates.append(iso_key)
        labels.append(current_day.strftime('%b %d'))
        earnings_map[iso_key] = 0.0
        count_map[iso_key] = 0
        current_day += timedelta(days=1)

    for delivery in deliveries:
        delivered_on = (delivery.get('delivered_at') or delivery.get('updated_at') or '')[:10]
        if delivered_on not in earnings_map:
            continue
        earnings_map[delivered_on] += float(delivery.get('delivery_fee') or 0)
        count_map[delivered_on] += 1

    earnings_series = [round(earnings_map[day], 2) for day in iso_dates]
    count_series = [count_map[day] for day in iso_dates]
    active_days = sum(1 for value in count_series if value > 0)
    peak_day = max(iso_dates, key=lambda day: earnings_map[day], default=None)
    peak_amount = round(earnings_map.get(peak_day, 0.0), 2) if peak_day else 0.0

    return {
        'labels': labels,
        'earnings': earnings_series,
        'counts': count_series,
        'total_deliveries': len(deliveries),
        'active_days': active_days,
        'average_per_delivery': round(total_earned / len(deliveries), 2) if deliveries else 0.0,
        'peak_day_label': datetime.strptime(peak_day, '%Y-%m-%d').strftime('%b %d, %Y') if peak_day and peak_amount > 0 else '—',
        'peak_day_amount': peak_amount,
        'has_data': any(value > 0 for value in earnings_series),
    }


@rider_bp.route('/earnings')
@login_required
@approved_rider_required
def earnings():
    rider_id = _get_rider_id()
    filters = _get_earnings_filters()
    start_date = filters['start_date']
    end_date = filters['end_date']
    deliveries, total_earned = _get_rider_earnings_data(rider_id, start_date, end_date)
    chart_data = _build_daily_earnings_chart(start_date, end_date, deliveries, total_earned)

    return render_template(
        'rider/earnings.html',
        deliveries=deliveries,
        total_earned=total_earned,
        chart_data=chart_data,
        current_period=filters['period'],
        period_title=filters['period_title'],
        period_label=filters['period_label'],
        start_date=start_date,
        end_date=end_date,
    )


@rider_bp.route('/earnings/export/csv')
@login_required
@approved_rider_required
def export_earnings_csv():
    """Download the rider delivery history for the selected period as CSV."""
    rider_id = _get_rider_id()
    filters = _get_earnings_filters()
    start_date = filters['start_date']
    end_date = filters['end_date']
    deliveries, total_earned = _get_rider_earnings_data(rider_id, start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['KidZora Rider Delivery History'])
    writer.writerow(['Period Type', filters['period_title']])
    writer.writerow(['Period', f'{start_date} to {end_date}'])
    writer.writerow(['Generated', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')])
    writer.writerow(['Completed Deliveries', len(deliveries)])
    writer.writerow(['Total Earned (PHP)', f'{total_earned:.2f}'])
    writer.writerow([])
    writer.writerow([
        'Delivered Date',
        'Order ID',
        'Status',
        'Payment Method',
        'Order Total (PHP)',
        'Delivery Fee (PHP)',
    ])

    for delivery in deliveries:
        delivered_at = (delivery.get('delivered_at') or delivery.get('updated_at') or '')[:10]
        writer.writerow([
            delivered_at,
            delivery.get('id', ''),
            delivery.get('status', ''),
            delivery.get('payment_method', ''),
            f"{float(delivery.get('total_amount') or 0):.2f}",
            f"{float(delivery.get('delivery_fee') or 0):.2f}",
        ])

    filename = f'kidzora_rider_delivery_history_{start_date}_{end_date}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@rider_bp.route('/earnings/export/pdf')
@login_required
@approved_rider_required
def export_earnings_pdf():
    """Render a print-ready rider earnings page for Save-as-PDF."""
    rider_id = _get_rider_id()
    filters = _get_earnings_filters()
    start_date = filters['start_date']
    end_date = filters['end_date']
    deliveries, total_earned = _get_rider_earnings_data(rider_id, start_date, end_date)

    return render_template(
        'rider/print_earnings.html',
        deliveries=deliveries,
        total_earned=total_earned,
        period_title=filters['period_title'],
        period_label=filters['period_label'],
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
    )
