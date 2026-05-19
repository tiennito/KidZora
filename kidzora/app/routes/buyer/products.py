"""Buyer product browsing + seller shop routes."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, request, flash, session
from flask_login import current_user

from app.extensions import supabase_admin as supabase
from app.utils.pagination import paginate_list
from app.utils.pricing import annotate_sale
from .utils import buyer_bp, buyer_required


def _relative_time(dt_str):
    """Return a human-readable 'X ago' string from an ISO datetime string."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        days = (now - dt).days
        if days < 1:
            return 'Today'
        if days < 30:
            return f'{days} day{"s" if days != 1 else ""} ago'
        months = days // 30
        if months < 12:
            return f'{months} month{"s" if months != 1 else ""} ago'
        years = days // 365
        return f'{years} year{"s" if years != 1 else ""} ago'
    except Exception:
        return '—'


_CATEGORIES  = ['Toys', 'Clothing', 'Books', 'Educational', 'Safety', 'Accessories', 'Other']
_AGE_GROUPS  = ['0-2', '3-5', '6-8', '9-12']
_CONDITIONS  = ['new', 'like_new', 'good', 'fair']
_SORT_OPTS   = [
    ('newest',     'Newest First'),
    ('oldest',     'Oldest First'),
    ('price_asc',  'Price: Low → High'),
    ('price_desc', 'Price: High → Low'),
    ('name_asc',   'Name A → Z'),
]


@buyer_bp.route('/browse')
def browse_products():
    q         = request.args.get('q', '').strip()
    category  = request.args.get('category', '').strip()
    age_group = request.args.get('age_group', '').strip()
    condition = request.args.get('condition', '').strip()
    sort      = request.args.get('sort', 'newest').strip()

    try:
        min_price = float(request.args.get('min_price') or 0)
    except (ValueError, TypeError):
        min_price = 0.0
    try:
        max_price = float(request.args.get('max_price') or 0)
    except (ValueError, TypeError):
        max_price = 0.0

    try:
        query = supabase.table('products').select('*').eq('is_active', True).eq('is_deleted', False)

        # ── exact-match filters (all executed server-side) ────────────────
        if category:
            # Normalize category to match one of the valid categories (case-insensitive check)
            normalized_category = None
            for cat in _CATEGORIES:
                if cat.lower() == category.lower():
                    normalized_category = cat
                    break
            if normalized_category:
                query = query.ilike('category', normalized_category)
        if age_group and age_group in _AGE_GROUPS:
            query = query.eq('age_group', age_group)
        if condition and condition in _CONDITIONS:
            query = query.eq('condition', condition)
        if min_price > 0:
            query = query.gte('price', min_price)
        if max_price > 0:
            query = query.lte('price', max_price)

        # ── full-text search across name + description ────────────────────
        if q:
            # Sanitise: remove characters that break PostgREST filter syntax
            safe_q = q.replace('%', '').replace("'", '').replace('"', '').replace(',', '')
            try:
                query = query.or_(
                    f'name.ilike.%{safe_q}%,description.ilike.%{safe_q}%'
                )
            except Exception:
                # Fallback: apply name ilike only at DB level; description filtered in Python
                query = query.ilike('name', f'%{safe_q}%')

        # ── sort ──────────────────────────────────────────────────────────
        if sort == 'price_asc':
            query = query.order('price', desc=False)
        elif sort == 'price_desc':
            query = query.order('price', desc=True)
        elif sort == 'name_asc':
            query = query.order('name', desc=False)
        elif sort == 'oldest':
            query = query.order('created_at', desc=False)
        else:
            query = query.order('created_at', desc=True)

        product_list = query.execute().data or []

        # ── Python-side description fallback (if or_ was not available) ──
        if q and product_list:
            ql = q.lower()
            # Check if any result lacks q in name — means or_ worked; skip re-filter
            any_desc_only = any(
                ql not in (p.get('name') or '').lower()
                for p in product_list
            )
            if not any_desc_only:
                # or_ may not have fired — add description matches from a second pass
                try:
                    desc_rows = (
                        supabase.table('products')
                        .select('*')
                        .eq('is_active', True)
                        .ilike('description', f'%{safe_q}%')
                        .execute()
                        .data or []
                    )
                    existing_ids = {p['id'] for p in product_list}
                    for p in desc_rows:
                        if p['id'] not in existing_ids:
                            product_list.append(p)
                except Exception:
                    pass

    except Exception as exc:
        flash(f'Could not load products: {exc}', 'error')
        product_list = []

    # ── Attach seller shop names for attribution on browse cards ─────────
    _seller_ids = list({p['seller_id'] for p in product_list if p.get('seller_id')})
    _seller_name_map = {}
    if _seller_ids:
        try:
            sel_r = supabase.table('sellers').select('id,shop_name') \
                .in_('id', _seller_ids).execute()
            _seller_name_map = {s['id']: s['shop_name'] for s in (sel_r.data or [])}
        except Exception:
            pass
    for p in product_list:
        p['_shop_name'] = _seller_name_map.get(p.get('seller_id') or '', '')
        annotate_sale(p)

    pag = paginate_list(product_list, per_page=20)
    return render_template(
        'buyer/browse.html',
        pagination=pag,
        products=pag.items,
        q=q,
        category=category,
        age_group=age_group,
        condition=condition,
        min_price=min_price or '',
        max_price=max_price or '',
        sort=sort,
        categories=_CATEGORIES,
        age_groups=_AGE_GROUPS,
        conditions=_CONDITIONS,
        sort_opts=_SORT_OPTS,
    )


