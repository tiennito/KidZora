"""Seller return/refund request handling."""
from datetime import datetime, timedelta, timezone

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from app.services.email import notify_return_seller_approved, notify_return_seller_rejected
from app.services.notify import push_return_event
from app.utils.pagination import paginate_list
from app.utils.settings import get_return_auto_approve_days
from .utils import seller_bp, seller_required, _get_seller_id

_REASON_LABELS = {
    'wrong_item':       'Wrong item received',
    'damaged':          'Item arrived damaged',
    'defective':        'Item is defective / not working',
    'not_as_described': 'Item not as described',
    'incomplete':       'Incomplete / missing items',
    'other':            'Other',
}


@seller_bp.route('/returns')
@login_required
@seller_required
def returns():
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.dashboard'))

    status_filter = request.args.get('status', '')

    try:
        query = (supabase.table('return_requests')
                 .select('*, orders(id, total_amount, status)')
                 .eq('seller_id', seller_id))
        if status_filter:
            query = query.eq('status', status_filter)
        rows = query.order('created_at', desc=True).execute().data or []
    except Exception as e:
        flash(f'Could not load returns: {e}', 'error')
        rows = []

    # Count pending for badge
    pending_count = sum(1 for r in rows if r.get('status') == 'pending') if not status_filter else 0
    if status_filter:
        try:
            pending_count = len(supabase.table('return_requests').select('id')
                                .eq('seller_id', seller_id).eq('status', 'pending')
                                .execute().data or [])
        except Exception:
            pending_count = 0

    # ── Attach auto-approve deadline to each pending row ──────────────────
    auto_approve_days = get_return_auto_approve_days()
    now = datetime.now(timezone.utc)
    for rr in rows:
        if rr.get('status') == 'pending' and rr.get('created_at'):
            try:
                created = datetime.fromisoformat(rr['created_at'].replace('Z', '+00:00'))
                deadline = created + timedelta(days=auto_approve_days)
                rr['_auto_approve_deadline'] = deadline.isoformat()
                delta = deadline - now
                rr['_days_remaining'] = max(0, delta.days)
                rr['_hours_remaining'] = max(0, int(delta.total_seconds() // 3600))
            except Exception:
                rr['_auto_approve_deadline'] = None
                rr['_days_remaining'] = None
                rr['_hours_remaining'] = None
        else:
            rr['_auto_approve_deadline'] = None
            rr['_days_remaining'] = None
            rr['_hours_remaining'] = None

    pag = paginate_list(rows, per_page=15)
    return render_template(
        'seller/returns.html',
        requests=pag.items,
        pagination=pag,
        selected_status=status_filter,
        pending_count=pending_count,
        reason_labels=_REASON_LABELS,
        auto_approve_days=auto_approve_days,
    )


@seller_bp.route('/returns/<rr_id>')
@login_required
@seller_required
def return_detail(rr_id):
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.returns'))

    try:
        rr = (supabase.table('return_requests')
              .select('*, orders(id, total_amount, status)')
              .eq('id', rr_id).eq('seller_id', seller_id)
              .single().execute().data)
    except Exception:
        rr = None

    if not rr:
        flash('Return request not found.', 'error')
        return redirect(url_for('seller.returns'))

    return render_template('seller/return_detail.html', rr=rr, reason_labels=_REASON_LABELS)


@seller_bp.route('/returns/<rr_id>/approve', methods=['POST'])
@login_required
@seller_required
def return_approve(rr_id):
    seller_id = _get_seller_id()
    try:
        rr = (supabase.table('return_requests')
              .select('id,status').eq('id', rr_id).eq('seller_id', seller_id)
              .single().execute().data)
    except Exception:
        rr = None

    if not rr or rr.get('status') != 'pending':
        flash('No pending return request found.', 'warning')
        return redirect(url_for('seller.returns'))

    response = request.form.get('seller_response', '').strip()

    try:
        supabase.table('return_requests').update({
            'status': 'seller_approved',
            'seller_response': response or 'Return/refund approved by seller.',
        }).eq('id', rr_id).execute()
        flash('Return Approved||The buyer has been notified. Refund process will begin.', 'success')
        notify_return_seller_approved(rr_id, response or 'Return/refund approved by seller.')
        push_return_event(rr_id, 'approved')
        push_return_event(rr_id, 'approved')
    except Exception as e:
        flash(f'Could not approve: {e}', 'error')

    return redirect(url_for('seller.return_detail', rr_id=rr_id))


@seller_bp.route('/returns/<rr_id>/reject', methods=['POST'])
@login_required
@seller_required
def return_reject(rr_id):
    seller_id = _get_seller_id()
    try:
        rr = (supabase.table('return_requests')
              .select('id,status').eq('id', rr_id).eq('seller_id', seller_id)
              .single().execute().data)
    except Exception:
        rr = None

    if not rr or rr.get('status') != 'pending':
        flash('No pending return request found.', 'warning')
        return redirect(url_for('seller.returns'))

    response = request.form.get('seller_response', '').strip()
    if not response:
        flash('Please provide a reason for rejection.', 'error')
        return redirect(url_for('seller.return_detail', rr_id=rr_id))

    try:
        supabase.table('return_requests').update({
            'status': 'seller_rejected',
            'seller_response': response,
        }).eq('id', rr_id).execute()
        flash('Return Rejected||The buyer may escalate this decision to admin for further review.', 'info')
        notify_return_seller_rejected(rr_id, response)
        push_return_event(rr_id, 'rejected')
        push_return_event(rr_id, 'rejected')
    except Exception as e:
        flash(f'Could not reject: {e}', 'error')

    return redirect(url_for('seller.return_detail', rr_id=rr_id))
