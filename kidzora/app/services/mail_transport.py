import smtplib
import ssl
from email.utils import parseaddr

import requests
from flask import current_app


def _mail_provider() -> str:
    return (current_app.config.get('MAIL_PROVIDER') or '').lower()


def _uses_brevo_api() -> bool:
    provider = _mail_provider()
    server = (current_app.config.get('MAIL_SERVER') or '').lower()
    return bool(current_app.config.get('BREVO_API_KEY')) or provider == 'brevo' or 'brevo' in server or 'sendinblue' in server


def _uses_resend_api() -> bool:
    provider = _mail_provider()
    server = (current_app.config.get('MAIL_SERVER') or '').lower()
    return bool(current_app.config.get('RESEND_API_KEY')) or provider == 'resend' or 'resend.com' in server


def _resend_api_key() -> str:
    return current_app.config.get('RESEND_API_KEY') or current_app.config.get('MAIL_PASSWORD', '')


def _brevo_api_key() -> str:
    return current_app.config.get('BREVO_API_KEY') or current_app.config.get('MAIL_PASSWORD', '')


def _sender_parts() -> tuple[str, str]:
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_FROM_ADDRESS', '')
    name, email = parseaddr(sender)
    if not email:
        email = sender.strip()
    return name or 'KidZora', email


def send_html_email(to_email: str, subject: str, html: str) -> bool:
    """Send HTML email through a configured HTTP API provider, otherwise SMTP."""
    if _uses_brevo_api():
        return _send_brevo_api(to_email, subject, html)
    if _uses_resend_api():
        return _send_resend_api(to_email, subject, html)
    return _send_smtp(to_email, subject, html)


def _send_brevo_api(to_email: str, subject: str, html: str) -> bool:
    api_key = _brevo_api_key()
    sender_name, sender_email = _sender_parts()
    timeout = float(current_app.config.get('MAIL_TIMEOUT_SECONDS', 5))

    if not api_key:
        print('[email] Brevo API key is missing. Set BREVO_API_KEY or MAIL_PASSWORD.')
        return False
    if not sender_email:
        print('[email] Sender is missing. Set MAIL_DEFAULT_SENDER or MAIL_FROM_ADDRESS.')
        return False

    try:
        response = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={
                'sender': {'name': sender_name, 'email': sender_email},
                'to': [{'email': to_email}],
                'subject': subject,
                'htmlContent': html,
            },
            timeout=timeout,
        )
        if 200 <= response.status_code < 300:
            print(f'Email sent via Brevo API to {to_email}')
            return True
        print(f'[email] Brevo API error {response.status_code}: {response.text}')
        return False
    except Exception as e:
        print(f'[email] Brevo API connection error: {e}')
        return False


def _send_resend_api(to_email: str, subject: str, html: str) -> bool:
    api_key = _resend_api_key()
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_FROM_ADDRESS')
    timeout = float(current_app.config.get('MAIL_TIMEOUT_SECONDS', 5))

    if not api_key:
        print('[email] Resend API key is missing. Set RESEND_API_KEY or MAIL_PASSWORD.')
        return False
    if not sender:
        print('[email] Sender is missing. Set MAIL_DEFAULT_SENDER.')
        return False

    try:
        response = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'from': sender,
                'to': [to_email],
                'subject': subject,
                'html': html,
            },
            timeout=timeout,
        )
        if 200 <= response.status_code < 300:
            print(f'Email sent via Resend API to {to_email}')
            return True
        print(f'[email] Resend API error {response.status_code}: {response.text}')
        return False
    except Exception as e:
        print(f'[email] Resend API connection error: {e}')
        return False


def _send_smtp(to_email: str, subject: str, html: str) -> bool:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(current_app.config.get('MAIL_PORT', 465))
        username = current_app.config.get('MAIL_USERNAME', '')
        password = current_app.config.get('MAIL_PASSWORD', '')
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', username)
        use_ssl = current_app.config.get('MAIL_USE_SSL', True)
        use_tls = current_app.config.get('MAIL_USE_TLS', False)
        timeout = float(current_app.config.get('MAIL_TIMEOUT_SECONDS', 5))

        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))

        context = ssl.create_default_context()
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=timeout)
            if use_tls:
                server.starttls(context=context)

        server.login(username, password)
        server.sendmail(username, to_email, msg.as_string())
        server.quit()
        print(f'Email sent via {smtp_server} to {to_email}')
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f'[email] SMTP Auth Error: {e}')
        return False
    except (TimeoutError, OSError) as e:
        print(f'[email] SMTP Connection Error: {e}')
        return False
    except Exception as e:
        print(f'[email] SMTP send error: {e}')
        return False
