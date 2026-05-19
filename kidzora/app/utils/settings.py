"""
app/utils/settings.py
---------------------
Thin helpers to read/write platform_settings rows in Supabase.

Values are cached in-process for 60 seconds so every request doesn't
hit the DB, but changes made via the admin UI take effect within a minute.
"""
import time
from flask import current_app

_cache: dict = {}
_cache_ts: dict = {}
_TTL = 60  # seconds


def _client():
    from app.extensions import supabase_admin
    return supabase_admin


def get_setting(key: str, default=None):
    """Return the value of *key* from platform_settings (cached 60 s)."""
    now = time.monotonic()
    if key in _cache and (now - _cache_ts.get(key, 0)) < _TTL:
        return _cache[key]
    try:
        row = (_client()
               .table('platform_settings')
               .select('value')
               .eq('key', key)
               .maybe_single()
               .execute())
        val = row.data['value'] if row.data else None
    except Exception:
        val = None
    result = val if val is not None else default
    _cache[key] = result
    _cache_ts[key] = now
    return result


def set_setting(key: str, value: str) -> bool:
    """Upsert *key* → *value* in platform_settings and bust the cache."""
    try:
        _client().table('platform_settings').upsert(
            {'key': key, 'value': str(value)},
            on_conflict='key'
        ).execute()
        _cache[key] = str(value)
        _cache_ts[key] = time.monotonic()
        return True
    except Exception as exc:
        current_app.logger.error('set_setting(%s) failed: %s', key, exc)
        return False


def get_commission_rate() -> float:
    """Return the current platform commission rate as a float (e.g. 0.05)."""
    raw = get_setting('commission_rate', None)
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    # Fall back to config value if DB is unavailable
    return float(current_app.config.get('COMMISSION_RATE', 0.05))


def get_payout_frequency() -> str:
    return get_setting('payout_frequency', 'weekly')


def get_return_auto_approve_days() -> int:
    """Return number of days before a pending return request is auto-approved (default 5)."""
    raw = get_setting('return_auto_approve_days', None)
    if raw is not None:
        try:
            val = int(raw)
            if val > 0:
                return val
        except (TypeError, ValueError):
            pass
    return 5
