"""Buyer product reviews routes."""
import os
import uuid

from flask import redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import buyer_bp

# Allowed file extensions for review media
ALLOWED_REVIEW_MEDIA = {
    'jpg', 'jpeg', 'png', 'gif', 'webp',        # images
    'mp4', 'mov', 'avi', 'webm', 'mkv',          # videos
}


def _allowed_review_media(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_REVIEW_MEDIA


def _save_review_media(files, buyer_id):
    """Upload review media to Supabase Storage; return list of public URLs."""
    saved = []
    from app.utils.images import upload_to_storage, upload_raw_to_storage, is_image_ext

    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed_review_media(f.filename):
            continue
        ext  = f.filename.rsplit('.', 1)[1].lower()
        stem = uuid.uuid4().hex
        try:
            if is_image_ext(f.filename):
                storage_path = f'reviews/{buyer_id}/{stem}.webp'
                url = upload_to_storage(f, 'review-media', storage_path,
                                        max_width=1200, max_height=1200, quality=82)
            else:
                storage_path = f'reviews/{buyer_id}/{stem}.{ext}'
                url = upload_raw_to_storage(f, 'review-media', storage_path)
            saved.append(url)
        except Exception as e:
            print(f'[_save_review_media] upload failed: {e}')
    return saved


# ─────────────────────────────────────────────────────────────
#  Submit or update a review
# ─────────────────────────────────────────────────────────────
@buyer_bp.route('/product/<product_id>/review', methods=['POST'])
@login_required
def submit_review(product_id):
    rating = request.form.get('rating', type=int)
    title  = (request.form.get('title') or '').strip()[:120]
    body   = (request.form.get('body')  or '').strip()[:2000]

    if not rating or rating not in range(1, 6):
        flash('Invalid rating – please choose 1–5 stars.||Please pick a star rating before submitting.', 'error')
        return redirect(url_for('buyer.product_detail', product_id=product_id))

    buyer_id   = current_user.id
    variant_id = request.form.get('variant_id', '').strip() or None

    # ── Guard: check for at least one completed order containing this product
    try:
        oi_res = supabase.table('order_items') \
            .select('order_id, orders!inner(buyer_id, status)') \
            .eq('product_id', product_id) \
            .eq('orders.buyer_id', buyer_id) \
            .eq('orders.status', 'completed') \
            .limit(1) \
            .execute()
        eligible_items = oi_res.data or []
    except Exception:
        eligible_items = []

    if not eligible_items:
        flash('Reviews require a purchase||You can only review a product after completing an order that contains it.', 'warning')
        return redirect(url_for('buyer.product_detail', product_id=product_id))

    order_id = eligible_items[0]['order_id']

    # ── Resolve variant name
    variant_name = None
    if variant_id:
        try:
            vr = supabase.table('product_variants').select('name') \
                .eq('id', variant_id).single().execute().data
            variant_name = (vr or {}).get('name')
        except Exception:
            pass

    # ── Media: get existing media_urls (for edit case) then append new uploads
    existing_media: list = []
    try:
        ex = supabase.table('product_reviews') \
            .select('media_urls') \
            .eq('product_id', product_id) \
            .eq('buyer_id', buyer_id) \
            .execute().data
        if ex:
            existing_media = ex[0].get('media_urls') or []
    except Exception:
        pass

    new_files  = request.files.getlist('media')
    new_media  = _save_review_media(new_files, buyer_id)
    media_urls = existing_media + new_media

    # ── Upsert (insert or update if buyer already reviewed this product)
    try:
        supabase.table('product_reviews').upsert({
            'product_id':           product_id,
            'buyer_id':             buyer_id,
            'order_id':             order_id,
            'rating':               rating,
            'title':                title        or None,
            'body':                 body         or None,
            'is_verified_purchase': True,
            'variant_id':           variant_id   or None,
            'variant_name':         variant_name or None,
            'media_urls':           media_urls,
        }, on_conflict='product_id,buyer_id').execute()
    except Exception as e:
        flash(f'Could not save review||{e}', 'error')
        return redirect(url_for('buyer.product_detail', product_id=product_id))

    flash('Review Saved!||Your review has been published on this product page.', 'success')
    return redirect(url_for('buyer.product_detail', product_id=product_id) + '#reviews')


# ─────────────────────────────────────────────────────────────
#  Toggle "helpful" vote  (AJAX – returns JSON)
# ─────────────────────────────────────────────────────────────
@buyer_bp.route('/reviews/<review_id>/helpful', methods=['POST'])
@login_required
def toggle_helpful(review_id):
    voter_id = current_user.id

    # Check existing vote
    try:
        existing = supabase.table('review_helpful_votes') \
            .select('review_id') \
            .eq('review_id', review_id) \
            .eq('voter_id', voter_id) \
            .execute().data
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

    try:
        if existing:
            # Remove vote
            supabase.table('review_helpful_votes') \
                .delete() \
                .eq('review_id', review_id) \
                .eq('voter_id', voter_id) \
                .execute()
            # Decrement (floor at 0)
            cur = supabase.table('product_reviews').select('helpful_count').eq('id', review_id).single().execute().data
            new_count = max(0, (cur.get('helpful_count') or 0) - 1)
            supabase.table('product_reviews').update({'helpful_count': new_count}).eq('id', review_id).execute()
            voted = False
        else:
            # Add vote
            supabase.table('review_helpful_votes') \
                .insert({'review_id': review_id, 'voter_id': voter_id}) \
                .execute()
            cur = supabase.table('product_reviews').select('helpful_count').eq('id', review_id).single().execute().data
            new_count = (cur.get('helpful_count') or 0) + 1
            supabase.table('product_reviews').update({'helpful_count': new_count}).eq('id', review_id).execute()
            voted = True
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

    return jsonify(success=True, voted=voted, count=new_count)


# ─────────────────────────────────────────────────────────────
#  Delete own review
# ─────────────────────────────────────────────────────────────
@buyer_bp.route('/reviews/<review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    buyer_id = current_user.id
    # Only delete if owner
    try:
        supabase.table('product_reviews') \
            .delete() \
            .eq('id', review_id) \
            .eq('buyer_id', buyer_id) \
            .execute()
        flash('Review Deleted||Your review has been removed.', 'info')
    except Exception as e:
        flash(f'Could not delete review||{e}', 'error')

    # Redirect back to product page (we need to find product_id)
    product_id = request.form.get('product_id', '')
    if product_id:
        return redirect(url_for('buyer.product_detail', product_id=product_id) + '#reviews')
    return redirect(url_for('buyer.browse_products'))
