"""
Seller routes package.

Structure:
  seller/
    __init__.py   ← this file  (exposes seller_bp)
    utils.py      ← Blueprint instance + shared helpers/decorators
    dashboard.py  ← /seller/dashboard
    products.py   ← /seller/products  (list, add, edit, delete, toggle)
    orders.py     ← /seller/orders    (list, detail, status update)
    profile.py    ← /seller/profile

Import order matters: utils must be first (defines seller_bp),
then each module imports seller_bp and registers its routes.
"""

from .utils import seller_bp  # noqa: F401  — exported for app/__init__.py

# Register routes by importing the sub-modules (side-effects only)
from . import dashboard      # noqa: F401
from . import products       # noqa: F401
from . import orders         # noqa: F401
from . import profile        # noqa: F401
from . import coupons        # noqa: F401
from . import returns        # noqa: F401
from . import chat           # noqa: F401
from . import notifications  # noqa: F401
from . import analytics      # noqa: F401
from . import reviews        # noqa: F401
from . import payouts        # noqa: F401
