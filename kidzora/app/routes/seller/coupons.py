"""Seller coupon management routes."""
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import seller_bp, seller_required, _get_seller_id


@seller_bp.route('/coupons')
@login_required
@seller_required
def coupons():
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.dashboard'))

    try:
        rows = (supabase.table('seller_coupons').select('*')
                .eq('seller_id', seller_id)
                .order('created_at', desc=True).execute().data or [])
    except Exception as e:
        flash(f'Could not load coupons: {e}', 'error')
        rows = []

    # ── Aggregate real discount totals & last-used dates from orders ─────
    coupon_ids = [c['id'] for c in rows]
    if coupon_ids:
        try:
            ord_r = supabase.table('orders') \
                .select('seller_coupon_id, discount_amount, created_at') \
                .in_('seller_coupon_id', coupon_ids).execute()
            usage_map = {}
            for o in (ord_r.data or []):
                cid = o['seller_coupon_id']
                if cid not in usage_map:
                    usage_map[cid] = {'total_discount': 0.0, 'last_used': None}
                usage_map[cid]['total_discount'] += float(o.get('discount_amount') or 0)
                ts = o.get('created_at', '')
                if ts and (not usage_map[cid]['last_used'] or ts > usage_map[cid]['last_used']):
                    usage_map[cid]['last_used'] = ts
            for c in rows:
                stats = usage_map.get(c['id'], {'total_discount': 0.0, 'last_used': None})
                c['total_discount_given'] = stats['total_discount']
                c['last_used_at'] = stats['last_used']
        except Exception:
            for c in rows:
                c['total_discount_given'] = 0.0
                c['last_used_at'] = None
    else:
        for c in rows:
            c['total_discount_given'] = 0.0
            c['last_used_at'] = None

    # ── Summary totals for stat cards ─────────────────────────────────────
    total_uses     = sum(c.get('usage_count', 0) for c in rows)
    total_discount = sum(c.get('total_discount_given', 0.0) for c in rows)
    active_count   = sum(1 for c in rows if c.get('is_active'))

    return render_template('seller/coupons.html', coupons=rows,
                           total_uses=total_uses,
                           total_discount=total_discount,
                           active_count=active_count)


@seller_bp.route('/coupons/create', methods=['POST'])
@login_required
@seller_required
def create_coupon():
    seller_id = _get_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'})

    code          = (request.form.get('code') or '').strip().upper()
    description   = (request.form.get('description') or '').strip()
    discount_type = request.form.get('discount_type', 'percentage')
    expires_raw   = request.form.get('expires_at', '').strip()

    if not code:
        flash('Coupon code is required.', 'error')
        return redirect(url_for('seller.coupons'))

    # Validate type-value pairs
    if discount_type == 'free_delivery':
        discount_value = 0.0
    else:
        try:
            discount_value = float(request.form.get('discount_value') or 0)
            if discount_value <= 0:
                raise ValueError
        except ValueError:
            flash('Discount value must be greater than 0.', 'error')
            return redirect(url_for('seller.coupons'))

    payload = {
        'seller_id':      seller_id,
        'code':           code,
        'description':    description or None,
        'discount_type':  discount_type,
        'discount_value': discount_value,
        'min_order_amount': float(request.form.get('min_order_amount') or 0),
        'usage_limit':    int(request.form.get('usage_limit')) if request.form.get('usage_limit') else None,
        'is_active':      request.form.get('is_active') == 'on',
        'expires_at':     expires_raw or None,
    }
    max_disc = request.form.get('max_discount_amount', '').strip()
    if max_disc:
        try:
            payload['max_discount_amount'] = float(max_disc)
        except ValueError:
            pass

    try:
        supabase.table('seller_coupons').insert(payload).execute()
        flash(f'Coupon Created||Coupon "{code}" is now active in your store.', 'success')
    except Exception as e:
        msg = str(e)
        if 'unique' in msg.lower() or '23505' in msg:
            flash(f'Coupon code "{code}" already exists in your shop.', 'error')
        else:
            flash(f'Failed to create coupon: {e}', 'error')

    return redirect(url_for('seller.coupons'))


@seller_bp.route('/coupons/<coupon_id>/edit', methods=['POST'])
@login_required
@seller_required
def edit_coupon(coupon_id):
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.coupons'))

    # Verify ownership
    try:
        row = supabase.table('seller_coupons').select('id').eq('id', coupon_id).eq('seller_id', seller_id).execute().data
        if not row:
            flash('Coupon not found.', 'error')
            return redirect(url_for('seller.coupons'))
    except Exception:
        flash('Coupon not found.', 'error')
        return redirect(url_for('seller.coupons'))

    discount_type = request.form.get('discount_type', 'percentage')
    expires_raw   = request.form.get('expires_at', '').strip()

    if discount_type == 'free_delivery':
        discount_value = 0.0
    else:
        try:
            discount_value = float(request.form.get('discount_value') or 0)
        except ValueError:
            discount_value = 0.0

    update = {
        'description':    (request.form.get('description') or '').strip() or None,
        'discount_type':  discount_type,
        'discount_value': discount_value,
        'min_order_amount': float(request.form.get('min_order_amount') or 0),
        'usage_limit':    int(request.form.get('usage_limit')) if request.form.get('usage_limit') else None,
        'is_active':      request.form.get('is_active') == 'on',
        'expires_at':     expires_raw or None,
        'updated_at':     datetime.now(timezone.utc).isoformat(),
    }
    max_disc = request.form.get('max_discount_amount', '').strip()
    if max_disc:
        try:
            update['max_discount_amount'] = float(max_disc)
        except ValueError:
            pass

    try:
        supabase.table('seller_coupons').update(update).eq('id', coupon_id).execute()
        flash('Coupon Updated||Your coupon changes have been saved.', 'success')
    except Exception as e:
        flash(f'Failed to update coupon: {e}', 'error')

    return redirect(url_for('seller.coupons'))


@seller_bp.route('/coupons/<coupon_id>/toggle', methods=['POST'])
@login_required
@seller_required
def toggle_coupon(coupon_id):
    seller_id = _get_seller_id()
    if not seller_id:
        return jsonify({'success': False})

    try:
        row = supabase.table('seller_coupons').select('is_active').eq('id', coupon_id).eq('seller_id', seller_id).single().execute().data
        new_state = not row.get('is_active', True)
        supabase.table('seller_coupons').update({'is_active': new_state}).eq('id', coupon_id).execute()
        return jsonify({'success': True, 'is_active': new_state})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@seller_bp.route('/coupons/<coupon_id>/delete', methods=['POST'])
@login_required
@seller_required
def delete_coupon(coupon_id):
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.coupons'))

    try:
        supabase.table('seller_coupons').delete().eq('id', coupon_id).eq('seller_id', seller_id).execute()
        flash('Coupon Deleted||The coupon has been removed from your store.', 'success')
    except Exception as e:
        flash(f'Failed to delete coupon: {e}', 'error')

    return redirect(url_for('seller.coupons'))
