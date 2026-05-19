"""Pricing helpers — compute effective (possibly sale) price for a product dict."""
from datetime import datetime, timezone


def effective_price(p: dict) -> float:
    """Return sale_price if a sale is currently active, else the regular price."""
    sp   = p.get('sale_price')
    base = float(p.get('price') or 0)
    if not sp:
        return base
    try:
        sp = float(sp)
    except (TypeError, ValueError):
        return base

    now = datetime.now(timezone.utc)

    def _parse(s):
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(str(s).replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    starts    = _parse(p.get('sale_starts_at'))
    ends      = _parse(p.get('sale_ends_at'))
    started   = (starts is None) or (now >= starts)
    not_ended = (ends   is None) or (now <= ends)
    return sp if (started and not_ended) else base


def annotate_sale(p: dict) -> dict:
    """Adds _effective_price and _on_sale keys to a product dict in-place."""
    ep = effective_price(p)
    p['_effective_price'] = ep
    p['_on_sale'] = ep < float(p.get('price') or 0)
    return p
