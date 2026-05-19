"""Seller product CRUD routes."""
import re
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import supabase_admin
from app.services.notify import push_new_product, LOW_STOCK_THRESHOLD
from app.utils.pagination import paginate_list
from app.utils.pricing import annotate_sale
from .utils import seller_bp, seller_required, _save_product_image, _get_seller_id

_CATEGORIES = ['Toys', 'Clothing', 'Books', 'Educational', 'Safety', 'Accessories', 'Other']
_AGE_GROUPS  = ['0-2 years', '3-5 years', '6-8 years', '9-12 years', '13+ years']


def _slugify(text: str) -> str:
    """Convert a string to a URL-safe slug, e.g. 'Wooden Blocks Set' → 'wooden-blocks-set'."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


def _unique_slug(base: str, exclude_id: str | None = None) -> str:
    """Append -2, -3, … until the slug is unique in the products table."""
    candidate = base
    n = 2
    while True:
        q = supabase_admin.table('products').select('id').eq('slug', candidate)
        if exclude_id:
            q = q.neq('id', exclude_id)
        r = q.execute()
        if not (r.data):
            return candidate
        candidate = f"{base}-{n}"
        n += 1


def _save_variants(product_id, seller_id):
    """Read variant fields from request and persist to product_variants table.
    Also syncs product.stock_quantity to the sum of all variant stocks."""
    count = int(request.form.get('variant_count', 0))
    rows = []
    for i in range(count):
        name = request.form.get(f'variant_name_{i}', '').strip()
        if not name:
            continue   # skip blank rows
        # Handle variant image
        image_url = request.form.get(f'variant_keep_image_{i}', '').strip()  # existing url
        file = request.files.get(f'variant_image_{i}')
        if file and file.filename:
            saved = _save_product_image(file, seller_id)
            if saved:
                image_url = saved
        rows.append({
            'product_id':      product_id,
            'name':            name,
            'image_url':       image_url or None,
            'price_modifier':  float(request.form.get(f'variant_price_{i}', 0) or 0),
            'stock_quantity':  int(request.form.get(f'variant_stock_{i}', 0) or 0),
            'sort_order':      i,
        })
    if rows:
        supabase_admin.table('product_variants').insert(rows).execute()
        # Sync product.stock_quantity = sum of all variant stocks
        total_stock = sum(r['stock_quantity'] for r in rows)
        supabase_admin.table('products').update({'stock_quantity': total_stock}).eq('id', product_id).execute()


@seller_bp.route('/products')
@login_required
@seller_required
def products():
    category    = request.args.get('category', '')
    status      = request.args.get('status', '')
    stock_status = request.args.get('stock_status', '')
    q           = request.args.get('q', '')

    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.dashboard'))
    try:
        query = supabase_admin.table('products').select('*').eq('seller_id', seller_id)
        if category:
            query = query.eq('category', category)
        if status == 'archived':
            query = query.eq('is_deleted', True)
        else:
            query = query.eq('is_deleted', False)
            if status == 'active':
                query = query.eq('is_active', True)
            elif status == 'inactive':
                query = query.eq('is_active', False)
        product_list = query.order('created_at', desc=True).execute().data or []

        if q:
            product_list = [p for p in product_list if q.lower() in (p.get('name') or '').lower()]

        # Annotate each product with a stock status label + sale info
        for p in product_list:
            qty = p.get('stock_quantity') or 0
            if qty == 0:
                p['_stock_status'] = 'oos'
            elif qty <= LOW_STOCK_THRESHOLD:
                p['_stock_status'] = 'low'
            else:
                p['_stock_status'] = 'ok'
            annotate_sale(p)

        # Apply stock_status filter
        if stock_status in ('oos', 'low'):
            product_list = [p for p in product_list if p['_stock_status'] == stock_status]
        elif stock_status == 'alert':
            product_list = [p for p in product_list if p['_stock_status'] in ('oos', 'low')]

        # Sort: out-of-stock first → low stock → normal
        _order = {'oos': 0, 'low': 1, 'ok': 2}
        product_list.sort(key=lambda p: _order[p['_stock_status']])

        oos_count = sum(1 for p in product_list if p['_stock_status'] == 'oos')
        low_count = sum(1 for p in product_list if p['_stock_status'] == 'low')
    except Exception as e:
        flash(f'Could not load products: {e}', 'error')
        product_list = []
        oos_count = 0
        low_count = 0

    # Archived count (for the filter badge — always a quick count)
    archived_count = 0
    try:
        arch_r = supabase_admin.table('products').select('id', count='exact') \
            .eq('seller_id', seller_id).eq('is_deleted', True).execute()
        archived_count = arch_r.count or 0
    except Exception:
        pass

    pag = paginate_list(product_list, per_page=20)
    return render_template(
        'seller/products.html',
        products=pag.items,
        pagination=pag,
        categories=_CATEGORIES,
        selected_category=category,
        selected_status=status,
        selected_stock_status=stock_status,
        oos_count=oos_count,
        low_count=low_count,
        low_stock_threshold=LOW_STOCK_THRESHOLD,
        archived_count=archived_count,
        q=q,
    )


@seller_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@seller_required
def product_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Product name is required.', 'error')
            return render_template('seller/product_form.html', categories=_CATEGORIES,
                                   age_groups=_AGE_GROUPS, product=None, variants=[])

        # Collect all uploaded images
        seller_id = _get_seller_id()
        if not seller_id:
            flash('Seller profile not found. Please contact support.', 'error')
            return render_template('seller/product_form.html', categories=_CATEGORIES,
                                   age_groups=_AGE_GROUPS, product=None, variants=[])
        image_urls = []
        for file in request.files.getlist('images'):
            url = _save_product_image(file, seller_id)
            if url:
                image_urls.append(url)

        # SEO fields
        _raw_slug = request.form.get('slug', '').strip()
        slug = _unique_slug(_slugify(_raw_slug or name))
        meta_title = request.form.get('meta_title', '').strip() or None
        meta_desc  = request.form.get('meta_description', '').strip() or None

        try:
            res = supabase_admin.table('products').insert({
                'seller_id':        seller_id,
                'name':             name,
                'description':      request.form.get('description', '').strip(),
                'price':            float(request.form.get('price', 0)),
                'sale_price':       float(request.form.get('sale_price') or 0) or None,
                'sale_starts_at':   request.form.get('sale_starts_at') or None,
                'sale_ends_at':     request.form.get('sale_ends_at') or None,
                'stock_quantity':   int(request.form.get('stock_quantity', 0)),
                'category':         request.form.get('category', ''),
                'age_group':        request.form.get('age_group', ''),
                'condition':        request.form.get('condition', 'new'),
                'is_active':        request.form.get('is_active') == 'on',
                'images':           image_urls if image_urls else None,
                'slug':             slug,
                'meta_title':       meta_title,
                'meta_description': meta_desc,
            }).execute()
            new_product_id = res.data[0]['id'] if res.data else None
            if new_product_id:
                _save_variants(new_product_id, seller_id)
                # Notify followers if the product is published immediately
                if request.form.get('is_active') == 'on':
                    try:
                        s_r = supabase_admin.table('sellers').select('shop_name') \
                            .eq('id', seller_id).execute().data
                        shop_name = s_r[0]['shop_name'] if s_r else 'A seller'
                    except Exception:
                        shop_name = 'A seller'
                    push_new_product(
                        seller_id=seller_id,
                        product_id=new_product_id,
                        product_name=name,
                        shop_name=shop_name,
                    )
            print(f"[DEBUG product_add] saved images: {image_urls}")
            flash('Product Added!||Your product is now listed in your store.', 'success')
            return redirect(url_for('seller.products'))
        except Exception as e:
            flash(f'Failed to add product: {e}', 'error')

    return render_template('seller/product_form.html', categories=_CATEGORIES,
                           age_groups=_AGE_GROUPS, product=None, variants=[])


@seller_bp.route('/products/<product_id>/edit', methods=['GET', 'POST'])
@login_required
@seller_required
def product_edit(product_id):
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.products'))
    try:
        product = (supabase_admin.table('products').select('*')
                   .eq('id', product_id).eq('seller_id', seller_id)
                   .single().execute().data)
    except Exception:
        product = None

    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('seller.products'))

    # Load existing variants
    try:
        variants = (supabase_admin.table('product_variants').select('*')
                    .eq('product_id', product_id)
                    .order('sort_order').execute().data or [])
    except Exception:
        variants = []

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Product name is required.', 'error')
            return render_template('seller/product_form.html', categories=_CATEGORIES,
                                   age_groups=_AGE_GROUPS, product=product, variants=variants)

        # SEO fields
        _raw_slug = request.form.get('slug', '').strip()
        slug = _unique_slug(_slugify(_raw_slug or name), exclude_id=product_id)
        meta_title = request.form.get('meta_title', '').strip() or None
        meta_desc  = request.form.get('meta_description', '').strip() or None

        update_data = {
            'name':             name,
            'description':      request.form.get('description', '').strip(),
            'price':            float(request.form.get('price', 0)),
            'sale_price':       float(request.form.get('sale_price') or 0) or None,
            'sale_starts_at':   request.form.get('sale_starts_at') or None,
            'sale_ends_at':     request.form.get('sale_ends_at') or None,
            'stock_quantity':   int(request.form.get('stock_quantity', 0)),
            'category':         request.form.get('category', ''),
            'age_group':        request.form.get('age_group', ''),
            'condition':        request.form.get('condition', 'new'),
            'is_active':        request.form.get('is_active') == 'on',
            'slug':             slug,
            'meta_title':       meta_title,
            'meta_description': meta_desc,
        }

        # Handle image updates — respect drag-reorder (images_order) and removals
        new_urls = []
        for file in request.files.getlist('images'):
            url = _save_product_image(file, seller_id)
            if url:
                new_urls.append(url)

        remove_list = [u for u in request.form.get('remove_images', '').split(',') if u]
        images_order_raw = request.form.get('images_order', '').strip()

        if images_order_raw:
            # Use the explicit drag-drop order; filter out any removed images
            ordered_existing = [u for u in images_order_raw.split(',') if u and u not in remove_list]
        elif remove_list:
            existing = product.get('images') or []
            ordered_existing = [u for u in existing if u not in remove_list]
        else:
            ordered_existing = product.get('images') or []

        final_images = ordered_existing + new_urls
        update_data['images'] = final_images or None

        try:
            (supabase_admin.table('products').update(update_data)
             .eq('id', product_id).eq('seller_id', seller_id).execute())

            # Replace variants: delete all then re-insert
            supabase_admin.table('product_variants').delete().eq('product_id', product_id).execute()
            _save_variants(product_id, seller_id)

            flash('Product Updated!||Your changes have been saved to the database.', 'success')
            return redirect(url_for('seller.products'))
        except Exception as e:
            flash(f'Failed to update product: {e}', 'error')

    return render_template('seller/product_form.html', categories=_CATEGORIES,
                           age_groups=_AGE_GROUPS, product=product, variants=variants)


@seller_bp.route('/products/bulk-action', methods=['POST'])
@login_required
@seller_required
def products_bulk_action():
    """Bulk activate / deactivate / archive / restore for selected product IDs."""
    data   = request.get_json(force=True) or {}
    action = data.get('action', '')
    ids    = data.get('ids', [])

    _VALID_ACTIONS = {
        'activate':   {'is_active': True},
        'deactivate': {'is_active': False},
        'archive':    {'is_deleted': True, 'is_active': False},
        'restore':    {'is_deleted': False},
    }
    if not ids or action not in _VALID_ACTIONS:
        return jsonify({'success': False, 'error': 'invalid request'}), 400

    seller_id = _get_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'error': 'seller not found'}), 403

    updates = _VALID_ACTIONS[action]
    try:
        for pid in ids:
            (supabase_admin.table('products')
             .update(updates)
             .eq('id', str(pid))
             .eq('seller_id', seller_id)
             .execute())
        return jsonify({'success': True, 'count': len(ids)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@seller_bp.route('/products/<product_id>/delete', methods=['POST'])
@login_required
@seller_required
def product_delete(product_id):
    """Soft-delete: marks is_deleted=True and deactivates. Order history is preserved."""
    seller_id = _get_seller_id()
    try:
        (supabase_admin.table('products')
         .update({'is_deleted': True, 'is_active': False})
         .eq('id', product_id).eq('seller_id', seller_id or current_user.id).execute())
        flash('Product Archived||The product is hidden from buyers. You can restore it from the Archived filter.', 'success')
    except Exception as e:
        flash(f'Could not archive product: {e}', 'error')
    return redirect(url_for('seller.products'))


@seller_bp.route('/products/<product_id>/restore', methods=['POST'])
@login_required
@seller_required
def product_restore(product_id):
    """Undo soft-delete: marks is_deleted=False (keeps is_active=False so seller can review first)."""
    seller_id = _get_seller_id()
    try:
        (supabase_admin.table('products')
         .update({'is_deleted': False})
         .eq('id', product_id).eq('seller_id', seller_id or current_user.id).execute())
        flash('Product Restored||The product has been moved back to your inactive listings. Activate it when ready.', 'success')
    except Exception as e:
        flash(f'Could not restore product: {e}', 'error')
    return redirect(url_for('seller.products', status='archived'))


@seller_bp.route('/products/<product_id>/toggle', methods=['POST'])
@login_required
@seller_required
def product_toggle(product_id):
    seller_id = _get_seller_id()
    try:
        row = (supabase_admin.table('products').select('is_active')
               .eq('id', product_id).eq('seller_id', seller_id or current_user.id)
               .single().execute().data or {})
        new_state = not row.get('is_active', False)
        (supabase_admin.table('products').update({'is_active': new_state})
         .eq('id', product_id).eq('seller_id', seller_id or current_user.id).execute())
        return jsonify({'success': True, 'is_active': new_state})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
