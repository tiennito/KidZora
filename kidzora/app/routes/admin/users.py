"""Admin user-management routes.

Covers:
  GET  /admin/users/pending           — list pending sellers & riders
  GET  /admin/api/seller-details/<id> — JSON payload for the view modal
  POST /admin/users/<id>/approve      — approve a seller/rider
  POST /admin/users/<id>/reject       — reject & delete a seller/rider
  GET  /admin/users                   — full user list with filters
  POST /admin/users/<id>/ban          — ban a user
  POST /admin/users/<id>/activate     — unban a user
"""
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required

from app.models.profile import Profile
from app.models.seller import Seller
from app.models.rider import Rider
from app.extensions import supabase_admin
from app.services.audit_log import log_admin_action
from app.services.email import notify_welcome_approved
from app.utils.pagination import paginate_list
from .utils import (admin_bp, admin_required,
                     send_approval_email, send_rejection_email,
                     send_ban_email, send_unban_approved_email, send_unban_rejected_email)


@admin_bp.route('/users/pending')
@login_required
@admin_required
def users_pending():
    pending_sellers = Profile.get_all({'role': 'seller', 'is_approved': False})

    # Pending riders = unapproved AND not yet rejected (rejection_reason IS NULL / empty).
    # Rejected riders who have resubmitted also clear rejection_reason → re-enter this list.
    _rider_rows = supabase_admin.table('profiles') \
        .select('*') \
        .eq('role', 'rider') \
        .eq('is_approved', False) \
        .is_('rejection_reason', 'null') \
        .execute()
    pending_riders = [Profile(r) for r in _rider_rows.data]

    for seller in pending_sellers:
        seller.seller_details = Seller.get_by_user_id(seller.id)
    for rider in pending_riders:
        rider.rider_details = Rider.get_by_user_id(rider.id)

    return render_template('admin/users_pending.html',
                           pending_sellers=pending_sellers,
                           pending_riders=pending_riders)


@admin_bp.route('/api/seller-details/<user_id>')
@login_required
@admin_required
def seller_details_api(user_id):
    """Return full seller profile as JSON for the admin view modal."""
    profile = Profile.get_by_id(user_id)
    if not profile:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    full_address = ', '.join(filter(None, [
        profile.building_number, profile.street_name, profile.barangay,
        profile.city, profile.province, profile.region,
        profile.postal_code, profile.country,
    ]))

    return jsonify({'success': True, 'data': {
        'id':                   profile.id,
        'full_name':            profile.get_full_name(),
        'email':                profile.email,
        'phone':                profile.phone,
        'role':                 profile.role,
        'is_approved':          profile.is_approved,
        'is_banned':            profile.is_banned,
        'full_address':         full_address,
        'region':               profile.region,
        'province':             profile.province,
        'city':                 profile.city,
        'barangay':             profile.barangay,
        'postal_code':          profile.postal_code,
        'country':              profile.country,
        'building_number':      profile.building_number,
        'street_name':          profile.street_name,
        'business_name':        profile.business_name,
        'business_type':        profile.business_type,
        'seller_id_type':       profile.seller_id_type,
        'seller_id_number':     profile.seller_id_number,
        'seller_id_file':       profile.seller_id_file,
        'business_permit_file': profile.business_permit_file,
        'bir_file':             profile.bir_file,
        'created_at':           profile.created_at,
    }})


