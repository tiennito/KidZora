"""
app/services/notify.py
──────────────────────
Central helper for inserting in-app notifications into the `notifications`
table.  All callers are fire-and-forget — a failure to push a notification
must never break the calling request.

Usage:
    from app.services.notify import push, push_order_event

    # Generic
    push(user_id='uuid...', ntype='message_received',
         title='New message from Admin',
         body='Hello, here is an update on your account.',
         data={'sender': 'admin'})

    # Pre-built helpers
    push_order_event(order_id='uuid...', event='order_confirmed')
"""

from __future__ import annotations

import traceback
from typing import Any

from app.extensions import supabase_admin as _supa
from app.services.email import notify_low_stock_email

# ── Low-level insert ──────────────────────────────────────────────────────────

def push(
    user_id: str,
    ntype: str,
    title: str,
    body: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Insert one notification row.  Silently swallows errors."""
    try:
        _supa.table('notifications').insert({
            'user_id': user_id,
            'type':    ntype,
            'title':   title,
            'body':    body or '',
            'data':    data or {},
        }).execute()
    except Exception:  # pragma: no cover
        traceback.print_exc()


# ── Order lifecycle helpers ───────────────────────────────────────────────────

# Maps order status → (notification type, who gets it, title template, body template)
# `{who}` values: 'buyer' | 'seller' | 'both'
_ORDER_EVENTS: dict[str, tuple[str, str, str, str]] = {
    'order_placed': (
        'order_placed', 'seller',
        'New Order Received',
        'A buyer just placed an order. Review it in your Orders page.',
    ),
    'order_confirmed': (
        'order_confirmed', 'buyer',
        'Order Confirmed',
        'Great news! Your order has been confirmed by the seller.',
    ),
    # seller sends 'confirmed' (short form)
    'confirmed': (
        'order_confirmed', 'buyer',
        'Order Confirmed',
        'Great news! Your order has been confirmed by the seller.',
    ),
    'order_preparing': (
        'order_preparing', 'buyer',
        'Order Being Prepared',
        'The seller is now preparing your order.',
    ),
    # seller sends 'preparing' (short form)
    'preparing': (
        'order_preparing', 'buyer',
        'Order Being Prepared',
        'The seller is now preparing your order.',
    ),
    'order_ready_for_pickup': (
        'order_ready_pickup', 'buyer',
        'Ready for Pickup',
        'Your order is ready and waiting for a rider to pick it up.',
    ),
    'ready_for_pickup': (
        'order_ready_pickup', 'buyer',
        'Ready for Pickup',
        'Your order is ready and waiting for a rider to pick it up.',
    ),
    'rider_assigned': (
        'rider_assigned', 'buyer',
        'Rider Assigned 🛵',
        'A rider has accepted your order and will pick it up from the seller shortly.',
    ),
    'order_out_for_delivery': (
        'order_out_delivery', 'buyer',
        'Out for Delivery 🛵',
        'Your order is on its way! A rider has picked it up.',
    ),
    'out_for_delivery': (
        'order_out_delivery', 'buyer',
        'Out for Delivery',
        'Your order is on its way! A rider has picked it up.',
    ),
    'order_delivered': (
        'order_delivered', 'buyer',
        'Order Delivered',
        'Your order has been delivered. Please confirm receipt to complete the order.',
    ),
    'delivered': (
        'order_delivered', 'buyer',
        'Order Delivered',
        'Your order has been delivered. Please confirm receipt to complete the order.',
    ),
    'order_completed': (
        'order_completed', 'seller',
        'Order Completed',
        'The buyer confirmed receipt of the order. Earnings have been recorded.',
    ),
    'completed': (
        'order_completed', 'seller',
        'Order Completed',
        'The buyer confirmed receipt of the order. Earnings have been recorded.',
    ),
    'order_cancelled': (
        'order_cancelled', 'both',
        'Order Cancelled',
        'The order has been cancelled.',
    ),
    'cancelled': (
        'order_cancelled', 'both',
        'Order Cancelled',
        'The order has been cancelled.',
    ),
    # Cancellation workflow
    'cancel_request': (
        'cancel_request', 'seller',
        'Cancellation Request',
        'A buyer has requested to cancel their order. Please review.',
    ),
    'cancel_approved': (
        'cancel_approved', 'buyer',
        'Cancellation Approved',
        'Your cancellation request has been approved. The order is now cancelled.',
    ),
    'cancel_rejected': (
        'cancel_rejected', 'buyer',
        'Cancellation Rejected',
        'Your cancellation request was rejected. The order will continue.',
    ),
}


def push_order_event(order_id: str, event: str, extra_body: str | None = None) -> None:
    """
    Look up the order, determine who to notify, and push the notification.
    `event` is one of the keys in `_ORDER_EVENTS` or a raw order status string.

    NOTE: orders.buyer_id  → profiles.id  (correct for push directly)
          orders.seller_id → sellers.id   (must resolve to sellers.user_id first)
    """
    try:
        order = _supa.table('orders').select('id, buyer_id, seller_id') \
            .eq('id', order_id).single().execute().data
        if not order:
            return
    except Exception:
        return

    cfg = _ORDER_EVENTS.get(event)
    if not cfg:
        return

    ntype, who, title, body = cfg
    if extra_body:
        body = extra_body

    short_id = str(order_id)[:8].upper()
    title = f'{title} — #{short_id}'

    if who in ('buyer', 'both') and order.get('buyer_id'):
        push(order['buyer_id'], ntype, title, body,
             data={'order_id': order_id, 'url': f'/buyer/orders/{order_id}'})

    if who in ('seller', 'both') and order.get('seller_id'):
        # seller_id in orders references sellers.id — resolve to profiles user_id
        try:
            seller_row = _supa.table('sellers').select('user_id') \
                .eq('id', order['seller_id']).single().execute().data
            seller_user_id = seller_row.get('user_id') if seller_row else None
        except Exception:
            seller_user_id = None
        if seller_user_id:
            push(seller_user_id, ntype, title, body,
                 data={'order_id': order_id, 'url': f'/seller/orders/{order_id}'})


# ── Message helpers ───────────────────────────────────────────────────────────

def push_message(
    receiver_id: str,
    sender_display: str,
    preview: str,
    url: str | None = None,
) -> None:
    """Notify a user that they received a new chat message."""
    # Truncate preview to 120 chars
    preview_short = preview[:120] + ('\u2026' if len(preview) > 120 else '')
    push(
        user_id=receiver_id,
        ntype='message_received',
        title=f'New message from {sender_display}',
        body=preview_short,
        data={'sender_name': sender_display, **(({'url': url}) if url else {})},
    )


# ── Return/refund helpers ─────────────────────────────────────────────────────

def push_return_submitted(order_id: str, seller_id: str, rr_id: str | None = None) -> None:
    """Notify seller and admin when a buyer submits a return request.
    seller_id may be sellers.id (shop row) — resolved to profiles.id internally."""
    short_id = str(order_id)[:8].upper()
    # Resolve sellers.id → profiles.id
    seller_user_id: str | None = None
    try:
        s_row = _supa.table('sellers').select('user_id').eq('id', seller_id).single().execute().data
        seller_user_id = s_row.get('user_id') if s_row else None
    except Exception:
        pass
    # Notify seller
    if seller_user_id:
        push(
            user_id=seller_user_id,
            ntype='return_submitted',
            title=f'Return Request \u2014 #{short_id}',
            body='A buyer has submitted a return/refund request for one of your orders.',
            data={'order_id': order_id,
                  **(({'rr_id': rr_id, 'url': f'/seller/returns/{rr_id}'}) if rr_id else {})},
        )
    # Notify all admins
    try:
        admins = _supa.table('profiles').select('id').eq('role', 'admin').execute().data or []
        for admin in admins:
            push(
                user_id=admin['id'],
                ntype='return_submitted',
                title=f'Return Request \u2014 #{short_id}',
                body='A buyer submitted a return/refund request. Please review.',
                data={'order_id': order_id,
                      **(({'rr_id': rr_id, 'url': f'/admin/returns/{rr_id}'}) if rr_id else {})},
            )
    except Exception:
        pass


def push_return_event(rr_id: str, new_status: str) -> None:
    """Convenience: look up buyer_id + order_id from rr_id, then push update."""
    try:
        rr = _supa.table('return_requests').select('buyer_id, order_id') \
            .eq('id', rr_id).single().execute().data
        if rr:
            push_return_updated(rr['buyer_id'], rr['order_id'], new_status, rr_id=rr_id)
    except Exception:
        traceback.print_exc()


def push_return_updated(buyer_id: str, order_id: str, new_status: str, rr_id: str | None = None) -> None:

    """Notify buyer when admin/seller updates their return request status."""
    short_id = str(order_id)[:8].upper()
    status_labels = {
        'pending':          'Your return request is under review.',
        'approved':         'Your return request has been approved. A refund will be processed.',
        'rejected':         'Your return request has been reviewed and was not approved.',
        'processing':       'Your refund is being processed.',
        'refunded':         'Your refund has been issued. Please check your payment method.',
        'escalated':        'Your return request has been escalated to the admin for review.',
    }
    body = status_labels.get(new_status, f'Your return request status: {new_status}.')
    push(
        user_id=buyer_id,
        ntype='return_updated',
        title=f'Return Update \u2014 #{short_id}',
        body=body,
        data={'order_id': order_id, 'status': new_status,
              **(({'rr_id': rr_id, 'url': f'/buyer/returns/{rr_id}'}) if rr_id else {})},
    )


# ── Low-stock / out-of-stock alerts ─────────────────────────────────────────

LOW_STOCK_THRESHOLD: int = 5  # Notify seller at this many units remaining or fewer


def push_low_stock(
    seller_id: str,
    product_id: str,
    product_name: str,
    stock_left: int,
    variant_name: str | None = None,
    email_alert: bool = True,
) -> None:
    """Notify a seller that a product (or variant) is low on stock or sold out.
    seller_id may be sellers.id (shop row) — resolved to profiles.id internally."""
    # Resolve sellers.id → profiles.id
    try:
        s_row = _supa.table('sellers').select('user_id').eq('id', seller_id).single().execute().data
        seller_user_id = s_row.get('user_id') if s_row else None
    except Exception:
        return
    if not seller_user_id:
        return
    label = f'{product_name} ({variant_name})' if variant_name else product_name
    if stock_left == 0:
        ntype = 'out_of_stock'
        title = f'Out of Stock — {label}'
        body  = (f'"{label}" is now out of stock. Update your inventory to '
                 f'continue selling.')
    else:
        ntype = 'low_stock'
        units = 'unit' if stock_left == 1 else 'units'
        title = f'Low Stock — {label}'
        body  = (f'"{label}" has only {stock_left} {units} remaining. '
                 f'Restock soon to avoid missed sales.')
    push(
        user_id=seller_user_id,
        ntype=ntype,
        title=title,
        body=body,
        data={
            'product_id': product_id,
            'stock_left': stock_left,
            'url': f'/seller/products/{product_id}/edit',
        },
    )
    
    # Send email alert
    if email_alert:
        try:
            notify_low_stock_email(
                seller_user_id=seller_user_id,
                product_id=product_id,
                product_name=product_name,
                stock_left=stock_left,
                variant_name=variant_name,
            )
        except Exception:
            pass  # Email failure should not break stock alert


# ── Seller-follow helpers ─────────────────────────────────────────────────────

def push_new_product(
    seller_id: str,
    product_id: str,
    product_name: str,
    shop_name: str,
) -> None:
    """Notify all followers of a seller when a new product is listed."""
    try:
        rows = _supa.table('seller_follows') \
            .select('buyer_id') \
            .eq('seller_id', seller_id) \
            .execute().data or []
    except Exception:
        return
    for row in rows:
        push(
            user_id=row['buyer_id'],
            ntype='new_product',
            title=f'New listing from {shop_name}',
            body=f'{shop_name} just listed: {product_name}',
            data={
                'seller_id':   seller_id,
                'product_id':  product_id,
                'url':         f'/buyer/product/{product_id}',
            },
        )


# ── New pickup alert for available riders ─────────────────────────────────────

def push_new_pickup(order_id: str, shop_name: str) -> None:
    """Notify all online riders that a new order is ready for pickup."""
    short_id = str(order_id)[:8].upper()
    try:
        rows = (
            _supa.table('riders')
            .select('user_id')
            .eq('is_active', True)
            .eq('is_available', True)
            .execute().data or []
        )
    except Exception:
        return
    for row in rows:
        push(
            user_id=row['user_id'],
            ntype='new_pickup',
            title=f'New Pickup Available — {shop_name}',
            body=f'Order #{short_id} is packed and ready for pickup.',
            data={'order_id': order_id, 'url': '/rider/available'},
        )
        # Web Push (browser notification even when tab is closed)
        try:
            from app.services.push import send_push
            send_push(
                user_id=row['user_id'],
                title=f'New Pickup 📦 — {shop_name}',
                body=f'Order #{short_id} is packed and ready for collection.',
                url='/rider/available',
            )
        except Exception:
            pass


# ── Rider-to-seller delivery events ─────────────────────────────────────────

def push_seller_pickup_alert(order_id: str, rider_name: str = 'A rider') -> None:
    """Notify seller when a rider picks up their order (→ out_for_delivery)."""
    try:
        order = _supa.table('orders').select('seller_id') \
            .eq('id', order_id).single().execute().data
        if not order or not order.get('seller_id'):
            return
        seller_row = _supa.table('sellers').select('user_id') \
            .eq('id', order['seller_id']).single().execute().data
        seller_user_id = seller_row.get('user_id') if seller_row else None
    except Exception:
        return
    if not seller_user_id:
        return
    short_id = str(order_id)[:8].upper()
    push(
        user_id=seller_user_id,
        ntype='order_picked_up',
        title=f'Order Picked Up 🛵 — #{short_id}',
        body=f'{rider_name} has picked up order #{short_id} and is heading to the customer.',
        data={'order_id': order_id, 'url': f'/seller/orders/{order_id}'},
    )


def push_seller_delivered_alert(order_id: str, rider_name: str = 'The rider') -> None:
    """Notify seller when a rider marks their order as delivered."""
    try:
        order = _supa.table('orders').select('seller_id') \
            .eq('id', order_id).single().execute().data
        if not order or not order.get('seller_id'):
            return
        seller_row = _supa.table('sellers').select('user_id') \
            .eq('id', order['seller_id']).single().execute().data
        seller_user_id = seller_row.get('user_id') if seller_row else None
    except Exception:
        return
    if not seller_user_id:
        return
    short_id = str(order_id)[:8].upper()
    push(
        user_id=seller_user_id,
        ntype='order_delivered_seller',
        title=f'Order Delivered ✓ — #{short_id}',
        body=f'{rider_name} delivered order #{short_id}. Waiting for buyer to confirm receipt.',
        data={'order_id': order_id, 'url': f'/seller/orders/{order_id}'},
    )


# ── Rider payout helpers ──────────────────────────────────────────────────────

def push_rider_handback(order_id: str, rider_name: str, reason: str) -> None:
    """Notify seller + buyer that the assigned rider handed back the order (could not complete)."""
    try:
        order = _supa.table('orders').select('seller_id, buyer_id') \
            .eq('id', order_id).single().execute().data
        if not order:
            return
        seller_row = _supa.table('sellers').select('user_id') \
            .eq('id', order['seller_id']).single().execute().data
        seller_user_id = seller_row.get('user_id') if seller_row else None
    except Exception:
        return
    short_id = str(order_id)[:8].upper()
    reason_str = reason.strip() if reason else 'No reason provided.'
    # Notify seller
    if seller_user_id:
        push(
            user_id=seller_user_id,
            ntype='rider_handback',
            title=f'Rider Returned Order — #{short_id}',
            body=f'{rider_name} could not complete the delivery. Reason: {reason_str}. Order is now back in the pickup pool.',
            data={'order_id': order_id, 'url': f'/seller/orders/{order_id}'},
        )
    # Notify buyer
    if order.get('buyer_id'):
        push(
            user_id=order['buyer_id'],
            ntype='rider_handback',
            title=f'Delivery Delayed — #{short_id}',
            body='Your rider was unable to collect the order. A new rider will be assigned shortly. We apologise for the delay.',
            data={'order_id': order_id, 'url': f'/buyer/orders/{order_id}'},
        )
    # Web Push to seller so they're notified even off-page
    if seller_user_id:
        try:
            from app.services.push import send_push
            send_push(
                user_id=seller_user_id,
                title=f'Rider Returned Order — #{short_id}',
                body=f'{rider_name} could not complete the delivery. Order is back in the pickup pool.',
                url=f'/seller/orders/{order_id}',
            )
        except Exception:
            pass


def push_rider_payout_requested(rider_user_id: str, amount: float) -> None:
    """Notify all admins that a rider submitted a withdrawal request."""
    try:
        admins = _supa.table('profiles').select('id').eq('role', 'admin').execute().data or []
    except Exception:
        return
    for admin in admins:
        push(
            user_id=admin['id'],
            ntype='rider_payout_requested',
            title='Rider Withdrawal Request',
            body=f'A rider has requested a withdrawal of ₱{amount:,.2f}. Please review.',
            data={'url': '/admin/rider-payouts'},
        )


def push_rider_payout_event(rider_user_id: str, status: str, amount: float) -> None:
    """Notify a rider that their withdrawal request was approved or rejected."""
    if status == 'approved':
        title = 'Withdrawal Approved ✓'
        body  = f'Your withdrawal of ₱{amount:,.2f} has been approved. Funds will be sent to your account.'
    else:
        title = 'Withdrawal Request Rejected'
        body  = f'Your withdrawal request of ₱{amount:,.2f} was not approved. Check your withdrawal history for details.'
    push(
        user_id=rider_user_id,
        ntype=f'rider_payout_{status}',
        title=title,
        body=body,
        data={'url': '/rider/payouts'},
    )
    # Web Push
    try:
        from app.services.push import send_push
        send_push(user_id=rider_user_id, title=title, body=body, url='/rider/payouts')
    except Exception:
        pass
