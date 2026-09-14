"""
Failed-login throttling and account lockout.

The audit found no rate limiting on sign-in. The DRF throttle was in fact wired
to the API login, but two things defanged it: development settings raise the
`auth` scope from 5/min to 50/min (and the live server was running development
settings), and LocMemCache is per-process, so with several gunicorn workers each
worker counted separately.

Rate limiting alone also only slows a spray. This adds a lockout keyed on the
account, so guessing one password does not simply move to another IP.
"""
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Failures tolerated before the account is locked, and for how long.
MAX_FAILURES_PER_ACCOUNT = 5
ACCOUNT_LOCKOUT_SECONDS = 15 * 60

# A single IP may be trying many accounts.
MAX_FAILURES_PER_IP = 20
IP_LOCKOUT_SECONDS = 15 * 60


def client_ip(request):
    """
    The caller's address, trusting X-Forwarded-For only as far as nginx sets it.

    Takes the first hop, which is what the proxy prepends; anything further left
    is client-supplied and forgeable.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _account_key(identifier):
    return f'login-fail:account:{(identifier or "").strip().lower()}'


def _ip_key(ip):
    return f'login-fail:ip:{ip}'


def is_locked_out(identifier, ip):
    """True when this account or address has failed too often recently."""
    if cache.get(_account_key(identifier), 0) >= MAX_FAILURES_PER_ACCOUNT:
        return True
    return cache.get(_ip_key(ip), 0) >= MAX_FAILURES_PER_IP


def register_failure(identifier, ip):
    """Counts a failed attempt. Returns True once that trips a lockout."""
    for key, limit, ttl in (
        (_account_key(identifier), MAX_FAILURES_PER_ACCOUNT, ACCOUNT_LOCKOUT_SECONDS),
        (_ip_key(ip), MAX_FAILURES_PER_IP, IP_LOCKOUT_SECONDS),
    ):
        # add() only sets when absent, so the window starts at the first failure
        # and does not slide forward with every later one.
        cache.add(key, 0, ttl)
        try:
            count = cache.incr(key)
        except ValueError:
            # Expired between the add and the incr.
            cache.set(key, 1, ttl)
            count = 1

        if count >= limit:
            logger.warning(
                'Login lockout triggered (%s), identifier=%s ip=%s',
                key.split(':')[1], identifier, ip,
            )
            return True
    return False


def reset(identifier, ip):
    """Clears the counters after a successful sign-in."""
    cache.delete(_account_key(identifier))
    cache.delete(_ip_key(ip))
