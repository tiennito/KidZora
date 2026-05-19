"""Saved delivery addresses — CRUD for buyers."""
from flask import jsonify, request
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import buyer_bp

_ADDR_FIELDS = [
    'label', 'full_name', 'phone', 'region', 'province',
    'city', 'barangay', 'street_name', 'building_number', 'postal_code',
]


@buyer_bp.route('/addresses', methods=['GET'])
@login_required
def list_addresses():
    try:
        rows = (supabase.table('buyer_addresses')
                .select('*')
                .eq('buyer_id', current_user.id)
                .order('is_default', desc=True)
                .order('created_at')
                .execute().data or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify(rows)


@buyer_bp.route('/addresses', methods=['POST'])
@login_required
def add_address():
    data = request.get_json(silent=True) or {}
    row = {'buyer_id': current_user.id}
    for f in _ADDR_FIELDS:
        row[f] = (data.get(f) or '').strip()

    # First address is automatically the default
    try:
        existing = (supabase.table('buyer_addresses')
                    .select('id', count='exact')
                    .eq('buyer_id', current_user.id)
                    .execute())
        row['is_default'] = (existing.count == 0)
    except Exception:
        row['is_default'] = False

    if data.get('is_default'):
        # Clear existing defaults first
        try:
            supabase.table('buyer_addresses').update({'is_default': False}) \
                .eq('buyer_id', current_user.id).execute()
        except Exception:
            pass
        row['is_default'] = True

    try:
        result = supabase.table('buyer_addresses').insert(row).execute()
        return jsonify(result.data[0] if result.data else {}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@buyer_bp.route('/addresses/<addr_id>/default', methods=['POST'])
@login_required
def set_default_address(addr_id):
    try:
        # Verify ownership
        rows = (supabase.table('buyer_addresses').select('id')
                .eq('id', addr_id).eq('buyer_id', current_user.id)
                .execute().data or [])
        if not rows:
            return jsonify({'error': 'Not found'}), 404
        # Clear all defaults for buyer, then set this one
        supabase.table('buyer_addresses').update({'is_default': False}) \
            .eq('buyer_id', current_user.id).execute()
        supabase.table('buyer_addresses').update({'is_default': True}) \
            .eq('id', addr_id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@buyer_bp.route('/addresses/<addr_id>/delete', methods=['POST'])
@login_required
def delete_address(addr_id):
    try:
        rows = (supabase.table('buyer_addresses').select('id,is_default')
                .eq('id', addr_id).eq('buyer_id', current_user.id)
                .execute().data or [])
        if not rows:
            return jsonify({'error': 'Not found'}), 404
        supabase.table('buyer_addresses').delete().eq('id', addr_id).execute()
        # If deleted address was default, promote the oldest remaining one
        if rows[0].get('is_default'):
            remaining = (supabase.table('buyer_addresses').select('id')
                         .eq('buyer_id', current_user.id)
                         .order('created_at').execute().data or [])
            if remaining:
                supabase.table('buyer_addresses').update({'is_default': True}) \
                    .eq('id', remaining[0]['id']).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
