"""Admin return/refund dispute resolution.
Admin only steps in when the buyer escalates after a seller rejection.
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from app.services.email import notify_return_admin_resolved
from app.services.notify import push_return_event
from app.utils.decorators import admin_required
from app.utils.pagination import paginate_query
from .utils import admin_bp

_REASON_LABELS = {
    'wrong_item':       'Wrong item received',
    'damaged':          'Item arrived damaged',
    'defective':        'Item is defective / not working',
    'not_as_described': 'Item not as described',
    'incomplete':       'Incomplete / missing items',
    'other':            'Other',
}


@admin_bp.route('/returns')
@login_required
@admin_required
def returns():
    """List return requests — defaults to showing escalated ones first."""
    status_filter = request.args.get('status', 'escalated')

    try:
        query = supabase.table('return_requests').select('*, orders(id, total_amount, status)', count='exact')
        if status_filter and status_filter != 'all':
            query = query.eq('status', status_filter)
        query = query.order('created_at', desc=True)
        pag = paginate_query(query, per_page=25)
        rows = pag.items
    except Exception as e:
        flash(f'Could not load returns: {e}', 'error')
        from app.utils.pagination import Pagination
        pag = Pagination(items=[], page=1, per_page=25, total=0)
        rows = []

    # Badge count for escalated
    try:
        escalated_count = len(supabase.table('return_requests').select('id')
                               .eq('status', 'escalated').execute().data or [])
    except Exception:
        escalated_count = 0

    return render_template(
        'admin/returns.html',
        requests=rows,
        pagination=pag,
        selected_status=status_filter,
        escalated_count=escalated_count,
        reason_labels=_REASON_LABELS,
    )


@admin_bp.route('/returns/<rr_id>')
@login_required
@admin_required
def return_detail(rr_id):
    try:
        rr = (supabase.table('return_requests')
              .select('*, orders(id, total_amount, status)')
              .eq('id', rr_id).single().execute().data)
    except Exception:
        rr = None

    if not rr:
        flash('Return request not found.', 'error')
        return redirect(url_for('admin.returns'))

    return render_template('admin/return_detail.html', rr=rr, reason_labels=_REASON_LABELS)


@admin_bp.route('/returns/<rr_id>/resolve', methods=['POST'])
@login_required
@admin_required
def return_resolve(rr_id):
    """Admin resolves an escalated dispute."""
    decision       = request.form.get('decision', '')      # 'approve' or 'reject'
    admin_response = request.form.get('admin_response', '').strip()

    if decision not in ('approve', 'reject'):
        flash('Invalid decision.', 'error')
        return redirect(url_for('admin.return_detail', rr_id=rr_id))

    if not admin_response:
        flash('Please provide a resolution note.', 'error')
        return redirect(url_for('admin.return_detail', rr_id=rr_id))

    try:
        rr = (supabase.table('return_requests').select('id,status')
              .eq('id', rr_id).single().execute().data)
    except Exception:
        rr = None

    if not rr or rr.get('status') != 'escalated':
        flash('This request is not in escalated status.', 'warning')
        return redirect(url_for('admin.returns'))

    new_status = 'admin_approved' if decision == 'approve' else 'admin_rejected'
    try:
        supabase.table('return_requests').update({
            'status':         new_status,
            'admin_response': admin_response,
        }).eq('id', rr_id).execute()
        label = 'approved — refund will be processed' if decision == 'approve' else 'rejected'
        flash(f'Dispute Resolved||The return request has been {label} by admin.', 'success')
        notify_return_admin_resolved(rr_id, decision, admin_response)
        push_return_event(rr_id, 'approved' if decision == 'approve' else 'rejected')
    except Exception as e:
        flash(f'Could not resolve: {e}', 'error')

    return redirect(url_for('admin.return_detail', rr_id=rr_id))
