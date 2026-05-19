"""Rider deliveries routes — available pickups, active deliveries, detail, status."""
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.notify import push_order_event, push_message, push_seller_pickup_alert, push_seller_delivered_alert, push_rider_handback
from .utils import rider_bp, approved_rider_required, _get_rider_id, _get_rider_availability, _save_proof_photo


# ── Availability toggle ────────────────────────────────────────────────────────

@rider_bp.route('/toggle-availability', methods=['POST'])
@login_required
@approved_rider_required
def toggle_availability():
    current = _get_rider_availability()
    new_val = not current
    try:
        supabase.table('riders').update({'is_available': new_val}) \
            .eq('user_id', current_user.id).execute()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({'ok': True, 'is_available': new_val})


# ── Available orders (preparing + no rider yet) ────────────────────────────────

@rider_bp.route('/available')
@login_required
@approved_rider_required
def available():
    # Riders who are offline still CAN visit the page but see an offline banner.
    try:
        orders = (supabase.table('orders')
                  .select('*, sellers(shop_name, user_id)')
                  .eq('status', 'ready_for_pickup')
                  .is_('rider_id', 'null')
                  .order('created_at', desc=False)
                  .execute().data or [])
    except Exception as e:
        flash(f'Could not load available orders: {e}', 'error')
        orders = []

    # Attach first item thumbnail per order
    for order in orders:
        try:
            r = supabase.table('order_items') \
                .select('quantity, products(name, images)') \
                .eq('order_id', order['id']).limit(3).execute()
            order['_items'] = r.data or []
        except Exception:
            order['_items'] = []

    return render_template('rider/available.html', orders=orders)


@rider_bp.route('/available/<order_id>/accept', methods=['POST'])
@login_required
@approved_rider_required
def accept_order(order_id):
    rider_id = _get_rider_id()
    if not rider_id:
        flash('Rider profile not found. Please complete your profile.', 'error')
        return redirect(url_for('rider.available'))

    try:
        # Double-check it's still unassigned
        r = supabase.table('orders').select('id, rider_id, status') \
            .eq('id', order_id).single().execute()
        order = r.data
    except Exception:
        flash('Order not found.', 'error')
        return redirect(url_for('rider.available'))

    # Block offline riders from accepting orders
    if not _get_rider_availability():
        flash('Set yourself Online first before accepting deliveries.', 'warning')
        return redirect(url_for('rider.available'))

    if not order or order.get('rider_id') or order.get('status') != 'ready_for_pickup':
        flash('This order is no longer available.', 'warning')
        return redirect(url_for('rider.available'))

    try:
        supabase.table('orders').update({
            'rider_id':  rider_id,
            'status':    'rider_assigned',
        }).eq('id', order_id).execute()
        flash('Order Accepted!||Head to the seller to pick up the order, then tap "I\'ve Picked Up the Order".', 'success')
        push_order_event(order_id, 'rider_assigned')
    except Exception as e:
        flash(f'Could not accept order: {e}', 'error')

    return redirect(url_for('rider.delivery_detail', order_id=order_id))


# ── Confirm Pickup (rider physically collects the order from the seller) ──────

