"""Buyer wishlist route."""
from flask import render_template, flash, jsonify, request, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.utils.pagination import paginate_list
from .utils import buyer_bp


@buyer_bp.route('/wishlist')
@login_required
def wishlist():
    try:
        result = (
            supabase.table('wishlists')
            .select('*, products(*)')
            .eq('buyer_id', current_user.id)
            .execute()
        )
        items = [row['products'] for row in (result.data or []) if row.get('products')]
    except Exception:
        items = []
    pag = paginate_list(items, per_page=20)
    return render_template('buyer/wishlist.html', wishlist_items=pag.items, pagination=pag)


@buyer_bp.route('/wishlist/toggle/<product_id>', methods=['POST'])
@login_required
def toggle_wishlist(product_id):
    """AJAX: add or remove a product from the current user's wishlist.
    Also handles regular form POST (from Favorites page) and redirects back."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        existing = supabase.table('wishlists').select('id') \
            .eq('buyer_id', current_user.id).eq('product_id', product_id).execute()
        if existing.data:
            supabase.table('wishlists').delete() \
                .eq('buyer_id', current_user.id).eq('product_id', product_id).execute()
            wishlisted = False
        else:
            supabase.table('wishlists').insert({
                'buyer_id': current_user.id,
                'product_id': product_id,
            }).execute()
            wishlisted = True
        if is_ajax:
            return jsonify({'success': True, 'wishlisted': wishlisted})
        # Form POST from the Favorites page — redirect back
        if not wishlisted:
            flash('Removed from Favorites||The item has been removed from your favorites.', 'info')
        return redirect(request.referrer or url_for('buyer.wishlist'))
    except Exception as e:
        print(f'[toggle_wishlist] ERROR product={product_id}: {e}')
        if is_ajax:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Could not update favorites: {e}', 'error')
        return redirect(url_for('buyer.wishlist'))
