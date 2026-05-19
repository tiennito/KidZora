"""Admin ↔ Seller chat routes."""
from datetime import datetime, timezone

from flask import abort, jsonify, render_template, request, url_for
from flask_login import current_user

from app.extensions import supabase_admin as supabase
from app.services.notify import push
from app.services.chat import set_typing, is_typing
from app.services.email import notify_new_message
from .utils import admin_bp, admin_required


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_profile(user_id):
    try:
        r = supabase.table('profiles').select(
            'id,first_name,last_name,business_name,role,avatar_url'
        ).eq('id', user_id).single().execute()
        return r.data
    except Exception:
        return None


def _display_name(prof):
    if not prof:
        return 'User'
    return (
        f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip()
        or prof.get('business_name')
        or 'User'
    )


def _mark_read(my_id, other_id):
    try:
        supabase.table('messages').update({'is_read': True, 'is_delivered': True}) \
            .eq('receiver_id', my_id) \
            .eq('sender_id', other_id) \
            .eq('is_read', False) \
            .execute()
    except Exception:
        pass


def _mark_delivered(my_id, other_id):
    try:
        supabase.table('messages').update({'is_delivered': True}) \
            .eq('receiver_id', my_id) \
            .eq('sender_id', other_id) \
            .eq('is_delivered', False) \
            .execute()
    except Exception:
        pass


