"""Admin coupon management routes."""
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required

from app.models.coupon import Coupon
from .utils import admin_bp, admin_required


@admin_bp.route('/coupons', methods=['GET', 'POST'])
@login_required
@admin_required
def coupons():
    if request.method == 'POST':
        discount_type = request.form.get('discount_type', 'percentage')
        coupon_data = {
            'code':               request.form.get('code', '').upper(),
            'description':        request.form.get('description'),
            'discount_type':      discount_type,
            'discount_value':     0.0 if discount_type == 'free_delivery'
                                  else float(request.form.get('discount_value') or 0),
            'min_order_amount':   float(request.form.get('min_order_amount') or 0),
            'max_discount_amount': float(request.form.get('max_discount_amount'))
                                   if request.form.get('max_discount_amount') else None,
            'usage_limit':        int(request.form.get('usage_limit'))
                                  if request.form.get('usage_limit', '').strip() else None,
            'expires_at':         request.form.get('expires_at') or None,
            'is_active':          request.form.get('is_active') == 'on',
        }
        if Coupon.create(coupon_data):
            flash('Coupon Created||The new coupon is now active in the system.', 'success')
        else:
            flash('Failed to create coupon', 'error')
        return redirect(url_for('admin.coupons'))

    return render_template('admin/coupons.html', coupons=Coupon.get_all())


@admin_bp.route('/coupons/<coupon_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_coupon(coupon_id):
    coupon = Coupon.get_by_id(coupon_id)
    if not coupon:
        flash('Coupon not found', 'error')
        return redirect(url_for('admin.coupons'))

    edit_discount_type = request.form.get('discount_type', 'percentage')
    update_data = {
        'description':        request.form.get('description'),
        'discount_type':      edit_discount_type,
        'discount_value':     0.0 if edit_discount_type == 'free_delivery'
                              else float(request.form.get('discount_value') or 0),
        'min_order_amount':   float(request.form.get('min_order_amount') or 0),
        'max_discount_amount': float(request.form.get('max_discount_amount'))
                               if request.form.get('max_discount_amount') else None,
        'usage_limit':        int(request.form.get('usage_limit'))
                              if request.form.get('usage_limit', '').strip() else None,
        'expires_at':         request.form.get('expires_at') or None,
        'is_active':          request.form.get('is_active') == 'on',
    }

    if coupon.update(update_data):
        flash('Coupon Updated||The coupon changes have been saved.', 'success')
    else:
        flash('Failed to update coupon', 'error')

    return redirect(url_for('admin.coupons'))


@admin_bp.route('/coupons/<coupon_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_coupon(coupon_id):
    coupon = Coupon.get_by_id(coupon_id)
    if not coupon:
        flash('Coupon not found', 'error')
        return redirect(url_for('admin.coupons'))

    if coupon.delete():
        flash('Coupon Deleted||The coupon has been removed from the system.', 'success')
    else:
        flash('Failed to delete coupon', 'error')

    return redirect(url_for('admin.coupons'))
