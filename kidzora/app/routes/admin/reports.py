"""Admin reports route."""
import csv
import io
from flask import render_template, request, flash, redirect, url_for, jsonify, Response, current_app
from flask_login import login_required, current_user

from app.models.transaction import Transaction
from app.models.report import Report
from app.extensions import supabase_admin
from app.utils.settings import get_commission_rate as _get_commission_rate
from .utils import admin_bp, admin_required


def _end_of_day(date_str):
    """Append end-of-day time if no time component is present."""
    return date_str + 'T23:59:59' if 'T' not in date_str else date_str


def _build_sales_report(start_date, end_date):
    """Query orders table and return real sales aggregates."""
    try:
        orders = (
            supabase_admin.table('orders')
            .select('id, total_amount, commission, seller_earnings, status, payment_method, created_at')
            .gte('created_at', start_date)
            .lte('created_at', _end_of_day(end_date))
            .order('created_at', desc=True)
            .execute()
            .data or []
        )
    except Exception as exc:
        print(f'_build_sales_report error: {exc}')
        orders = []

    total_revenue = 0.0
    total_commission = 0.0
    total_earnings = 0.0
    orders_by_status = {}
    orders_by_payment = {}
    rows = []

    for o in orders:
        amount     = float(o.get('total_amount') or 0)
        commission = float(o.get('commission') or 0) or round(amount * _get_commission_rate(), 2)
        earnings   = float(o.get('seller_earnings') or 0) or round(amount - commission, 2)
        status     = o.get('status') or 'unknown'
        payment    = o.get('payment_method') or 'unknown'

        if status in ('delivered', 'completed'):
            total_revenue    += amount
            total_commission += commission
            total_earnings   += earnings

        orders_by_status[status]   = orders_by_status.get(status, 0) + 1
        orders_by_payment[payment] = orders_by_payment.get(payment, 0) + 1

        rows.append({
            'order_id':       (o.get('id') or '')[:8],
            'amount':         round(amount, 2),
            'commission':     round(commission, 2),
            'status':         status,
            'payment_method': payment,
            'created_at':     (o.get('created_at') or '')[:10],
        })

    completed = orders_by_status.get('completed', 0) + orders_by_status.get('delivered', 0)
    return {
        'total_orders':         len(orders),
        'completed_orders':     completed,
        'cancelled_orders':     orders_by_status.get('cancelled', 0),
        'total_revenue':        round(total_revenue, 2),
        'total_commission':     round(total_commission, 2),
        'total_seller_earnings': round(total_earnings, 2),
        'avg_order_value':      round(total_revenue / completed, 2) if completed else 0,
        'orders_by_status':     orders_by_status,
        'orders_by_payment':    orders_by_payment,
        'rows':                 rows,
    }


def _build_users_report(start_date, end_date):
    """Query profiles table and return real user registration data."""
    try:
        profiles = (
            supabase_admin.table('profiles')
            .select('id, first_name, last_name, role, is_approved, is_banned, created_at')
            .gte('created_at', start_date)
            .lte('created_at', _end_of_day(end_date))
            .order('created_at', desc=True)
            .execute()
            .data or []
        )
    except Exception as exc:
        print(f'_build_users_report error: {exc}')
        profiles = []

    by_role = {}
    approved_sellers = 0
    pending_sellers  = 0
    banned_count     = 0
    rows = []

    for p in profiles:
        role = p.get('role') or 'unknown'
        by_role[role] = by_role.get(role, 0) + 1

        if p.get('is_banned'):
            banned_count += 1
        if role == 'seller':
            if p.get('is_approved'):
                approved_sellers += 1
            else:
                pending_sellers += 1

        name   = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        status = 'Banned' if p.get('is_banned') else ('Approved' if p.get('is_approved') else 'Pending')
        rows.append({
            'name':       name or 'Unknown',
            'role':       role,
            'status':     status,
            'registered': (p.get('created_at') or '')[:10],
        })

    return {
        'total_new_users':  len(profiles),
        'by_role':          by_role,
        'new_buyers':       by_role.get('buyer', 0),
        'new_sellers':      by_role.get('seller', 0),
        'new_riders':       by_role.get('rider', 0),
        'approved_sellers': approved_sellers,
        'pending_sellers':  pending_sellers,
        'banned_users':     banned_count,
        'rows':             rows,
    }


