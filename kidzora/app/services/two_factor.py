"""Authenticator-app TOTP helpers for KidZora account security."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import struct
import time
from urllib.parse import quote

from flask import current_app


def new_totp_secret() -> str:
    """Return a 160-bit base32 TOTP secret without padding."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def provisioning_uri(email: str, secret: str) -> str:
    label = quote(f"KidZora:{email}", safe="")
    issuer = quote("KidZora", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&digits=6&period=30"


def qr_data_uri(payload: str) -> str | None:
    """Render a QR image when qrcode is installed; manual setup still works."""
    try:
        import qrcode
    except ImportError:
        return None

    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_secret(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("ascii")
    except (ValueError, _invalid_token_error()):
        return None


def verify_totp(secret: str | None, code: str, window: int = 1) -> bool:
    clean_code = "".join(ch for ch in (code or "") if ch.isdigit())
    if not secret or len(clean_code) != 6:
        return False

    now = int(time.time())
    for drift in range(-window, window + 1):
        try:
            if hmac.compare_digest(_totp_at(secret, now + (drift * 30)), clean_code):
                return True
        except (ValueError, TypeError):
            return False
    return False


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as e:
        raise RuntimeError(
            "Authenticator 2FA requires the cryptography package. "
            "Install the updated requirements.txt dependencies."
        ) from e

    material = current_app.config.get("TOTP_ENCRYPTION_KEY") or current_app.secret_key
    digest = hashlib.sha256(str(material).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _invalid_token_error():
    try:
        from cryptography.fernet import InvalidToken
    except ImportError:
        return RuntimeError
    return InvalidToken


def _totp_at(secret: str, unix_time: int) -> str:
    padded = secret.upper() + ("=" * ((8 - len(secret) % 8) % 8))
    key = base64.b32decode(padded, casefold=True)
    counter = struct.pack(">Q", unix_time // 30)
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1000000:06d}"
