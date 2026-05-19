"""Rider ratings route – allows riders to see their own ratings."""
from flask import render_template
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import rider_bp, approved_rider_required, _get_rider_id


@rider_bp.route('/ratings')
@login_required
@approved_rider_required
def ratings():
    rider_id = _get_rider_id()
    rating_list = []
    stats = {'total': 0, 'avg': 0.0, 'five': 0, 'four': 0, 'three': 0, 'two': 0, 'one': 0}

    if rider_id:
        try:
            r = supabase.table('rider_ratings') \
                .select('id,rating,feedback,created_at,order_id,'
                        'profiles!rider_ratings_buyer_id_fkey(first_name,last_name,avatar_url)') \
                .eq('rider_id', rider_id) \
                .order('created_at', desc=True) \
                .execute()
            rating_list = r.data or []
        except Exception:
            # Fallback without join if FK alias not available
            try:
                r = supabase.table('rider_ratings') \
                    .select('id,rating,feedback,created_at,order_id,buyer_id') \
                    .eq('rider_id', rider_id) \
                    .order('created_at', desc=True) \
                    .execute()
                raw = r.data or []

                # Enrich with buyer names
                buyer_ids = list({row['buyer_id'] for row in raw})
                buyer_map = {}
                if buyer_ids:
                    bp_r = supabase.table('profiles') \
                        .select('id,first_name,last_name,avatar_url') \
                        .in_('id', buyer_ids) \
                        .execute().data or []
                    buyer_map = {b['id']: b for b in bp_r}

                for row in raw:
                    row['profiles'] = buyer_map.get(row['buyer_id'], {})
                rating_list = raw
            except Exception as e:
                print(f'[rider.ratings] {e}')

        if rating_list:
            total = len(rating_list)
            avg   = sum(r['rating'] for r in rating_list) / total
            label_map = {5: 'five', 4: 'four', 3: 'three', 2: 'two', 1: 'one'}
            dist = {v: 0 for v in label_map.values()}
            for r in rating_list:
                key = label_map.get(r['rating'])
                if key:
                    dist[key] += 1
            stats = {'total': total, 'avg': round(avg, 1), **dist}

    return render_template(
        'rider/ratings.html',
        rating_list = rating_list,
        stats       = stats,
    )