def _time_label(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds()
        if diff < 60:
            return 'just now'
        if diff < 3600:
            return f"{int(diff // 60)}m ago"
        if diff < 86400:
            return f"{int(diff // 3600)}h ago"
        return dt.strftime('%b %d').replace(' 0', ' ')
    except Exception:
        return ''


# ── Admin Inbox ───────────────────────────────────────────────────────────────

@admin_bp.route('/inbox')
@admin_required
def inbox():
    convos = []
    try:
        uid = current_user.id

        _q = supabase.table('messages').select('*')
        _q.params = _q.params.add('or', f'(sender_id.eq.{uid},receiver_id.eq.{uid})')
        r = _q.order('created_at', desc=True).execute()
        msgs = r.data or []

        seen: dict[str, dict] = {}
        for m in msgs:
            other_id = m['receiver_id'] if m['sender_id'] == uid else m['sender_id']
            if other_id not in seen:
                seen[other_id] = m

        if not seen:
            all_users = []
            try:
                ur = supabase.table('profiles').select(
                    'id,first_name,last_name,business_name,role,avatar_url'
                ).neq('role', 'admin').order('first_name').execute()
                for p in (ur.data or []):
                    all_users.append({
                        'id':         p['id'],
                        'name':       _display_name(p),
                        'role':       p.get('role', 'buyer'),
                        'avatar_url': p.get('avatar_url') or '',
                        'chat_url':   url_for('admin.chat_with_seller', other_user_id=p['id']),
                    })
            except Exception:
                pass
            return render_template('admin/inbox.html', convos=[], all_users=all_users,
                badge='Admin',
                dashboard_url=url_for('admin.dashboard'),
                tabs_config=[
                    {'key': 'seller', 'label': 'Sellers', 'icon': 'fa-store'},
                    {'key': 'buyer',  'label': 'Buyers',  'icon': 'fa-user'},
                    {'key': 'rider',  'label': 'Riders',  'icon': 'fa-motorcycle'},
                ],
                stat3_role='seller', stat3_label='Sellers',
            )

        unread_r = supabase.table('messages').select('sender_id') \
            .eq('receiver_id', uid).eq('is_read', False).execute()
        unread_map: dict[str, int] = {}
        for u in (unread_r.data or []):
            sid = u['sender_id']
            unread_map[sid] = unread_map.get(sid, 0) + 1

        partner_ids = list(seen.keys())
        prof_r = supabase.table('profiles').select(
            'id,first_name,last_name,business_name,role,avatar_url'
        ).in_('id', partner_ids).execute()
        prof_map = {p['id']: p for p in (prof_r.data or [])}

        for oid, latest in seen.items():
            prof = prof_map.get(oid, {})
            convos.append({
                'other_id':   oid,
                'name':       _display_name(prof),
                'role':       prof.get('role', ''),
                'avatar_url': prof.get('avatar_url') or '',
                'latest':     latest.get('content', ''),
                'latest_at':  latest.get('created_at', ''),
                'time_label': _time_label(latest.get('created_at', '')),
                'unread':     unread_map.get(oid, 0),
                'is_mine':    latest.get('sender_id') == uid,
                'chat_url':   url_for('admin.chat_with_seller', other_user_id=oid),
            })

        convos.sort(key=lambda c: c['latest_at'], reverse=True)

    except Exception as e:
        print(f"[admin.inbox] error: {e}")

    # Fetch all non-admin users so admin can start new conversations
    all_users = []
    try:
        ur = supabase.table('profiles').select(
            'id,first_name,last_name,business_name,role,avatar_url'
        ).neq('role', 'admin').order('first_name').execute()
        for p in (ur.data or []):
            all_users.append({
                'id':         p['id'],
                'name':       _display_name(p),
                'role':       p.get('role', 'buyer'),
                'avatar_url': p.get('avatar_url') or '',
                'chat_url':   url_for('admin.chat_with_seller', other_user_id=p['id']),
            })
    except Exception as e:
        print(f"[admin.inbox] all_users error: {e}")

    return render_template('admin/inbox.html', convos=convos, all_users=all_users,
        badge='Admin',
        dashboard_url=url_for('admin.dashboard'),
        tabs_config=[
            {'key': 'seller', 'label': 'Sellers', 'icon': 'fa-store'},
            {'key': 'buyer',  'label': 'Buyers',  'icon': 'fa-user'},
            {'key': 'rider',  'label': 'Riders',  'icon': 'fa-motorcycle'},
        ],
        stat3_role='seller', stat3_label='Sellers',
    )


# ── Chat window ───────────────────────────────────────────────────────────────

@admin_bp.route('/chat/<other_user_id>')
@admin_required
def chat_with_seller(other_user_id):
    other = _get_profile(other_user_id)
    if not other:
        abort(404)

    _mark_read(current_user.id, other_user_id)

    msgs = []
    try:
        uid = current_user.id
        _q = supabase.table('messages').select('*')
        _q.params = _q.params.add('or', f'(and(sender_id.eq.{uid},receiver_id.eq.{other_user_id}),and(sender_id.eq.{other_user_id},receiver_id.eq.{uid}))')
        r = _q.order('created_at', desc=False).limit(100).execute()
        msgs = r.data or []
    except Exception as e:
        print(f"[admin.chat_with_seller] error: {e}")

    embed = bool(request.args.get('embed'))
    return render_template(
        'shared/chat_dark.html',
        other=other,
        other_name=_display_name(other),
        messages=msgs,
        embed=embed,
        back_url=url_for('admin.inbox'),
        send_url=url_for('admin.chat_send',   other_user_id=other_user_id),
        poll_url=url_for('admin.chat_poll',   other_user_id=other_user_id),
        typing_url=url_for('admin.chat_typing', other_user_id=other_user_id),
    )


# ── Send message (AJAX POST) ──────────────────────────────────────────────────

@admin_bp.route('/chat/<other_user_id>/send', methods=['POST'])
@admin_required
def chat_send(other_user_id):
    content = (request.json or {}).get('content', '').strip()
    if not content:
        return jsonify({'ok': False, 'error': 'Empty message'}), 400

    try:
        now = datetime.now(timezone.utc).isoformat()
        r = supabase.table('messages').insert({
            'sender_id':    current_user.id,
            'receiver_id':  other_user_id,
            'content':      content,
            'message_type': 'text',
            'is_read':      False,
            'created_at':   now,
        }).execute()
        msg = r.data[0] if r.data else {}

        push(
            user_id=other_user_id,
            ntype='message_received',
            title='New message from KidZora Admin',
            body=content[:120],
            data={
                'sender_id':      current_user.id,
                'sender_name':    'KidZora Admin',
                'avatar_initial': 'A',
                'avatar_url':     getattr(current_user, 'avatar_url', None) or '',
            },
        )

        # Send email notification if recipient is offline
        notify_new_message(
            message_id=msg.get('id', ''),
            sender_id=current_user.id,
            receiver_id=other_user_id,
            message_content=content,
        )

        return jsonify({'ok': True, 'msg': msg})
    except Exception as e:
        print(f"[admin.chat_send] error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


# ── Poll for new messages (AJAX GET) ─────────────────────────────────────────

@admin_bp.route('/chat/<other_user_id>/poll')
@admin_required
def chat_poll(other_user_id):
    since = request.args.get('since', '')
    try:
        uid = current_user.id
        _q = supabase.table('messages').select('*')
        _q.params = _q.params.add('or', f'(and(sender_id.eq.{uid},receiver_id.eq.{other_user_id}),and(sender_id.eq.{other_user_id},receiver_id.eq.{uid}))')
        _q = _q.order('created_at', desc=False)
        if since:
            _q = _q.gt('created_at', since)
        r = _q.limit(50).execute()
        msgs = r.data or []

        _mark_delivered(uid, other_user_id)
        _mark_read(uid, other_user_id)

        typing = is_typing(other_user_id, uid)

        return jsonify({'ok': True, 'messages': msgs, 'typing': typing})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ── Typing indicator (POST) ───────────────────────────────────────────────────

@admin_bp.route('/chat/<other_user_id>/typing', methods=['POST'])
@admin_required
def chat_typing(other_user_id):
    set_typing(current_user.id, other_user_id)
    return jsonify({'ok': True})
