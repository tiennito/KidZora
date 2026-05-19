"""Admin system health dashboard."""
from flask import render_template
from flask_login import login_required

from app.extensions import supabase_admin
from .utils import admin_bp, admin_required


_COUNT_TABLES = [
    'profiles',
    'orders',
    'products',
    'order_items',
    'messages',
    'notifications',
    'return_requests',
    'payout_requests',
    'rider_payout_requests',
    'audit_logs',
    'app_error_logs',
]


def _table_counts():
    out = []
    for table_name in _COUNT_TABLES:
        try:
            res = supabase_admin.table(table_name).select('id', count='exact').limit(1).execute()
            out.append({'table': table_name, 'count': int(res.count or 0), 'ok': True})
        except Exception as exc:
            out.append({'table': table_name, 'count': None, 'ok': False, 'error': str(exc)})
    return out


def _recent_errors(limit=25):
    try:
        rows = supabase_admin.table('app_error_logs') \
            .select('id, level, message, error_type, path, method, user_id, created_at') \
            .order('created_at', desc=True).limit(limit).execute().data or []
        return rows
    except Exception:
        return []


def _bucket_usage():
    buckets_out = []
    total_objects = 0
    total_bytes = 0

    try:
        buckets = supabase_admin.storage.list_buckets() or []
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'buckets': [], 'total_objects': 0, 'total_bytes': 0}

    for b in buckets:
        bname = b.get('name') if isinstance(b, dict) else None
        if not bname:
            continue

        object_count = 0
        bytes_sum = 0
        try:
            rows = supabase_admin.table('storage.objects') \
                .select('id, metadata') \
                .eq('bucket_id', bname).execute().data or []
            object_count = len(rows)
            for r in rows:
                md = r.get('metadata') or {}
                size = md.get('size')
                if isinstance(size, (int, float)):
                    bytes_sum += int(size)
        except Exception:
            pass

        buckets_out.append({
            'name': bname,
            'public': bool((b or {}).get('public')),
            'object_count': object_count,
            'bytes': bytes_sum,
        })
        total_objects += object_count
        total_bytes += bytes_sum

    buckets_out.sort(key=lambda x: x.get('name', ''))
    return {
        'ok': True,
        'error': None,
        'buckets': buckets_out,
        'total_objects': total_objects,
        'total_bytes': total_bytes,
    }


def _check_db_health():
    try:
        supabase_admin.table('profiles').select('id').limit(1).execute()
        return {'ok': True, 'message': 'Connected'}
    except Exception as exc:
        return {'ok': False, 'message': str(exc)}


@admin_bp.route('/system-health')
@login_required
@admin_required
def system_health():
    db_health = _check_db_health()
    table_counts = _table_counts()
    storage = _bucket_usage()
    recent_errors = _recent_errors(limit=25)

    counts_ok = sum(1 for c in table_counts if c.get('ok'))
    counts_fail = len(table_counts) - counts_ok

    return render_template(
        'admin/system_health.html',
        db_health=db_health,
        table_counts=table_counts,
        counts_ok=counts_ok,
        counts_fail=counts_fail,
        storage=storage,
        recent_errors=recent_errors,
    )
