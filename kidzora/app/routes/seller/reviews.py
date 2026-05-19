"""Seller – Product Reviews page.

Routes:
  GET  /seller/reviews              — list all reviews for this seller's products
  POST /seller/reviews/<id>/reply   — save / update a seller reply
  POST /seller/reviews/<id>/delete-reply — remove a seller reply
"""
from datetime import datetime, timezone

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import seller_bp, seller_required, _get_seller_id


# ─────────────────────────────────────────────────────────────
#  Helper
# ─────────────────────────────────────────────────────────────
def _star_label(r):
    return {5: 'Excellent', 4: 'Good', 3: 'Okay', 2: 'Poor', 1: 'Terrible'}.get(r, '')


# ─────────────────────────────────────────────────────────────
#  List reviews
# ─────────────────────────────────────────────────────────────
@seller_bp.route('/reviews')
@login_required
@seller_required
def reviews():
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.dashboard'))

    # ── All products for this seller (for filter dropdown)
    try:
        prod_r = supabase.table('products') \
            .select('id,name') \
            .eq('seller_id', seller_id) \
            .order('name') \
            .execute()
        products = prod_r.data or []
    except Exception:
        products = []

    product_ids = [p['id'] for p in products]

    # ── Filter params
    filter_product = request.args.get('product', '').strip()
    filter_rating  = request.args.get('rating', '').strip()
    filter_replied = request.args.get('replied', '').strip()   # 'yes' | 'no' | ''
    page           = max(1, request.args.get('page', 1, type=int))
    per_page       = 20

    # ── Fetch reviews
    review_list = []
    total        = 0

    if product_ids:
        try:
            # Which product IDs to query?
            target_ids = [filter_product] if filter_product and filter_product in product_ids \
                         else product_ids

            q = supabase.table('product_reviews') \
                .select(
                    'id,product_id,buyer_id,rating,title,body,'
                    'is_verified_purchase,helpful_count,media_urls,'
                    'variant_name,seller_reply,seller_reply_at,created_at'
                ) \
                .in_('product_id', target_ids) \
                .order('created_at', desc=True)

            if filter_rating:
                q = q.eq('rating', int(filter_rating))

            if filter_replied == 'yes':
                q = q.not_.is_('seller_reply', 'null')
            elif filter_replied == 'no':
                q = q.is_('seller_reply', 'null')

            all_r = q.execute().data or []

            # Enrich with product + buyer info
            # Build lookup maps
            prod_map = {p['id']: p for p in products}

            buyer_ids = list({r['buyer_id'] for r in all_r})
            buyer_map = {}
            if buyer_ids:
                try:
                    bp_r = supabase.table('profiles') \
                        .select('id,first_name,last_name,avatar_url') \
                        .in_('id', buyer_ids) \
                        .execute()
                    for b in (bp_r.data or []):
                        buyer_map[b['id']] = b
                except Exception:
                    pass

            for rv in all_r:
                rv['product']    = prod_map.get(rv['product_id'], {})
                byr              = buyer_map.get(rv['buyer_id'], {})
                rv['buyer_name'] = f"{byr.get('first_name','')  } {byr.get('last_name','')}".strip() or 'Anonymous'
                rv['buyer_avatar'] = byr.get('avatar_url') or ''
                rv['star_label'] = _star_label(rv['rating'])

            total       = len(all_r)
            start       = (page - 1) * per_page
            review_list = all_r[start:start + per_page]

        except Exception as e:
            flash(f'Could not load reviews||{e}', 'error')

    # ── KPI summary (always across ALL products, no filter applied)
    kpis = {'total': 0, 'avg': 0.0, 'unreplied': 0, 'five_star': 0}
    if product_ids:
        try:
            all_for_kpi = supabase.table('product_reviews') \
                .select('rating,seller_reply') \
                .in_('product_id', product_ids) \
                .execute().data or []
            kpis['total']     = len(all_for_kpi)
            kpis['avg']       = round(sum(r['rating'] for r in all_for_kpi) / len(all_for_kpi), 1) \
                                if all_for_kpi else 0.0
            kpis['unreplied'] = sum(1 for r in all_for_kpi if not r.get('seller_reply'))
            kpis['five_star'] = sum(1 for r in all_for_kpi if r['rating'] == 5)
        except Exception:
            pass

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'seller/reviews.html',
        reviews      = review_list,
        products     = products,
        kpis         = kpis,
        total        = total,
        page         = page,
        total_pages  = total_pages,
        per_page     = per_page,
        filter_product  = filter_product,
        filter_rating   = filter_rating,
        filter_replied  = filter_replied,
    )


# ─────────────────────────────────────────────────────────────
#  Save / update seller reply
# ─────────────────────────────────────────────────────────────
@seller_bp.route('/reviews/<review_id>/reply', methods=['POST'])
@login_required
@seller_required
def reply_review(review_id):
    seller_id = _get_seller_id()
    reply_text = (request.form.get('reply') or '').strip()

    if not reply_text:
        flash('Reply cannot be empty.', 'warning')
        return redirect(url_for('seller.reviews'))

    # Verify this review belongs to one of the seller's products
    try:
        rv = supabase.table('product_reviews') \
            .select('id,product_id,products!inner(seller_id)') \
            .eq('id', review_id) \
            .eq('products.seller_id', seller_id) \
            .execute().data
    except Exception:
        rv = None

    if not rv:
        flash('Review not found or access denied.', 'error')
        return redirect(url_for('seller.reviews'))

    try:
        supabase.table('product_reviews').update({
            'seller_reply':    reply_text,
            'seller_reply_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', review_id).execute()
        flash('Reply Saved!||Your response has been published on the product page.', 'success')
    except Exception as e:
        flash(f'Could not save reply||{e}', 'error')

    return redirect(url_for('seller.reviews') + f'#rev-{review_id}')


# ─────────────────────────────────────────────────────────────
#  Delete seller reply
# ─────────────────────────────────────────────────────────────
@seller_bp.route('/reviews/<review_id>/delete-reply', methods=['POST'])
@login_required
@seller_required
def delete_reply(review_id):
    seller_id = _get_seller_id()

    try:
        rv = supabase.table('product_reviews') \
            .select('id,product_id,products!inner(seller_id)') \
            .eq('id', review_id) \
            .eq('products.seller_id', seller_id) \
            .execute().data
    except Exception:
        rv = None

    if not rv:
        flash('Review not found or access denied.', 'error')
        return redirect(url_for('seller.reviews'))

    try:
        supabase.table('product_reviews').update({
            'seller_reply':    None,
            'seller_reply_at': None,
        }).eq('id', review_id).execute()
        flash('Reply removed.', 'info')
    except Exception as e:
        flash(f'Could not remove reply||{e}', 'error')

    return redirect(url_for('seller.reviews'))
