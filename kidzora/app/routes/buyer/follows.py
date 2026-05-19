"""Buyer — follow / unfollow a seller shop."""
from flask import jsonify, request
from flask_login import current_user, login_required

from app.extensions import supabase_admin as supabase
from .utils import buyer_bp


@buyer_bp.route('/shop/<seller_id>/follow', methods=['POST'])
@login_required
def toggle_follow(seller_id):
    """Toggle follow state for the authenticated buyer on a seller shop.

    Returns JSON: {"following": bool, "follower_count": int}
    """
    buyer_id = str(current_user.id)

    # Check current state
    try:
        existing = supabase.table('seller_follows') \
            .select('id') \
            .eq('buyer_id', buyer_id) \
            .eq('seller_id', seller_id) \
            .execute().data
    except Exception:
        existing = []

    if existing:
        # Unfollow
        try:
            supabase.table('seller_follows') \
                .delete() \
                .eq('buyer_id', buyer_id) \
                .eq('seller_id', seller_id) \
                .execute()
        except Exception:
            pass
        following = False
    else:
        # Follow
        try:
            supabase.table('seller_follows') \
                .insert({'buyer_id': buyer_id, 'seller_id': seller_id}) \
                .execute()
        except Exception:
            pass
        following = True

    # Return updated follower count
    try:
        cnt_r = supabase.table('seller_follows') \
            .select('id', count='exact') \
            .eq('seller_id', seller_id) \
            .execute()
        follower_count = cnt_r.count or 0
    except Exception:
        follower_count = 0

    return jsonify({'following': following, 'follower_count': follower_count})
