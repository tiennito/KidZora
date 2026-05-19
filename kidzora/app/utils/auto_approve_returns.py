"""
app/utils/auto_approve_returns.py
----------------------------------
Scans for return requests that have been sitting in 'pending' status longer
than the configured `return_auto_approve_days` platform setting and
auto-approves them on behalf of the seller.

Called lazily from app's before_request hook — runs at most once every
5 minutes in-process to avoid hammering the DB on every single request.
"""
from __future__ import annotations

import time
import traceback
from datetime import datetime, timedelta, timezone

_last_run: float = 0.0
_RUN_INTERVAL = 300  # seconds between checks (5 minutes)


def maybe_run_auto_approvals() -> None:
    """Call this from before_request.  Throttled to once per 5 minutes."""
    global _last_run
    now = time.monotonic()
    if now - _last_run < _RUN_INTERVAL:
        return
    _last_run = now
    try:
        _run()
    except Exception:
        traceback.print_exc()


def _run() -> None:
    from app.extensions import supabase_admin as supabase
    from app.utils.settings import get_return_auto_approve_days
    from app.services.notify import push

    days = get_return_auto_approve_days()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Find all pending returns older than the cutoff
    try:
        rows = (supabase.table('return_requests')
                .select('id, order_id, buyer_id, seller_id')
                .eq('status', 'pending')
                .lt('created_at', cutoff)
                .execute().data or [])
    except Exception:
        traceback.print_exc()
        return

    if not rows:
        return

    for rr in rows:
        rr_id     = rr['id']
        buyer_id  = rr.get('buyer_id')
        seller_id = rr.get('seller_id')
        order_id  = rr.get('order_id')
        short     = (order_id or rr_id)[:8].upper()
        try:
            supabase.table('return_requests').update({
                'status':          'seller_approved',
                'seller_response': (
                    f'Auto-approved by system after {days} days with no seller response.'
                ),
            }).eq('id', rr_id).eq('status', 'pending').execute()
        except Exception:
            traceback.print_exc()
            continue

        # Notify buyer
        if buyer_id:
            try:
                push(
                    user_id=buyer_id,
                    ntype='return_auto_approved',
                    title=f'Return Auto-Approved — #{short}',
                    body=(
                        f'Your return request was automatically approved because the seller '
                        f'did not respond within {days} days. A refund will be processed.'
                    ),
                    data={'rr_id': rr_id, 'url': f'/buyer/returns/{rr_id}'},
                )
            except Exception:
                traceback.print_exc()

        # Notify seller
        if seller_id:
            try:
                push(
                    user_id=seller_id,
                    ntype='return_auto_approved',
                    title=f'Return Auto-Approved — #{short}',
                    body=(
                        f'A return request was automatically approved after {days} days '
                        f'without a response. Please process the refund.'
                    ),
                    data={'rr_id': rr_id, 'url': f'/seller/returns/{rr_id}'},
                )
            except Exception:
                traceback.print_exc()