@buyer_bp.route('/shop/<seller_id>')
def seller_shop(seller_id):
    """Show all active products from one seller, plus store info."""
    seller = None
    try:
        s_r = supabase.table('sellers').select('id,user_id,shop_name,shop_description,shop_banner_url,about_store').eq('id', seller_id).execute()
        if s_r.data:
            s = s_r.data[0]
            p_r = supabase.table('profiles').select('first_name,last_name,business_name,city,province,avatar_url').eq('id', s['user_id']).execute()
            if p_r.data:
                seller = {**s, **p_r.data[0]}
            else:
                seller = s
    except Exception:
        pass

    if not seller:
        flash('Store not found.', 'error')
        return redirect(url_for('buyer.browse_products'))

    # First product image as store avatar
    try:
        av_r = supabase.table('products').select('images').eq('seller_id', seller_id)\
                 .eq('is_active', True).limit(1).execute()
        imgs = (av_r.data[0].get('images') or []) if av_r.data else []
        seller['avatar'] = imgs[0] if imgs else None
    except Exception:
        seller['avatar'] = None

    products = []
    try:
        pr = supabase.table('products').select('*').eq('seller_id', seller_id).eq('is_active', True)\
               .eq('is_deleted', False).order('created_at', desc=True).execute()
        products = pr.data or []
    except Exception:
        pass

    # ── Follow state + follower count ─────────────────────────────────────
    is_following = False
    follower_count = 0
    try:
        cnt_r = supabase.table('seller_follows').select('id', count='exact') \
            .eq('seller_id', seller_id).execute()
        follower_count = cnt_r.count or 0
    except Exception:
        pass
    if current_user.is_authenticated:
        try:
            sf_r = supabase.table('seller_follows').select('id') \
                .eq('buyer_id', str(current_user.id)) \
                .eq('seller_id', seller_id).execute()
            is_following = bool(sf_r.data)
        except Exception:
            pass

    # ── Wishlist state for this page ──────────────────────────────────────
    wishlisted_ids = set()
    if current_user.is_authenticated and products:
        try:
            pids = [p['id'] for p in products]
            wl_r = supabase.table('wishlists').select('product_id') \
                .eq('buyer_id', str(current_user.id)) \
                .in_('product_id', pids).execute()
            wishlisted_ids = {row['product_id'] for row in (wl_r.data or [])}
        except Exception:
            pass

    return render_template('buyer/shop.html', seller=seller, products=products,
                           is_following=is_following, follower_count=follower_count,
                           wishlisted_ids=wishlisted_ids)


# ── Slug-based SEO URL ────────────────────────────────────────────────────────

