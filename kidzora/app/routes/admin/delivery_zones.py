"""Admin UI for location-based delivery fees."""
from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.models.delivery_zone import DeliveryZone
from app.services.delivery_fee_service import get_default_delivery_fee, validate_delivery_zone_payload
from app.utils.settings import set_setting
from .utils import admin_bp, admin_required


@admin_bp.route('/delivery-zones', methods=['GET', 'POST'])
@login_required
@admin_required
def delivery_zones():
    if request.method == 'POST':
        payload, error = validate_delivery_zone_payload(request.form)
        if error:
            flash(error, 'error')
        else:
            try:
                DeliveryZone.create(payload)
                flash('Delivery zone created successfully.', 'success')
            except Exception as exc:
                flash(f'Could not create delivery zone: {exc}', 'error')
        return redirect(url_for('admin.delivery_zones'))

    return render_template(
        'admin/delivery_zones.html',
        zones=DeliveryZone.get_all(),
        default_delivery_fee=get_default_delivery_fee(),
    )


@admin_bp.route('/delivery-zones/default-fee', methods=['POST'])
@login_required
@admin_required
def update_default_delivery_fee():
    try:
        fee = float(request.form.get('default_delivery_fee') or 0)
    except (TypeError, ValueError):
        flash('Default delivery fee must be a valid number.', 'error')
        return redirect(url_for('admin.delivery_zones'))

    if fee < 0:
        flash('Default delivery fee cannot be negative.', 'error')
        return redirect(url_for('admin.delivery_zones'))

    if set_setting('default_delivery_fee', f'{fee:.2f}'):
        flash('Default delivery fee updated.', 'success')
    else:
        flash('Could not update default delivery fee.', 'error')
    return redirect(url_for('admin.delivery_zones'))


@admin_bp.route('/delivery-zones/<zone_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_delivery_zone(zone_id):
    zone = DeliveryZone.get_by_id(zone_id)
    if not zone:
        flash('Delivery zone not found.', 'error')
        return redirect(url_for('admin.delivery_zones'))

    payload, error = validate_delivery_zone_payload(request.form, existing_id=zone_id)
    if error:
        flash(error, 'error')
    else:
        try:
            zone.update(payload)
            flash('Delivery zone updated successfully.', 'success')
        except Exception as exc:
            flash(f'Could not update delivery zone: {exc}', 'error')
    return redirect(url_for('admin.delivery_zones'))


@admin_bp.route('/delivery-zones/<zone_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_delivery_zone(zone_id):
    zone = DeliveryZone.get_by_id(zone_id)
    if not zone:
        flash('Delivery zone not found.', 'error')
        return redirect(url_for('admin.delivery_zones'))

    try:
        zone.delete()
        flash('Delivery zone deleted successfully.', 'success')
    except Exception as exc:
        flash(f'Could not delete delivery zone: {exc}', 'error')
    return redirect(url_for('admin.delivery_zones'))
