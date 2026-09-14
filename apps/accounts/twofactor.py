"""
TOTP two-factor authentication for staff accounts.

The dashboard login page claimed "2FA Enabled" while nothing of the sort was
implemented. This provides it for real, using standard TOTP (RFC 6238) so any
authenticator app works — Google Authenticator, Authy, 1Password.

Scoped to staff: these are the accounts that can reach user records, payment
data and the audio library. Forcing it on every bar mitzvah bochur would be a
support burden for no security gain.
"""
import base64
import hashlib
import hmac
import os

import pyotp
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_secret():
    """A fresh base32 TOTP secret."""
    return pyotp.random_base32()


def provisioning_uri(user, secret):
    """
    The otpauth:// URI an authenticator app scans.

    The issuer is what shows in the app's list, so it should read as the product.
    """
    return pyotp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name='Ezlain Admin',
    )


def verify_code(secret, code):
    """
    Checks a 6-digit code.

    valid_window=1 accepts the adjacent 30-second step either side, which covers
    ordinary clock drift between the phone and the server without meaningfully
    widening the guess space.
    """
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(str(code).strip().replace(' ', ''), valid_window=1)


def generate_recovery_codes(count=8):
    """
    Single-use codes for when the phone is lost.

    Without these, losing a device means a developer editing the database — and
    an admin who fears lockout simply never enables 2FA.
    """
    return [base64.b32encode(os.urandom(5)).decode('ascii').rstrip('=') for _ in range(count)]


def hash_recovery_code(code):
    """
    Recovery codes are stored hashed — they are passwords, not identifiers.

    SHA-256 with the project secret rather than a slow KDF: these are 40 bits of
    genuine randomness, so there is no dictionary to grind.
    """
    normalized = str(code).strip().upper().replace(' ', '').replace('-', '')
    return hmac.new(
        settings.SECRET_KEY.encode(), normalized.encode(), hashlib.sha256
    ).hexdigest()
