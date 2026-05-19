"""Seller order routes."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.email import (
    notify_order_status,
    notify_cancel_approved,
    notify_cancel_rejected,
)
from app.services.notify import push_order_event, push, push_new_pickup
from app.utils.pagination import paginate_list
from .utils import seller_bp, seller_required, _get_seller_id

_STATUSES = [
    'pending', 'confirmed', 'preparing',
    'ready_for_pickup', 'out_for_delivery',
    'delivered', 'cancelled',
]
# completed is set by the buyer only — not listed as a seller-settable status
_DISPLAY_STATUSES = _STATUSES + ['completed']


@seller_bp.route('/orders')
@login_required
@seller_required
def orders():
    status_filter = request.args.get('status', '')
    q             = request.args.get('q', '')

    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.dashboard'))

    try:
        query = supabase.table('orders').select('*').eq('seller_id', seller_id)
        if status_filter:
            query = query.eq('status', status_filter)
        order_list = query.order('created_at', desc=True).execute().data or []
        if q:
            order_list = [o for o in order_list if q.lower() in str(o.get('id', '')).lower()]
    except Exception as e:
        flash(f'Could not load orders: {e}', 'error')
        order_list = []

    pag = paginate_list(order_list, per_page=20)
    return render_template(
        'seller/orders.html',
        orders=pag.items,
        pagination=pag,
        statuses=_STATUSES,
        selected_status=status_filter,
        q=q,
    )


@seller_bp.route('/orders/<order_id>')
@login_required
@seller_required
def order_detail(order_id):
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.orders'))

    try:
        order = (supabase.table('orders').select('*')
                 .eq('id', order_id).eq('seller_id', seller_id)
                 .single().execute().data)
    except Exception:
        order = None

    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('seller.orders'))

    try:
        items = (supabase.table('order_items')
                 .select('*, products(name, images), product_variants(name)')
                 .eq('order_id', order_id).execute().data or [])
    except Exception:
        items = []

    # ── Rider chat info (only when a rider is assigned) ───────────────────
    rider_profile_id = None
    rider_name       = None
    rider_messages   = []

    if order.get('rider_id'):
        try:
            rider_row = (supabase.table('riders')
                         .select('user_id, profiles(first_name, last_name, avatar_url)')
                         .eq('id', order['rider_id'])
                         .single().execute().data)
            if rider_row:
                rider_profile_id = rider_row.get('user_id')
                prof = rider_row.get('profiles') or {}
                rider_name = (
                    f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip()
                    or 'Rider'
                )
        except Exception:
            pass

        if rider_profile_id:
            try:
                uid = current_user.id
                rider_messages = (
                    supabase.table('messages').select('*')
                    .or_(
                        f'and(sender_id.eq.{uid},receiver_id.eq.{rider_profile_id}),'
                        f'and(sender_id.eq.{rider_profile_id},receiver_id.eq.{uid})'
                    )
                    .order('created_at', desc=False).limit(50).execute().data or []
                )
            except Exception:
                rider_messages = []

    return render_template('seller/order_detail.html',
                           order=order, items=items, statuses=_STATUSES,
                           rider_profile_id=rider_profile_id,
                           rider_name=rider_name,
                           rider_messages=rider_messages)


@seller_bp.route('/orders/<order_id>/status', methods=['POST'])
@login_required
@seller_required
def order_status(order_id):
    new_status = request.form.get('status', '').strip()
    if not new_status:
        flash('No status provided.', 'error')
        return redirect(url_for('seller.order_detail', order_id=order_id))

    if new_status not in _STATUSES:
        flash(f'Invalid status "{new_status}".', 'error')
        return redirect(url_for('seller.order_detail', order_id=order_id))

    try:
        (supabase.table('orders').update({'status': new_status})
         .eq('id', order_id).eq('seller_id', _get_seller_id() or current_user.id).execute())
        flash(f'Status Updated||Order status has been changed to "{new_status}".', 'success')
        notify_order_status(order_id, new_status)
        push_order_event(order_id, new_status)
        if new_status == 'ready_for_pickup':
            try:
                _order = supabase.table('orders').select('sellers(shop_name)') \
                    .eq('id', order_id).single().execute().data
                _shop = (_order.get('sellers') or {}).get('shop_name', 'a seller') if _order else 'a seller'
                push_new_pickup(order_id, _shop)
            except Exception:
                pass
        # Push a notification to the seller themselves so the bell panel has a URL
        try:
            short_id = str(order_id)[:8].upper()
            push(
                user_id=current_user.id,
                ntype='order_confirmed',  # reuse success state
                title=f'Status Updated \u2014 #{short_id}',
                body=f'Order status has been changed to "{new_status}".',
                data={'order_id': order_id, 'url': f'/seller/orders/{order_id}'},
            )
        except Exception:
            pass
    except Exception as e:
        flash(f'Could not update status: {e}', 'error')

    return redirect(url_for('seller.order_detail', order_id=order_id))


@seller_bp.route('/orders/<order_id>/cancel-approve', methods=['POST'])
@login_required
@seller_required
def cancel_approve(order_id):
    """Seller approves a buyer's cancellation request → order becomes cancelled."""
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.orders'))

    try:
        order = (supabase.table('orders').select('id,status,cancel_requested,cancel_status')
                 .eq('id', order_id).eq('seller_id', seller_id).single().execute().data)
    except Exception:
        order = None

    if not order or not order.get('cancel_requested') or order.get('cancel_status') != 'pending_review':
        flash('No pending cancellation request found for this order.', 'warning')
        return redirect(url_for('seller.order_detail', order_id=order_id))

    try:
        supabase.table('orders').update({
            'status': 'cancelled',
            'cancel_status': 'approved',
        }).eq('id', order_id).execute()
        flash('Cancellation Approved||The order has been cancelled and the buyer notified.', 'success')
        notify_cancel_approved(order_id)
        push_order_event(order_id, 'cancel_approved')
    except Exception as e:
        flash(f'Could not approve cancellation: {e}', 'error')

    return redirect(url_for('seller.order_detail', order_id=order_id))


@seller_bp.route('/orders/<order_id>/cancel-reject', methods=['POST'])
@login_required
@seller_required
def cancel_reject(order_id):
    """Seller rejects a buyer's cancellation request."""
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.orders'))

    response_msg = request.form.get('cancel_response', '').strip()

    try:
        order = (supabase.table('orders').select('id,cancel_requested,cancel_status')
                 .eq('id', order_id).eq('seller_id', seller_id).single().execute().data)
    except Exception:
        order = None

    if not order or not order.get('cancel_requested') or order.get('cancel_status') != 'pending_review':
        flash('No pending cancellation request found for this order.', 'warning')
        return redirect(url_for('seller.order_detail', order_id=order_id))

    try:
        supabase.table('orders').update({
            'cancel_status': 'rejected',
            'cancel_response': response_msg or 'Cancellation request rejected by seller.',
        }).eq('id', order_id).execute()
        flash('Request Rejected||The cancellation has been denied. The order will continue as normal.', 'info')
        notify_cancel_rejected(order_id, response_msg)
        push_order_event(order_id, 'cancel_rejected',
                         extra_body=response_msg or 'Your cancellation request was rejected.')
    except Exception as e:
        flash(f'Could not reject cancellation: {e}', 'error')

    return redirect(url_for('seller.order_detail', order_id=order_id))

