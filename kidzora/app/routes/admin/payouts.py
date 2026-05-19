"""Admin – Payout Requests management.

Routes:
  GET  /admin/payouts            — list all payout requests
  POST /admin/payouts/<id>/approve
  POST /admin/payouts/<id>/reject
"""
from datetime import datetime, timezone

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.audit_log import log_admin_action
from .utils import admin_bp, admin_required


@admin_bp.route('/payouts')
@login_required
@admin_required
def payouts():
    status_filter = request.args.get('status', 'pending')
    page          = max(1, request.args.get('page', 1, type=int))
    per_page      = 25

    # ── Fetch requests
    requests_list = []
    try:
        q = supabase.table('payout_requests').select('*').order('created_at', desc=True)
        if status_filter and status_filter != 'all':
            q = q.eq('status', status_filter)
        all_r = q.execute().data or []

        # Enrich with seller info
        seller_ids = list({r['seller_id'] for r in all_r})
        seller_map = {}
        if seller_ids:
            s_r = supabase.table('sellers') \
                .select('id,shop_name,user_id') \
                .in_('id', seller_ids) \
                .execute().data or []
            user_ids = [s['user_id'] for s in s_r]
            profile_map = {}
            if user_ids:
                p_r = supabase.table('profiles') \
                    .select('id,first_name,last_name,email') \
                    .in_('id', user_ids) \
                    .execute().data or []
                profile_map = {p['id']: p for p in p_r}
            for s in s_r:
                s['profile'] = profile_map.get(s['user_id'], {})
                seller_map[s['id']] = s

        for r in all_r:
            r['seller'] = seller_map.get(r['seller_id'], {})

        total         = len(all_r)
        start         = (page - 1) * per_page
        requests_list = all_r[start:start + per_page]
        total_pages   = max(1, (total + per_page - 1) // per_page)

    except Exception as e:
        flash(f'Could not load payout requests||{e}', 'error')
        total       = 0
        total_pages = 1

    # ── Summary counts
    counts = {'pending': 0, 'approved': 0, 'rejected': 0, 'total': 0}
    try:
        all_counts = supabase.table('payout_requests').select('status').execute().data or []
        for row in all_counts:
            s = row.get('status', '')
            counts[s] = counts.get(s, 0) + 1
            counts['total'] += 1
    except Exception:
        pass

    return render_template(
        'admin/payouts.html',
        requests      = requests_list,
        counts        = counts,
        status_filter = status_filter,
        page          = page,
        total_pages   = total_pages,
        total         = total,
        per_page      = per_page,
    )


@admin_bp.route('/payouts/<payout_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_payout(payout_id):
    notes = (request.form.get('notes') or '').strip()
    try:
        row = supabase.table('payout_requests').select('id,seller_id,amount').eq('id', payout_id).single().execute().data
        target_user_id = None
        if row and row.get('seller_id'):
            seller_row = supabase.table('sellers').select('user_id').eq('id', row.get('seller_id')).single().execute().data
            target_user_id = (seller_row or {}).get('user_id')
        supabase.table('payout_requests').update({
            'status':       'approved',
            'admin_notes':  notes or None,
            'processed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', payout_id).execute()
        log_admin_action(
            action='approve_seller_payout',
            entity_type='payout_request',
            entity_id=payout_id,
            target_user_id=target_user_id,
            details={'seller_id': (row or {}).get('seller_id'), 'amount': (row or {}).get('amount'), 'notes': notes or None},
        )
        flash('Payout Approved!||The seller has been notified and funds can be released.', 'success')
    except Exception as e:
        flash(f'Could not approve payout||{e}', 'error')
    return redirect(url_for('admin.payouts'))


@admin_bp.route('/payouts/<payout_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_payout(payout_id):
    notes = (request.form.get('notes') or '').strip()
    if not notes:
        flash('Please provide a reason for rejection.', 'warning')
        return redirect(url_for('admin.payouts'))
    try:
        row = supabase.table('payout_requests').select('id,seller_id,amount').eq('id', payout_id).single().execute().data
        target_user_id = None
        if row and row.get('seller_id'):
            seller_row = supabase.table('sellers').select('user_id').eq('id', row.get('seller_id')).single().execute().data
            target_user_id = (seller_row or {}).get('user_id')
        supabase.table('payout_requests').update({
            'status':       'rejected',
            'admin_notes':  notes,
            'processed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', payout_id).execute()
        log_admin_action(
            action='reject_seller_payout',
            entity_type='payout_request',
            entity_id=payout_id,
            target_user_id=target_user_id,
            details={'seller_id': (row or {}).get('seller_id'), 'amount': (row or {}).get('amount'), 'notes': notes},
        )
        flash('Payout Rejected||The seller has been notified.', 'info')
    except Exception as e:
        flash(f'Could not reject payout||{e}', 'error')
    return redirect(url_for('admin.payouts'))
