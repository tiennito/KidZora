"""Admin orders route — view all orders and handle cancel requests."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import supabase_admin as supabase
from app.utils.decorators import admin_required
from app.utils.pagination import paginate_query
from .utils import admin_bp

_ALL_STATUSES = [
    'pending', 'confirmed', 'preparing',
    'ready_for_pickup', 'out_for_delivery',
    'delivered', 'completed', 'cancelled',
]


@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    status_filter = request.args.get('status', '')
    cancel_filter = request.args.get('cancel', '')   # 'pending' → only cancel requests

    try:
        query = supabase.table('orders').select('*', count='exact')
        if status_filter:
            query = query.eq('status', status_filter)
        if cancel_filter == 'pending':
            query = query.eq('cancel_requested', True).eq('cancel_status', 'pending_review')
        query = query.order('created_at', desc=True)
        pag = paginate_query(query, per_page=25)
        order_list = pag.items
    except Exception as e:
        flash(f'Could not load orders: {e}', 'error')
        from app.utils.pagination import Pagination
        pag = Pagination(items=[], page=1, per_page=25, total=0)
        order_list = []

    # Count pending cancel requests for the badge
    try:
        cancel_count = len(supabase.table('orders').select('id')
                           .eq('cancel_requested', True)
                           .eq('cancel_status', 'pending_review')
                           .execute().data or [])
    except Exception:
        cancel_count = 0

    # Resolve seller shop names
    seller_shops = {}
    seller_ids = list({o['seller_id'] for o in order_list if o.get('seller_id')})
    if seller_ids:
        try:
            rows = (
                supabase.table('sellers')
                .select('id, shop_name')
                .in_('id', seller_ids)
                .execute().data or []
            )
            seller_shops = {r['id']: r['shop_name'] for r in rows}
        except Exception:
            pass

    return render_template(
        'admin/orders.html',
        orders=order_list,
        pagination=pag,
        seller_shops=seller_shops,
        all_statuses=_ALL_STATUSES,
        selected_status=status_filter,
        cancel_filter=cancel_filter,
        cancel_count=cancel_count,
    )


@admin_bp.route('/orders/<order_id>')
@login_required
@admin_required
def order_detail(order_id):
    try:
        order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    except Exception as e:
        print(f"Error fetching order: {e}")
        order = None

    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('admin.orders'))

    try:
        items = (supabase.table('order_items')
                 .select('*, products(name, images), product_variants(name)')
                 .eq('order_id', order_id).execute().data or [])
    except Exception as e:
        print(f"Error fetching items: {e}")
        items = []

    # Fetch seller shop name - more robust approach
    seller_info = {}
    if order.get('seller_id'):
        seller_id = order['seller_id']
        print(f"\n[DEBUG] Looking for seller with ID: {seller_id}")
        try:
            # Query sellers table for shop_name only (email column doesn't exist)
            seller_response = supabase.table('sellers').select('id, shop_name').eq('id', seller_id).execute()
            print(f"[DEBUG] Seller response: {seller_response.data}")
            if seller_response.data and len(seller_response.data) > 0:
                seller_info = seller_response.data[0]
                print(f"[DEBUG] Seller info set to: {seller_info}")
            else:
                print(f"[DEBUG] No seller data found")
        except Exception as e:
            print(f"[DEBUG] Exception fetching seller: {type(e).__name__}: {e}")

    # Fetch buyer name - more robust approach
    buyer_info = {}
    if order.get('buyer_id'):
        buyer_id = order['buyer_id']
        print(f"[DEBUG] Looking for buyer with ID: {buyer_id}")
        try:
            buyer_response = supabase.table('profiles').select('id, first_name, last_name, email').eq('id', buyer_id).execute()
            print(f"[DEBUG] Buyer response: {buyer_response.data}")
            if buyer_response.data and len(buyer_response.data) > 0:
                buyer_info = buyer_response.data[0]
                print(f"[DEBUG] Buyer info set to: {buyer_info}")
            else:
                print(f"[DEBUG] No buyer data found")
        except Exception as e:
            print(f"[DEBUG] Exception fetching buyer: {type(e).__name__}: {e}")

    print(f"\n[DEBUG] Final seller_info: {seller_info}")
    print(f"[DEBUG] Final buyer_info: {buyer_info}\n")

    return render_template('admin/order_detail.html', order=order, items=items, seller_info=seller_info, buyer_info=buyer_info)


@admin_bp.route('/orders/<order_id>/cancel-review', methods=['POST'])
@login_required
@admin_required
def cancel_review(order_id):
    """Approve or reject a buyer's cancellation request directly from the orders list."""
    action = request.form.get('action')   # 'approve' or 'reject'

    if action not in ('approve', 'reject'):
        flash('Invalid action.', 'error')
        return redirect(url_for('admin.orders'))

    update = {'cancel_status': 'approved' if action == 'approve' else 'rejected'}
    if action == 'approve':
        update['status'] = 'cancelled'

    try:
        supabase.table('orders').update(update).eq('id', order_id).execute()
        label = 'approved' if action == 'approve' else 'rejected'
        flash(f'Cancellation {label}||The cancellation request has been {label}.', 'success')
    except Exception as e:
        flash(f'Could not update cancellation: {e}', 'error')

    # Return to the same filtered view the admin was on
    back = request.form.get('back_url', url_for('admin.orders'))
    return redirect(back)


@admin_bp.route('/orders/<order_id>/force-cancel', methods=['POST'])
@login_required
@admin_required
def force_cancel_order(order_id):
    """Admin can force-cancel any order regardless of status."""
    reason = request.form.get('reason', 'Cancelled by admin.').strip()

    try:
        supabase.table('orders').update({
            'status': 'cancelled',
            'cancel_requested': True,
            'cancel_reason': reason,
            'cancel_status': 'approved',
        }).eq('id', order_id).execute()
        flash('Order Cancelled||The order has been force-cancelled by admin.', 'success')
    except Exception as e:
        flash(f'Could not cancel order: {e}', 'error')

    return redirect(url_for('admin.order_detail', order_id=order_id))
