"""Admin commission overview route."""
from datetime import datetime, timedelta
import csv
import io

from flask import render_template, request, jsonify, send_file
from flask_login import login_required

from app.models.transaction import Transaction
from app.services.audit_log import log_admin_action
from app.utils.settings import get_commission_rate, get_payout_frequency, get_return_auto_approve_days, set_setting
from .utils import admin_bp, admin_required


@admin_bp.route('/commission/settings', methods=['POST'])
@login_required
@admin_required
def commission_settings_save():
    data = request.get_json(force=True)
    try:
        rate = float(data.get('commission_rate', ''))
        if not (0 <= rate <= 100):
            raise ValueError('out of range')
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Rate must be a number between 0 and 100.'}), 400

    freq = data.get('payout_frequency', 'weekly')
    if freq not in ('daily', 'weekly', 'biweekly', 'monthly'):
        freq = 'weekly'

    try:
        auto_days = int(data.get('return_auto_approve_days', 5))
        if auto_days < 1:
            raise ValueError('must be >= 1')
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Auto-approve days must be a positive integer.'}), 400

    ok1 = set_setting('commission_rate',           str(round(rate / 100, 6)))
    ok2 = set_setting('payout_frequency',          freq)
    ok3 = set_setting('return_auto_approve_days',  str(auto_days))
    if ok1 and ok2 and ok3:
        log_admin_action(
            action='update_platform_settings',
            entity_type='platform_settings',
            entity_id='commission_settings',
            details={
                'commission_rate_percent': rate,
                'payout_frequency': freq,
                'return_auto_approve_days': auto_days,
            },
        )
        return jsonify({'success': True,
                        'message': f'Settings saved. Commission rate updated to {rate}%.'}) 
    return jsonify({'success': False,
                    'message': 'Failed to save settings. Check server logs.'}), 500


@admin_bp.route('/commission')
@login_required
@admin_required
def commission_overview():
    start_date = request.args.get('start_date')
    end_date   = request.args.get('end_date')
    period     = request.args.get('period', 'all')

    now = datetime.utcnow()
    period_map = {
        'day':   now - timedelta(days=1),
        'week':  now - timedelta(weeks=1),
        'month': now - timedelta(days=30),
        'year':  now - timedelta(days=365),
    }

    if start_date and end_date:
        # Custom date range from form
        commission_data = Transaction.get_commission_summary(start_date, end_date)
        period = 'custom'
    elif period in period_map:
        start_date = period_map[period].isoformat()
        end_date   = now.isoformat()
        commission_data = Transaction.get_commission_summary(start_date, end_date)
    else:
        # All time
        start_date = None
        end_date   = None
        commission_data = Transaction.get_commission_summary()

    # Fetch seller shop names for all transactions
    from app.extensions import supabase_admin
    seller_info_map = {}
    if commission_data.get('transactions'):
        seller_ids = list(set([t.get('seller_id') for t in commission_data.get('transactions', [])]))
        if seller_ids:
            try:
                seller_data = supabase_admin.table('sellers').select('id, shop_name').in_('id', seller_ids).execute()
                for seller in seller_data.data:
                    seller_info_map[seller['id']] = seller.get('shop_name', seller['id'])
            except Exception as e:
                print(f"[ERROR] Failed to fetch seller info: {e}")
        
        # Add shop_name and calculate historical rate for each transaction
        for transaction in commission_data.get('transactions', []):
            seller_id = transaction.get('seller_id')
            transaction['seller_shop_name'] = seller_info_map.get(seller_id, seller_id)
            
            # Calculate the actual commission rate applied to this transaction
            order_amount = transaction.get('amount', 1)
            commission_amount = transaction.get('commission_amount', 0)
            if order_amount > 0:
                transaction['historical_rate'] = round((commission_amount / order_amount) * 100, 2)
            else:
                transaction['historical_rate'] = 0

    commission_rate_pct      = round(get_commission_rate() * 100, 4)
    payout_frequency         = get_payout_frequency()
    return_auto_approve_days = get_return_auto_approve_days()

    return render_template('admin/commission.html',
                           commission_data=commission_data,
                           start_date=start_date,
                           end_date=end_date,
                           active_period=period,
                           commission_rate_pct=commission_rate_pct,
                           payout_frequency=payout_frequency,
                           return_auto_approve_days=return_auto_approve_days)


