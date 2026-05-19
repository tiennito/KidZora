"""Application error logging helpers."""
from flask import has_request_context, request
from flask_login import current_user

from app.extensions import supabase_admin


def log_app_error(exc, level='error', details=None):
    """Persist an application error event. Best-effort only."""
    try:
        payload = {
            'level': level,
            'message': str(exc)[:2000],
            'error_type': exc.__class__.__name__ if exc else None,
            'details': details or {},
        }

        if has_request_context():
            payload['path'] = request.path
            payload['method'] = request.method
            if getattr(current_user, 'is_authenticated', False):
                payload['user_id'] = str(current_user.id)

        supabase_admin.table('app_error_logs').insert(payload).execute()
    except Exception:
        pass
