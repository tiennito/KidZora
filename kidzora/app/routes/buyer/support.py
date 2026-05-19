"""Buyer – Support Tickets (Help Desk)."""
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app.extensions import supabase_admin as supabase
from app.services.notify import push
from .utils import buyer_bp, buyer_required

_CATEGORIES = [
    ('order',    'Order Issue'),
    ('payment',  'Payment / Billing'),
    ('return',   'Return / Refund'),
    ('account',  'Account / Profile'),
    ('product',  'Product Question'),
    ('delivery', 'Delivery Problem'),
    ('other',    'Other'),
]

_STATUS_LABELS = {
    'open':        ('Open',        'primary'),
    'in_progress': ('In Progress', 'warning'),
    'resolved':    ('Resolved',    'success'),
    'closed':      ('Closed',      'secondary'),
}


def _get_admin_id():
    """Return the profile id of any admin user (used for notifications)."""
    try:
        r = supabase.table('profiles').select('id').eq('role', 'admin').limit(1).execute()
        return r.data[0]['id'] if r.data else None
    except Exception:
        return None


# ── List my tickets + create new ticket ──────────────────────────────────────

@buyer_bp.route('/support', methods=['GET', 'POST'])
@buyer_required
def support():
    if request.method == 'POST':
        subject  = request.form.get('subject', '').strip()
        category = request.form.get('category', 'other').strip()
        message  = request.form.get('message', '').strip()

        if not subject or not message:
            flash('Subject and message are required.', 'danger')
            return redirect(url_for('buyer.support'))

        if len(subject) > 200:
            flash('Subject must be 200 characters or fewer.', 'danger')
            return redirect(url_for('buyer.support'))

        if category not in dict(_CATEGORIES):
            category = 'other'

        try:
            now = datetime.now(timezone.utc).isoformat()

            # Create the ticket
            ticket_r = supabase.table('support_tickets').insert({
                'buyer_id': current_user.id,
                'subject':  subject,
                'category': category,
                'status':   'open',
                'priority': 'medium',
            }).execute()
            ticket = ticket_r.data[0] if ticket_r.data else {}
            ticket_id = ticket.get('id')

            if not ticket_id:
                raise RuntimeError('Ticket insert returned no id')

            # First reply = buyer's opening message
            supabase.table('support_replies').insert({
                'ticket_id': ticket_id,
                'sender_id': current_user.id,
                'content':   message,
                'is_admin':  False,
            }).execute()

            # Notify admin
            admin_id = _get_admin_id()
            if admin_id:
                push(
                    user_id=admin_id,
                    ntype='support_ticket_new',
                    title='New Support Ticket',
                    body=f'{current_user.first_name} ({current_user.email}): {subject[:80]}',
                    data={'url': url_for('admin.support_detail', ticket_id=ticket_id),
                          'ticket_id': ticket_id},
                )

            flash('Your support ticket has been submitted. We\'ll get back to you soon!', 'success')
            return redirect(url_for('buyer.support_detail', ticket_id=ticket_id))

        except Exception as e:
            print(f'[buyer.support POST] {e}')
            flash('Failed to submit ticket. Please try again.', 'danger')
            return redirect(url_for('buyer.support'))

    # GET — list my tickets
    tickets = []
    try:
        rows = (supabase.table('support_tickets')
                .select('id,subject,category,status,priority,created_at,updated_at')
                .eq('buyer_id', current_user.id)
                .order('updated_at', desc=True)
                .execute().data or [])

        for t in rows:
            label, color = _STATUS_LABELS.get(t.get('status', 'open'), ('Open', 'primary'))
            t['status_label'] = label
            t['status_color'] = color
            cat_map = dict(_CATEGORIES)
            t['category_label'] = cat_map.get(t.get('category', 'other'), 'Other')

        tickets = rows
    except Exception as e:
        print(f'[buyer.support GET] {e}')

    return render_template('buyer/support.html',
                           tickets=tickets,
                           categories=_CATEGORIES)


# ── Ticket detail + reply ─────────────────────────────────────────────────────

@buyer_bp.route('/support/<ticket_id>', methods=['GET', 'POST'])
@buyer_required
def support_detail(ticket_id):
    # Load ticket (must belong to this buyer)
    try:
        ticket_r = (supabase.table('support_tickets')
                    .select('*')
                    .eq('id', ticket_id)
                    .eq('buyer_id', current_user.id)
                    .single()
                    .execute())
        ticket = ticket_r.data
    except Exception:
        abort(404)

    if not ticket:
        abort(404)

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('Reply cannot be empty.', 'danger')
            return redirect(url_for('buyer.support_detail', ticket_id=ticket_id))

        if ticket.get('status') in ('resolved', 'closed'):
            flash('This ticket is closed. Please open a new ticket if you need more help.', 'warning')
            return redirect(url_for('buyer.support_detail', ticket_id=ticket_id))

        try:
            supabase.table('support_replies').insert({
                'ticket_id': ticket_id,
                'sender_id': current_user.id,
                'content':   content,
                'is_admin':  False,
            }).execute()

            # Reopen if resolved so admin knows buyer needs more help
            if ticket.get('status') == 'resolved':
                supabase.table('support_tickets').update({'status': 'open'}).eq('id', ticket_id).execute()

            # Notify admin
            admin_id = _get_admin_id()
            if admin_id:
                push(
                    user_id=admin_id,
                    ntype='support_ticket_reply',
                    title='Buyer Replied to Ticket',
                    body=f'{current_user.first_name}: {content[:80]}',
                    data={'url': url_for('admin.support_detail', ticket_id=ticket_id),
                          'ticket_id': ticket_id},
                )

            flash('Reply sent.', 'success')
        except Exception as e:
            print(f'[buyer.support_detail POST] {e}')
            flash('Failed to send reply.', 'danger')

        return redirect(url_for('buyer.support_detail', ticket_id=ticket_id))

    # GET — load replies
    replies = []
    try:
        rep_r = (supabase.table('support_replies')
                 .select('id,sender_id,content,is_admin,created_at')
                 .eq('ticket_id', ticket_id)
                 .order('created_at', desc=False)
                 .execute())
        replies = rep_r.data or []
    except Exception as e:
        print(f'[buyer.support_detail GET replies] {e}')

    label, color = _STATUS_LABELS.get(ticket.get('status', 'open'), ('Open', 'primary'))
    ticket['status_label'] = label
    ticket['status_color'] = color
    cat_map = dict(_CATEGORIES)
    ticket['category_label'] = cat_map.get(ticket.get('category', 'other'), 'Other')

    is_closed = ticket.get('status') in ('resolved', 'closed')

    return render_template('buyer/support_detail.html',
                           ticket=ticket,
                           replies=replies,
                           is_closed=is_closed)
