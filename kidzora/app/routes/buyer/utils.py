"""
Buyer routes package — blueprint + shared decorator.

  buyer_bp       : Flask Blueprint (url_prefix='/buyer' set in app/__init__.py)
  buyer_required : login + role guard
"""
from functools import wraps

from flask import Blueprint, redirect, url_for, flash
from flask_login import current_user

buyer_bp = Blueprint('buyer', __name__)

ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def _allowed_img(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG_EXTENSIONS


def _save_avatar(file, user_id):
    """Upload a profile avatar to Supabase Storage; return its public URL, or None on failure."""
    if not file or file.filename == '':
        return None
    if not _allowed_img(file.filename):
        return None
    from app.utils.images import upload_to_storage
    storage_path = f'avatars/{user_id}.webp'
    try:
        return upload_to_storage(file, 'avatars', storage_path,
                                 max_width=320, max_height=320, quality=85)
    except Exception as e:
        print(f'[_save_avatar] upload failed: {e}')
        return None


def buyer_required(f):
    """Decorator: user must be authenticated and have role == 'buyer'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'buyer':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.login'))
        verification_status = (getattr(current_user, 'verification_status', '') or '').lower()
        if verification_status == 'rejected' or not getattr(current_user, 'is_approved', False):
            if verification_status == 'rejected':
                reason = getattr(current_user, 'rejection_reason', '') or 'Please contact support for details.'
                flash(f'Your account verification was rejected. Reason: {reason}', 'error')
            else:
                flash('Your account is pending admin identity verification.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
