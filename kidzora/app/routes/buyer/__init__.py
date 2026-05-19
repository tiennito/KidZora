"""
Buyer routes package.

Structure:
  buyer/
    __init__.py  ← this file (exposes buyer_bp)
    utils.py     ← Blueprint instance + buyer_required decorator
    dashboard.py ← GET /buyer/dashboard
    products.py  ← GET /buyer/browse
    orders.py    ← GET /buyer/orders
    wishlist.py  ← GET /buyer/wishlist
    profile.py   ← GET /buyer/profile
"""

from .utils import buyer_bp  # noqa: F401  — exported for app/__init__.py

from . import dashboard  # noqa: F401
from . import products   # noqa: F401
from . import orders     # noqa: F401
from . import wishlist   # noqa: F401
from . import profile    # noqa: F401
from . import cart       # noqa: F401
from . import checkout   # noqa: F401
from . import returns       # noqa: F401
from . import reviews       # noqa: F401
from . import chat          # noqa: F401
from . import notifications  # noqa: F401
from . import support        # noqa: F401
from . import addresses      # noqa: F401
from . import follows        # noqa: F401