@rider_bp.route('/deliveries/<order_id>/pickup', methods=['POST'])
@login_required
@approved_rider_required
def confirm_pickup(order_id):
    """
    Rider clicks 'I've Picked Up the Order'.
    Transitions rider_assigned → out_for_delivery and notifies the seller.
    """
    rider_id = _get_rider_id()
    if not rider_id:
        flash('Rider profile not found.', 'error')
        return redirect(url_for('rider.deliveries'))

    try:
        order = supabase.table('orders') \
            .select('id, rider_id, status, sellers(user_id)') \
            .eq('id', order_id).single().execute().data
    except Exception:
        order = None

    if not order or order.get('rider_id') != rider_id or order.get('status') != 'rider_assigned':
        flash('This order cannot be marked as picked up.', 'warning')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    try:
        supabase.table('orders').update({
            'status':            'out_for_delivery',
            'rider_assigned_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', order_id).execute()
        flash('Picked Up!||The seller has been notified. Head to the customer to complete the delivery.', 'success')
        push_order_event(order_id, 'out_for_delivery')

        # Get rider name once for both alerts
        try:
            prof = supabase.table('profiles') \
                .select('first_name,last_name') \
                .eq('id', current_user.id).single().execute().data or {}
            _rider_name = (
                f"{prof.get('first_name','')}"
                f"{' ' + prof.get('last_name','') if prof.get('last_name') else ''}"
            ).strip() or 'A rider'
        except Exception:
            _rider_name = 'A rider'

        # Push seller pickup notification
        try:
            push_seller_pickup_alert(order_id, _rider_name)
        except Exception:
            pass

        # Auto-send chat message to seller
        try:
            _seller_uid = (order.get('sellers') or {}).get('user_id')
            if _seller_uid:
                _short = order_id[:8].upper()
                _msg = f"[Order #{_short}] I've picked up the order."
                try:
                    supabase.table('messages').insert({
                        'sender_id':   current_user.id,
                        'receiver_id': _seller_uid,
                        'content':     _msg,
                        'order_ref':   order_id,
                    }).execute()
                except Exception:
                    supabase.table('messages').insert({
                        'sender_id':   current_user.id,
                        'receiver_id': _seller_uid,
                        'content':     _msg,
                    }).execute()
                push_message(_seller_uid, f'Rider: {_rider_name}', _msg)
        except Exception:
            pass

    except Exception as e:
        flash(f'Could not update status: {e}', 'error')

    return redirect(url_for('rider.delivery_detail', order_id=order_id))


# ── Hand back / reject order ───────────────────────────────────────────────────

@rider_bp.route('/deliveries/<order_id>/hand-back', methods=['POST'])
@login_required
@approved_rider_required
def hand_back(order_id):
    """
    Rider returns an accepted order they cannot complete.
    Only allowed while status is 'rider_assigned' (before physical pickup).
    Resets the order to 'ready_for_pickup' so another rider can take it.
    """
    rider_id = _get_rider_id()
    if not rider_id:
        flash('Rider profile not found.', 'error')
        return redirect(url_for('rider.deliveries'))

    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason before returning the order.', 'error')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    try:
        order = supabase.table('orders') \
            .select('id, rider_id, status, sellers(user_id)') \
            .eq('id', order_id).single().execute().data
    except Exception:
        order = None

    if not order or order.get('rider_id') != rider_id or order.get('status') != 'rider_assigned':
        flash('This order cannot be returned at this stage.', 'warning')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    try:
        supabase.table('orders').update({
            'status':   'ready_for_pickup',
            'rider_id': None,
        }).eq('id', order_id).execute()
    except Exception as e:
        flash(f'Could not return the order: {e}', 'error')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    # Get rider name for notifications and chat messages
    try:
        prof = supabase.table('profiles') \
            .select('first_name,last_name') \
            .eq('id', current_user.id).single().execute().data or {}
        _rider_name = (
            f"{prof.get('first_name','')}"
            f"{' ' + prof.get('last_name','') if prof.get('last_name') else ''}"
        ).strip() or 'A rider'
    except Exception:
        _rider_name = 'A rider'

    # Push seller + buyer notifications
    try:
        push_rider_handback(order_id, _rider_name, reason)
    except Exception:
        pass

    # Auto-send chat message to seller explaining the return
    try:
        _seller_uid = (order.get('sellers') or {}).get('user_id')
        if _seller_uid:
            _short = order_id[:8].upper()
            _msg = f"[Order #{_short}] I was unable to complete this delivery. Reason: {reason}. The order has been returned to the pickup pool."
            try:
                supabase.table('messages').insert({
                    'sender_id':   current_user.id,
                    'receiver_id': _seller_uid,
                    'content':     _msg,
                    'order_ref':   order_id,
                }).execute()
            except Exception:
                supabase.table('messages').insert({
                    'sender_id':   current_user.id,
                    'receiver_id': _seller_uid,
                    'content':     _msg,
                }).execute()
            push_message(_seller_uid, f'Rider: {_rider_name}', _msg)
    except Exception:
        pass

    flash(
        'Order Returned||The order has been sent back to the pickup pool. The seller has been notified.',
        'info',
    )
    return redirect(url_for('rider.deliveries'))


# ── My Deliveries list ─────────────────────────────────────────────────────────

@rider_bp.route('/deliveries')
@login_required
@approved_rider_required
def deliveries():
    rider_id = _get_rider_id()
    tab = request.args.get('tab', 'active')   # active | history

    delivery_list = []
    if rider_id:
        try:
            q = supabase.table('orders').select('*').eq('rider_id', rider_id)
            if tab == 'history':
                q = q.in_('status', ['delivered', 'completed', 'cancelled'])
            else:
                q = q.in_('status', ['rider_assigned', 'out_for_delivery'])
            delivery_list = q.order('updated_at', desc=True).execute().data or []
        except Exception as e:
            flash(f'Could not load deliveries: {e}', 'error')

        for order in delivery_list:
            try:
                r = supabase.table('order_items') \
                    .select('quantity, products(name, images)') \
                    .eq('order_id', order['id']).limit(3).execute()
                order['_items'] = r.data or []
            except Exception:
                order['_items'] = []

    return render_template('rider/deliveries.html',
                           deliveries=delivery_list, tab=tab)


# ── Delivery detail ────────────────────────────────────────────────────────────

@rider_bp.route('/deliveries/<order_id>')
@login_required
@approved_rider_required
def delivery_detail(order_id):
    rider_id = _get_rider_id()

    # Allow viewing available (unassigned) orders too
    try:
        order = supabase.table('orders') \
            .select('*, sellers(shop_name, user_id)') \
            .eq('id', order_id).single().execute().data
    except Exception:
        order = None

    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('rider.deliveries'))

    # Guard: must be unassigned or assigned to this rider
    if order.get('rider_id') and order['rider_id'] != rider_id:
        flash('This order belongs to another rider.', 'error')
        return redirect(url_for('rider.deliveries'))

    try:
        items = supabase.table('order_items') \
            .select('*, products(name, images), product_variants(name)') \
            .eq('order_id', order_id).execute().data or []
    except Exception:
        items = []

    # Fetch chat messages for this order (messages tagged with order reference)
    messages = []
    seller_profile_id = None
    seller_data = order.get('sellers') or {}
    if seller_data:
        seller_profile_id = seller_data.get('user_id')

    if seller_profile_id:
        try:
            r = supabase.table('messages').select('*') \
                .or_(
                    f'and(sender_id.eq.{current_user.id},receiver_id.eq.{seller_profile_id}),'
                    f'and(sender_id.eq.{seller_profile_id},receiver_id.eq.{current_user.id})'
                ) \
                .eq('order_ref', order_id) \
                .order('created_at', desc=False).limit(50).execute()
            messages = r.data or []
        except Exception:
            messages = []

    return render_template('rider/delivery_detail.html',
                           order=order, items=items,
                           messages=messages,
                           seller_profile_id=seller_profile_id,
                           rider_id=rider_id)