def _build_activity_report(start_date, end_date):
    """Combined platform activity summary."""
    sales = _build_sales_report(start_date, end_date)
    users = _build_users_report(start_date, end_date)
    return {
        'total_orders':       sales['total_orders'],
        'completed_orders':   sales['completed_orders'],
        'total_revenue':      sales['total_revenue'],
        'total_commission':   sales['total_commission'],
        'orders_by_status':   sales['orders_by_status'],
        'total_new_users':    users['total_new_users'],
        'new_users_by_role':  users['by_role'],
        'banned_users':       users['banned_users'],
    }


def _build_product_performance_report(start_date, end_date):
    """Query product sales and return top-selling products."""
    try:
        # Fetch all orders + items in date range
        orders = (
            supabase_admin.table('orders')
            .select('id, created_at')
            .gte('created_at', start_date)
            .lte('created_at', _end_of_day(end_date))
            .eq('status', 'completed')
            .execute()
            .data or []
        )
        
        order_ids = [o['id'] for o in orders]
        
        product_stats = {}
        
        if order_ids:
            items = (
                supabase_admin.table('order_items')
                .select('id, product_id, product_name, quantity, price')
                .in_('order_id', order_ids)
                .execute()
                .data or []
            )
            
            for item in items:
                pid = item.get('product_id')
                if not pid:
                    continue
                if pid not in product_stats:
                    product_stats[pid] = {
                        'name': item.get('product_name', 'Unknown'),
                        'total_quantity': 0,
                        'total_revenue': 0.0,
                    }
                product_stats[pid]['total_quantity'] += item.get('quantity', 0)
                product_stats[pid]['total_revenue'] += float(item.get('price', 0)) * item.get('quantity', 0)
        
        # Sort by revenue descending
        sorted_products = sorted(
            product_stats.items(),
            key=lambda x: x[1]['total_revenue'],
            reverse=True
        )
        
        rows = []
        total_products_sold = 0
        total_quantity = 0
        total_revenue = 0.0
        
        for pid, stats in sorted_products:
            total_products_sold += 1
            total_quantity += stats['total_quantity']
            total_revenue += stats['total_revenue']
            rows.append({
                'product_id': pid[:8] if pid else 'N/A',
                'product_name': stats['name'],
                'quantity_sold': stats['total_quantity'],
                'total_revenue': round(stats['total_revenue'], 2),
            })
        
        return {
            'total_products_sold': total_products_sold,
            'total_quantity_sold': total_quantity,
            'total_revenue': round(total_revenue, 2),
            'avg_revenue_per_product': round(total_revenue / total_products_sold, 2) if total_products_sold else 0,
            'top_10_products': rows[:10],
            'all_products': rows,
        }
    except Exception as exc:
        print(f'_build_product_performance_report error: {exc}')
        return {
            'total_products_sold': 0,
            'total_quantity_sold': 0,
            'total_revenue': 0,
            'avg_revenue_per_product': 0,
            'top_10_products': [],
            'all_products': [],
        }


def _build_user_growth_report(start_date, end_date):
    """Track user registrations over time by date."""
    try:
        profiles = (
            supabase_admin.table('profiles')
            .select('id, first_name, last_name, role, created_at')
            .gte('created_at', start_date)
            .lte('created_at', _end_of_day(end_date))
            .order('created_at', desc=False)
            .execute()
            .data or []
        )
    except Exception as exc:
        print(f'_build_user_growth_report error: {exc}')
        profiles = []
    
    # Count by date
    by_date = {}
    by_role = {}
    
    for p in profiles:
        date = (p.get('created_at') or '')[:10]
        role = p.get('role') or 'unknown'
        
        by_date[date] = by_date.get(date, 0) + 1
        by_role[role] = by_role.get(role, 0) + 1
    
    # Build chronological rows
    rows = []
    cumulative = 0
    for date in sorted(by_date.keys()):
        cumulative += by_date[date]
        rows.append({
            'date': date,
            'new_users': by_date[date],
            'cumulative': cumulative,
        })
    
    return {
        'total_new_users': len(profiles),
        'by_role': by_role,
        'daily_data': rows,
    }


