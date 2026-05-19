"""Buyer cart routes — session-backed, DB-persisted."""
from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.utils.pricing import effective_price
from .utils import buyer_bp


# ── DB persistence helpers ────────────────────────────────────────────────────

def _db_sync(buyer_id: str, cart: dict) -> None:
    """Full replace: delete all DB cart rows for buyer then re-insert current cart.
    Called on every mutation so the DB always mirrors the session.
    Errors are swallowed — DB sync failure must never break the cart UX.
    """
    try:
        supabase.table('cart_items').delete().eq('buyer_id', buyer_id).execute()
        if cart:
            rows = [
                {
                    'buyer_id':   buyer_id,
                    'cart_key':   k,
                    'product_id': v.get('product_id') or k.split('_')[0],
                    'variant_id': v.get('variant_id') or None,
                    'quantity':   v.get('qty', 1),
                    'name':       v.get('name', ''),
                    'price':      float(v.get('price', 0)),
                    'image_url':  v.get('image_url'),
                    'seller_id':  v.get('seller_id'),
                }
                for k, v in cart.items()
            ]
            supabase.table('cart_items').insert(rows).execute()
    except Exception as e:
        print(f'[cart] db_sync error: {e}')


def _db_load(buyer_id: str) -> dict:
    """Load persisted cart from DB; returns a session-compatible dict.
    Returns {} on any error so callers always get a safe value.
    """
    try:
        rows = supabase.table('cart_items').select('*') \
            .eq('buyer_id', buyer_id).execute().data or []
        return {
            r['cart_key']: {
                'product_id':   r['product_id'],
                'variant_id':   r.get('variant_id'),
                'variant_name': None,   # fetched live when the cart page is rendered
                'qty':          r['quantity'],
                'name':         r['name'],
                'price':        float(r['price']),
                'image_url':    r.get('image_url'),
                'seller_id':    r.get('seller_id'),
            }
            for r in rows
        }
    except Exception as e:
        print(f'[cart] db_load error: {e}')
        return {}


# ── Session helpers (used by cart routes + checkout) ─────────────────────────

def _get_cart() -> dict:
    """Return the current cart.
    For guests: returns session cart only (no DB access).
    For authenticated buyers: if session is missing (expired / new device), restore from DB.
    """
    cart = session.get('cart')
    if cart is None:
        # Only restore from DB if user is authenticated and is a buyer
        if current_user.is_authenticated and \
                getattr(current_user, 'role', None) == 'buyer':
            cart = _db_load(current_user.id)
            session['cart'] = cart
            session.modified = True
        else:
            # Guest or non-buyer: return empty cart
            cart = {}
    return cart


def _save_cart(cart: dict) -> None:
    """Save cart to session and sync to DB (for authenticated buyers only).
    For guests: save to session only (DB sync only happens after login via auth.py merger).
    """
    session['cart'] = cart
    session.modified = True
    # Only sync to DB if user is authenticated and is a buyer
    if current_user.is_authenticated and \
            getattr(current_user, 'role', None) == 'buyer':
        _db_sync(current_user.id, cart)


@buyer_bp.route('/cart')
def cart():
    raw_cart = _get_cart()
    enriched = []
    total = 0.0
    for cart_key, item in raw_cart.items():
        pid        = item.get('product_id') or cart_key  # backward compat
        variant_id = item.get('variant_id')
        try:
            r = supabase.table('products').select(
                'id,name,price,sale_price,sale_starts_at,sale_ends_at,images,stock_quantity,is_active,seller_id'
            ).eq('id', pid).single().execute()
            p = r.data
            if not p or not p.get('is_active'):
                continue
        except Exception:
            continue

        # Get live stock — prefer variant stock when variant is selected
        if variant_id:
            try:
                vr = supabase.table('product_variants').select('name,stock_quantity').eq('id', variant_id).single().execute()
                vdata = vr.data or {}
                live_stock    = vdata.get('stock_quantity') or 0
                variant_name  = vdata.get('name') or item.get('variant_name')
            except Exception:
                live_stock   = p.get('stock_quantity') or 0
                variant_name = item.get('variant_name')
        else:
            live_stock   = p.get('stock_quantity') or 0
            variant_name = None

        ep       = effective_price(p)
        qty      = min(item['qty'], live_stock) if live_stock > 0 else item['qty']
        subtotal = ep * qty
        total   += subtotal
        imgs     = p.get('images') or []
        enriched.append({
            'cart_key':       cart_key,
            'id':             pid,
            'variant_id':     variant_id,
            'variant_name':   variant_name,
            'name':           p['name'],
            'price':          ep,
            'original_price': float(p['price']),
            '_on_sale':       ep < float(p['price']),
            'image_url':      imgs[0] if imgs else None,
            'stock':          live_stock,
            'seller_id':      p.get('seller_id'),
            'qty':            qty,
            'subtotal':       subtotal,
        })
    return render_template('buyer/cart.html', items=enriched, total=total)


