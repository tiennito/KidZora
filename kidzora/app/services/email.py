"""
app/services/email.py
─────────────────────
Centralised order-related email notifications.
All functions are fire-and-forget — if email fails the order operation
still succeeds; the error is only logged to stdout.

Usage (inside a Flask route):
    from app.services.email import notify_order_status
    notify_order_status(order_id='abc...', new_status='confirmed')
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app, render_template

from app.extensions import supabase_admin as supabase
from app.services.mail_transport import send_html_email


# ── Low-level send ─────────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, html: str) -> None:
    """Send one HTML email. Silently swallows errors."""
    send_html_email(to_email, subject, html)
    return
    try:
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port   = int(current_app.config.get('MAIL_PORT', 465))
        username    = current_app.config.get('MAIL_USERNAME', '')
        password    = current_app.config.get('MAIL_PASSWORD', '')
        sender      = current_app.config.get('MAIL_DEFAULT_SENDER', username)
        use_ssl     = current_app.config.get('MAIL_USE_SSL', True)
        use_tls     = current_app.config.get('MAIL_USE_TLS', False)
        timeout     = float(current_app.config.get('MAIL_TIMEOUT_SECONDS', 5))

        msg = MIMEMultipart('alternative')
        msg['From']    = sender
        msg['To']      = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))

        ctx = ssl.create_default_context()
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=timeout)
            if use_tls:
                server.starttls(context=ctx)

        server.login(username, password)
        server.sendmail(username, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f'[email] FAILED to "{to_email}" — {e}')


# ── Lookup helpers ─────────────────────────────────────────────────────────────

def _get_email(user_id: str) -> str | None:
    """Return email for a user_id from profiles table."""
    try:
        rows = supabase.table('profiles').select('email').eq('id', user_id).execute().data or []
        return rows[0]['email'] if rows else None
    except Exception:
        return None


def _get_order(order_id: str) -> dict | None:
    try:
        rows = supabase.table('orders').select('id,buyer_id,seller_id,total_amount,status') \
            .eq('id', order_id).execute().data or []
        return rows[0] if rows else None
    except Exception:
        return None


# ── Shared HTML wrapper ────────────────────────────────────────────────────────

def _wrap_template(template_name: str, **kwargs) -> str:
    """Render an email template with the layout wrapper."""
    try:
        return render_template(f'emails/{template_name}', **kwargs)
    except Exception as e:
        current_app.logger.error(f'[email] template render error: {e}')
        return ''


def _order_ref(order_id: str) -> str:
    return f'#{order_id[:8].upper()}'


def _amount(order: dict) -> str:
    try:
        return f"₱{float(order.get('total_amount', 0)):,.2f}"
    except Exception:
        return '₱0.00'


# ══════════════════════════════════════════════════════════════════════════════
# ORDER STATUS CHANGE  (triggered when seller updates order status)
# ══════════════════════════════════════════════════════════════════════════════

_STATUS_CONFIG = {
    'confirmed': {
        'icon':    '✅',
        'color':   '#16a34a',
        'title':   'Order Confirmed!',
        'message': 'Great news! The seller has confirmed your order and will start preparing it soon.',
        'cta':     'Track Your Order',
    },
    'preparing': {
        'icon':    '📦',
        'color':   '#d97706',
        'title':   'Order Being Prepared',
        'message': 'The seller is now packing your order. A rider will pick it up shortly.',
        'cta':     'Track Your Order',
    },
    'ready_for_pickup': {
        'icon':    '🏪',
        'color':   '#2563eb',
        'title':   'Ready for Rider Pickup',
        'message': 'Your order is packed and waiting for a rider to pick it up.',
        'cta':     'Track Your Order',
    },
    'out_for_delivery': {
        'icon':    '🛵',
        'color':   '#4f46e5',
        'title':   'Out for Delivery!',
        'message': 'Your order is on its way! The rider is heading to your address right now.',
        'cta':     'Track Your Order',
    },
    'delivered': {
        'icon':    '🏠',
        'color':   '#16a34a',
        'title':   'Order Delivered',
        'message': 'Your order has been marked as delivered by the rider. Please confirm that you received it.',
        'cta':     'Confirm Receipt',
    },
    'cancelled': {
        'icon':    '❌',
        'color':   '#dc2626',
        'title':   'Order Cancelled',
        'message': 'Your order has been cancelled.',
        'cta':     'View Orders',
    },
    'completed': {
        'icon':    '⭐',
        'color':   '#16a34a',
        'title':   'Order Complete!',
        'message': 'Thank you for shopping with KidZora! Your order is fully complete.',
        'cta':     'Shop Again',
    },
}


def notify_order_status(order_id: str, new_status: str) -> None:
    """Send order status update email to the buyer."""
    cfg = _STATUS_CONFIG.get(new_status)
    if not cfg:
        return  # no email for this status

    order = _get_order(order_id)
    if not order:
        return

    buyer_email = _get_email(order['buyer_id'])
    if not buyer_email:
        return

    html = _wrap_template('order_status.html',
        order_ref=_order_ref(order_id),
        icon=cfg['icon'],
        color=cfg['color'],
        title=cfg['title'],
        message=cfg['message'],
        amount=_amount(order),
        status_display=new_status.replace('_', ' ').title()
    )
    
    if not html:
        return
        
    _send(buyer_email, f'KidZora — Order {_order_ref(order_id)} {cfg["title"]}', html)


# ══════════════════════════════════════════════════════════════════════════════
# CANCELLATION EMAILS
# ══════════════════════════════════════════════════════════════════════════════

def notify_cancel_requested(order_id: str, reason: str) -> None:
    """Tell the seller a buyer has requested cancellation on a confirmed order."""
    order = _get_order(order_id)
    if not order:
        return
    seller_email = _get_email(order['seller_id'])
    if not seller_email:
        return

    html = _wrap_template('cancel_requested.html',
        order_ref=_order_ref(order_id),
        reason=reason
    )
    if not html:
        return
    _send(seller_email, f'KidZora — Cancellation Request for Order {_order_ref(order_id)}', html)


def notify_cancel_approved(order_id: str) -> None:
    """Tell buyer their cancellation was approved."""
    order = _get_order(order_id)
    if not order:
        return
    buyer_email = _get_email(order['buyer_id'])
    if not buyer_email:
        return

    html = _wrap_template('cancel_approved.html',
        order_ref=_order_ref(order_id)
    )
    if not html:
        return
    _send(buyer_email, f'KidZora — Order {_order_ref(order_id)} Cancellation Approved', html)


def notify_cancel_rejected(order_id: str, seller_reason: str) -> None:
    """Tell buyer their cancellation was rejected."""
    order = _get_order(order_id)
    if not order:
        return
    buyer_email = _get_email(order['buyer_id'])
    if not buyer_email:
        return

    html = _wrap_template('cancel_rejected.html',
        order_ref=_order_ref(order_id),
        seller_reason=seller_reason
    )
    if not html:
        return
    _send(buyer_email, f'KidZora — Order {_order_ref(order_id)} Cancellation Rejected', html)


# ══════════════════════════════════════════════════════════════════════════════
# RETURN / REFUND EMAILS
# ══════════════════════════════════════════════════════════════════════════════

def notify_return_submitted(rr_id: str) -> None:
    """
    Tell buyer their request was received,
    and tell the seller they need to review it.
    """
    try:
        rr = supabase.table('return_requests').select('*').eq('id', rr_id).single().execute().data
    except Exception:
        return
    if not rr:
        return

    ref = _order_ref(rr['order_id'])

    # ── Email to buyer ──
    buyer_email = _get_email(rr['buyer_id'])
    if buyer_email:
        html = _wrap_template('return_submitted_buyer.html',
            order_ref=ref,
            refund_type=rr.get('refund_type'),
            reason=rr.get('reason', ''),
            details=rr.get('details')
        )
        if html:
            _send(buyer_email, f'KidZora — Return Request Submitted for Order {ref}', html)

    # ── Email to seller ──
    seller_email = _get_email(rr['seller_id'])
    if seller_email:
        html = _wrap_template('return_submitted_seller.html',
            order_ref=ref,
            refund_type=rr.get('refund_type'),
            reason=rr.get('reason', ''),
            details=rr.get('details')
        )
        if html:
            _send(seller_email, f'KidZora — Action Required: Return Request for Order {ref}', html)


def notify_return_seller_approved(rr_id: str, seller_response: str) -> None:
    """Tell buyer the seller approved their return/refund."""
    try:
        rr = supabase.table('return_requests').select('order_id,buyer_id').eq('id', rr_id).single().execute().data
    except Exception:
        return
    if not rr:
        return

    ref         = _order_ref(rr['order_id'])
    buyer_email = _get_email(rr['buyer_id'])
    if not buyer_email:
        return

    html = _wrap_template('return_seller_approved.html',
        order_ref=ref,
        seller_response=seller_response
    )
    if not html:
        return
    _send(buyer_email, f'KidZora — Refund Approved for Order {ref}', html)


def notify_return_seller_rejected(rr_id: str, seller_response: str) -> None:
    """Tell buyer the seller rejected their return/refund — and they can escalate."""
    try:
        rr = supabase.table('return_requests').select('order_id,buyer_id').eq('id', rr_id).single().execute().data
    except Exception:
        return
    if not rr:
        return

    ref         = _order_ref(rr['order_id'])
    buyer_email = _get_email(rr['buyer_id'])
    if not buyer_email:
        return

    html = _wrap_template('return_seller_rejected.html',
        order_ref=ref,
        seller_response=seller_response
    )
    if not html:
        return
    _send(buyer_email, f'KidZora — Refund Request Rejected for Order {ref}', html)


def notify_return_escalated(rr_id: str) -> None:
    """Tell buyer escalation was received; tell admin they have a new dispute."""
    try:
        rr = supabase.table('return_requests').select('*').eq('id', rr_id).single().execute().data
    except Exception:
        return
    if not rr:
        return

    ref = _order_ref(rr['order_id'])

    # ── Buyer confirmation ──
    buyer_email = _get_email(rr['buyer_id'])
    if buyer_email:
        html = _wrap_template('return_escalated.html',
            order_ref=ref
        )
        if html:
            _send(buyer_email, f'KidZora — Dispute Escalated for Order {ref}', html)


def notify_return_admin_resolved(rr_id: str, decision: str, admin_response: str) -> None:
    """Tell buyer and seller the admin's final decision."""
    try:
        rr = supabase.table('return_requests').select('*').eq('id', rr_id).single().execute().data
    except Exception:
        return
    if not rr:
        return

    ref      = _order_ref(rr['order_id'])
    approved = decision == 'approve'

    # ── Buyer email ──
    buyer_email = _get_email(rr['buyer_id'])
    if buyer_email:
        if approved:
            html = _wrap_template('return_admin_approved.html',
                order_ref=ref,
                admin_response=admin_response
            )
            if html:
                _send(buyer_email, f'KidZora — Admin Approved Refund for Order {ref}', html)
        else:
            html = _wrap_template('return_admin_denied.html',
                order_ref=ref,
                admin_response=admin_response
            )
            if html:
                _send(buyer_email, f'KidZora — Admin Decision for Order {ref}', html)

    # ── Seller email ──
    seller_email = _get_email(rr['seller_id'])
    if seller_email:
        decision_text = 'in your favour — no refund required' if not approved else 'in the buyer\'s favour — a refund will be processed'
        html = _wrap_template('return_admin_resolved_seller.html',
            order_ref=ref,
            decision_text=decision_text,
            admin_response=admin_response
        )
        if html:
            _send(seller_email, f'KidZora — Dispute Resolved for Order {ref}', html)


