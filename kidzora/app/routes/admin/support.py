"""Admin – Support Tickets queue."""
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app.extensions import supabase_admin as supabase
from app.services.notify import push
from .utils import admin_bp, admin_required

_STATUS_LABELS = {
    'open':        ('Open',        'primary'),
    'in_progress': ('In Progress', 'warning'),
    'resolved':    ('Resolved',    'success'),
    'closed':      ('Closed',      'secondary'),
}

_PRIORITY_LABELS = {
    'low':    ('Low',    'secondary'),
    'medium': ('Medium', 'info'),
    'high':   ('High',   'warning'),
    'urgent': ('Urgent', 'danger'),
}

_CATEGORY_LABELS = {
    'order':    'Order Issue',
    'payment':  'Payment / Billing',
    'return':   'Return / Refund',
    'account':  'Account / Profile',
    'product':  'Product Question',
    'delivery': 'Delivery Problem',
    'other':    'Other',
}


def _enrich(ticket: dict) -> dict:
    sl, sc = _STATUS_LABELS.get(ticket.get('status', 'open'), ('Open', 'primary'))
    pl, pc = _PRIORITY_LABELS.get(ticket.get('priority', 'medium'), ('Medium', 'info'))
    ticket['status_label']   = sl
    ticket['status_color']   = sc
    ticket['priority_label'] = pl
    ticket['priority_color'] = pc
    ticket['category_label'] = _CATEGORY_LABELS.get(ticket.get('category', 'other'), 'Other')
    return ticket


# ── Admin Ticket Queue ────────────────────────────────────────────────────────

@admin_bp.route('/support')
@admin_required
def support_tickets():
    status_filter   = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    category_filter = request.args.get('category', '')

    tickets = []
    try:
        q = supabase.table('support_tickets').select(
            'id,buyer_id,subject,category,status,priority,created_at,updated_at'
        )
        if status_filter:
            q = q.eq('status', status_filter)
        if priority_filter:
            q = q.eq('priority', priority_filter)
        if category_filter:
            q = q.eq('category', category_filter)

        rows = q.order('updated_at', desc=True).limit(200).execute().data or []

        # Bulk-fetch buyer profiles
        buyer_ids = list({r['buyer_id'] for r in rows})
        prof_map: dict[str, dict] = {}
        if buyer_ids:
            prows = (supabase.table('profiles')
                     .select('id,first_name,last_name,email,avatar_url')
                     .in_('id', buyer_ids)
                     .execute().data or [])
            prof_map = {p['id']: p for p in prows}

        for t in rows:
            prof = prof_map.get(t['buyer_id'], {})
            t['buyer_name']  = f"{prof.get('first_name','')} {prof.get('last_name','')}".strip() or 'Unknown'
            t['buyer_email'] = prof.get('email', '')
            _enrich(t)

        tickets = rows
    except Exception as e:
        print(f'[admin.support_tickets] {e}')

    # Count by status for summary pills
    counts = {'open': 0, 'in_progress': 0, 'resolved': 0, 'closed': 0}
    for t in tickets:
        s = t.get('status', 'open')
        if s in counts:
            counts[s] += 1

    return render_template('admin/support.html',
                           tickets=tickets,
                           counts=counts,
                           status_filter=status_filter,
                           priority_filter=priority_filter,
                           category_filter=category_filter,
                           status_labels=_STATUS_LABELS,
                           priority_labels=_PRIORITY_LABELS,
                           category_labels=_CATEGORY_LABELS)


# ── Admin Ticket Detail + Reply ───────────────────────────────────────────────