@buyer_bp.route('/cart/add/<product_id>', methods=['POST'])
def cart_add(product_id):
    qty        = max(1, int(request.form.get('qty', 1)))
    variant_id = request.form.get('variant_id', '').strip() or None

    try:
        r = supabase.table('products').select(
            'id,name,price,sale_price,sale_starts_at,sale_ends_at,images,stock_quantity,is_active,seller_id'
        ).eq('id', product_id).single().execute()
        p = r.data
        if not p or not p.get('is_active'):
            flash('Product is not available.', 'error')
            return redirect(request.referrer or url_for('buyer.browse_products'))
    except Exception as e:
        flash(f'Could not add item: {e}', 'error')
        return redirect(request.referrer or url_for('buyer.browse_products'))

    # Determine available stock + variant name
    variant_name = None
    if variant_id:
        try:
            vr = supabase.table('product_variants').select(
                'id,name,stock_quantity'
            ).eq('id', variant_id).single().execute()
            vdata = vr.data
            if not vdata:
                flash('Selected variant is not available.', 'error')
                return redirect(request.referrer or url_for('buyer.browse_products'))
            available_stock = vdata.get('stock_quantity') or 0
            variant_name    = vdata['name']
        except Exception as e:
            flash(f'Could not load variant: {e}', 'error')
            return redirect(request.referrer or url_for('buyer.browse_products'))
    else:
        available_stock = p.get('stock_quantity') or 0

    if available_stock < qty:
        flash(f'Only {available_stock} in stock.' if available_stock > 0 else 'This item is out of stock.', 'error')
        return redirect(request.referrer or url_for('buyer.browse_products'))

    imgs = p.get('images') or []
    # Cart key is composite so same product with different variants can coexist
    cart_key = f"{product_id}_{variant_id or ''}"
    cart = _get_cart()
    if cart_key in cart:
        new_qty = min(cart[cart_key]['qty'] + qty, available_stock)
        cart[cart_key]['qty'] = new_qty
    else:
        cart[cart_key] = {
            'product_id':   product_id,
            'variant_id':   variant_id,
            'variant_name': variant_name,
            'qty':          qty,
            'name':         p['name'],
            'price':        effective_price(p),
            'image_url':    imgs[0] if imgs else None,
            'seller_id':    p.get('seller_id'),
            'stock':        available_stock,
        }
    _save_cart(cart)
    label = f'"{p["name"]}"' + (f' ({variant_name})' if variant_name else '')
    flash(f'{label} Added to Cart||Check your cart to review items or place your order.', 'success')
    return redirect(request.referrer or url_for('buyer.browse_products'))


@buyer_bp.route('/buy-now/<product_id>', methods=['POST'])
def buy_now(product_id):
    """Add a single item to the cart and jump straight to checkout (Buy Now)."""
    qty        = max(1, int(request.form.get('qty', 1)))
    variant_id = request.form.get('variant_id', '').strip() or None

    try:
        r = supabase.table('products').select(
            'id,name,price,sale_price,sale_starts_at,sale_ends_at,images,stock_quantity,is_active,seller_id'
        ).eq('id', product_id).single().execute()
        p = r.data
        if not p or not p.get('is_active'):
            flash('Product is not available.', 'error')
            return redirect(request.referrer or url_for('buyer.browse_products'))
    except Exception as e:
        flash(f'Could not process: {e}', 'error')
        return redirect(request.referrer or url_for('buyer.browse_products'))

    variant_name = None
    if variant_id:
        try:
            vr = supabase.table('product_variants').select(
                'id,name,stock_quantity'
            ).eq('id', variant_id).single().execute()
            vdata = vr.data
            if not vdata:
                flash('Selected variant is not available.', 'error')
                return redirect(request.referrer or url_for('buyer.browse_products'))
            available_stock = vdata.get('stock_quantity') or 0
            variant_name    = vdata['name']
        except Exception as e:
            flash(f'Could not load variant: {e}', 'error')
            return redirect(request.referrer or url_for('buyer.browse_products'))
    else:
        available_stock = p.get('stock_quantity') or 0

    if available_stock < qty:
        flash(
            f'Only {available_stock} in stock.' if available_stock > 0 else 'This item is out of stock.',
            'error'
        )
        return redirect(request.referrer or url_for('buyer.browse_products'))

    imgs     = p.get('images') or []
    cart_key = f"{product_id}_{variant_id or ''}"

    # Store as a single-item buy-now session (does NOT touch the regular cart)
    session['buy_now_item'] = {
        'cart_key':     cart_key,
        'product_id':   product_id,
        'variant_id':   variant_id,
        'variant_name': variant_name,
        'qty':          qty,
        'name':         p['name'],
        'price':        effective_price(p),
        'image_url':    imgs[0] if imgs else None,
        'seller_id':    p.get('seller_id'),
        'stock':        available_stock,
    }
    session.modified = True
    return redirect(url_for('buyer.checkout'))


@buyer_bp.route('/cart/update/<path:cart_key>', methods=['POST'])
def cart_update(cart_key):
    qty = int(request.form.get('qty', 1))
    cart = _get_cart()
    if cart_key in cart:
        if qty < 1:
            cart.pop(cart_key)
        else:
            cart[cart_key]['qty'] = qty
        _save_cart(cart)
    return redirect(url_for('buyer.cart'))


@buyer_bp.route('/cart/remove/<path:cart_key>', methods=['POST'])
def cart_remove(cart_key):
    cart = _get_cart()
    cart.pop(cart_key, None)
    _save_cart(cart)
    flash('Item Removed||The item has been removed from your cart.', 'success')
    return redirect(url_for('buyer.cart'))


@buyer_bp.route('/cart/clear', methods=['POST'])
def cart_clear():
    _save_cart({})
    return redirect(url_for('buyer.cart'))