# ══════════════════════════════════════════════════════════════════════════════
# ORDER PLACEMENT EMAILS  (triggered at checkout)
# ══════════════════════════════════════════════════════════════════════════════

def notify_order_placed(
    order_id: str,
    items: list,
    total: float,
    delivery_address: dict,
) -> None:
    """
    Send an order-confirmation email to the buyer immediately after checkout.

    Parameters
    ----------
    order_id         : UUID of the newly created order row.
    items            : List of cart item dicts — each must have 'name', 'qty', 'price'.
    total            : Net total amount already paid (after discount / delivery fee).
    delivery_address : Dict with full_name, phone, city, province, street_name, etc.
    """
    try:
        # buyer_id lives in the order row
        row = supabase.table('orders').select('buyer_id').eq('id', order_id).execute().data or []
        if not row:
            return
        buyer_email = _get_email(row[0]['buyer_id'])
        if not buyer_email:
            return
    except Exception:
        return

    ref = _order_ref(order_id)
    addr = delivery_address or {}
    addr_line = ', '.join(filter(None, [
        addr.get('street_name'),
        addr.get('barangay'),
        addr.get('city'),
        addr.get('province'),
        addr.get('postal_code'),
    ]))

    # Format item subtotals
    item_subtotals = [f"{float(item.get('price', 0)) * item.get('qty', 1):,.2f}" for item in items]
    total_formatted = f"{total:,.2f}"

    html = _wrap_template('order_placed_buyer.html',
        order_ref=ref,
        full_name=addr.get('full_name', 'there'),
        items=items,
        item_subtotals=item_subtotals,
        total_formatted=total_formatted,
        phone=addr.get('phone', ''),
        address_line=addr_line
    )
    if not html:
        return

    _send(buyer_email, f'KidZora — Your Order {ref} is Confirmed! 🛒', html)


