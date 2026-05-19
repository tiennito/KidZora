"""Seller profile / account settings route."""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import seller_bp, seller_required, _save_avatar, _save_banner

_PROFILE_FIELDS = [
    'first_name', 'last_name', 'phone',
    'business_name', 'business_type',
    'seller_id_type', 'seller_id_number',
    'region', 'province', 'city', 'barangay',
    'building_number', 'street_name', 'postal_code',
]

_SELLER_FIELDS = ['shop_name', 'shop_description', 'about_store']


def _get_seller_row(user_id):
    """Fetch the seller row for the current user; returns {} on failure."""
    try:
        r = supabase.table('sellers').select(
            'id,shop_name,shop_description,about_store,shop_banner_url'
        ).eq('user_id', user_id).maybe_single().execute()
        return r.data or {}
    except Exception:
        return {}


@seller_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@seller_required
def profile():
    seller_row = _get_seller_row(current_user.id)

    if request.method == 'POST':
        update_data = {f: request.form.get(f, '').strip() for f in _PROFILE_FIELDS}

        # ── Avatar upload ──────────────────────────────────────────────────────
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename:
            saved_url = _save_avatar(avatar_file, current_user.id)
            if saved_url:
                try:
                    supabase.table('profiles').update({'avatar_url': saved_url}) \
                        .eq('id', current_user.id).execute()
                except Exception as av_err:
                    print(f'[seller.profile] avatar save error: {av_err}')

        # ── Store customization (sellers table) ───────────────────────────────
        seller_update = {f: request.form.get(f, '').strip() for f in _SELLER_FIELDS}
        # Banner upload
        banner_file = request.files.get('shop_banner')
        if banner_file and banner_file.filename and seller_row.get('id'):
            banner_url = _save_banner(banner_file, seller_row['id'])
            if banner_url:
                seller_update['shop_banner_url'] = banner_url
        if seller_row.get('id'):
            try:
                supabase.table('sellers').update(seller_update) \
                    .eq('id', seller_row['id']).execute()
            except Exception as se:
                print(f'[seller.profile] sellers update error: {se}')

        # ── Optional password change ───────────────────────────────────────────
        new_password     = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if new_password:
            if new_password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('seller/profile.html', seller_row=seller_row)
            if len(new_password) < 8:
                flash('Password must be at least 8 characters.', 'error')
                return render_template('seller/profile.html', seller_row=seller_row)
            try:
                import requests as http_requests
                supabase_url = current_app.config.get('SUPABASE_URL')
                service_key  = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')
                http_requests.put(
                    f'{supabase_url}/auth/v1/admin/users/{current_user.id}',
                    headers={
                        'apikey':        service_key,
                        'Authorization': f'Bearer {service_key}',
                        'Content-Type':  'application/json',
                    },
                    json={'password': new_password},
                    timeout=10,
                )
            except Exception as e:
                flash(f'Password update failed: {e}', 'error')
                return render_template('seller/profile.html', seller_row=seller_row)

        try:
            supabase.table('profiles').update(update_data).eq('id', current_user.id).execute()
            if new_password:
                flash('Password & Profile Saved!||Your password and profile details have been updated.', 'success')
            else:
                flash('Profile Saved!||Your changes have been saved successfully.', 'success')
        except Exception as e:
            flash(f'Could not save profile: {e}', 'error')

        return redirect(url_for('seller.profile'))

    return render_template('seller/profile.html', seller_row=seller_row)
