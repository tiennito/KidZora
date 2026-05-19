"""Buyer orders route."""
from flask import render_template, flash, abort, redirect, url_for, request
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.email import notify_order_status, notify_cancel_requested
from app.services.notify import push_order_event
from app.utils.pagination import paginate_query
from app.utils.settings import get_commission_rate
from .utils import buyer_bp


@buyer_bp.route('/orders')
@login_required
def orders():
    """Redirect to dashboard with purchases tab active."""
    return redirect(url_for('buyer.dashboard', tab='purchases'))


@buyer_bp.route('/orders/<order_id>')
@login_required
def order_detail(order_id):
    try:
        # Fetch the order (ensure it belongs to this buyer)
        o_res = supabase.table('orders').select('*').eq('id', order_id).eq('buyer_id', current_user.id).single().execute()
        order = o_res.data
    except Exception:
        order = None

    if not order:
        abort(404)

    try:
        items_res = supabase.table('order_items') \
            .select('*, products(name, images), product_variants(name)') \
            .eq('order_id', order_id) \
            .execute()
        items = items_res.data or []
    except Exception as e:
        flash(f'Could not load order items: {e}', 'warning')
        items = []

    # Fetch existing return request (if any)
    try:
        rr_res = (supabase.table('return_requests').select('id,status,reason,refund_type')
                  .eq('order_id', order_id).eq('buyer_id', current_user.id)
                  .order('created_at', desc=True).limit(1).execute().data or [])
        return_request = rr_res[0] if rr_res else None
    except Exception:
        return_request = None

    # Status progression for tracker
    STATUS_STEPS = [
        ('pending',           'fas fa-clock',           'Order Placed'),
        ('confirmed',         'fas fa-check-circle',    'Confirmed'),
        ('preparing',         'fas fa-box',             'Preparing'),
        ('ready_for_pickup',  'fas fa-store',           'Ready for Pickup'),
        ('out_for_delivery',  'fas fa-motorcycle',      'Out for Delivery'),
        ('delivered',         'fas fa-house-user',      'Delivered'),
        ('completed',         'fas fa-star',            'Completed'),
    ]

    # Per-step descriptions shown in the vertical activity timeline
    STEP_DETAILS = {
        'pending':           ('Your order has been placed and is waiting for the seller to confirm.',
                              'Waiting for seller confirmation…'),
        'confirmed':         ('The seller has confirmed your order and will begin preparing it.',
                              'Seller is getting started on your order…'),
        'preparing':         ('The seller is packing and preparing your items for shipment.',
                              'Your items are being carefully packed…'),
        'ready_for_pickup':  ('Your order is packed and ready! A rider will pick it up soon.',
                              'Waiting for a rider to pick up…'),
        'out_for_delivery':  ('A rider has picked up your order and is heading to your address.',
                              'Rider is on the way to you…'),
        'delivered':         ('Your order has been delivered. Please confirm receipt to complete the transaction.',
                              'Awaiting your confirmation…'),
        'completed':         ('Order complete! You have confirmed receipt.',
                              'All done — thank you for shopping with KidZora!'),
    }

    current_status = order.get('status', 'pending')
    status_indices = {s[0]: i for i, s in enumerate(STATUS_STEPS)}
    current_idx = status_indices.get(current_status, 0)

    # Fetch rider profile if one is assigned
    rider = None
    rider_id = order.get('rider_id')
    if rider_id:
        try:
            rider_res = supabase.table('profiles') \
                .select('first_name, last_name, phone, avatar_url') \
                .eq('id', rider_id).single().execute()
            rider = rider_res.data
        except Exception:
            pass

    # Fetch existing rider rating (if any) so the form can show it was submitted
    rider_rating = None
    if order.get('rider_id') and current_status in ('delivered', 'completed'):
        try:
            rrat = supabase.table('rider_ratings') \
                .select('id,rating,feedback') \
                .eq('order_id', order_id) \
                .eq('buyer_id', current_user.id) \
                .execute().data
            rider_rating = rrat[0] if rrat else None
        except Exception:
            pass

    return render_template(
        'buyer/order_detail.html',
        order=order,
        items=items,
        status_steps=STATUS_STEPS,
        step_details=STEP_DETAILS,
        current_idx=current_idx,
        is_cancelled=(current_status == 'cancelled'),
        return_request=return_request,
        rider=rider,
        rider_rating=rider_rating,
    )