def notify_new_order_seller(order_id: str, items: list, total: float) -> None:
    """
    Notify the seller that they have received a new order.

    Parameters
    ----------
    order_id : UUID of the new order row.
    items    : List of cart item dicts — each must have 'name', 'qty', 'price'.
    total    : Net order total.
    """
    try:
        row = supabase.table('orders').select('seller_id,buyer_id').eq('id', order_id).execute().data or []
        if not row:
            return
        seller_email = _get_email(row[0]['seller_id'])
        if not seller_email:
            return
    except Exception:
        return

    ref = _order_ref(order_id)

    # Format item subtotals
    item_subtotals = [f"{float(item.get('price', 0)) * item.get('qty', 1):,.2f}" for item in items]
    total_formatted = f"{total:,.2f}"

    html = _wrap_template('order_placed_seller.html',
        order_ref=ref,
        items=items,
        item_subtotals=item_subtotals,
        total_formatted=total_formatted
    )
    if not html:
        return

    _send(seller_email, f'KidZora — New Order {ref} Received! 🛍️', html)


# ══════════════════════════════════════════════════════════════════════════════
# CHAT MESSAGE NOTIFICATIONS  (triggered when offline user receives message)
# ══════════════════════════════════════════════════════════════════════════════

def notify_new_message(
    message_id: str,
    sender_id: str,
    receiver_id: str,
    message_content: str,
) -> None:
    """
    Send email notification for a new chat message when recipient is offline.
    
    Parameters
    ----------
    message_id       : UUID of the new message row.
    sender_id        : UUID of the sender.
    receiver_id      : UUID of the recipient.
    message_content  : The message text (will be truncated to 150 chars in email).
    """
    # Get recipient email
    receiver_email = _get_email(receiver_id)
    if not receiver_email:
        return
    
    # Get sender profile for display name and avatar
    try:
        sender_rows = supabase.table('profiles').select(
            'id,first_name,last_name,business_name,avatar_url'
        ).eq('id', sender_id).execute().data or []
        if not sender_rows:
            return
        
        sender = sender_rows[0]
        sender_name = (
            sender.get('business_name') 
            or f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip()
            or 'KidZora User'
        )
    except Exception:
        return
    
    # Get receiver name for greeting
    try:
        receiver_rows = supabase.table('profiles').select(
            'first_name,last_name'
        ).eq('id', receiver_id).execute().data or []
        if not receiver_rows:
            return
        
        receiver = receiver_rows[0]
        receiver_name = (
            receiver.get('first_name', 'there')
            or 'there'
        )
    except Exception:
        return
    
    # Truncate message to 150 chars
    message_preview = message_content[:150]
    if len(message_content) > 150:
        message_preview += '...'
    
    # Build chat URL (relative, will be converted to absolute in template if needed)
    chat_url = f'/inbox'  # User will click this to go to inbox
    
    # Render email template
    html = _wrap_template('message_received.html',
        recipient_name=receiver_name,
        sender_name=sender_name,
        message_preview=message_preview,
        chat_url=chat_url
    )
    if not html:
        return
    
    # Send email
    _send(receiver_email, f'KidZora — New message from {sender_name}', html)


