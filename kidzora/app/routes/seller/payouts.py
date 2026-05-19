"""Seller – Payouts / Withdrawals.

Routes:
  GET  /seller/payouts          — earnings summary + payout history + request form
  POST /seller/payouts/request  — submit a new withdrawal request
"""
from datetime import datetime, timezone

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import supabase_admin as supabase
from app.utils.settings import get_commission_rate
from .utils import seller_bp, seller_required, _get_seller_id

MIN_PAYOUT = 100.00  # minimum withdrawal (₱)


def _calc_earnings(seller_id: str) -> dict:
    """Return total_earned, total_paid_out, pending_balance from the DB."""
    total_earned   = 0.0
    total_paid_out = 0.0
    commission_rate = get_commission_rate()

    # ── Earned: sum seller_earnings on completed orders
    try:
        ord_r = supabase.table('orders') \
            .select('total') \
            .eq('seller_id', seller_id) \
            .eq('status', 'completed') \
            .execute()
        for o in (ord_r.data or []):
            total_earned += float(o.get('total') or 0) * (1 - commission_rate)
    except Exception:
        pass

    # ── Paid out: sum of approved payout requests
    try:
        pr_r = supabase.table('payout_requests') \
            .select('amount') \
            .eq('seller_id', seller_id) \
            .eq('status', 'approved') \
            .execute()
        for p in (pr_r.data or []):
            total_paid_out += float(p.get('amount') or 0)
    except Exception:
        pass

    # ── Frozen: pending requests lock the balance
    pending_lock = 0.0
    try:
        lock_r = supabase.table('payout_requests') \
            .select('amount') \
            .eq('seller_id', seller_id) \
            .eq('status', 'pending') \
            .execute()
        for p in (lock_r.data or []):
            pending_lock += float(p.get('amount') or 0)
    except Exception:
        pass

    available = max(0.0, total_earned - total_paid_out - pending_lock)
    return {
        'total_earned':   round(total_earned,   2),
        'total_paid_out': round(total_paid_out, 2),
        'pending_lock':   round(pending_lock,   2),
        'available':      round(available,      2),
    }


# ─────────────────────────────────────────────────────────────
#  Main page
# ─────────────────────────────────────────────────────────────
@seller_bp.route('/payouts')
@login_required
@seller_required
def payouts():
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.dashboard'))

    earnings = _calc_earnings(seller_id)

    # ── Payout history (all requests)
    history = []
    try:
        h_r = supabase.table('payout_requests') \
            .select('*') \
            .eq('seller_id', seller_id) \
            .order('created_at', desc=True) \
            .limit(50) \
            .execute()
        history = h_r.data or []
    except Exception as e:
        flash(f'Could not load payout history||{e}', 'error')

    # ── Seller's saved bank/GCash details
    seller_info = {}
    try:
        s_r = supabase.table('sellers') \
            .select('bank_account,bank_name') \
            .eq('id', seller_id) \
            .single() \
            .execute()
        seller_info = s_r.data or {}
    except Exception:
        pass

    # ── Check if there's already a pending request
    has_pending = any(h.get('status') == 'pending' for h in history)

    return render_template(
        'seller/payouts.html',
        earnings    = earnings,
        history     = history,
        seller_info = seller_info,
        has_pending = has_pending,
        min_payout  = MIN_PAYOUT,
    )


# ─────────────────────────────────────────────────────────────
#  Submit withdrawal request
# ─────────────────────────────────────────────────────────────
@seller_bp.route('/payouts/request', methods=['POST'])
@login_required
@seller_required
def request_payout():
    seller_id = _get_seller_id()
    if not seller_id:
        flash('Seller profile not found.', 'error')
        return redirect(url_for('seller.payouts'))

    amount_str     = request.form.get('amount', '').strip()
    method         = request.form.get('method', '').strip()
    account_name   = request.form.get('account_name', '').strip()
    account_number = request.form.get('account_number', '').strip()

    # ── Validation
    errors = []
    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        amount = 0.0
        errors.append('Enter a valid amount.')

    if amount < MIN_PAYOUT:
        errors.append(f'Minimum payout is ₱{MIN_PAYOUT:,.2f}.')
    if method not in ('gcash', 'bank_transfer'):
        errors.append('Choose a valid payout method.')
    if not account_name:
        errors.append('Account name is required.')
    if not account_number:
        errors.append('Account number / GCash number is required.')

    # ── Check available balance
    earnings = _calc_earnings(seller_id)
    if amount > earnings['available']:
        errors.append(
            f'Requested ₱{amount:,.2f} exceeds available balance '
            f'₱{earnings["available"]:,.2f}.'
        )

    # ── Block if there's already a pending request
    try:
        pending = supabase.table('payout_requests') \
            .select('id') \
            .eq('seller_id', seller_id) \
            .eq('status', 'pending') \
            .execute().data
        if pending:
            errors.append('You already have a pending payout request. Wait for it to be processed.')
    except Exception:
        pass

    if errors:
        for e in errors:
            flash(f'Cannot submit request||{e}', 'error')
        return redirect(url_for('seller.payouts'))

    # ── Insert request
    try:
        supabase.table('payout_requests').insert({
            'seller_id':      seller_id,
            'amount':         round(amount, 2),
            'method':         method,
            'account_name':   account_name,
            'account_number': account_number,
            'status':         'pending',
        }).execute()

        # Optionally save bank details back to sellers row
        supabase.table('sellers').update({
            'bank_account': account_number,
            'bank_name':    account_name,
        }).eq('id', seller_id).execute()

        flash(
            'Withdrawal Request Submitted!||'
            'Your request is now pending admin review. Funds are typically released within 1–3 business days.',
            'success'
        )
    except Exception as e:
        flash(f'Could not submit request||{e}', 'error')

    return redirect(url_for('seller.payouts'))
