"""Buyer checkout + place-order routes."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.notify import push_order_event, push, push_low_stock, LOW_STOCK_THRESHOLD
from app.services.email import notify_order_placed, notify_new_order_seller
from app.services.delivery_fee_service import calculate_delivery_fee, build_order_totals
from app.utils.settings import get_commission_rate
from .utils import buyer_bp
from .cart import _get_cart, _save_cart

def _validate_coupon(code: str, subtotal: float, seller_ids: list, delivery_fee: float):
    """
    Validate code against admin coupons then seller coupons.
    Returns dict with keys: success, coupon_id, coupon_type ('admin'|'seller'),
    seller_coupon_id, discount, description, message.
    """
    code = code.strip().upper()
    now  = datetime.now(timezone.utc)

    # ── Admin coupon ──────────────────────────────────────────────────────────
    try:
        rows = supabase.table('coupons').select('*').eq('code', code).eq('is_active', True).execute().data or []
    except Exception:
        rows = []

    if rows:
        c = rows[0]
        if c.get('expires_at'):
            exp = c['expires_at']
            if isinstance(exp, str):
                exp = datetime.fromisoformat(exp.replace('Z', '+00:00'))
            if exp < now:
                return {'success': False, 'message': 'This coupon has expired.'}

        if c.get('usage_limit') and (c.get('usage_count') or 0) >= c['usage_limit']:
            return {'success': False, 'message': 'Coupon usage limit has been reached.'}

        min_order = float(c.get('min_order_amount') or 0)
        if subtotal < min_order:
            return {'success': False, 'message': f'Minimum order of ₱{min_order:,.2f} required for this coupon.'}

        dt  = c['discount_type']
        val = float(c.get('discount_value') or 0)

        if dt == 'free_delivery':
            discount = delivery_fee
            desc = 'Free Delivery'
        elif dt == 'percentage':
            discount = subtotal * (val / 100)
            if c.get('max_discount_amount'):
                discount = min(discount, float(c['max_discount_amount']))
            desc = f'{val:.0f}% off'
        else:  # fixed
            discount = min(val, subtotal)
            desc = f'₱{val:,.2f} off'

        return {
            'success': True, 'coupon_id': c['id'], 'seller_coupon_id': None,
            'coupon_type': 'admin', 'discount': round(discount, 2),
            'description': c.get('description') or desc, 'message': f'Coupon applied: {desc}',
        }

    # ── Seller coupon ─────────────────────────────────────────────────────────
    if seller_ids:
        try:
            rows = (supabase.table('seller_coupons').select('*')
                    .eq('code', code).eq('is_active', True)
                    .in_('seller_id', seller_ids).execute().data or [])
        except Exception:
            rows = []

        if rows:
            c = rows[0]
            if c.get('expires_at'):
                exp = c['expires_at']
                if isinstance(exp, str):
                    exp = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                if exp < now:
                    return {'success': False, 'message': 'This coupon has expired.'}

            if c.get('usage_limit') and (c.get('usage_count') or 0) >= c['usage_limit']:
                return {'success': False, 'message': 'Coupon usage limit has been reached.'}

            min_order = float(c.get('min_order_amount') or 0)
            if subtotal < min_order:
                return {'success': False, 'message': f'Minimum order of ₱{min_order:,.2f} required for this coupon.'}

            dt  = c['discount_type']
            val = float(c.get('discount_value') or 0)

            if dt == 'free_delivery':
                discount = delivery_fee
                desc = 'Free Delivery (Seller)'
            elif dt == 'percentage':
                discount = subtotal * (val / 100)
                if c.get('max_discount_amount'):
                    discount = min(discount, float(c['max_discount_amount']))
                desc = f'{val:.0f}% off (Seller)'
            else:
                discount = min(val, subtotal)
                desc = f'₱{val:,.2f} off (Seller)'

            return {
                'success': True, 'coupon_id': None, 'seller_coupon_id': c['id'],
                'coupon_type': 'seller', 'discount': round(discount, 2),
                'description': c.get('description') or desc, 'message': f'Coupon applied: {desc}',
            }

    return {'success': False, 'message': 'Invalid or expired coupon code.'}


# ── AJAX: delivery fee ────────────────────────────────────────────────────────
@buyer_bp.route('/checkout/delivery-fee', methods=['POST'])
@login_required
def checkout_delivery_fee():
    data   = request.get_json(silent=True) or {}
    location = {
        'region': data.get('region', ''),
        'province': data.get('province', ''),
        'city': data.get('city', ''),
    }
    result = calculate_delivery_fee(location)
    return jsonify({
        'fee': result['fee'],
        'matched': result['matched'],
        'matchType': result['matchType'],
        'locationName': result['locationName'],
        'fallback': result['fallback'],
        'region': location['region'] or 'Unknown',
    })


# ── AJAX: apply coupon ────────────────────────────────────────────────────────
@buyer_bp.route('/checkout/apply-coupon', methods=['POST'])
@login_required
def checkout_apply_coupon():
    data         = request.get_json(silent=True) or {}
    code         = data.get('code', '')
    subtotal     = float(data.get('subtotal') or 0)
    seller_ids   = data.get('seller_ids') or []
    delivery_fee = float(data.get('delivery_fee') or 0)

    if not code:
        return jsonify({'success': False, 'message': 'Enter a coupon code.'})

    result = _validate_coupon(code, subtotal, seller_ids, delivery_fee)
    return jsonify(result)


# ── GET /checkout ─────────────────────────────────────────────────────────────
@buyer_bp.route('/checkout')
@login_required
def checkout():
    # Buy Now takes priority — single item, does not touch the cart
    buy_now_item = session.get('buy_now_item')
    if buy_now_item:
        cart = {buy_now_item['cart_key']: buy_now_item}
    else:
        cart = _get_cart()

    if not cart:
        flash('Your Cart is Empty||Add some items to your cart before checking out.', 'warning')
        return redirect(url_for('buyer.cart'))

    items = []
    total = 0.0
    seller_ids = set()
    for pid, item in cart.items():
        subtotal = float(item['price']) * item['qty']
        total   += subtotal
        items.append({**item, 'id': pid, 'subtotal': subtotal})
        if item.get('seller_id'):
            seller_ids.add(item['seller_id'])

    seller_ids_list = list(seller_ids)

    # ── Fetch available coupons for the picker ────────────────────────────────
    now_iso = __import__('datetime').datetime.utcnow().isoformat()
    available_coupons = []

    try:
        # Admin coupons (active, not expired, within usage limit)
        admin_rows = supabase.table('coupons').select(
            'id,code,description,discount_type,discount_value,min_order_amount,max_discount_amount,usage_limit,usage_count'
        ).eq('is_active', True).execute().data or []

        for c in admin_rows:
            if c.get('usage_limit') and (c.get('usage_count') or 0) >= c['usage_limit']:
                continue
            if float(c.get('min_order_amount') or 0) > total:
                continue
            available_coupons.append({
                'source': 'admin',
                'code':           c['code'],
                'description':    c.get('description') or '',
                'discount_type':  c['discount_type'],
                'discount_value': c.get('discount_value') or 0,
                'min_order_amount': c.get('min_order_amount') or 0,
                'max_discount_amount': c.get('max_discount_amount'),
            })
    except Exception as e:
        print(f'[checkout] admin coupon fetch error: {e}')

    try:
        # Seller coupons for sellers in cart
        if seller_ids_list:
            sc_rows = supabase.table('seller_coupons').select(
                'id,seller_id,code,description,discount_type,discount_value,min_order_amount,max_discount_amount,usage_limit,usage_count,expires_at'
            ).in_('seller_id', seller_ids_list).eq('is_active', True).execute().data or []

            for c in sc_rows:
                if c.get('usage_limit') and (c.get('usage_count') or 0) >= c['usage_limit']:
                    continue
                if float(c.get('min_order_amount') or 0) > total:
                    continue
                if c.get('expires_at') and c['expires_at'].replace('Z', '') < now_iso:
                    continue
                available_coupons.append({
                    'source': 'seller',
                    'code':           c['code'],
                    'description':    c.get('description') or '',
                    'discount_type':  c['discount_type'],
                    'discount_value': c.get('discount_value') or 0,
                    'min_order_amount': c.get('min_order_amount') or 0,
                    'max_discount_amount': c.get('max_discount_amount'),
                })
    except Exception as e:
        print(f'[checkout] seller coupon fetch error: {e}')

    initial_delivery = calculate_delivery_fee({
        'region': current_user.region or '',
        'province': current_user.province or '',
        'city': current_user.city or '',
    })

    payment_methods = ['cash', 'gcash', 'paymaya', 'bank_transfer']
    return render_template('buyer/checkout.html',
                           items=items,
                           total=total,
                           delivery_fee=initial_delivery['fee'],
                           delivery_fee_match=initial_delivery,
                           seller_ids=seller_ids_list,
                           available_coupons=available_coupons,
                           payment_methods=payment_methods)


# ── POST /checkout/place ──────────────────────────────────────────────────────
@buyer_bp.route('/checkout/place', methods=['POST'])
@login_required
def place_order():
    print('[CHECKOUT] Place order request received')
    # Buy Now takes priority — single item checkout
    buy_now_item = session.get('buy_now_item')
    is_buy_now   = bool(buy_now_item)
    if is_buy_now:
        cart = {buy_now_item['cart_key']: buy_now_item}
    else:
        cart = _get_cart()

    if not cart:
        flash('Your Cart is Empty||Add some items to your cart before checking out.', 'warning')
        return redirect(url_for('buyer.cart'))

    payment_method = request.form.get('payment_method', 'cash')
    region         = request.form.get('region', '')
    coupon_code    = (request.form.get('coupon_code') or '').strip().upper()
    notes          = (request.form.get('notes') or '').strip()

    delivery_address = {
        'full_name':   f'{current_user.first_name} {current_user.last_name}',
        'phone':       request.form.get('phone')       or current_user.phone       or '',
        'region':      region                          or current_user.region      or '',
        'province':    request.form.get('province')    or current_user.province    or '',
        'city':        request.form.get('city')        or current_user.city        or '',
        'barangay':    request.form.get('barangay')    or current_user.barangay    or '',
        'street_name': request.form.get('street_name') or current_user.street_name or '',
        'postal_code': request.form.get('postal_code') or current_user.postal_code or '',
    }

    delivery_fee = calculate_delivery_fee(delivery_address)['fee']

    # ── STEP 1: Pre-validate every item's stock ───────────────────────────────
    stock_errors = []
    for cart_key, item in cart.items():
        pid        = item.get('product_id') or cart_key
        variant_id = item.get('variant_id')
        qty        = item['qty']

        try:
            prod = supabase.table('products').select(
                'name,stock_quantity,is_active'
            ).eq('id', pid).single().execute().data
        except Exception:
            prod = None

        if not prod or not prod.get('is_active'):
            stock_errors.append(f'"{item.get("name", "A product")}" is no longer available.')
            continue

        if variant_id:
            try:
                var = supabase.table('product_variants').select(
                    'name,stock_quantity'
                ).eq('id', variant_id).single().execute().data
            except Exception:
                var = None
            if not var:
                stock_errors.append(f'"{prod["name"]}" – variant no longer available.')
                continue
            available = var.get('stock_quantity') or 0
            label     = f'{prod["name"]} ({var["name"]})'
        else:
            available = prod.get('stock_quantity') or 0
            label     = prod['name']

        if qty > available:
            if available == 0:
                stock_errors.append(f'"{label}" is out of stock.')
            else:
                stock_errors.append(
                    f'"{label}": only {available} available, but {qty} in your cart.'
                )

    if stock_errors:
        for msg in stock_errors:
            flash(msg, 'error')
        return redirect(url_for('buyer.cart'))

    # ── STEP 2: Group by seller ───────────────────────────────────────────────
    by_seller: dict = {}
    for cart_key, item in cart.items():
        sid = item.get('seller_id')
        if not sid:
            continue
        by_seller.setdefault(sid, []).append({
            'cart_key': cart_key, 'pid': item.get('product_id') or cart_key,
            'variant_id': item.get('variant_id'), **item,
        })

    if not by_seller:
        flash('No valid items to order.', 'error')
        return redirect(url_for('buyer.cart'))

    # ── STEP 3: Validate + compute coupon ────────────────────────────────────
    coupon_id        = None
    seller_coupon_id = None
    discount_amount  = 0.0
    grand_subtotal   = sum(
        float(i['price']) * i['qty'] for items_list in by_seller.values() for i in items_list
    )

    if coupon_code:
        coupon_result = _validate_coupon(
            coupon_code, grand_subtotal, list(by_seller.keys()), delivery_fee
        )
        if coupon_result['success']:
            discount_amount  = coupon_result['discount']
            coupon_id        = coupon_result.get('coupon_id')
            seller_coupon_id = coupon_result.get('seller_coupon_id')
            # Increment usage count
            try:
                if coupon_id:
                    c_row = supabase.table('coupons').select('usage_count').eq('id', coupon_id).single().execute().data
                    supabase.table('coupons').update({'usage_count': (c_row.get('usage_count') or 0) + 1}).eq('id', coupon_id).execute()
                if seller_coupon_id:
                    sc_row = supabase.table('seller_coupons').select('usage_count').eq('id', seller_coupon_id).single().execute().data
                    supabase.table('seller_coupons').update({'usage_count': (sc_row.get('usage_count') or 0) + 1}).eq('id', seller_coupon_id).execute()
            except Exception as e:
                print(f"[checkout] coupon usage increment error: {e}")
        else:
            flash(f'Coupon not applied: {coupon_result["message"]}', 'warning')

    # ── STEP 4: Create orders + deduct stock ──────────────────────────────────
    placed = []
    num_sellers = len(by_seller)
    # Spread discount + delivery fee across sellers; last seller receives the
    # exact remainder to avoid cent-level rounding loss (e.g. ₱100 / 3 × 3 = ₱99.99).
    delivery_allocated = 0.0
    discount_allocated = 0.0
    try:
        for idx, (seller_id, items_list) in enumerate(by_seller.items()):
            subtotal   = sum(float(i['price']) * i['qty'] for i in items_list)
            proportion = subtotal / grand_subtotal if grand_subtotal else 1.0
            is_last    = (idx == num_sellers - 1)
            # Last seller gets the exact remainder to keep totals accurate
            order_deliv_fee = (round(delivery_fee - delivery_allocated, 2)
                               if is_last else round(delivery_fee / num_sellers, 2))
            order_discount  = (round(discount_amount - discount_allocated, 2)
                               if is_last else round(discount_amount * proportion, 2))
            if not is_last:
                delivery_allocated += order_deliv_fee
                discount_allocated += order_discount
            totals          = build_order_totals(subtotal, order_deliv_fee, order_discount)
            net_total       = totals['total_amount']
            commission      = round(subtotal * get_commission_rate(), 2)
            earnings        = round(subtotal - commission, 2)

            order_resp = supabase.table('orders').insert({
                'buyer_id':          current_user.id,
                'seller_id':         seller_id,
                'subtotal':          totals['subtotal'],
                'total_amount':      net_total,
                'commission':        commission,
                'seller_earnings':   earnings,
                'delivery_fee':      order_deliv_fee,
                'delivery_address':  delivery_address,
                'discount_amount':   order_discount,
                'coupon_id':         coupon_id,
                'seller_coupon_id':  seller_coupon_id,
                'status':            'pending',
                'payment_status':    'pending',
                'payment_method':    payment_method,
                'notes':             notes or None,
            }).execute()
            order_id = order_resp.data[0]['id']

            for item in items_list:
                supabase.table('order_items').insert({
                    'order_id':   order_id,
                    'product_id': item['pid'],
                    'variant_id': item.get('variant_id'),
                    'quantity':   item['qty'],
                    'price':      float(item['price']),
                }).execute()

                # Deduct stock
                if item.get('variant_id'):
                    var_now = supabase.table('product_variants').select('stock_quantity') \
                        .eq('id', item['variant_id']).single().execute().data
                    new_var_stock = max(0, (var_now.get('stock_quantity') or 0) - item['qty'])
                    supabase.table('product_variants').update({'stock_quantity': new_var_stock}) \
                        .eq('id', item['variant_id']).execute()
                    all_vars = supabase.table('product_variants').select('stock_quantity') \
                        .eq('product_id', item['pid']).execute().data or []
                    prod_total = sum((v.get('stock_quantity') or 0) for v in all_vars)
                    supabase.table('products').update({'stock_quantity': prod_total}) \
                        .eq('id', item['pid']).execute()
                    # Low-stock / out-of-stock alert (variant)
                    try:
                        if new_var_stock <= LOW_STOCK_THRESHOLD:
                            push_low_stock(
                                seller_id=seller_id,
                                product_id=item['pid'],
                                product_name=item.get('name', 'Product'),
                                stock_left=new_var_stock,
                                variant_name=item.get('variant_name'),
                            )
                    except Exception:
                        pass
                else:
                    prod_now = supabase.table('products').select('stock_quantity') \
                        .eq('id', item['pid']).single().execute().data
                    new_prod_stock = max(0, (prod_now.get('stock_quantity') or 0) - item['qty'])
                    supabase.table('products').update({'stock_quantity': new_prod_stock}) \
                        .eq('id', item['pid']).execute()
                    # Low-stock / out-of-stock alert (no variant)
                    try:
                        if new_prod_stock <= LOW_STOCK_THRESHOLD:
                            push_low_stock(
                                seller_id=seller_id,
                                product_id=item['pid'],
                                product_name=item.get('name', 'Product'),
                                stock_left=new_prod_stock,
                            )
                    except Exception:
                        pass

            placed.append(order_id)
            # notify seller of new order (push + email)
            try:
                push_order_event(order_id, 'order_placed')
            except Exception:
                pass
            try:
                notify_new_order_seller(order_id, items_list, net_total)
            except Exception:
                pass
            # notify buyer — in-app push + order confirmation email
            try:
                short_id = str(order_id)[:8].upper()
                push(
                    user_id=current_user.id,
                    ntype='order_placed',
                    title=f'Order Placed! — #{short_id}',
                    body='Your order has been received. Tap to track its progress.',
                    data={'order_id': order_id, 'url': f'/buyer/orders/{order_id}'},
                )
            except Exception:
                pass
            try:
                notify_order_placed(order_id, items_list, net_total, delivery_address)
            except Exception:
                pass

    except Exception as e:
        flash(f'Order failed: {e}', 'error')
        return redirect(url_for('buyer.checkout'))

    # Clear only what was used: buy_now_item or the full cart
    if is_buy_now:
        session.pop('buy_now_item', None)
        session.modified = True
    else:
        _save_cart({})

    # Optionally save the delivery address for future use
    if request.form.get('save_address') == '1' and not request.form.get('_saved_addr_id'):
        try:
            label = (request.form.get('address_label') or 'Home').strip() or 'Home'
            existing = (supabase.table('buyer_addresses')
                        .select('id', count='exact')
                        .eq('buyer_id', current_user.id).execute())
            is_first = (existing.count == 0)
            supabase.table('buyer_addresses').insert({
                'buyer_id':        current_user.id,
                'label':           label,
                'full_name':       delivery_address['full_name'],
                'phone':           delivery_address['phone'],
                'region':          delivery_address['region'],
                'province':        delivery_address['province'],
                'city':            delivery_address['city'],
                'barangay':        delivery_address['barangay'],
                'street_name':     delivery_address['street_name'],
                'building_number': delivery_address.get('building_number', ''),
                'postal_code':     delivery_address['postal_code'],
                'is_default':      is_first,
            }).execute()
        except Exception as _ae:
            print(f'[checkout] save_address error: {_ae}')

    flash(f'Order Placed!||{len(placed)} order{"s" if len(placed) > 1 else ""} confirmed. Thank you for shopping with KidZora!', 'success')
    return redirect(url_for('buyer.orders'))



