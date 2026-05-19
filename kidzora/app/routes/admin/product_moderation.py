"""Admin product moderation queue routes."""
from datetime import datetime, timezone

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import supabase_admin
from .utils import admin_bp, admin_required


def _load_profiles(profile_ids):
    if not profile_ids:
        return {}
    try:
        rows = supabase_admin.table('profiles') \
            .select('id, first_name, last_name, email') \
            .in_('id', list(profile_ids)).execute().data or []
        return {r.get('id'): r for r in rows}
    except Exception:
        return {}


def _load_products(product_ids):
    if not product_ids:
        return {}
    try:
        rows = supabase_admin.table('products') \
            .select('id, seller_id, name, images, is_active, is_deleted, created_at') \
            .in_('id', list(product_ids)).execute().data or []
        return {r.get('id'): r for r in rows}
    except Exception:
        return {}


def _get_report_by_id(report_id):
    try:
        resp = supabase_admin.table('product_reports') \
            .select('id, product_id, reporter_id, status') \
            .eq('id', report_id).single().execute()
        return resp.data or None
    except Exception:
        return None


def _update_product_for_action(product_id, action):
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {'updated_at': now_iso}

    if action == 'hidden':
        payload['is_active'] = False
    elif action == 'removed':
        payload['is_active'] = False
        payload['is_deleted'] = True

    try:
        supabase_admin.table('products').update(payload).eq('id', product_id).execute()
        return True
    except Exception:
        # Backward compatibility: some environments may not yet have is_deleted.
        try:
            fallback = {'is_active': False, 'updated_at': now_iso}
            supabase_admin.table('products').update(fallback).eq('id', product_id).execute()
            return action in ('hidden', 'removed')
        except Exception:
            return False


@admin_bp.route('/product-moderation')
@login_required
@admin_required
def product_moderation():
    status = request.args.get('status', 'pending').strip().lower()
    if status not in ('pending', 'actioned', 'dismissed', 'all'):
        status = 'pending'

    try:
        query = supabase_admin.table('product_reports') \
            .select('id, product_id, reporter_id, reason, details, status, action_taken, admin_notes, reviewed_by, reviewed_at, created_at') \
            .order('created_at', desc=False)
        if status != 'all':
            query = query.eq('status', status)
        reports = query.execute().data or []
    except Exception as exc:
        print(f'product_moderation list error: {exc}')
        reports = []

    product_map = _load_products({r.get('product_id') for r in reports if r.get('product_id')})
    profile_map = _load_profiles({
        *(r.get('reporter_id') for r in reports if r.get('reporter_id')),
        *(r.get('reviewed_by') for r in reports if r.get('reviewed_by')),
    })

    for row in reports:
        product = product_map.get(row.get('product_id')) or {}
        reporter = profile_map.get(row.get('reporter_id')) or {}
        reviewer = profile_map.get(row.get('reviewed_by')) or {}

        row['product'] = product
        row['reporter'] = reporter
        row['reviewer'] = reviewer

    return render_template('admin/product_moderation.html', reports=reports, status_filter=status)


@admin_bp.route('/product-moderation/<report_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_product_report(report_id):
    action = (request.form.get('action') or '').strip().lower()
    admin_notes = (request.form.get('admin_notes') or '').strip()

    if action not in ('hide', 'remove', 'dismiss'):
        flash('Invalid moderation action.', 'error')
        return redirect(url_for('admin.product_moderation'))

    report = _get_report_by_id(report_id)
    if not report:
        flash('Report not found.', 'error')
        return redirect(url_for('admin.product_moderation'))
    if report.get('status') != 'pending':
        flash('Report already processed.', 'warning')
        return redirect(url_for('admin.product_moderation'))

    if action in ('hide', 'remove'):
        target_action = 'hidden' if action == 'hide' else 'removed'
        updated = _update_product_for_action(report.get('product_id'), target_action)
        if not updated:
            flash('Unable to update product status.', 'error')
            return redirect(url_for('admin.product_moderation'))
        new_status = 'actioned'
        action_taken = target_action
    else:
        new_status = 'dismissed'
        action_taken = 'dismissed'

    try:
        supabase_admin.table('product_reports').update({
            'status': new_status,
            'action_taken': action_taken,
            'admin_notes': admin_notes or None,
            'reviewed_by': str(current_user.id),
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', report_id).execute()
    except Exception as exc:
        print(f'resolve_product_report update error: {exc}')
        flash('Moderation action applied, but report status update failed.', 'warning')
        return redirect(url_for('admin.product_moderation'))

    if action == 'hide':
        flash('Product hidden and report marked as actioned.', 'success')
    elif action == 'remove':
        flash('Product removed and report marked as actioned.', 'success')
    else:
        flash('Report dismissed.', 'success')

    return redirect(url_for('admin.product_moderation'))