def _build_category_sales_report(start_date, end_date):
    """Aggregate order sales revenue by product category."""
    try:
        # Fetch completed orders
        orders = (
            supabase_admin.table('orders')
            .select('id, created_at')
            .gte('created_at', start_date)
            .lte('created_at', _end_of_day(end_date))
            .eq('status', 'completed')
            .execute()
            .data or []
        )
        
        order_ids = [o['id'] for o in orders]
        category_stats = {}
        
        if order_ids:
            # Get all items from those orders with product category
            items = (
                supabase_admin.table('order_items')
                .select('id, product_id, quantity, price')
                .in_('order_id', order_ids)
                .execute()
                .data or []
            )
            
            product_ids = list(set(item.get('product_id') for item in items if item.get('product_id')))
            
            if product_ids:
                products = (
                    supabase_admin.table('products')
                    .select('id, category')
                    .in_('id', product_ids)
                    .execute()
                    .data or []
                )
                
                product_categories = {p['id']: p.get('category', 'Uncategorized') for p in products}
                
                for item in items:
                    product_id = item.get('product_id')
                    category = product_categories.get(product_id, 'Uncategorized')
                    quantity = item.get('quantity', 0)
                    price = float(item.get('price', 0))
                    revenue = quantity * price
                    
                    if category not in category_stats:
                        category_stats[category] = {'quantity': 0, 'revenue': 0.0}
                    
                    category_stats[category]['quantity'] += quantity
                    category_stats[category]['revenue'] += revenue
        
        # Sort by revenue descending
        sorted_cats = sorted(
            category_stats.items(),
            key=lambda x: x[1]['revenue'],
            reverse=True
        )
        
        rows = []
        total_quantity = 0
        total_revenue = 0.0
        
        for category, stats in sorted_cats:
            total_quantity += stats['quantity']
            total_revenue += stats['revenue']
            rows.append({
                'category': category,
                'quantity_sold': stats['quantity'],
                'total_revenue': round(stats['revenue'], 2),
            })
        
        return {
            'total_categories': len(rows),
            'total_quantity_sold': total_quantity,
            'total_revenue': round(total_revenue, 2),
            'breakdown': rows,
        }
    except Exception as exc:
        print(f'_build_category_sales_report error: {exc}')
        return {
            'total_categories': 0,
            'total_quantity_sold': 0,
            'total_revenue': 0,
            'breakdown': [],
        }


def _build_monthly_active_buyers_report(start_date, end_date):
    """Count unique buyers per month in the period."""
    try:
        # Fetch completed orders with buyer
        orders = (
            supabase_admin.table('orders')
            .select('id, buyer_id, created_at')
            .gte('created_at', start_date)
            .lte('created_at', _end_of_day(end_date))
            .eq('status', 'completed')
            .execute()
            .data or []
        )
    except Exception as exc:
        print(f'_build_monthly_active_buyers_report error: {exc}')
        orders = []
    
    # Group by month
    monthly_buyers = {}
    total_unique = set()
    
    for o in orders:
        buyer_id = o.get('buyer_id')
        created_at = o.get('created_at') or ''
        month = created_at[:7]  # YYYY-MM
        
        if not buyer_id or not month:
            continue
        
        if month not in monthly_buyers:
            monthly_buyers[month] = set()
        
        monthly_buyers[month].add(buyer_id)
        total_unique.add(buyer_id)
    
    # Build rows
    rows = []
    for month in sorted(monthly_buyers.keys()):
        rows.append({
            'month': month,
            'unique_buyers': len(monthly_buyers[month]),
        })
    
    # Calculate average
    avg_buyers = len(total_unique) / len(monthly_buyers) if monthly_buyers else 0
    
    return {
        'total_unique_buyers': len(total_unique),
        'months_with_activity': len(monthly_buyers),
        'avg_buyers_per_month': round(avg_buyers, 0),
        'monthly_breakdown': rows,
    }


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    report_type = request.args.get('type', '').strip()
    start_date  = request.args.get('start_date')
    end_date    = request.args.get('end_date')

    if start_date and end_date:
        # Validate report type is provided
        if not report_type:
            flash('Please select a report type.', 'warning')
            return redirect(url_for('admin.reports'))
        
        if report_type == 'sales':
            report_data = _build_sales_report(start_date, end_date)
        elif report_type == 'users':
            report_data = _build_users_report(start_date, end_date)
        elif report_type == 'activity':
            report_data = _build_activity_report(start_date, end_date)
        elif report_type == 'commissions':
            report_data = Transaction.get_commission_summary(start_date, end_date)
        elif report_type == 'products':
            report_data = _build_product_performance_report(start_date, end_date)
        elif report_type == 'user_growth':
            report_data = _build_user_growth_report(start_date, end_date)
        elif report_type == 'category_sales':
            report_data = _build_category_sales_report(start_date, end_date)
        elif report_type == 'monthly_active_buyers':
            report_data = _build_monthly_active_buyers_report(start_date, end_date)
        else:
            report_data = {}

        Report.create({
            'report_type': report_type,
            'title':       f'{report_type.title()} Report',
            'description': f'Report generated from {start_date} to {end_date}',
            'parameters':  {'start_date': start_date, 'end_date': end_date},
            'data':        report_data,
            'generated_by': current_user.id,
            'start_date':  start_date,
            'end_date':    end_date,
        })

        flash('Report Generated||Your report has been created and is ready to view.', 'success')
        return redirect(url_for('admin.reports'))

    all_reports = Report.get_all()
    return render_template('admin/reports.html',
                           reports=all_reports,
                           report_type=report_type,
                           start_date=start_date,
                           end_date=end_date)