@buyer_bp.route('/p/<slug>')
def product_detail_by_slug(slug):
    """SEO-friendly product URL — resolves slug to UUID then renders the same detail page."""
    try:
        r = supabase.table('products').select('id') \
            .eq('slug', slug).eq('is_active', True).eq('is_deleted', False) \
            .single().execute()
        product_id = r.data['id'] if r.data else None
    except Exception:
        product_id = None
    if not product_id:
        flash('Product not found.', 'error')
        return redirect(url_for('buyer.browse_products'))
    return _render_product_detail(product_id)


@buyer_bp.route('/product/<product_id>')
def product_detail(product_id):
    return _render_product_detail(product_id)


def _render_product_detail(product_id):
    try:
        p = supabase.table('products').select('*').eq('id', product_id).eq('is_active', True).eq('is_deleted', False).single().execute().data
    except Exception:
        p = None
    if not p:
        flash('Product not found.', 'error')
        return redirect(url_for('buyer.browse_products'))

    # Annotate effective / sale price
    annotate_sale(p)

    # Ensure images is always a list
    imgs = p.get('images')
    if not isinstance(imgs, list):
        imgs = []
    p['images']    = imgs
    p['image_url'] = imgs[0] if imgs else None
    print(f"[DEBUG product_detail] id={product_id} images={imgs}")

    # Get seller info: products.seller_id → sellers.user_id → profiles
    seller = None
    try:
        seller_row = supabase.table('sellers').select(
            'id,user_id,shop_name,shop_description,created_at'
        ).eq('id', p['seller_id']).execute().data
        if seller_row:
            profile_row = supabase.table('profiles').select(
                'first_name,last_name,business_name,city,province,avatar_url'
            ).eq('id', seller_row[0]['user_id']).execute().data
            if profile_row:
                seller = {**seller_row[0], **profile_row[0]}
            else:
                seller = dict(seller_row[0])

            # Seller stats ──────────────────────────────────
            if seller:
                # Product count
                try:
                    pc_r = supabase.table('products').select('id', count='exact') \
                        .eq('seller_id', seller['id']).eq('is_active', True).execute()
                    seller['product_count'] = pc_r.count or 0
                except Exception:
                    seller['product_count'] = 0

                # Avg rating & rating count across all seller products
                try:
                    all_prod = supabase.table('products').select('id') \
                        .eq('seller_id', seller['id']).execute().data or []
                    all_pids = [r['id'] for r in all_prod]
                    if all_pids:
                        rev_r = supabase.table('product_reviews').select('rating') \
                            .in_('product_id', all_pids).execute().data or []
                        seller['review_count'] = len(rev_r)
                        seller['avg_rating'] = round(
                            sum(r['rating'] for r in rev_r) / len(rev_r), 1
                        ) if rev_r else 0.0
                    else:
                        seller['review_count'] = 0
                        seller['avg_rating'] = 0.0
                except Exception:
                    seller['review_count'] = 0
                    seller['avg_rating'] = 0.0

                # First product image as avatar
                try:
                    av_r = supabase.table('products').select('images') \
                        .eq('seller_id', seller['id']).eq('is_active', True).limit(1).execute()
                    imgs = (av_r.data[0].get('images') or []) if av_r.data else []
                    seller['avatar'] = imgs[0] if imgs else None
                except Exception:
                    seller['avatar'] = None

                # Joined relative time
                seller['joined'] = _relative_time(seller.get('created_at', ''))

    except Exception:
        pass

    # Load product variants
    variants = []
    try:
        v_r = supabase.table('product_variants').select('*').eq('product_id', product_id).order('sort_order').execute()
        variants = v_r.data or []
    except Exception:
        pass

    # ── Reviews ────────────────────────────────────────────────────────────
    reviews        = []
    avg_rating     = 0.0
    rating_dist    = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    can_review     = False
    existing_review = None
    my_helpful_ids  = set()

    try:
        r_res = supabase.table('product_reviews') \
            .select('*') \
            .eq('product_id', product_id) \
            .order('created_at', desc=True) \
            .execute()
        reviews = r_res.data or []
    except Exception:
        reviews = []

    # Attach reviewer first names in bulk
    if reviews:
        buyer_ids = list({r['buyer_id'] for r in reviews})
        try:
            prof_res = supabase.table('profiles') \
                .select('id, first_name, last_name') \
                .in_('id', buyer_ids).execute()
            name_map = {p['id']: p for p in (prof_res.data or [])}
        except Exception:
            name_map = {}
        for r in reviews:
            prof = name_map.get(r['buyer_id'], {})
            r['_reviewer_name'] = (prof.get('first_name') or 'Anonymous').strip() or 'Anonymous'

        # Rating stats
        total = len(reviews)
        rating_sum = sum(r['rating'] for r in reviews)
        avg_rating = round(rating_sum / total, 1) if total else 0.0
        for r in reviews:
            rating_dist[r['rating']] = rating_dist.get(r['rating'], 0) + 1

    # Current user: can they review? have they already?
    buyer_ordered_variants = []   # variants the buyer has actually purchased

    if current_user.is_authenticated:
        existing_review = next((r for r in reviews if r['buyer_id'] == current_user.id), None)
        if not existing_review:
            # Check for a completed order containing this product
            try:
                oi_res = supabase.table('order_items') \
                    .select('order_id, variant_id, orders!inner(buyer_id, status)') \
                    .eq('product_id', product_id) \
                    .eq('orders.buyer_id', current_user.id) \
                    .eq('orders.status', 'completed') \
                    .execute()
                can_review = bool(oi_res.data)
            except Exception:
                can_review = False
        else:
            can_review = True  # allow edit

        # Collect unique variants the buyer ordered (for review variant picker)
        try:
            oi_all = supabase.table('order_items') \
                .select('variant_id, orders!inner(buyer_id, status)') \
                .eq('product_id', product_id) \
                .eq('orders.buyer_id', current_user.id) \
                .eq('orders.status', 'completed') \
                .execute()
            variant_ids_ordered = list({
                item['variant_id']
                for item in (oi_all.data or [])
                if item.get('variant_id')
            })
        except Exception:
            variant_ids_ordered = []

        if variant_ids_ordered:
            try:
                vv = supabase.table('product_variants').select('id,name') \
                    .in_('id', variant_ids_ordered).execute()
                buyer_ordered_variants = vv.data or []
            except Exception:
                buyer_ordered_variants = []

        # Which reviews did the current user find helpful?
        if reviews:
            try:
                hv_res = supabase.table('review_helpful_votes') \
                    .select('review_id') \
                    .eq('voter_id', current_user.id) \
                    .in_('review_id', [r['id'] for r in reviews]) \
                    .execute()
                my_helpful_ids = {row['review_id'] for row in (hv_res.data or [])}
            except Exception:
                my_helpful_ids = set()

    # ── Sold count ─────────────────────────────────────────────────────────
    sold_count = 0
    try:
        sold_r = supabase.table('order_items').select('id', count='exact') \
            .eq('product_id', product_id).execute()
        sold_count = sold_r.count or 0
    except Exception:
        sold_count = 0

    # ── Track this view in session (recently viewed, max 10) ──────────────
    rv = session.get('recently_viewed') or []
    pid_str = str(product_id)
    rv = [i for i in rv if i != pid_str]   # remove duplicate if present
    rv.insert(0, pid_str)                  # push to front
    session['recently_viewed'] = rv[:10]   # cap at 10
    session.modified = True

    # ── Wishlist status ────────────────────────────────────────────────────
    is_wishlisted = False
    if current_user.is_authenticated:
        try:
            wl_r = supabase.table('wishlists').select('id') \
                .eq('buyer_id', current_user.id).eq('product_id', product_id).execute()
            is_wishlisted = bool(wl_r.data)
        except Exception:
            is_wishlisted = False

    # ── From the same shop ────────────────────────────────────────────────
    same_shop = []
    if p.get('seller_id'):
        try:
            ss_r = supabase.table('products').select('id,name,price,images') \
                .eq('seller_id', p['seller_id']).eq('is_active', True) \
                .neq('id', product_id).order('created_at', desc=True).limit(12).execute()
            for sp in (ss_r.data or []):
                imgs = sp.get('images') or []
                same_shop.append({**sp, 'image_url': imgs[0] if imgs else None})
        except Exception:
            same_shop = []

    # ── You may also like (same category, sorted by sold count) ───────────
    also_like = []
    if p.get('category'):
        try:
            al_r = supabase.table('products').select('id,name,price,images') \
                .eq('category', p['category']).eq('is_active', True) \
                .neq('id', product_id).order('created_at', desc=True).limit(20).execute()
            al_products = al_r.data or []
            # Fetch sold counts for ranking
            al_ids = [ap['id'] for ap in al_products]
            sold_map = {}
            if al_ids:
                try:
                    oi_r = supabase.table('order_items') \
                        .select('product_id', count='exact') \
                        .in_('product_id', al_ids).execute()
                    for row in (oi_r.data or []):
                        pid = row.get('product_id')
                        sold_map[pid] = sold_map.get(pid, 0) + 1
                except Exception:
                    pass
            al_products.sort(key=lambda x: sold_map.get(x['id'], 0), reverse=True)
            for ap in al_products[:12]:
                imgs = ap.get('images') or []
                also_like.append({**ap,
                    'image_url': imgs[0] if imgs else None,
                    'sold_count': sold_map.get(ap['id'], 0),
                })
        except Exception:
            also_like = []

    # ── Follow state for this product's seller ────────────────────────────
    is_following_seller = False
    seller_follower_count = 0
    if seller:
        try:
            cnt_r = supabase.table('seller_follows').select('id', count='exact') \
                .eq('seller_id', seller['id']).execute()
            seller_follower_count = cnt_r.count or 0
        except Exception:
            pass
        if current_user.is_authenticated:
            try:
                sf_r = supabase.table('seller_follows').select('id') \
                    .eq('buyer_id', str(current_user.id)) \
                    .eq('seller_id', seller['id']).execute()
                is_following_seller = bool(sf_r.data)
            except Exception:
                pass

    # ── Canonical URL (slug-based when available) ─────────────────────
    if p.get('slug'):
        canonical_url = url_for('buyer.product_detail_by_slug', slug=p['slug'], _external=True)
    else:
        canonical_url = url_for('buyer.product_detail', product_id=product_id, _external=True)

    return render_template(
        'buyer/product_detail.html',
        product=p,
        seller=seller,
        variants=variants,
        reviews=reviews,
        avg_rating=avg_rating,
        rating_dist=rating_dist,
        can_review=can_review,
        existing_review=existing_review,
        my_helpful_ids=my_helpful_ids,
        buyer_ordered_variants=buyer_ordered_variants,
        sold_count=sold_count,
        is_wishlisted=is_wishlisted,
        same_shop=same_shop,
        also_like=also_like,
        is_following_seller=is_following_seller,
        seller_follower_count=seller_follower_count,
        canonical_url=canonical_url,
    )


