"""Buyer return/refund requests."""
import os
import uuid

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.email import notify_return_submitted, notify_return_escalated
from app.utils.pagination import paginate_query
from .utils import buyer_bp

# Allowed file extensions for return evidence
_ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
_ALLOWED_VIDEOS = {'mp4', 'mov', 'avi', 'webm', 'mkv'}
_ALLOWED_EVIDENCE = _ALLOWED_IMAGES | _ALLOWED_VIDEOS
_MAX_FILES = 5          # max attachments per request
_MAX_FILE_MB = 30       # max MB per file


def _allowed_evidence(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in _ALLOWED_EVIDENCE


def _save_evidence_files(files, order_id):
    """Upload evidence files to Supabase Storage; return list of public URLs."""
    saved_paths = []
    from app.utils.images import upload_to_storage, upload_raw_to_storage, is_image_ext

    for file in files[:_MAX_FILES]:
        if not file or file.filename == '':
            continue
        if not _allowed_evidence(file.filename):
            continue
        ext  = file.filename.rsplit('.', 1)[1].lower()
        stem = uuid.uuid4().hex
        try:
            if is_image_ext(file.filename):
                storage_path = f'returns/{order_id}/{stem}.webp'
                url = upload_to_storage(file, 'return-evidence', storage_path,
                                        max_width=1280, max_height=1280, quality=80)
            else:
                storage_path = f'returns/{order_id}/{stem}.{ext}'
                url = upload_raw_to_storage(file, 'return-evidence', storage_path)
            saved_paths.append(url)
        except Exception as e:
            print(f'[_save_evidence_files] upload failed: {e}')

    return saved_paths

_REASONS = [
    ('wrong_item',       'Wrong item received'),
    ('damaged',          'Item arrived damaged'),
    ('defective',        'Item is defective / not working'),
    ('not_as_described', 'Item not as described'),
    ('incomplete',       'Incomplete / missing items'),
    ('other',            'Other'),
]


@buyer_bp.route('/returns')
@login_required
def returns():
    """List all return requests by this buyer."""
    try:
        query = (supabase.table('return_requests')
                 .select('*, orders(id, total_amount, created_at, status)', count='exact')
                 .eq('buyer_id', current_user.id)
                 .order('created_at', desc=True))
        pag = paginate_query(query, per_page=10)
    except Exception as e:
        flash(f'Could not load returns: {e}', 'error')
        from app.utils.pagination import Pagination
        pag = Pagination(items=[], page=1, per_page=10, total=0)
    return render_template('buyer/returns.html', requests=pag.items, pagination=pag)


@buyer_bp.route('/returns/<rr_id>')
@login_required
def return_detail(rr_id):
    """Detail view for a single return request."""
    try:
        rr = (supabase.table('return_requests')
              .select('*, orders(id, total_amount, status)')
              .eq('id', rr_id).eq('buyer_id', current_user.id)
              .single().execute().data)
    except Exception:
        rr = None
    if not rr:
        abort(404)

    # Compute auto-approve deadline for pending requests
    from datetime import datetime, timedelta, timezone
    from app.utils.settings import get_return_auto_approve_days
    auto_approve_days     = get_return_auto_approve_days()
    auto_approve_deadline = None
    if rr.get('status') == 'pending' and rr.get('created_at'):
        try:
            created = datetime.fromisoformat(rr['created_at'].replace('Z', '+00:00'))
            auto_approve_deadline = (created + timedelta(days=auto_approve_days)).date().isoformat()
        except Exception:
            pass

    return render_template('buyer/return_detail.html', rr=rr, reasons=dict(_REASONS),
                           auto_approve_days=auto_approve_days,
                           auto_approve_deadline=auto_approve_deadline)


@buyer_bp.route('/orders/<order_id>/return', methods=['POST'])
@login_required
def submit_return(order_id):
    """Buyer submits a return/refund request for a delivered/completed order."""
    reason      = request.form.get('reason', '').strip()
    details     = request.form.get('details', '').strip()
    refund_type = request.form.get('refund_type', 'refund').strip()

    valid_reasons = {r[0] for r in _REASONS}
    if reason not in valid_reasons:
        flash('Please select a valid reason.', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    if refund_type not in ('refund', 'return_and_refund'):
        refund_type = 'refund'

    # Fetch the order
    try:
        order = (supabase.table('orders').select('id,status,buyer_id,seller_id')
                 .eq('id', order_id).eq('buyer_id', current_user.id)
                 .single().execute().data)
    except Exception:
        order = None

    if not order:
        abort(404)

    if order.get('status') not in ('delivered', 'completed'):
        flash('You can only request a return for delivered or completed orders.', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    # Check for existing active return request
    try:
        existing = (supabase.table('return_requests')
                    .select('id,status').eq('order_id', order_id)
                    .not_.in_('status', ['admin_rejected', 'seller_rejected'])
                    .execute().data or [])
    except Exception:
        existing = []

    if existing:
        flash('A return request is already active for this order.', 'warning')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    # Handle evidence file uploads
    evidence_files = []
    uploaded_files = request.files.getlist('evidence_files')
    if uploaded_files:
        try:
            evidence_files = _save_evidence_files(uploaded_files, order_id)
        except Exception as e:
            flash(f'Warning: could not save some attachments — {e}', 'warning')

    try:
        result = supabase.table('return_requests').insert({
            'order_id':       order_id,
            'buyer_id':       current_user.id,
            'seller_id':      order['seller_id'],
            'reason':         reason,
            'details':        details or None,
            'refund_type':    refund_type,
            'status':         'pending',
            'evidence_files': evidence_files,   # list → JSONB
        }).execute()
        rr_id = result.data[0]['id'] if result.data else None
        flash('Request Submitted||The seller will review your return/refund request shortly.', 'success')
        push_return_submitted(order_id, order['seller_id'], rr_id=rr_id)
        if rr_id:
            notify_return_submitted(rr_id)
            return redirect(url_for('buyer.return_detail', rr_id=rr_id))
    except Exception as e:
        flash(f'Could not submit request: {e}', 'error')

    return redirect(url_for('buyer.order_detail', order_id=order_id))


@buyer_bp.route('/returns/<rr_id>/escalate', methods=['POST'])
@login_required
def escalate_return(rr_id):
    """Buyer escalates a seller-rejected request to admin."""
    try:
        rr = (supabase.table('return_requests')
              .select('id,status,buyer_id')
              .eq('id', rr_id).eq('buyer_id', current_user.id)
              .single().execute().data)
    except Exception:
        rr = None

    if not rr:
        abort(404)

    if rr.get('status') != 'seller_rejected':
        flash('Only seller-rejected requests can be escalated to admin.', 'warning')
        return redirect(url_for('buyer.return_detail', rr_id=rr_id))

    try:
        supabase.table('return_requests').update({'status': 'escalated'}).eq('id', rr_id).execute()
        flash('Escalated to Admin||Our team will review your dispute and get back to you.', 'info')
        notify_return_escalated(rr_id)
        # Re-notify all admins about escalation
        from app.services.notify import push_return_submitted
        try:
            from app.extensions import supabase_admin as _supa
            rr_data = _supa.table('return_requests').select('order_id, seller_id').eq('id', rr_id).single().execute().data
            if rr_data:
                admins = _supa.table('profiles').select('id').eq('role', 'admin').execute().data or []
                for admin in admins:
                    from app.services.notify import push
                    short_id = str(rr_data.get('order_id', ''))[:8].upper()
                    push(admin['id'], 'return_submitted',
                         f'Escalated Return \u2014 #{short_id}',
                         'A buyer has escalated a return dispute for admin review.',
                         data={'order_id': rr_data.get('order_id'),
                               'rr_id': rr_id,
                               'url': f'/admin/returns/{rr_id}'})
        except Exception:
            pass
    except Exception as e:
        flash(f'Could not escalate: {e}', 'error')

    return redirect(url_for('buyer.return_detail', rr_id=rr_id))