@admin_bp.route('/commission/export-csv', methods=['POST'])
@login_required
@admin_required
def commission_export_csv():
    """Export commission data as CSV file."""
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    period = request.form.get('period', 'all')

    # Get the commission data
    now = datetime.utcnow()
    period_map = {
        'day':   now - timedelta(days=1),
        'week':  now - timedelta(weeks=1),
        'month': now - timedelta(days=30),
        'year':  now - timedelta(days=365),
    }

    if start_date and end_date:
        commission_data = Transaction.get_commission_summary(start_date, end_date)
        date_range = f"{start_date} to {end_date}"
    elif period in period_map:
        start_date = period_map[period].isoformat()
        end_date = now.isoformat()
        commission_data = Transaction.get_commission_summary(start_date, end_date)
        date_range = period.title()
    else:
        commission_data = Transaction.get_commission_summary()
        date_range = "All Time"

    # Fetch seller shop names for all transactions
    from app.extensions import supabase_admin
    seller_info_map = {}
    if commission_data.get('transactions'):
        seller_ids = list(set([t.get('seller_id') for t in commission_data.get('transactions', [])]))
        if seller_ids:
            try:
                seller_data = supabase_admin.table('sellers').select('id, shop_name').in_('id', seller_ids).execute()
                for seller in seller_data.data:
                    seller_info_map[seller['id']] = seller.get('shop_name', seller['id'])
            except Exception as e:
                print(f"[ERROR] Failed to fetch seller info: {e}")

    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers with commission rate
    commission_rate = round(get_commission_rate() * 100, 2)
    writer.writerow(['Commission Report - ' + date_range])
    writer.writerow(['Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')])
    writer.writerow([])
    
    # Summary section
    writer.writerow(['Summary'])
    writer.writerow(['Total Commission', f"₱{commission_data.get('total_commission', 0):.2f}"])
    writer.writerow(['Total Seller Earnings', f"₱{commission_data.get('total_earnings', 0):.2f}"])
    writer.writerow(['Transaction Count', commission_data.get('transaction_count', 0)])
    writer.writerow(['Commission Rate', f"{commission_rate}%"])
    writer.writerow([])
    
    # Transaction details
    writer.writerow(['Transaction Details'])
    writer.writerow(['Date', 'Order ID', 'Seller Name', 'Order Amount', 'Commission Amount', 'Commission Rate Applied', 'Seller Earnings', 'Status'])
    
    for transaction in commission_data.get('transactions', []):
        seller_id = transaction.get('seller_id', '')
        seller_name = seller_info_map.get(seller_id, seller_id)
        
        # Calculate historical rate for this transaction
        order_amount = transaction.get('amount', 1)
        commission_amount = transaction.get('commission_amount', 0)
        historical_rate = round((commission_amount / order_amount) * 100, 2) if order_amount > 0 else 0
        
        writer.writerow([
            transaction.get('created_at', '')[:10],
            transaction.get('order_id', ''),
            seller_name,
            f"₱{transaction.get('amount', 0):.2f}",
            f"₱{transaction.get('commission_amount', 0):.2f}",
            f"{historical_rate}%",
            f"₱{transaction.get('seller_earnings', 0):.2f}",
            transaction.get('status', '').title()
        ])

    # Log the export action
    log_admin_action(
        action='export_commission_data',
        entity_type='commission_report',
        entity_id='csv_export',
        details={'date_range': date_range, 'transaction_count': commission_data.get('transaction_count', 0)}
    )

    # Create response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"commission_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    )