@buyer_bp.route('/orders/<order_id>/rate-rider', methods=['POST'])
@login_required
def rate_rider(order_id):
    """Submit or update a rider rating for a delivered/completed order."""
    # Verify order belongs to this buyer and has a rider
    try:
        o = supabase.table('orders') \
            .select('id,rider_id,status,buyer_id') \
            .eq('id', order_id) \
            .eq('buyer_id', current_user.id) \
            .single().execute().data
    except Exception:
        o = None

    if not o or not o.get('rider_id'):
        flash('Order not found or no rider assigned.', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    if o.get('status') not in ('delivered', 'completed'):
        flash('You can only rate a rider after the order is delivered.', 'warning')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    rating_str = request.form.get('rider_rating', '').strip()
    feedback   = (request.form.get('rider_feedback') or '').strip()[:500]

    try:
        rating = int(rating_str)
    except (ValueError, TypeError):
        rating = 0

    if rating not in range(1, 6):
        flash('Please choose a star rating (1–5).', 'warning')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    # Fetch the riders.id from the rider_id (which is riders.id on orders)
    rider_id = o['rider_id']

    try:
        # Upsert: one rating per order
        supabase.table('rider_ratings').upsert({
            'order_id': order_id,
            'rider_id': rider_id,
            'buyer_id': current_user.id,
            'rating':   rating,
            'feedback': feedback or None,
        }, on_conflict='order_id').execute()
        flash('Rider Rated!||Thank you for your feedback.', 'success')
    except Exception as e:
        flash(f'Could not save rating||{e}', 'error')

    return redirect(url_for('buyer.order_detail', order_id=order_id))


@buyer_bp.route('/orders/<order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """
    Buyer cancels an order.
      - status == 'pending'   → immediate cancel, no seller approval needed
      - status == 'confirmed' → create a cancel request for seller to approve/reject
      - anything else         → not allowed
    """
    reason = request.form.get('reason', '').strip()

    try:
        order = supabase.table('orders').select('id,status,buyer_id,cancel_requested') \
            .eq('id', order_id).eq('buyer_id', current_user.id).single().execute().data
    except Exception:
        order = None

    if not order:
        abort(404)

    status = order.get('status')

    # Guard: already pending cancel or wrong stage
    if order.get('cancel_requested'):
        flash('A cancellation request is already pending for this order.', 'warning')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    if status not in ('pending', 'confirmed'):
        flash('This order cannot be cancelled at its current stage.', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    try:
        if status == 'pending':
            # Immediate cancel — no seller involvement needed
            supabase.table('orders').update({
                'status': 'cancelled',
                'cancel_reason': reason or 'Buyer cancelled order.',
                'cancel_requested': True,
                'cancel_status': 'approved',
            }).eq('id', order_id).execute()
            flash('Order Cancelled||Your order has been successfully cancelled.', 'success')
            notify_order_status(order_id, 'cancelled')
            push_order_event(order_id, 'order_cancelled')

        else:  # confirmed
            if not reason:
                flash('Please provide a reason for the cancellation request.', 'error')
                return redirect(url_for('buyer.order_detail', order_id=order_id))
            supabase.table('orders').update({
                'cancel_requested': True,
                'cancel_reason': reason,
                'cancel_status': 'pending_review',
            }).eq('id', order_id).execute()
            flash('Request Submitted||The seller will review your cancellation request shortly.', 'info')
            notify_cancel_requested(order_id, reason)
            push_order_event(order_id, 'cancel_request')

    except Exception as e:
        flash(f'Could not process cancellation: {e}', 'error')

    return redirect(url_for('buyer.order_detail', order_id=order_id))


@buyer_bp.route('/orders/<order_id>/confirm-receipt', methods=['POST'])
@login_required
def confirm_receipt(order_id):
    """Buyer confirms they received the order (delivered → completed)."""
    try:
        order = supabase.table('orders') \
            .select('id,status,buyer_id,total_amount,seller_id') \
            .eq('id', order_id).eq('buyer_id', current_user.id).single().execute().data
    except Exception:
        order = None

    if not order:
        abort(404)

    if order.get('status') != 'delivered':
        flash('This order cannot be confirmed at this stage.', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    try:
        supabase.table('orders').update({'status': 'completed'}).eq('id', order_id).execute()
        # Record commission transaction
        try:
            from app.models.transaction import Transaction
            amount     = float(order.get('total_amount') or 0)
            commission = round(amount * get_commission_rate(), 2)
            Transaction.create({
                'order_id':         order_id,
                'seller_id':        order.get('seller_id'),
                'amount':           amount,
                'commission_amount':commission,
                'seller_earnings':  round(amount - commission, 2),
                'type':             'commission',
                'status':           'completed',
            })
        except Exception:
            pass  # commission logging failure never blocks the buyer
        flash('Order Received!||Thank you for confirming. Your order is now complete.', 'success')
        push_order_event(order_id, 'completed')

        # ── Optional inline review saving (skipped if buyer chose "Skip") ──
        if not request.form.get('skip_review'):
            try:
                items_res = supabase.table('order_items') \
                    .select('product_id, variant_id') \
                    .eq('order_id', order_id).execute()
                order_items_data = items_res.data or []
                for oi in order_items_data:
                    pid = oi.get('product_id')
                    if not pid:
                        continue
                    rating_str = request.form.get(f'rating_{pid}', '').strip()
                    if not rating_str:
                        continue
                    try:
                        rating = int(rating_str)
                    except ValueError:
                        continue
                    if not (1 <= rating <= 5):
                        continue
                    title      = request.form.get(f'title_{pid}', '').strip() or None
                    body       = request.form.get(f'body_{pid}', '').strip() or None
                    variant_id = (request.form.get(f'variant_id_{pid}', '').strip()
                                  or oi.get('variant_id') or None)
                    variant_name = None
                    if variant_id:
                        try:
                            vn_res = supabase.table('product_variants').select('name') \
                                .eq('id', variant_id).single().execute().data
                            variant_name = vn_res.get('name') if vn_res else None
                        except Exception:
                            pass
                    supabase.table('product_reviews').upsert({
                        'product_id':           pid,
                        'buyer_id':             current_user.id,
                        'order_id':             order_id,
                        'rating':               rating,
                        'title':                title,
                        'body':                 body,
                        'is_verified_purchase': True,
                        'variant_id':           variant_id,
                        'variant_name':         variant_name,
                        'media_urls':           [],
                    }, on_conflict='product_id,buyer_id').execute()
            except Exception:
                pass  # review failures never block order completion
    except Exception as e:
        flash(f'Could not confirm receipt: {e}', 'error')

    return redirect(url_for('buyer.order_detail', order_id=order_id))


@buyer_bp.route('/orders/<order_id>/reorder', methods=['POST'])
@login_required
def reorder(order_id):
    """Add all items from a past order back into the cart.

    Items that are out of stock or no longer available are skipped with a warning.
    At least one item must be addable; otherwise the buyer stays on the order detail page.
    """
    from .cart import _get_cart, _save_cart

    try:
        order = supabase.table('orders') \
            .select('id,buyer_id') \
            .eq('id', order_id).eq('buyer_id', current_user.id).single().execute().data
    except Exception:
        order = None

    if not order:
        abort(404)

    try:
        items = supabase.table('order_items') \
            .select('product_id, variant_id, quantity, price') \
            .eq('order_id', order_id).execute().data or []
    except Exception as e:
        flash(f'Could not load order items: {e}', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    cart = _get_cart()
    added = 0
    skipped = []

    for item in items:
        pid        = item.get('product_id')
        variant_id = item.get('variant_id')
        qty        = max(1, item.get('quantity') or 1)

        if not pid:
            continue

        # Fetch current product state
        try:
            p = supabase.table('products').select(
                'id,name,price,images,stock_quantity,is_active,seller_id'
            ).eq('id', pid).single().execute().data
        except Exception:
            p = None

        if not p or not p.get('is_active'):
            skipped.append(item.get('name') or 'A product')
            continue

        # Determine stock and variant name
        variant_name = None
        available    = p.get('stock_quantity') or 0

        if variant_id:
            try:
                vdata = supabase.table('product_variants').select(
                    'id,name,stock_quantity'
                ).eq('id', variant_id).single().execute().data
            except Exception:
                vdata = None

            if not vdata:
                skipped.append(p['name'])
                continue
            available    = vdata.get('stock_quantity') or 0
            variant_name = vdata['name']

        if available == 0:
            skipped.append(p['name'] + (f' ({variant_name})' if variant_name else ''))
            continue

        cart_key   = f"{pid}_{variant_id or ''}"
        imgs       = p.get('images') or []
        qty_to_add = min(qty, available)

        if cart_key in cart:
            cart[cart_key]['qty'] = min(cart[cart_key]['qty'] + qty_to_add, available)
        else:
            cart[cart_key] = {
                'product_id':   pid,
                'variant_id':   variant_id,
                'variant_name': variant_name,
                'qty':          qty_to_add,
                'name':         p['name'],
                'price':        float(p['price']),
                'image_url':    imgs[0] if imgs else None,
                'seller_id':    p.get('seller_id'),
                'stock':        available,
            }
        added += 1

    if skipped:
        names  = ', '.join(f'"{s}"' for s in skipped[:3])
        suffix = f' and {len(skipped) - 3} more' if len(skipped) > 3 else ''
        flash(f'Some items unavailable||{names}{suffix} could not be added (out of stock or removed).', 'warning')

    if added == 0:
        flash('Nothing to reorder||All items from this order are currently unavailable.', 'error')
        return redirect(url_for('buyer.order_detail', order_id=order_id))

    _save_cart(cart)
    flash(f'Added to Cart!||{added} item{"s" if added > 1 else ""} from your previous order have been added to your cart.', 'success')
    return redirect(url_for('buyer.cart'))
