"""
Rider routes package.

Structure:
  rider/
    __init__.py    ← this file (exposes rider_bp)
    utils.py       ← Blueprint instance + rider_required decorator
    dashboard.py   ← GET /rider/dashboard
    deliveries.py  ← /rider/deliveries (list, detail, status update)
    earnings.py    ← GET /rider/earnings
    profile.py     ← GET/POST /rider/profile
"""

from .utils import rider_bp  # noqa: F401  — exported for app/__init__.py

from . import dashboard       # noqa: F401
from . import deliveries     # noqa: F401
from . import earnings       # noqa: F401
from . import notifications  # noqa: F401
from . import profile        # noqa: F401
from . import chat           # noqa: F401
from . import ratings        # noqa: F401
from . import payouts        # noqa: F401
