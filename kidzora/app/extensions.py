from __future__ import annotations

from flask_login import LoginManager
from supabase import create_client
from config import Config

# Supabase anon client (for user-facing operations)
try:
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
except Exception as e:
    print(f"Warning: Supabase not configured properly: {e}")
    supabase = None

# Supabase admin client (service role - bypasses RLS and email confirmation)
try:
    supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
except Exception as e:
    print(f"Warning: Supabase admin client not configured: {e}")
    supabase_admin = None

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from app.models.profile import Profile
    return Profile.get_by_id(user_id)
