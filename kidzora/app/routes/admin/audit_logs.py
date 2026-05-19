"""Admin audit log viewer route."""
from datetime import datetime, timedelta
import csv
import io
from io import StringIO

from flask import render_template, request, send_file
from flask_login import login_required

from app.extensions import supabase_admin
from .utils import admin_bp, admin_required


def _profile_map(ids):
    ids = [i for i in ids if i]
    if not ids:
        return {}
    try:
        rows = supabase_admin.table('profiles').select('id,first_name,last_name,email') \
            .in_('id', list(set(ids))).execute().data or []
        return {r.get('id'): r for r in rows}
    except Exception:
        return {}


def _get_audit_stats(all_logs):
    """Calculate stats from logs: most active admins, most common actions."""
    admin_counts = {}
    action_counts = {}
    
    for log in all_logs:
        actor = log.get('actor_id')
        if actor:
            admin_counts[actor] = admin_counts.get(actor, 0) + 1
        
        action = log.get('action', 'unknown')
        action_counts[action] = action_counts.get(action, 0) + 1
    
    top_admins = sorted(admin_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'top_admins': top_admins,
        'top_actions': top_actions,
        'total_actions': sum(action_counts.values()),
    }


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    action_filter = request.args.get('action', '').strip()
    actor_filter = request.args.get('actor_id', '').strip()
    target_filter = request.args.get('target_user_id', '').strip()
    entity_id_filter = request.args.get('entity_id', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 40

    logs = []
    total = 0
    total_pages = 1
    try:
        q = supabase_admin.table('audit_logs').select(
            'id, actor_id, actor_role, action, entity_type, entity_id, target_user_id, details, created_at'
        ).order('created_at', desc=True)

        if action_filter:
            q = q.ilike('action', f'%{action_filter}%')
        if actor_filter:
            q = q.eq('actor_id', actor_filter)
        if target_filter:
            q = q.eq('target_user_id', target_filter)
        if entity_id_filter:
            q = q.ilike('entity_id', f'%{entity_id_filter}%')
        
        all_rows = q.execute().data or []
        
        # Date range filtering (client-side)
        if date_from or date_to:
            filtered_rows = []
            for row in all_rows:
                created_at = row.get('created_at', '')
                if created_at:
                    created_date = created_at[:10]
                    if date_from and created_date < date_from:
                        continue
                    if date_to and created_date > date_to:
                        continue
                filtered_rows.append(row)
            all_rows = filtered_rows
        
        total = len(all_rows)
        start = (page - 1) * per_page
        logs = all_rows[start:start + per_page]
        total_pages = max(1, (total + per_page - 1) // per_page)
    except Exception:
        logs = []

    profile_ids = []
    for row in logs:
        profile_ids.append(row.get('actor_id'))
        profile_ids.append(row.get('target_user_id'))
    pmap = _profile_map(profile_ids)

    for row in logs:
        row['actor_profile'] = pmap.get(row.get('actor_id')) or {}
        row['target_profile'] = pmap.get(row.get('target_user_id')) or {}

    # Get stats from ALL logs (not just filtered page)
    all_logs_for_stats = []
    try:
        all_logs_for_stats = supabase_admin.table('audit_logs').select(
            'actor_id, action'
        ).limit(500).execute().data or []
    except Exception:
        pass
    
    stats = _get_audit_stats(all_logs_for_stats)

    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        page=page,
        total_pages=total_pages,
        total=total,
        per_page=per_page,
        action_filter=action_filter,
        actor_filter=actor_filter,
        target_filter=target_filter,
        entity_id_filter=entity_id_filter,
        date_from=date_from,
        date_to=date_to,
        stats=stats,
        profile_map=pmap,
    )


@admin_bp.route('/audit-logs/export')
@login_required
@admin_required
def export_audit_logs():
    """Export filtered audit logs to CSV."""
    action_filter = request.args.get('action', '').strip()
    actor_filter = request.args.get('actor_id', '').strip()
    target_filter = request.args.get('target_user_id', '').strip()
    entity_id_filter = request.args.get('entity_id', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    logs = []
    try:
        q = supabase_admin.table('audit_logs').select(
            'id, actor_id, actor_role, action, entity_type, entity_id, target_user_id, details, created_at'
        ).order('created_at', desc=True).limit(5000)

        if action_filter:
            q = q.ilike('action', f'%{action_filter}%')
        if actor_filter:
            q = q.eq('actor_id', actor_filter)
        if target_filter:
            q = q.eq('target_user_id', target_filter)
        if entity_id_filter:
            q = q.ilike('entity_id', f'%{entity_id_filter}%')

        all_rows = q.execute().data or []
        
        if date_from or date_to:
            filtered_rows = []
            for row in all_rows:
                created_at = row.get('created_at', '')
                if created_at:
                    created_date = created_at[:10]
                    if date_from and created_date < date_from:
                        continue
                    if date_to and created_date > date_to:
                        continue
                filtered_rows.append(row)
            logs = filtered_rows
        else:
            logs = all_rows
    except Exception:
        logs = []

    # Enrich with profile names
    profile_ids = list(set([log.get('actor_id') for log in logs if log.get('actor_id')]))
    pmap = _profile_map(profile_ids)

    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Action', 'Admin', 'Admin Email', 'Affected User ID', 'Entity Type', 'Entity ID', 'Details'])
    
    for log in logs:
        actor = pmap.get(log.get('actor_id'), {})
        actor_name = f"{actor.get('first_name', '')} {actor.get('last_name', '')}".strip() or 'Unknown'
        actor_email = actor.get('email', 'N/A')
        details_str = str(log.get('details') or {})
        
        writer.writerow([
            log.get('created_at', '')[:19],
            log.get('action', ''),
            actor_name,
            actor_email,
            log.get('target_user_id', ''),
            log.get('entity_type', ''),
            log.get('entity_id', ''),
            details_str,
        ])

    # Return as download
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='audit_logs.csv'
    )
