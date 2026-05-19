import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    COMMISSION_RATE = float(os.environ.get('COMMISSION_RATE', 0.05))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'app/static/uploads')
    # Default: 150 MB to support up to 5 × 30 MB evidence files on return/refund requests
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 157286400))
    
    # Email Configuration (Resend SMTP)
    USE_SUPABASE_EMAIL = os.environ.get('USE_SUPABASE_EMAIL', 'False').lower() in ['true', 'on', '1']
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.resend.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 465)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'True').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'resend'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 're_cGQHWAKD_C8XTsGLcpvrkE6AgoQRAvEHJ'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'KidZora <onboarding@resend.dev>'
    MAIL_FROM_ADDRESS = os.environ.get('MAIL_FROM_ADDRESS') or 'onboarding@resend.dev'
    
    # ── Web Push / VAPID ──────────────────────────────────────────────────────
    # Generate a key pair once and store in .env:
    #   python -c "from pywebpush import Vapid; v=Vapid(); v.generate_keys(); print('PRIVATE:',v.private_key.decode()); print('PUBLIC:',v.public_key.decode())"
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
    VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_MAILTO      = os.environ.get('VAPID_MAILTO', 'mailto:admin@kidzora.com')

    # Ensure upload folder exists (only if not in serverless environment)
    @staticmethod
    def ensure_upload_folder():
        try:
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        except (PermissionError, OSError):
            # Serverless environment - uploads folder not critical
            pass

class DevelopmentConfig(Config):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