@admin_bp.route('/reports/<report_id>/data')
@login_required
@admin_required
def report_data(report_id):
    """Return stored report data as JSON (used by the modal viewer)."""
    report = Report.get_by_id(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify({
        'id':          report.id,
        'report_type': report.report_type,
        'title':       report.title,
        'start_date':  (report.start_date or '')[:10],
        'end_date':    (report.end_date or '')[:10],
        'created_at':  (report.created_at or '')[:10],
        'data':        report.get_data_dict(),
    })


@admin_bp.route('/reports/<report_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_report(report_id):
    report = Report.get_by_id(report_id)
    if report:
        report.delete()
        flash('Report Deleted||The report has been deleted.', 'success')
    else:
        flash('Not Found||Report not found.', 'danger')
    return redirect(url_for('admin.reports'))


@admin_bp.route('/reports/<report_id>/export/csv')
@login_required
@admin_required
def export_csv(report_id):
    """Stream a CSV download of the stored report data."""
    report = Report.get_by_id(report_id)
    if not report:
        flash('Not Found||Report not found.', 'danger')
        return redirect(url_for('admin.reports'))

    data  = report.get_data_dict()
    rtype = report.report_type

    output = io.StringIO()
    writer = csv.writer(output)

    # ── metadata header ──────────────────────────────────
    writer.writerow(['KidZora Report'])
    writer.writerow(['Type',      rtype.title()])
    writer.writerow(['Period',    f"{(report.start_date or '')[:10]} to {(report.end_date or '')[:10]}"])
    writer.writerow(['Generated', (report.created_at or '')[:10]])
    writer.writerow([])

    if rtype == 'sales':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Orders',         data.get('total_orders', 0)])
        writer.writerow(['Completed Orders',      data.get('completed_orders', 0)])
        writer.writerow(['Cancelled Orders',      data.get('cancelled_orders', 0)])
        writer.writerow(['Total Revenue (PHP)',   data.get('total_revenue', 0)])
        writer.writerow(['Total Commission (PHP)',data.get('total_commission', 0)])
        writer.writerow(['Seller Earnings (PHP)', data.get('total_seller_earnings', 0)])
        writer.writerow(['Avg Order Value (PHP)', data.get('avg_order_value', 0)])
        writer.writerow([])
        writer.writerow(['ORDERS BY STATUS'])
        writer.writerow(['Status', 'Count'])
        for status, count in (data.get('orders_by_status') or {}).items():
            writer.writerow([status, count])
        writer.writerow([])
        writer.writerow(['ORDER DETAILS'])
        writer.writerow(['Date', 'Order ID', 'Amount (PHP)', 'Commission (PHP)', 'Status', 'Payment Method'])
        for row in data.get('rows', []):
            writer.writerow([row['created_at'], row['order_id'], row['amount'],
                             row['commission'], row['status'], row['payment_method']])

    elif rtype == 'users':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total New Users',   data.get('total_new_users', 0)])
        writer.writerow(['New Buyers',        data.get('new_buyers', 0)])
        writer.writerow(['New Sellers',       data.get('new_sellers', 0)])
        writer.writerow(['New Riders',        data.get('new_riders', 0)])
        writer.writerow(['Approved Sellers',  data.get('approved_sellers', 0)])
        writer.writerow(['Pending Sellers',   data.get('pending_sellers', 0)])
        writer.writerow(['Banned Users',      data.get('banned_users', 0)])
        writer.writerow([])
        writer.writerow(['REGISTRATIONS'])
        writer.writerow(['Date', 'Name', 'Role', 'Status'])
        for row in data.get('rows', []):
            writer.writerow([row['registered'], row['name'], row['role'], row['status']])

    elif rtype == 'commissions':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Orders',             data.get('transaction_count', 0)])
        writer.writerow(['Total Commission (PHP)',   data.get('total_commission', 0)])
        writer.writerow(['Total Seller Earnings (PHP)', data.get('total_earnings', 0)])
        writer.writerow([])
        writer.writerow(['COMMISSION BREAKDOWN'])
        writer.writerow(['Date', 'Order ID', 'Amount (PHP)', 'Commission (PHP)', 'Seller Earnings (PHP)'])
        for row in data.get('transactions', []):
            writer.writerow([
                (row.get('created_at') or '')[:10],
                (row.get('order_id') or '')[:8],
                row.get('amount', 0),
                row.get('commission_amount', 0),
                row.get('seller_earnings', 0),
            ])

    elif rtype == 'activity':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Orders',        data.get('total_orders', 0)])
        writer.writerow(['Completed Orders',    data.get('completed_orders', 0)])
        writer.writerow(['Total Revenue (PHP)', data.get('total_revenue', 0)])
        writer.writerow(['Total Commission (PHP)', data.get('total_commission', 0)])
        writer.writerow(['New Users',           data.get('total_new_users', 0)])
        writer.writerow(['Banned Users',        data.get('banned_users', 0)])
        writer.writerow([])
        writer.writerow(['ORDERS BY STATUS'])
        writer.writerow(['Status', 'Count'])
        for status, count in (data.get('orders_by_status') or {}).items():
            writer.writerow([status, count])
        writer.writerow([])
        writer.writerow(['NEW USERS BY ROLE'])
        writer.writerow(['Role', 'Count'])
        for role, count in (data.get('new_users_by_role') or {}).items():
            writer.writerow([role, count])

    elif rtype == 'products':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Unique Products Sold', data.get('total_products_sold', 0)])
        writer.writerow(['Total Quantity Sold',        data.get('total_quantity_sold', 0)])
        writer.writerow(['Total Revenue (PHP)',        data.get('total_revenue', 0)])
        writer.writerow(['Avg Revenue Per Product (PHP)', data.get('avg_revenue_per_product', 0)])
        writer.writerow([])
        writer.writerow(['TOP 10 SELLING PRODUCTS'])
        writer.writerow(['Rank', 'Product Name', 'Quantity Sold', 'Revenue (PHP)'])
        for idx, row in enumerate(data.get('top_10_products', []), 1):
            writer.writerow([idx, row['product_name'], row['quantity_sold'], row['total_revenue']])
        writer.writerow([])
        writer.writerow(['ALL PRODUCTS SOLD'])
        writer.writerow(['Product Name', 'Quantity Sold', 'Revenue (PHP)'])
        for row in data.get('all_products', []):
            writer.writerow([row['product_name'], row['quantity_sold'], row['total_revenue']])

    elif rtype == 'user_growth':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total New Users', data.get('total_new_users', 0)])
        writer.writerow(['Breakdown by Role'])
        writer.writerow([])
        for role, count in (data.get('by_role') or {}).items():
            writer.writerow([f'  {role.title()}', count])
        writer.writerow([])
        writer.writerow(['DAILY REGISTRATION TREND'])
        writer.writerow(['Date', 'New Users', 'Cumulative'])
        for row in data.get('daily_data', []):
            writer.writerow([row['date'], row['new_users'], row['cumulative']])

    elif rtype == 'category_sales':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Categories Active',  data.get('total_categories', 0)])
        writer.writerow(['Total Quantity Sold',     data.get('total_quantity_sold', 0)])
        writer.writerow(['Total Revenue (PHP)',     data.get('total_revenue', 0)])
        writer.writerow([])
        writer.writerow(['SALES BY CATEGORY'])
        writer.writerow(['Category', 'Quantity Sold', 'Revenue (PHP)'])
        for row in data.get('breakdown', []):
            writer.writerow([row['category'], row['quantity_sold'], row['total_revenue']])

    elif rtype == 'monthly_active_buyers':
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Unique Buyers',       data.get('total_unique_buyers', 0)])
        writer.writerow(['Months with Activity',      data.get('months_with_activity', 0)])
        writer.writerow(['Avg Buyers Per Month',      data.get('avg_buyers_per_month', 0)])
        writer.writerow([])
        writer.writerow(['MONTHLY BREAKDOWN'])
        writer.writerow(['Month', 'Unique Buyers'])
        for row in data.get('monthly_breakdown', []):
            writer.writerow([row['month'], row['unique_buyers']])

    else:
        writer.writerow(['Data'])
        writer.writerow([str(data)])

    s = (report.start_date or '')[:10]
    e = (report.end_date   or '')[:10]
    filename = f"kidzora_{rtype}_report_{s}_{e}.csv"

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@admin_bp.route('/reports/<report_id>/export/pdf')
@login_required
@admin_required
def export_pdf(report_id):
    """Render a print-ready HTML page; the browser handles Save-as-PDF."""
    report = Report.get_by_id(report_id)
    if not report:
        flash('Not Found||Report not found.', 'danger')
        return redirect(url_for('admin.reports'))

    data = report.get_data_dict()
    return render_template('admin/print_report.html', report=report, data=data)
