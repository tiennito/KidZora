"""
Shared utilities for the seller blueprint:
  - seller_bp  : the Flask Blueprint instance
  - seller_required : login + role decorator
  - _allowed_img, _save_product_image : file-upload helpers
"""
import os
from functools import wraps

from flask import Blueprint, redirect, url_for, flash
from flask_login import current_user
from werkzeug.utils import secure_filename

seller_bp = Blueprint('seller', __name__)


def _get_seller_id():
    """Return the sellers.id for the current logged-in user.
    Auto-creates the sellers row if it doesn't exist (for accounts registered before this fix)."""
    from app.extensions import supabase_admin
    try:
        # Use list query (no .single()) so missing row doesn't raise an exception
        r = supabase_admin.table('sellers').select('id').eq('user_id', current_user.id).execute()
        rows = r.data or []
        if rows:
            return rows[0]['id']
        # No sellers row yet — create one now
        shop_name = getattr(current_user, 'business_name', None) or \
                    f"{getattr(current_user, 'first_name', '')} {getattr(current_user, 'last_name', '')}".strip() or \
                    'My Shop'
        ins = supabase_admin.table('sellers').insert({
            'user_id':   current_user.id,
            'shop_name': shop_name,
        }).execute()
        return ins.data[0]['id'] if ins.data else None
    except Exception as e:
        print(f"[_get_seller_id] error: {e}")
        return None

ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def seller_required(f):
    """Decorator: user must be authenticated and have role == 'seller'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'seller':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


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


def _save_banner(file, seller_id):
    """Upload a shop banner to Supabase Storage; return its public URL, or None on failure."""
    if not file or file.filename == '':
        return None
    if not _allowed_img(file.filename):
        return None
    from app.utils.images import upload_to_storage
    storage_path = f'banners/{seller_id}.webp'
    try:
        return upload_to_storage(file, 'shop-banners', storage_path,
                                 max_width=1400, max_height=480, quality=85)
    except Exception as e:
        print(f'[_save_banner] upload failed: {e}')
        return None


def _save_product_image(file, seller_id):
    """Upload a product image to Supabase Storage; return its public URL, or None on failure."""
    if not file or file.filename == '':
        return None
    if not _allowed_img(file.filename):
        return None
    import uuid
    from app.utils.images import upload_to_storage
    stem         = uuid.uuid4().hex
    storage_path = f'sellers/{seller_id}/products/{stem}.webp'
    try:
        return upload_to_storage(file, 'product-images', storage_path,
                                 max_width=900, max_height=900, quality=82)
    except Exception as e:
        print(f'[_save_product_image] upload failed: {e}')
        return None