# ══════════════════════════════════════════════════════════════════════════════
# WELCOME EMAIL  (triggered when admin approves seller/rider registration)
# ══════════════════════════════════════════════════════════════════════════════

def notify_welcome_approved(user_id: str) -> None:
    """
    Send welcome email to a newly approved seller or rider.
    
    Parameters
    ----------
    user_id : UUID of the profile (seller or rider).
    """
    # Get user email and role
    try:
        user_rows = supabase.table('profiles').select(
            'id,first_name,email,role'
        ).eq('id', user_id).execute().data or []
        if not user_rows:
            return
        
        user = user_rows[0]
        user_email = user.get('email')
        role = user.get('role')
        first_name = user.get('first_name', 'there')
        
        if not user_email or role not in ['seller', 'rider']:
            return
    except Exception:
        return
    
    # Set role-specific text
    role_label = 'Seller' if role == 'seller' else 'Rider'
    if role == 'seller':
        dashboard_text = 'seller dashboard and start listing your products'
        dashboard_link = '/seller/dashboard'
    else:
        dashboard_text = 'rider dashboard and start accepting deliveries'
        dashboard_link = '/rider/dashboard'
    
    # Render email template
    html = _wrap_template('welcome_registered.html',
        recipient_name=first_name,
        role=role,
        role_label=role_label,
        dashboard_text=dashboard_text,
        dashboard_link=dashboard_link
    )
    if not html:
        return
    
    # Send email
    _send(user_email, f'KidZora — Your {role_label} Account Has Been Approved!', html)