# ── Mark as Delivered ──────────────────────────────────────────────────────────

@rider_bp.route('/deliveries/<order_id>/deliver', methods=['POST'])
@login_required
@approved_rider_required
def mark_delivered(order_id):
    rider_id = _get_rider_id()
    if not rider_id:
        flash('Rider profile not found.', 'error')
        return redirect(url_for('rider.deliveries'))

    # ── Proof-of-delivery photo (required) ────────────────────────────────────
    proof_file = request.files.get('proof_photo')
    if not proof_file or not proof_file.filename:
        flash('Proof of delivery photo is required.||Please take a photo of the delivered package before marking as delivered.', 'error')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    try:
        proof_url = _save_proof_photo(proof_file, order_id)
    except ValueError as upload_err:
        flash(f'Photo upload failed||{upload_err}', 'error')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    try:
        supabase.table('orders').update({
            'status':                 'delivered',
            'delivered_at':           datetime.now(timezone.utc).isoformat(),
            'proof_of_delivery_url':  proof_url,
        }).eq('id', order_id).eq('rider_id', rider_id).execute()
        flash('Delivered!||The order has been marked as delivered successfully.', 'success')
        push_order_event(order_id, 'delivered')
        # Notify the seller their order was delivered
        try:
            prof = supabase.table('profiles') \
                .select('first_name,last_name') \
                .eq('id', current_user.id).single().execute().data or {}
            _rider_name = f"{prof.get('first_name','')}{' '+prof.get('last_name','') if prof.get('last_name') else ''}".strip() or 'The rider'
            push_seller_delivered_alert(order_id, _rider_name)
        except Exception:
            pass
        # Auto-send chat message to seller
        try:
            _order_data = supabase.table('orders').select('sellers(user_id)') \
                .eq('id', order_id).single().execute().data or {}
            _seller_uid = (_order_data.get('sellers') or {}).get('user_id')
            if _seller_uid:
                _short = order_id[:8].upper()
                _msg = f"[Order #{_short}] Order has been delivered."
                try:
                    supabase.table('messages').insert({
                        'sender_id':   current_user.id,
                        'receiver_id': _seller_uid,
                        'content':     _msg,
                        'order_ref':   order_id,
                    }).execute()
                except Exception:
                    supabase.table('messages').insert({
                        'sender_id':   current_user.id,
                        'receiver_id': _seller_uid,
                        'content':     _msg,
                    }).execute()
                push_message(_seller_uid, f'Rider: {_rider_name}', _msg)
        except Exception:
            pass
    except Exception as e:
        flash(f'Could not update status: {e}', 'error')

    return redirect(url_for('rider.delivery_detail', order_id=order_id))


# ── Send message to seller ─────────────────────────────────────────────────────

@rider_bp.route('/deliveries/<order_id>/message', methods=['POST'])
@login_required
@approved_rider_required
def send_message(order_id):
    content = request.form.get('content', '').strip()
    seller_profile_id = request.form.get('seller_profile_id', '').strip()

    if not content or not seller_profile_id:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('rider.delivery_detail', order_id=order_id))

    try:
        supabase.table('messages').insert({
            'sender_id':   current_user.id,
            'receiver_id': seller_profile_id,
            'content':     content,
            'order_ref':   order_id,
        }).execute()
    except Exception:
        # Fallback: try without order_ref if column doesn't exist
        try:
            supabase.table('messages').insert({
                'sender_id':   current_user.id,
                'receiver_id': seller_profile_id,
                'content':     f'[Order #{order_id[:8].upper()}] {content}',
            }).execute()
        except Exception as e2:
            flash(f'Could not send message: {e2}', 'error')
            return redirect(url_for('rider.delivery_detail', order_id=order_id))

    flash('Message Sent||Your message has been delivered to the seller.', 'success')
    sender_name = current_user.get_full_name() or current_user.email or 'Rider'
    push_message(seller_profile_id, f'Rider: {sender_name}', content)
    return redirect(url_for('rider.delivery_detail', order_id=order_id))
