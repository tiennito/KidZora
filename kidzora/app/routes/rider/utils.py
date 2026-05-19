"""
Rider routes package — blueprint + shared decorator.

  rider_bp       : Flask Blueprint (url_prefix='/rider' set in app/__init__.py)
  rider_required : login + role guard
"""
from functools import wraps

from flask import Blueprint, redirect, url_for, flash
from flask_login import current_user

from app.extensions import supabase_admin as supabase

rider_bp = Blueprint('rider', __name__)

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
        print(f'[rider._save_avatar] upload failed: {e}')
        return None


def rider_required(f):
    """Decorator: user must be authenticated and have role == 'rider'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'rider':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def approved_rider_required(f):
    """Decorator: rider must be authenticated, role == 'rider', AND is_approved."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'rider':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.login'))
        if not current_user.is_approved:
            flash('Documents Pending||Please re-upload your documents before accessing the dashboard.', 'warning')
            return redirect(url_for('rider.profile'))
        return f(*args, **kwargs)
    return decorated


def _get_rider_id():
    """Return riders.id for the current user (NOT profiles.id)."""
    try:
        r = supabase.table('riders').select('id').eq('user_id', current_user.id).single().execute()
        return r.data['id'] if r.data else None
    except Exception:
        return None


def _get_rider_availability() -> bool:
    """Return the current rider's is_available flag (True = online)."""
    try:
        r = supabase.table('riders').select('is_available') \
            .eq('user_id', current_user.id).single().execute()
        return bool(r.data.get('is_available', True)) if r.data else True
    except Exception:
        return True


def _save_proof_photo(file, order_id):
    """Upload a proof-of-delivery photo to Supabase Storage; return its public URL.
    Raises ValueError with a user-friendly message on any failure.
    """
    if not file or file.filename == '':
        raise ValueError('No file was received — please select a photo and try again.')

    # Accept by MIME type (reliable on mobile) OR by file extension
    mime_ok = (file.content_type or '').startswith('image/')
    ext_ok  = _allowed_img(file.filename)
    if not mime_ok and not ext_ok:
        raise ValueError(
            f'File type not accepted ({file.content_type or "unknown"}). '
            'Please use a JPG, PNG, or WEBP photo.'
        )

    from app.utils.images import upload_to_storage
    storage_path = f'delivery-proofs/{order_id}.webp'
    try:
        return upload_to_storage(file, 'delivery-proofs', storage_path,
                                 max_width=1280, max_height=960, quality=82)
    except Exception as e:
        print(f'[rider._save_proof_photo] upload failed: {e}')
        raise ValueError(str(e)) from e


@rider_bp.context_processor
def _inject_rider_availability():
    """Make ``rider_is_available`` available in every rider template."""
    if current_user.is_authenticated and current_user.role == 'rider':
        return {'rider_is_available': _get_rider_availability()}
    return {'rider_is_available': True}
