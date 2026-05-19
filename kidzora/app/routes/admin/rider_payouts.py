"""Admin – Rider Payout Requests management.

Routes:
  GET  /admin/rider-payouts                   — list all rider payout requests
  POST /admin/rider-payouts/<id>/approve
  POST /admin/rider-payouts/<id>/reject
"""
from datetime import datetime, timezone

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from app.services.audit_log import log_admin_action
from .utils import admin_bp, admin_required


@admin_bp.route('/rider-payouts')
@login_required
@admin_required
def rider_payouts():
    status_filter = request.args.get('status', 'pending')
    page          = max(1, request.args.get('page', 1, type=int))
    per_page      = 25

    # ── Fetch requests
    requests_list = []
    total         = 0
    total_pages   = 1

    try:
        q = supabase.table('rider_payout_requests').select('*').order('created_at', desc=True)
        if status_filter and status_filter != 'all':
            q = q.eq('status', status_filter)
        all_r = q.execute().data or []

        # Enrich with rider profile info
        rider_ids = list({r['rider_id'] for r in all_r})
        rider_map = {}
        if rider_ids:
            rd_r = supabase.table('riders') \
                .select('id,user_id') \
                .in_('id', rider_ids) \
                .execute().data or []
            user_ids = [rd['user_id'] for rd in rd_r]
            profile_map = {}
            if user_ids:
                p_r = supabase.table('profiles') \
                    .select('id,first_name,last_name,email') \
                    .in_('id', user_ids) \
                    .execute().data or []
                profile_map = {p['id']: p for p in p_r}
            for rd in rd_r:
                rd['profile'] = profile_map.get(rd['user_id'], {})
                rider_map[rd['id']] = rd

        for r in all_r:
            r['rider'] = rider_map.get(r['rider_id'], {})

        total         = len(all_r)
        start         = (page - 1) * per_page
        requests_list = all_r[start:start + per_page]
        total_pages   = max(1, (total + per_page - 1) // per_page)

    except Exception as e:
        flash(f'Could not load rider payout requests||{e}', 'error')

    # ── Summary counts
    counts = {'pending': 0, 'approved': 0, 'rejected': 0, 'total': 0}
    try:
        all_counts = supabase.table('rider_payout_requests').select('status').execute().data or []
        for row in all_counts:
            s = row.get('status', '')
            counts[s] = counts.get(s, 0) + 1
            counts['total'] += 1
    except Exception:
        pass

    return render_template(
        'admin/rider_payouts.html',
        requests      = requests_list,
        counts        = counts,
        status_filter = status_filter,
        page          = page,
        total_pages   = total_pages,
        total         = total,
        per_page      = per_page,
    )


@admin_bp.route('/rider-payouts/<payout_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_rider_payout(payout_id):
    notes = (request.form.get('notes') or '').strip()
    try:
        row = supabase.table('rider_payout_requests').select('id,rider_id,amount').eq('id', payout_id).single().execute().data
        target_user_id = None
        if row and row.get('rider_id'):
            rider_row = supabase.table('riders').select('user_id').eq('id', row.get('rider_id')).single().execute().data
            target_user_id = (rider_row or {}).get('user_id')
        supabase.table('rider_payout_requests').update({
            'status':       'approved',
            'admin_notes':  notes or None,
            'processed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', payout_id).execute()

        log_admin_action(
            action='approve_rider_payout',
            entity_type='rider_payout_request',
            entity_id=payout_id,
            target_user_id=target_user_id,
            details={'rider_id': (row or {}).get('rider_id'), 'amount': (row or {}).get('amount'), 'notes': notes or None},
        )

        # Notify rider
        _notify_rider_payout(payout_id, 'approved')

        flash('Rider Payout Approved!||The rider has been notified and funds can be released.', 'success')
    except Exception as e:
        flash(f'Could not approve payout||{e}', 'error')
    return redirect(url_for('admin.rider_payouts'))


@admin_bp.route('/rider-payouts/<payout_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_rider_payout(payout_id):
    notes = (request.form.get('notes') or '').strip()
    if not notes:
        flash('Please provide a reason for rejection.', 'warning')
        return redirect(url_for('admin.rider_payouts'))
    try:
        row = supabase.table('rider_payout_requests').select('id,rider_id,amount').eq('id', payout_id).single().execute().data
        target_user_id = None
        if row and row.get('rider_id'):
            rider_row = supabase.table('riders').select('user_id').eq('id', row.get('rider_id')).single().execute().data
            target_user_id = (rider_row or {}).get('user_id')
        supabase.table('rider_payout_requests').update({
            'status':       'rejected',
            'admin_notes':  notes,
            'processed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', payout_id).execute()

        log_admin_action(
            action='reject_rider_payout',
            entity_type='rider_payout_request',
            entity_id=payout_id,
            target_user_id=target_user_id,
            details={'rider_id': (row or {}).get('rider_id'), 'amount': (row or {}).get('amount'), 'notes': notes},
        )

        # Notify rider
        _notify_rider_payout(payout_id, 'rejected')

        flash('Rider Payout Rejected||The rider has been notified.', 'info')
    except Exception as e:
        flash(f'Could not reject payout||{e}', 'error')
    return redirect(url_for('admin.rider_payouts'))


def _notify_rider_payout(payout_id: str, status: str) -> None:
    """Look up the rider user_id and push a notification."""
    try:
        pr = supabase.table('rider_payout_requests') \
            .select('rider_id, amount') \
            .eq('id', payout_id) \
            .single().execute().data
        if not pr:
            return
        rider = supabase.table('riders') \
            .select('user_id') \
            .eq('id', pr['rider_id']) \
            .single().execute().data
        if not rider:
            return
        from app.services.notify import push_rider_payout_event
        push_rider_payout_event(
            rider_user_id=rider['user_id'],
            status=status,
            amount=float(pr.get('amount') or 0),
        )
    except Exception:
        pass
