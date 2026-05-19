"""
Admin routes package.

Structure:
  admin/
    __init__.py   ← this file (exposes admin_bp)
    utils.py      ← Blueprint + email helpers + admin_required re-export
    dashboard.py  ← /admin/dashboard
    users.py      ← /admin/users/* (pending, approve, reject, list, ban, activate)
                     /admin/api/seller-details/<id>
                     /admin/users/unban-requests
                     /admin/users/unban-requests/<request_id>/approve
                     /admin/users/unban-requests/<request_id>/reject
    commission.py ← /admin/commission
    reports.py    ← /admin/reports
    product_moderation.py ← /admin/product-moderation
    audit_logs.py ← /admin/audit-logs
    system_health.py ← /admin/system-health
    coupons.py    ← /admin/coupons (list/create/edit/delete)
    chat.py       ← /admin/chat/<seller_id>
    orders.py     ← /admin/orders (list, detail, force-cancel)
"""

from .utils import admin_bp  # noqa: F401  — exported for app/__init__.py

# Register routes by importing sub-modules (side-effects only)
from . import dashboard   # noqa: F401
from . import users       # noqa: F401
from . import commission  # noqa: F401
from . import reports     # noqa: F401
from . import product_moderation  # noqa: F401
from . import audit_logs  # noqa: F401
from . import system_health  # noqa: F401
from . import coupons     # noqa: F401
from . import chat        # noqa: F401
from . import orders      # noqa: F401
from . import payouts     # noqa: F401
from . import rider_payouts  # noqa: F401
from . import returns     # noqa: F401
from . import analytics   # noqa: F401
from . import support     # noqa: F401
from . import delivery_zones  # noqa: F401
