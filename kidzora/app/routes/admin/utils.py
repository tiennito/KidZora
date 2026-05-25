"""
Admin routes package — blueprint + shared email helpers.

  admin_bp            : Flask Blueprint (url_prefix='/admin' set in app/__init__.py)
  _send_admin_email   : low-level SMTP send
  send_approval_email : styled approval notification
  send_rejection_email: styled rejection notification
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Blueprint, current_app

from app.services.mail_transport import send_html_email
from app.utils.decorators import admin_required  # re-exported for sub-modules

admin_bp = Blueprint('admin', __name__)


# ── Email helpers ──────────────────────────────────────────────────────────────

def _send_admin_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML notification email."""
    return send_html_email(to_email, subject, html_body)
    try:
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port   = int(current_app.config.get('MAIL_PORT', 465))
        username    = current_app.config.get('MAIL_USERNAME', '')
        password    = current_app.config.get('MAIL_PASSWORD', '')
        sender_full = current_app.config.get('MAIL_DEFAULT_SENDER', username)
        use_ssl     = current_app.config.get('MAIL_USE_SSL', True)
        use_tls     = current_app.config.get('MAIL_USE_TLS', False)

        msg = MIMEMultipart('alternative')
        msg['From']    = sender_full
        msg['To']      = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        context = ssl.create_default_context()
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls(context=context)

        server.login(username, password)
        server.sendmail(username, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f'Admin email error: {e}')
        return False


def send_approval_email(user) -> None:
    role        = getattr(user, 'role', 'seller')
    is_rider    = role == 'rider'
    is_buyer    = role == 'buyer'
    role_label  = 'Buyer' if is_buyer else 'Rider' if is_rider else 'Seller'
    if is_buyer:
        dashboard = 'account and start shopping'
    else:
        dashboard = 'rider dashboard and start accepting deliveries' if is_rider else 'seller dashboard and start listing your products'
    subject     = f'KidZora - Your {role_label} Account Has Been Approved!'

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
      <div style="max-width:500px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <h1 style="color:#4f46e5;text-align:center;">KidZora</h1>
        <h2 style="color:#16a34a;">&#10003; Your {role_label} Account Has Been Approved!</h2>
        <p>Hi <strong>{user.get_full_name()}</strong>,</p>
        <p>Great news! Your {role_label.lower()} registration on <strong>KidZora</strong> has been reviewed and
           <strong>approved</strong> by our admin team.</p>
        <p>You can now log in to your {dashboard}.</p>
        <div style="text-align:center;margin:30px 0;">
          <a href="/auth/login" style="background:#4f46e5;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">Go to Dashboard</a>
        </div>
        <p style="color:#6b7280;font-size:13px;">If you have any questions, contact us at support@kidzora.com.</p>
        <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
      </div>
    </body></html>
    """
    _send_admin_email(user.email, subject, html)


def send_rejection_email(user, reason: str) -> None:
    role        = getattr(user, 'role', 'seller')
    is_rider    = role == 'rider'
    is_buyer    = role == 'buyer'
    role_label  = 'Buyer' if is_buyer else 'Rider' if is_rider else 'Seller'
    if is_buyer:
        default_reason = 'Submitted identity verification did not meet our requirements.'
    else:
        default_reason = 'Does not meet our rider requirements.' if is_rider else 'Does not meet our seller requirements.'
    subject     = f'KidZora - {role_label} Registration Update'

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
      <div style="max-width:500px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <h1 style="color:#4f46e5;text-align:center;">KidZora</h1>
        <h2 style="color:#dc2626;">&#10007; {role_label} Registration Update</h2>
        <p>Hi <strong>{user.get_full_name()}</strong>,</p>
        <p>We regret to inform you that your {role_label.lower()} registration on <strong>KidZora</strong> has been
           <strong>reviewed and was not approved</strong> at this time.</p>
        <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;border-radius:4px;margin:20px 0;">
          <strong>Reason:</strong> {reason or default_reason}
        </div>
        <p>You are welcome to re-apply once you have addressed the issues above.
           If you believe this was a mistake, please contact us.</p>
        <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
      </div>
    </body></html>
    """
    _send_admin_email(user.email, subject, html)


def send_ban_email(user, reason: str) -> None:
    role_label = 'Rider' if getattr(user, 'role', '') == 'rider' else 'Seller' if getattr(user, 'role', '') == 'seller' else 'Account'
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
      <div style="max-width:520px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <h1 style="color:#4f46e5;text-align:center;">KidZora</h1>
        <h2 style="color:#dc2626;">&#9888; Your Account Has Been Suspended</h2>
        <p>Hi <strong>{user.get_full_name()}</strong>,</p>
        <p>Your <strong>KidZora {role_label} account</strong> has been <strong>suspended</strong> by our admin team.</p>
        <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;border-radius:4px;margin:20px 0;">
          <strong>Reason:</strong><br>{reason or 'Violation of KidZora platform terms.'}
        </div>
        <p>If you believe this is a mistake or have addressed the issue, you can submit an
           <strong>appeal</strong> by logging in and uploading the required documents.</p>
        <div style="text-align:center;margin:30px 0;">
          <a href="/auth/login" style="background:#4f46e5;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">Submit an Appeal</a>
        </div>
        <p style="color:#6b7280;font-size:13px;">Questions? Contact us at support@kidzora.com.</p>
        <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
      </div>
    </body></html>
    """
    _send_admin_email(user.email, 'KidZora - Your Account Has Been Suspended', html)


def send_unban_approved_email(user) -> None:
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
      <div style="max-width:520px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <h1 style="color:#4f46e5;text-align:center;">KidZora</h1>
        <h2 style="color:#16a34a;">&#10003; Your Account Has Been Reinstated</h2>
        <p>Hi <strong>{user.get_full_name()}</strong>,</p>
        <p>Your appeal was approved! Your <strong>KidZora account has been reinstated</strong>.
           You can now log in and continue using the platform.</p>
        <div style="text-align:center;margin:30px 0;">
          <a href="/auth/login" style="background:#16a34a;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">Log In Now</a>
        </div>
        <p style="color:#6b7280;font-size:13px;">Questions? Contact us at support@kidzora.com.</p>
        <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
      </div>
    </body></html>
    """
    _send_admin_email(user.email, 'KidZora - Your Account Has Been Reinstated', html)


def send_unban_rejected_email(user, admin_notes: str) -> None:
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
      <div style="max-width:520px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <h1 style="color:#4f46e5;text-align:center;">KidZora</h1>
        <h2 style="color:#dc2626;">&#10007; Appeal Not Approved</h2>
        <p>Hi <strong>{user.get_full_name()}</strong>,</p>
        <p>We reviewed your appeal. Unfortunately, your <strong>KidZora account</strong> cannot be
           reinstated at this time.</p>
        <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;border-radius:4px;margin:20px 0;">
          <strong>Admin notes:</strong><br>{admin_notes or 'The submitted documents did not meet our requirements.'}
        </div>
        <p>You may log in and submit a new appeal after addressing the issues above.</p>
        <p style="color:#6b7280;font-size:13px;">Questions? Contact us at support@kidzora.com.</p>
        <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
      </div>
    </body></html>
    """
    _send_admin_email(user.email, 'KidZora - Appeal Update', html)