@admin_bp.route('/api/rider-details/<user_id>')
@login_required
@admin_required
def rider_details_api(user_id):
    """Return full rider profile + documents as JSON for the admin view modal."""
    try:
        profile_resp = supabase_admin.table('profiles').select('*').eq('id', user_id).execute()
        if not profile_resp.data:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        p = profile_resp.data[0]

        rider_resp = supabase_admin.table('riders').select('*').eq('user_id', user_id).execute()
        r = rider_resp.data[0] if rider_resp.data else {}
        docs = r  # document URLs are columns on the riders row itself

        full_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()

        return jsonify({'success': True, 'data': {
            'id':                               p.get('id'),
            'full_name':                        full_name,
            'email':                            p.get('email'),
            'phone':                            p.get('phone'),
            'role':                             p.get('role'),
            'is_approved':                      p.get('is_approved'),
            'is_banned':                        p.get('is_banned', False),
            'region':                           p.get('region'),
            'province':                         p.get('province'),
            'city':                             p.get('city'),
            'barangay':                         p.get('barangay'),
            'postal_code':                      p.get('postal_code'),
            'country':                          p.get('country'),
            'building_number':                  p.get('building_number'),
            'street_name':                      p.get('street_name'),
            'created_at':                       p.get('created_at'),
            'vehicle_type':                     r.get('vehicle_type'),
            'vehicle_plate':                    r.get('vehicle_plate'),
            'licensed_id_url':                  r.get('licensed_id_url'),
            'original_receipt_url':             r.get('original_receipt_url'),
            'certificate_of_registration_url':  r.get('certificate_of_registration_url'),
        }})

    except Exception as e:
        print(f'rider_details_api error: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/users/<user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = Profile.get_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users_pending'))

    if user.update({'is_approved': True}):
        send_approval_email(user)
        notify_welcome_approved(user.id)
        log_admin_action(
            action='approve_user',
            entity_type='profile',
            entity_id=user.id,
            target_user_id=user.id,
            details={'role': user.role, 'email': user.email},
        )
        flash(f'User Approved||{user.get_full_name()} has been approved and notified by email.', 'success')
    else:
        flash('Failed to approve user', 'error')

    return redirect(url_for('admin.users_pending'))


@admin_bp.route('/users/<user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = Profile.get_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users_pending'))

    reason    = request.form.get('reason', '').strip()
    user_name = user.get_full_name()

    # ── Riders: soft-reject so they can re-upload documents ───────────────────
    if user.role == 'rider':
        send_rejection_email(user, reason)
        try:
            supabase_admin.table('profiles') \
                .update({'rejection_reason': reason or 'Documents did not meet requirements.'}) \
                .eq('id', user.id).execute()
            log_admin_action(
                action='reject_user_soft',
                entity_type='profile',
                entity_id=user.id,
                target_user_id=user.id,
                details={'role': user.role, 'reason': reason or 'Documents did not meet requirements.'},
            )
        except Exception as e:
            print(f'Warning: could not set rejection_reason for {user.id}: {e}')
        flash(f'Rider Rejected||{user_name} has been notified. They can log in to re-upload their documents.', 'success')
        return redirect(url_for('admin.users_pending'))

    # ── Sellers / others: hard-delete (must re-register) ──────────────────────
    uid = user.id
    send_rejection_email(user, reason)

    try:
        supabase_admin.table('profiles').delete().eq('id', uid).execute()
        log_admin_action(
            action='reject_user_hard',
            entity_type='profile',
            entity_id=uid,
            target_user_id=uid,
            details={'role': user.role, 'reason': reason},
        )
    except Exception as profile_err:
        print(f'Warning: could not delete profile row {uid}: {profile_err}')

    try:
        supabase_admin.auth.admin.delete_user(uid)
    except Exception as auth_err:
        print(f'Warning: could not delete auth user {uid}: {auth_err}')

    flash(f'User Rejected||{user_name} has been rejected and their account removed.', 'success')
    return redirect(url_for('admin.users_pending'))


@admin_bp.route('/users')
@login_required
@admin_required
def users_list():
    role_filter   = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    search_filter = request.args.get('search', '').strip()

    filters = {}
    if role_filter:
        filters['role'] = role_filter
    if status_filter == 'banned':
        filters['is_banned'] = True
    elif status_filter == 'active':
        filters['is_banned'] = False

    users = Profile.get_all(filters)

    if search_filter:
        q = search_filter.lower()
        users = [u for u in users if
                 q in (u.get_full_name() or '').lower() or
                 q in (u.email or '').lower()]

    pag = paginate_list(users, per_page=25)
    return render_template('admin/users_list.html', users=pag.items,
                           pagination=pag,
                           role_filter=role_filter,
                           status_filter=status_filter,
                           search_filter=search_filter)


