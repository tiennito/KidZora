"""Audit log helpers for admin actions."""
from flask import has_request_context
from flask_login import current_user

from app.extensions import supabase_admin


def log_admin_action(action, entity_type=None, entity_id=None, target_user_id=None, details=None):
    """Persist one admin audit log row. Best-effort (never raises)."""
    try:
        actor_id = None
        actor_role = None
        if has_request_context() and getattr(current_user, 'is_authenticated', False):
            actor_id = str(current_user.id)
            actor_role = getattr(current_user, 'role', None)

        payload = {
            'actor_id': actor_id,
            'actor_role': actor_role,
            'action': str(action or '').strip() or 'unknown_action',
            'entity_type': entity_type,
            'entity_id': str(entity_id) if entity_id is not None else None,
            'target_user_id': str(target_user_id) if target_user_id else None,
            'details': details or {},
        }
        supabase_admin.table('audit_logs').insert(payload).execute()
    except Exception:
        pass
