"""Buyer dashboard route."""
from collections import Counter
from flask import render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.services.delivery_fee_service import recalculate_pending_buyer_orders
from app.utils.pricing import annotate_sale
from .utils import buyer_bp, _save_avatar

_PROFILE_FIELDS = [
    'first_name', 'last_name', 'phone',
    'region', 'province', 'city', 'barangay',
    'building_number', 'street_name', 'postal_code',
]

@buyer_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # ── Handle profile form submission ──────────────────────────────────
    if request.method == 'POST':
        try:
            avatar_url = None
            
            # Handle avatar upload
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename:
                    avatar_url = _save_avatar(file, current_user.id)
            
            # Build update dict
            update_data = {}
            for field in _PROFILE_FIELDS:
                val = request.form.get(field, '').strip()
                update_data[field] = val or None
            
            if avatar_url:
                update_data['avatar_url'] = avatar_url
            
            # Update user profile
            if update_data:
                supabase.table('profiles').update(update_data).eq('user_id', str(current_user.id)).execute()
                current_user.first_name = update_data.get('first_name') or current_user.first_name
                current_user.last_name = update_data.get('last_name') or current_user.last_name
                recalculate_pending_buyer_orders(current_user.id, {
                    'region': update_data.get('region'),
                    'province': update_data.get('province'),
                    'city': update_data.get('city'),
                    'barangay': update_data.get('barangay'),
                    'street_name': update_data.get('street_name'),
                    'building_number': update_data.get('building_number'),
                    'postal_code': update_data.get('postal_code'),
                })
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('buyer.dashboard', tab='account'))
            
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
    
    # ── Fetch profile data ─────────────────────────────────────────────
    profile_data = {}
    try:
        prof_r = supabase.table('profiles').select('*').eq('user_id', str(current_user.id)).execute()
        if prof_r.data:
            profile_data = prof_r.data[0]
    except Exception:
        pass
    
    # ── New arrivals (8 latest active products) ──────────────────────────
    new_products = []
    try:
        r = supabase.table('products').select('*').eq('is_active', True).eq('is_deleted', False)\
              .order('created_at', desc=True).limit(8).execute()
        new_products = r.data or []
        for p in new_products:
            annotate_sale(p)
    except Exception:
        pass

    # ── Best-selling products (top 8 by total qty sold) ──────────────────
    best_products = []
    try:
        items_r = supabase.table('order_items').select('product_id, quantity').execute()
        items   = items_r.data or []
        counts  = Counter()
        for i in items:
            counts[i['product_id']] += (i.get('quantity') or 1)
        top_pids = [pid for pid, _ in counts.most_common(8)]
        if top_pids:
            pr = supabase.table('products').select('*').in_('id', top_pids).eq('is_active', True).eq('is_deleted', False).execute()
            pid_map = {p['id']: p for p in (pr.data or [])}
            best_products = [pid_map[pid] for pid in top_pids if pid in pid_map]
            for p in best_products:
                annotate_sale(p)
    except Exception:
        pass

    # Fall back to newest if no order history yet
    if not best_products:
        best_products = new_products[:8]

    # ── Best-selling stores (top 6 sellers by number of orders) ──────────
    best_stores = []
    try:
        orders_r = supabase.table('orders').select('seller_id').execute()
        orders   = orders_r.data or []
        s_counts = Counter(o['seller_id'] for o in orders if o.get('seller_id'))
        top_sids = [sid for sid, _ in s_counts.most_common(6)]
        if not top_sids:
            # No orders yet — just show any active sellers
            any_s = supabase.table('sellers').select('id').limit(6).execute()
            top_sids = [s['id'] for s in (any_s.data or [])]
        if top_sids:
            sellers_r = supabase.table('sellers').select('id,user_id,shop_name,shop_description').in_('id', top_sids).execute()
            for s in (sellers_r.data or []):
                # Grab first product image as store avatar
                prod_r = supabase.table('products').select('images').eq('seller_id', s['id'])\
                           .eq('is_active', True).limit(1).execute()
                avatar = None
                if prod_r.data:
                    imgs = prod_r.data[0].get('images') or []
                    avatar = imgs[0] if imgs else None
                s['avatar']    = avatar
                s['order_count'] = s_counts.get(s['id'], 0)
                best_stores.append(s)
    except Exception:
        pass

    # ── Buyer stats ───────────────────────────────────────────────────────
    stats = {'orders': 0, 'wishlist': 0}
    try:
        order_count = supabase.table('orders').select('id', count='exact')\
                        .eq('buyer_id', current_user.id).execute()
        stats['orders'] = order_count.count or 0
    except Exception:
        pass
    try:
        wl_count = supabase.table('wishlists').select('id', count='exact')\
                     .eq('buyer_id', current_user.id).execute()
        stats['wishlist'] = wl_count.count or 0
    except Exception:
        pass

    # ── Recently viewed products (from session, most recent first) ─────────
    recently_viewed = []
    rv_ids = session.get('recently_viewed') or []
    if rv_ids:
        try:
            rv_rows = supabase.table('products').select(
                'id,name,price,images,condition'
            ).in_('id', rv_ids).eq('is_active', True).eq('is_deleted', False).execute().data or []
            # Preserve the session order (most recently viewed first)
            rv_map = {p['id']: p for p in rv_rows}
            recently_viewed = [rv_map[i] for i in rv_ids if i in rv_map]
            for p in recently_viewed:
                annotate_sale(p)
        except Exception:
            pass

    # ── Shops the buyer follows ───────────────────────────────────────────
    followed_shops = []
    try:
        sf_rows = supabase.table('seller_follows').select('seller_id') \
            .eq('buyer_id', str(current_user.id)) \
            .order('created_at', desc=True).execute().data or []
        followed_ids = [r['seller_id'] for r in sf_rows]
        if followed_ids:
            sellers_r = supabase.table('sellers').select('id,user_id,shop_name') \
                .in_('id', followed_ids).execute().data or []
            s_map = {s['id']: s for s in sellers_r}
            for sid in followed_ids:
                if sid not in s_map:
                    continue
                s = dict(s_map[sid])
                # Grab first product image as avatar
                try:
                    av_r = supabase.table('products').select('images') \
                        .eq('seller_id', sid).eq('is_active', True).limit(1).execute()
                    imgs = (av_r.data[0].get('images') or []) if av_r.data else []
                    s['avatar'] = imgs[0] if imgs else None
                except Exception:
                    s['avatar'] = None
                followed_shops.append(s)
    except Exception:
        pass

    # ── Wishlisted IDs (for heart buttons) ───────────────────────────────
    wishlisted_ids = set()
    try:
        all_pids = [p['id'] for p in recently_viewed + new_products + best_products]
        if all_pids:
            wl_r = supabase.table('wishlists').select('product_id') \
                     .eq('buyer_id', current_user.id) \
                     .in_('product_id', all_pids).execute()
            wishlisted_ids = {row['product_id'] for row in (wl_r.data or [])}
    except Exception:
        pass

    # ── Buyer's orders by status ────────────────────────────────────────────
    buyer_orders = []
    orders_by_status = {
        'all': [],               # All orders
        'pending': [],           # Order Placed
        'confirmed': [],         # Confirmed
        'preparing': [],         # Preparing
        'ready_for_pickup': [],  # Ready for Pickup
        'out_for_delivery': [],  # Out for Delivery
        'delivered': [],         # Delivered
        'completed': []          # Completed
    }
    
    try:
        # Fetch all orders (no pagination for dashboard, just last 50)
        orders_r = supabase.table('orders').select('*') \
            .eq('buyer_id', current_user.id) \
            .order('created_at', desc=True) \
            .limit(50) \
            .execute()
        orders_data = orders_r.data or []
        print(f'[DEBUG] Dashboard fetched {len(orders_data)} orders for buyer {current_user.id}')
        
        # Fetch items for each order
        for order in orders_data:
            try:
                # Fetch order items with product join (same as orders.py)
                items_res = supabase.table('order_items') \
                    .select('quantity, price, products(id, name, images), product_variants(name)') \
                    .eq('order_id', order['id']) \
                    .limit(4) \
                    .execute()
                order['_items'] = items_res.data or []
                print(f'[DEBUG] Order {order["id"][:8]} has {len(order["_items"])} items')
                
                # Get seller info if needed
                if order.get('seller_id'):
                    try:
                        seller_r = supabase.table('sellers').select('shop_name') \
                            .eq('id', order['seller_id']).single().execute()
                        order['shop_name'] = seller_r.data.get('shop_name', 'Unknown Store') if seller_r.data else 'Unknown Store'
                    except Exception:
                        order['shop_name'] = 'Unknown Store'
                else:
                    order['shop_name'] = 'Unknown Store'
                
                # Add to all orders
                buyer_orders.append(order)
                orders_by_status['all'].append(order)
                
                # Add to status-specific list
                status = order.get('status', 'pending')
                if status in orders_by_status:
                    orders_by_status[status].append(order)
                    print(f'[DEBUG] Order {order["id"][:8]} status={status}')
                else:
                    print(f'[DEBUG] Order {order["id"][:8]} has unknown status: {status}')
                    
            except Exception as item_err:
                print(f'[DEBUG] Error processing order {order.get("id")}: {item_err}')
                import traceback
                traceback.print_exc()
                continue
        
        print(f'[DEBUG] Order summary: all={len(orders_by_status["all"])}, pending={len(orders_by_status["pending"])}, confirmed={len(orders_by_status["confirmed"])}, preparing={len(orders_by_status["preparing"])}, ready_for_pickup={len(orders_by_status["ready_for_pickup"])}, out_for_delivery={len(orders_by_status["out_for_delivery"])}, delivered={len(orders_by_status["delivered"])}, completed={len(orders_by_status["completed"])}')
                
    except Exception as e:
        print(f'[buyer.dashboard] Error fetching orders: {e}')
        import traceback
        traceback.print_exc()

    # Determine active tab from query parameter
    active_tab = request.args.get('tab', 'purchases')
    
    return render_template('buyer/dashboard.html',
                           new_products=new_products,
                           best_products=best_products,
                           best_stores=best_stores,
                           stats=stats,
                           recently_viewed=recently_viewed,
                           followed_shops=followed_shops,
                           wishlisted_ids=wishlisted_ids,
                           buyer_orders=buyer_orders,
                           orders_by_status=orders_by_status,
                           profile_data=profile_data,
                           active_tab=active_tab)