@admin_bp.route('/users/<user_id>/ban', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    user = Profile.get_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users_list'))

    reason = request.form.get('reason', '').strip()
    update_data = {'is_banned': True, 'ban_reason': reason}
    if user.update(update_data):
        send_ban_email(user, reason)
        log_admin_action(
            action='ban_user',
            entity_type='profile',
            entity_id=user.id,
            target_user_id=user.id,
            details={'reason': reason, 'role': user.role},
        )
        flash(f'User Suspended||{user.get_full_name()} has been suspended and notified by email.', 'success')
    else:
        flash('Failed to suspend user', 'error')

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/unban-requests')
@login_required
@admin_required
def unban_requests():
    """List all pending unban appeal requests."""
    try:
        resp = supabase_admin.table('unban_requests') \
            .select('*, profiles(first_name, last_name, email, role)') \
            .eq('status', 'pending') \
            .order('created_at', desc=False) \
            .execute()
        requests_list = resp.data or []
    except Exception as e:
        print(f'unban_requests error: {e}')
        requests_list = []
    return render_template('admin/unban_requests.html', requests=requests_list)


def _get_pending_unban_request(request_id):
    """Return one pending unban request row by id, or None if missing/processed."""
    try:
        resp = supabase_admin.table('unban_requests') \
            .select('id, user_id, status') \
            .eq('id', request_id).single().execute()
        row = resp.data or None
        if not row or row.get('status') != 'pending':
            return None
        return row
    except Exception:
        return None


@admin_bp.route('/users/unban-requests/<request_id>/approve', methods=['POST'])
@login_required
@admin_required
def unban_approve(request_id):
    req_row = _get_pending_unban_request(request_id)
    if not req_row:
        flash('Appeal not found or already processed.', 'warning')
        return redirect(url_for('admin.unban_requests'))

    user_id = req_row.get('user_id')
    user = Profile.get_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.unban_requests'))

    # Unban the profile first.
    if user.update({'is_banned': False, 'ban_reason': None}):
        # Mark this request approved.
        try:
            supabase_admin.table('unban_requests') \
                .update({'status': 'approved'}) \
                .eq('id', request_id).eq('status', 'pending').execute()

            # Any other still-pending appeals by the same user become superseded.
            supabase_admin.table('unban_requests') \
                .update({'status': 'superseded'}) \
                .eq('user_id', user_id).eq('status', 'pending').neq('id', request_id).execute()
            log_admin_action(
                action='approve_unban_request',
                entity_type='unban_request',
                entity_id=request_id,
                target_user_id=user_id,
                details={'request_id': request_id},
            )
        except Exception as e:
            print(f'unban_requests update error: {e}')
        send_unban_approved_email(user)
        flash(f'User Reinstated||{user.get_full_name()} has been reinstated and notified by email.', 'success')
    else:
        flash('Failed to reinstate user.', 'error')
    return redirect(url_for('admin.unban_requests'))


@admin_bp.route('/users/unban-requests/<request_id>/reject', methods=['POST'])
@login_required
@admin_required
def unban_reject(request_id):
    req_row = _get_pending_unban_request(request_id)
    if not req_row:
        flash('Appeal not found or already processed.', 'warning')
        return redirect(url_for('admin.unban_requests'))

    user_id = req_row.get('user_id')
    user = Profile.get_by_id(user_id)
    admin_notes = request.form.get('admin_notes', '').strip()
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.unban_requests'))

    if not admin_notes:
        flash('Admin notes are required when rejecting an appeal.', 'error')
        return redirect(url_for('admin.unban_requests'))

    # Keep user banned, mark this request rejected.
    try:
        supabase_admin.table('unban_requests') \
            .update({'status': 'rejected', 'admin_notes': admin_notes}) \
            .eq('id', request_id).eq('status', 'pending').execute()
        log_admin_action(
            action='reject_unban_request',
            entity_type='unban_request',
            entity_id=request_id,
            target_user_id=user_id,
            details={'admin_notes': admin_notes},
        )
    except Exception as e:
        print(f'unban_requests reject error: {e}')
    send_unban_rejected_email(user, admin_notes)
    flash(f'Appeal Rejected||{user.get_full_name()}\u2019s appeal has been denied. The suspension remains in place.', 'warning')
    return redirect(url_for('admin.unban_requests'))


@admin_bp.route('/users/<user_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    user = Profile.get_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users_list'))

    if user.update({'is_banned': False}):
        log_admin_action(
            action='activate_user',
            entity_type='profile',
            entity_id=user.id,
            target_user_id=user.id,
            details={'role': user.role},
        )
        flash(f'User Activated||{user.get_full_name()} account is now active.', 'success')
    else:
        flash('Failed to activate user', 'error')

    return redirect(url_for('admin.users_list'))
