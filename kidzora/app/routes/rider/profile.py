"""Rider profile / account settings route."""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from .utils import rider_bp, rider_required, _save_avatar

_PROFILE_FIELDS = [
    'first_name', 'last_name', 'phone',
    'region', 'province', 'city', 'barangay',
    'building_number', 'street_name', 'postal_code',
]


def _get_rider_docs():
    """Return (rider_row_dict, rejection_reason_str) for the current user."""
    try:
        r = supabase.table('riders').select(
            'licensed_id_url,original_receipt_url,certificate_of_registration_url'
        ).eq('user_id', current_user.id).single().execute()
        docs = r.data or {}
    except Exception:
        docs = {}

    try:
        p = supabase.table('profiles').select('rejection_reason,is_approved') \
            .eq('id', current_user.id).single().execute()
        rejection_reason = (p.data or {}).get('rejection_reason') or ''
        is_approved      = (p.data or {}).get('is_approved', True)
    except Exception:
        rejection_reason = ''
        is_approved      = True

    return docs, rejection_reason, is_approved


@rider_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@rider_required
def profile():
    if request.method == 'POST':
        action = request.form.get('profile_action', 'details').strip().lower()

        # Only include fields that were actually submitted by this form.
        update_data = {
            f: request.form.get(f, '').strip()
            for f in _PROFILE_FIELDS
            if f in request.form
        }

        # ── Avatar upload ──────────────────────────────────────────────────────
        avatar_file = request.files.get('avatar')
        avatar_saved = False
        if avatar_file and avatar_file.filename:
            saved_url = _save_avatar(avatar_file, current_user.id)
            if saved_url:
                try:
                    supabase.table('profiles').update({'avatar_url': saved_url}) \
                        .eq('id', current_user.id).execute()
                    avatar_saved = True
                except Exception as av_err:
                    print(f'[rider.profile] avatar save error: {av_err}')

        if action == 'avatar':
            if avatar_saved:
                flash('Photo Updated!||Your profile photo has been updated.', 'success')
            else:
                flash('Could not update photo. Please choose a valid image and try again.', 'error')
            return redirect(url_for('rider.profile'))

        # ── Optional password change ───────────────────────────────────────────
        new_password     = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if new_password:
            if new_password != confirm_password:
                flash('Passwords do not match.', 'error')
                docs, rejection_reason, is_approved = _get_rider_docs()
                return render_template('rider/profile.html',
                                       rider_docs=docs,
                                       rejection_reason=rejection_reason,
                                       is_approved=is_approved)
            if len(new_password) < 8:
                flash('Password must be at least 8 characters.', 'error')
                docs, rejection_reason, is_approved = _get_rider_docs()
                return render_template('rider/profile.html',
                                       rider_docs=docs,
                                       rejection_reason=rejection_reason,
                                       is_approved=is_approved)
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
                docs, rejection_reason, is_approved = _get_rider_docs()
                return render_template('rider/profile.html',
                                       rider_docs=docs,
                                       rejection_reason=rejection_reason,
                                       is_approved=is_approved)

        try:
            if update_data:
                supabase.table('profiles').update(update_data).eq('id', current_user.id).execute()

            if new_password and update_data:
                flash('Password & Profile Saved!||Your password and profile details have been updated.', 'success')
            elif new_password:
                flash('Password Updated!||Your password has been changed successfully.', 'success')
            elif update_data:
                flash('Profile Saved!||Your changes have been saved successfully.', 'success')
            else:
                flash('No changes detected.', 'info')
        except Exception as e:
            flash(f'Could not save profile: {e}', 'error')

        return redirect(url_for('rider.profile'))

    docs, rejection_reason, is_approved = _get_rider_docs()
    return render_template('rider/profile.html',
                           rider_docs=docs,
                           rejection_reason=rejection_reason,
                           is_approved=is_approved)


@rider_bp.route('/profile/documents', methods=['POST'])
@login_required
@rider_required
def resubmit_documents():
    """Allow a rejected rider to re-upload their verification documents."""
    from app.routes.auth import save_rider_file

    _, rejection_reason, is_approved = _get_rider_docs()
    if is_approved or not rejection_reason:
        flash('No document re-submission required.', 'info')
        return redirect(url_for('rider.profile'))

    uid = current_user.id
    updates = {}

    licensed_id_file = request.files.get('licensed_id')
    receipt_file     = request.files.get('original_receipt')
    cor_file         = request.files.get('certificate_of_registration')

    if licensed_id_file and licensed_id_file.filename:
        url = save_rider_file(licensed_id_file, uid, 'licensed_id')
        if url:
            updates['licensed_id_url'] = url

    if receipt_file and receipt_file.filename:
        url = save_rider_file(receipt_file, uid, 'original_receipt')
        if url:
            updates['original_receipt_url'] = url

    if cor_file and cor_file.filename:
        url = save_rider_file(cor_file, uid, 'certificate_of_registration')
        if url:
            updates['certificate_of_registration_url'] = url

    if not updates:
        flash('No files uploaded. Please select at least one document to re-submit.', 'error')
        return redirect(url_for('rider.profile'))

    try:
        supabase.table('riders').update(updates).eq('user_id', uid).execute()
        # Clear rejection reason — puts rider back in the admin pending queue
        supabase.table('profiles').update({'rejection_reason': None}).eq('id', uid).execute()
        flash(
            'Documents Resubmitted!||'
            'Your documents have been sent for review. '
            'You will be notified by email once approved.',
            'success'
        )
    except Exception as e:
        print(f'[rider.resubmit_documents] error: {e}')
        flash(f'Upload failed: {e}', 'error')

    return redirect(url_for('rider.profile'))