@buyer_bp.route('/product/<product_id>/report', methods=['POST'])
@buyer_required
def report_product(product_id):
    reason = (request.form.get('reason') or '').strip()
    details = (request.form.get('details') or '').strip()

    if not reason:
        flash('Please select a reason for this report.', 'error')
        return redirect(url_for('buyer.product_detail', product_id=product_id))

    try:
        product = supabase.table('products').select('id, is_active, is_deleted').eq('id', product_id).single().execute().data
    except Exception:
        product = None

    if not product or product.get('is_deleted'):
        flash('Product not found.', 'error')
        return redirect(url_for('buyer.browse_products'))

    try:
        existing = supabase.table('product_reports').select('id, status') \
            .eq('product_id', product_id) \
            .eq('reporter_id', str(current_user.id)) \
            .eq('status', 'pending').limit(1).execute().data or []
        if existing:
            flash('You already have a pending report for this product.', 'warning')
            return redirect(url_for('buyer.product_detail', product_id=product_id))

        supabase.table('product_reports').insert({
            'product_id': product_id,
            'reporter_id': str(current_user.id),
            'reason': reason,
            'details': details or None,
            'status': 'pending',
        }).execute()

        flash('Report submitted. Our admin team will review this listing.', 'success')
    except Exception as exc:
        print(f'report_product error: {exc}')
        flash('Unable to submit report right now. Please try again.', 'error')

    return redirect(url_for('buyer.product_detail', product_id=product_id))