# ══════════════════════════════════════════════════════════════════════════════
# LOW-STOCK ALERTS  (triggered when product inventory falls below threshold)
# ══════════════════════════════════════════════════════════════════════════════

def notify_low_stock_email(
    seller_user_id: str,
    product_id: str,
    product_name: str,
    stock_left: int,
    variant_name: str | None = None,
) -> None:
    """
    Send low-stock / out-of-stock alert email to a seller.
    
    Parameters
    ----------
    seller_user_id   : UUID of the seller (profiles.id, not sellers.id).
    product_id       : UUID of the product.
    product_name     : Name of the product.
    stock_left       : Number of units remaining (0 = out of stock).
    variant_name     : Optional variant name (e.g., "Size Large").
    """
    # Get seller email and first name
    try:
        seller_rows = supabase.table('profiles').select(
            'id,first_name,email'
        ).eq('id', seller_user_id).execute().data or []
        if not seller_rows:
            return
        
        seller = seller_rows[0]
        seller_email = seller.get('email')
        seller_name = seller.get('first_name', 'there')
        
        if not seller_email:
            return
    except Exception:
        return
    
    # Determine alert level and messaging
    is_out_of_stock = stock_left == 0
    if is_out_of_stock:
        subject = f'KidZora — Out of Stock: {product_name}'
    else:
        subject = f'KidZora — Low Stock Alert: {product_name}'
    
    # Build full product label
    product_label = f'{product_name} ({variant_name})' if variant_name else product_name
    edit_product_url = f'/seller/products/{product_id}/edit'
    
    # Render email template
    html = _wrap_template('low_stock_alert.html',
        seller_name=seller_name,
        product_name=product_name,
        variant_name=variant_name,
        stock_left=stock_left,
        is_out_of_stock=is_out_of_stock,
        edit_product_url=edit_product_url
    )
    if not html:
        return
    
    # Send email
    _send(seller_email, subject, html)
