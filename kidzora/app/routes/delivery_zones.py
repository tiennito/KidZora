"""Root DeliveryZone CRUD API.

Endpoints:
  POST   /delivery-zones
  GET    /delivery-zones
  GET    /delivery-zones/<id>
  PUT    /delivery-zones/<id>
  DELETE /delivery-zones/<id>
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.models.delivery_zone import DeliveryZone
from app.services.delivery_fee_service import validate_delivery_zone_payload
from app.utils.decorators import admin_required

delivery_zones_bp = Blueprint('delivery_zones', __name__)


@delivery_zones_bp.route('/delivery-zones', methods=['GET'])
@login_required
@admin_required
def list_delivery_zones():
    zones = DeliveryZone.get_all()
    return jsonify({'data': [zone.to_dict() for zone in zones]})


@delivery_zones_bp.route('/delivery-zones/<zone_id>', methods=['GET'])
@login_required
@admin_required
def get_delivery_zone(zone_id):
    zone = DeliveryZone.get_by_id(zone_id)
    if not zone:
        return jsonify({'error': 'Delivery zone not found.'}), 404
    return jsonify({'data': zone.to_dict()})


@delivery_zones_bp.route('/delivery-zones', methods=['POST'])
@login_required
@admin_required
def create_delivery_zone():
    data = request.get_json(silent=True) or {}
    payload, error = validate_delivery_zone_payload(data)
    if error:
        return jsonify({'error': error}), 400
    try:
        zone = DeliveryZone.create(payload)
    except Exception as exc:
        return jsonify({'error': f'Could not create delivery zone: {exc}'}), 500
    return jsonify({'data': zone.to_dict()}), 201


@delivery_zones_bp.route('/delivery-zones/<zone_id>', methods=['PUT'])
@login_required
@admin_required
def update_delivery_zone(zone_id):
    zone = DeliveryZone.get_by_id(zone_id)
    if not zone:
        return jsonify({'error': 'Delivery zone not found.'}), 404

    data = request.get_json(silent=True) or {}
    payload, error = validate_delivery_zone_payload(data, existing_id=zone_id)
    if error:
        return jsonify({'error': error}), 400

    try:
        zone.update(payload)
    except Exception as exc:
        return jsonify({'error': f'Could not update delivery zone: {exc}'}), 500
    return jsonify({'data': zone.to_dict()})


@delivery_zones_bp.route('/delivery-zones/<zone_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_delivery_zone(zone_id):
    zone = DeliveryZone.get_by_id(zone_id)
    if not zone:
        return jsonify({'error': 'Delivery zone not found.'}), 404

    try:
        zone.delete()
    except Exception as exc:
        return jsonify({'error': f'Could not delete delivery zone: {exc}'}), 500
    return jsonify({'ok': True})