@admin_bp.route('/support/<ticket_id>', methods=['GET', 'POST'])
@admin_required
def support_detail(ticket_id):
    try:
        ticket_r = (supabase.table('support_tickets')
                    .select('*')
                    .eq('id', ticket_id)
                    .single()
                    .execute())
        ticket = ticket_r.data
    except Exception:
        abort(404)

    if not ticket:
        abort(404)

    # Fetch buyer profile
    buyer = {}
    try:
        br = (supabase.table('profiles')
              .select('id,first_name,last_name,email,avatar_url')
              .eq('id', ticket['buyer_id'])
              .single()
              .execute())
        buyer = br.data or {}
    except Exception:
        pass

    if request.method == 'POST':
        action = request.form.get('action', 'reply')

        # ── Status change ──────────────────────────────────────────────────
        if action == 'status':
            new_status = request.form.get('status', 'open')
            if new_status not in _STATUS_LABELS:
                flash('Invalid status.', 'danger')
                return redirect(url_for('admin.support_detail', ticket_id=ticket_id))
            try:
                supabase.table('support_tickets').update({'status': new_status}).eq('id', ticket_id).execute()
                push(
                    user_id=ticket['buyer_id'],
                    ntype='support_ticket_update',
                    title='Support Ticket Updated',
                    body=f'Your ticket "{ticket["subject"][:60]}" is now {_STATUS_LABELS[new_status][0]}.',
                    data={'url': url_for('buyer.support_detail', ticket_id=ticket_id),
                          'ticket_id': ticket_id},
                )
                flash(f'Status changed to {_STATUS_LABELS[new_status][0]}.', 'success')
            except Exception as e:
                print(f'[admin.support_detail status] {e}')
                flash('Failed to update status.', 'danger')
            return redirect(url_for('admin.support_detail', ticket_id=ticket_id))

        # ── Priority change ────────────────────────────────────────────────
        if action == 'priority':
            new_priority = request.form.get('priority', 'medium')
            if new_priority not in _PRIORITY_LABELS:
                flash('Invalid priority.', 'danger')
                return redirect(url_for('admin.support_detail', ticket_id=ticket_id))
            try:
                supabase.table('support_tickets').update({'priority': new_priority}).eq('id', ticket_id).execute()
                flash(f'Priority changed to {_PRIORITY_LABELS[new_priority][0]}.', 'success')
            except Exception as e:
                print(f'[admin.support_detail priority] {e}')
                flash('Failed to update priority.', 'danger')
            return redirect(url_for('admin.support_detail', ticket_id=ticket_id))

        # ── Admin reply ────────────────────────────────────────────────────
        content = request.form.get('content', '').strip()
        if not content:
            flash('Reply cannot be empty.', 'danger')
            return redirect(url_for('admin.support_detail', ticket_id=ticket_id))

        try:
            supabase.table('support_replies').insert({
                'ticket_id': ticket_id,
                'sender_id': current_user.id,
                'content':   content,
                'is_admin':  True,
            }).execute()

            # Auto-move open → in_progress on first admin reply
            if ticket.get('status') == 'open':
                supabase.table('support_tickets').update({'status': 'in_progress'}).eq('id', ticket_id).execute()

            # Notify buyer
            push(
                user_id=ticket['buyer_id'],
                ntype='support_ticket_reply',
                title='Support Reply from KidZora',
                body=content[:100],
                data={'url': url_for('buyer.support_detail', ticket_id=ticket_id),
                      'ticket_id': ticket_id},
            )
            flash('Reply sent to buyer.', 'success')
        except Exception as e:
            print(f'[admin.support_detail reply] {e}')
            flash('Failed to send reply.', 'danger')

        return redirect(url_for('admin.support_detail', ticket_id=ticket_id))

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
        print(f'[admin.support_detail GET] {e}')

    _enrich(ticket)
    buyer_name = f"{buyer.get('first_name','')} {buyer.get('last_name','')}".strip() or 'Unknown'

    return render_template('admin/support_detail.html',
                           ticket=ticket,
                           replies=replies,
                           buyer=buyer,
                           buyer_name=buyer_name,
                           status_labels=_STATUS_LABELS,
                           priority_labels=_PRIORITY_LABELS)
