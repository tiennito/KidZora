from __future__ import annotations

from typing import Any

from app.extensions import supabase_admin as supabase
from app.models.delivery_zone import DeliveryZone
from app.utils.settings import get_setting

DEFAULT_DELIVERY_FEE_SETTING = 'default_delivery_fee'
LOCKED_DELIVERY_STATUSES = {
    'confirmed',
    'preparing',
    'ready_for_pickup',
    'rider_assigned',
    'shipped',
    'out_for_delivery',
    'delivered',
    'completed',
    'cancelled',
}
LOCKED_PAYMENT_STATUSES = {'paid', 'refunded'}


def normalize_location(value: str | None) -> str:
    return ' '.join((value or '').strip().lower().split())


def get_default_delivery_fee() -> float:
    raw = get_setting(DEFAULT_DELIVERY_FEE_SETTING, '120')
    try:
        fee = float(raw)
    except (TypeError, ValueError):
        fee = 120.0
    return max(0.0, round(fee, 2))


def calculate_delivery_fee(location: dict[str, Any] | None) -> dict[str, Any]:
    """
    Match buyer location against delivery_zones in priority order:
    city -> province -> region. Falls back to the configurable
    platform_settings.default_delivery_fee value.
    """
    location = location or {}
    candidates = [
        ('city', location.get('city')),
        ('province', location.get('province')),
        ('region', location.get('region')),
    ]
    candidate_keys = [(kind, normalize_location(value)) for kind, value in candidates if normalize_location(value)]

    try:
        zones = DeliveryZone.get_all()
    except Exception:
        zones = []

    zone_by_key = {
        normalize_location(zone.location_name): zone
        for zone in zones
        if normalize_location(zone.location_name)
    }

    for kind, key in candidate_keys:
        zone = zone_by_key.get(key)
        if zone:
            return {
                'fee': round(float(zone.delivery_fee or 0), 2),
                'matched': True,
                'matchType': kind,
                'locationName': zone.location_name,
                'zoneId': zone.id,
                'fallback': False,
            }

    return {
        'fee': get_default_delivery_fee(),
        'matched': False,
        'matchType': None,
        'locationName': None,
        'zoneId': None,
        'fallback': True,
    }


def validate_delivery_zone_payload(data: dict[str, Any], existing_id: str | None = None) -> tuple[dict[str, Any], str | None]:
    location_name = (data.get('locationName') or data.get('location_name') or '').strip()
    raw_fee = data.get('deliveryFee', data.get('delivery_fee'))

    if not location_name:
        return {}, 'Location name is required.'

    try:
        delivery_fee = float(raw_fee)
    except (TypeError, ValueError):
        return {}, 'Delivery fee must be a valid number.'

    if delivery_fee < 0:
        return {}, 'Delivery fee cannot be negative.'

    duplicate = DeliveryZone.find_by_location_name(location_name)
    if duplicate and str(duplicate.id) != str(existing_id or ''):
        return {}, 'A delivery zone with this location name already exists.'

    return {
        'location_name': location_name,
        'delivery_fee': round(delivery_fee, 2),
    }, None


def order_delivery_fee_is_locked(order: dict[str, Any]) -> bool:
    status = normalize_location(order.get('status') or 'pending')
    payment_status = normalize_location(order.get('payment_status') or 'pending')
    return status in LOCKED_DELIVERY_STATUSES or payment_status in LOCKED_PAYMENT_STATUSES


def _order_subtotal(order: dict[str, Any]) -> float:
    if order.get('subtotal') is not None:
        try:
            return round(float(order.get('subtotal') or 0), 2)
        except (TypeError, ValueError):
            pass

    try:
        items = (
            supabase.table('order_items')
            .select('quantity,price')
            .eq('order_id', order['id'])
            .execute()
            .data
            or []
        )
    except Exception:
        items = []

    return round(sum(float(item.get('price') or 0) * int(item.get('quantity') or 0) for item in items), 2)


def build_order_totals(subtotal: float, delivery_fee: float, discount_amount: float = 0) -> dict[str, float]:
    subtotal = round(float(subtotal or 0), 2)
    delivery_fee = round(float(delivery_fee or 0), 2)
    discount_amount = round(float(discount_amount or 0), 2)
    total_amount = max(0.0, round(subtotal + delivery_fee - discount_amount, 2))
    return {
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'discount_amount': discount_amount,
        'total_amount': total_amount,
    }


def recalculate_pending_buyer_orders(buyer_id: str, location: dict[str, Any]) -> dict[str, Any]:
    """
    Recompute delivery fee for pending/unpaid orders only.
    Paid or progressed orders keep their stored fee forever.
    """
    result = calculate_delivery_fee(location)
    try:
        rows = (
            supabase.table('orders')
            .select('*')
            .eq('buyer_id', buyer_id)
            .eq('status', 'pending')
            .eq('payment_status', 'pending')
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    unlocked = [order for order in rows if not order_delivery_fee_is_locked(order)]
    if not unlocked:
        return {'updated': 0, 'fee': result['fee'], 'matched': result}

    total_fee = result['fee']
    allocated = 0.0
    updated = 0
    for idx, order in enumerate(unlocked):
        is_last = idx == len(unlocked) - 1
        order_fee = round(total_fee - allocated, 2) if is_last else round(total_fee / len(unlocked), 2)
        allocated += order_fee
        subtotal = _order_subtotal(order)
        discount = float(order.get('discount_amount') or 0)
        totals = build_order_totals(subtotal, order_fee, discount)
        payload = {
            **totals,
            'delivery_address': {
                **(order.get('delivery_address') or {}),
                **{k: v for k, v in location.items() if v is not None},
            },
        }
        try:
            supabase.table('orders').update(payload).eq('id', order['id']).execute()
            updated += 1
        except Exception:
            continue

    return {'updated': updated, 'fee': total_fee, 'matched': result}