@admin_bp.route('/commission/export-pdf', methods=['POST'])
@login_required
@admin_required
def commission_export_pdf():
    """Export commission data as PDF file."""
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    period = request.form.get('period', 'all')

    # Get the commission data
    now = datetime.utcnow()
    period_map = {
        'day':   now - timedelta(days=1),
        'week':  now - timedelta(weeks=1),
        'month': now - timedelta(days=30),
        'year':  now - timedelta(days=365),
    }

    if start_date and end_date:
        commission_data = Transaction.get_commission_summary(start_date, end_date)
        date_range = f"{start_date} to {end_date}"
    elif period in period_map:
        start_date = period_map[period].isoformat()
        end_date = now.isoformat()
        commission_data = Transaction.get_commission_summary(start_date, end_date)
        date_range = period.title()
    else:
        commission_data = Transaction.get_commission_summary()
        date_range = "All Time"

    # Fetch seller shop names for all transactions
    from app.extensions import supabase_admin
    seller_info_map = {}
    if commission_data.get('transactions'):
        seller_ids = list(set([t.get('seller_id') for t in commission_data.get('transactions', [])]))
        if seller_ids:
            try:
                seller_data = supabase_admin.table('sellers').select('id, shop_name').in_('id', seller_ids).execute()
                for seller in seller_data.data:
                    seller_info_map[seller['id']] = seller.get('shop_name', seller['id'])
            except Exception as e:
                print(f"[ERROR] Failed to fetch seller info: {e}")

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    except ImportError:
        return jsonify({'success': False, 'message': 'PDF export requires reportlab library. Please install it.'}), 500

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#13111a'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    elements.append(Paragraph('Commission Report', title_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Summary info
    commission_rate = round(get_commission_rate() * 100, 2)
    summary_text = f"<b>Period:</b> {date_range} | <b>Rate:</b> {commission_rate}% | <b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    elements.append(Paragraph(summary_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary metrics table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Commission', f"₱{commission_data.get('total_commission', 0):.2f}"],
        ['Total Seller Earnings', f"₱{commission_data.get('total_earnings', 0):.2f}"],
        ['Transaction Count', str(commission_data.get('transaction_count', 0))],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#a5b4fc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#13111a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Transactions table
    if commission_data.get('transactions'):
        elements.append(Paragraph('Transaction Details', styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))
        
        trans_data = [[
            'Date', 'Order ID', 'Seller Name', 'Amount', 'Commission\n(Amount)', 'Rate\nApplied',
            'Seller\nEarnings', 'Status'
        ]]
        
        for transaction in commission_data.get('transactions', [])[:50]:  # Limit to 50 rows per page
            seller_id = transaction.get('seller_id', '')
            seller_name = seller_info_map.get(seller_id, seller_id)
            
            # Calculate historical rate for this transaction
            order_amount = transaction.get('amount', 1)
            commission_amount = transaction.get('commission_amount', 0)
            historical_rate = round((commission_amount / order_amount) * 100, 2) if order_amount > 0 else 0
            
            trans_data.append([
                transaction.get('created_at', '')[:10],
                transaction.get('order_id', '')[:12] + '...',
                seller_name[:20] + '...' if len(seller_name) > 20 else seller_name,
                f"₱{transaction.get('amount', 0):.2f}",
                f"₱{transaction.get('commission_amount', 0):.2f}",
                f"{historical_rate}%",
                f"₱{transaction.get('seller_earnings', 0):.2f}",
                transaction.get('status', '').title()
            ])
        
        trans_table = Table(trans_data, colWidths=[0.75*inch, 0.9*inch, 0.9*inch, 0.75*inch, 0.8*inch, 0.65*inch, 0.8*inch, 0.6*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#a5b4fc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#13111a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        elements.append(trans_table)
    
    # Build PDF
    doc.build(elements)

    # Log the export action
    log_admin_action(
        action='export_commission_data',
        entity_type='commission_report',
        entity_id='pdf_export',
        details={'date_range': date_range, 'transaction_count': commission_data.get('transaction_count', 0)}
    )

    # Return PDF
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"commission_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
