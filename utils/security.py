"""
utils/security.py
------------------
VERSION 1.0: shared security helpers used across the app.

WHAT LIVES HERE
----------------
1. Aadhaar masking - Aadhaar is a sensitive Indian government ID
   number. The database still stores the full 12-digit value (needed
   for uniqueness checks / official records), but the UI should never
   display it in full by default. mask_aadhaar() turns
   "123456789012" into "XXXX XXXX 9012" - only the last 4 digits stay
   visible, matching the common real-world convention (this is the
   same masking style used on Aadhaar's own official "masked Aadhaar"
   downloads). The trainee detail page pairs this with a client-side
   "Reveal" toggle so an admin can still see the full number when they
   genuinely need to, without it being visible by default.

2. Login throttling - a light, dependency-free brute-force guard for
   the login form. We deliberately do NOT add a new database table or
   model for this (that would be a schema change for something that's
   fundamentally short-lived, in-memory data) - instead we keep a
   small in-process counter keyed by username. This resets if the app
   restarts, which is an acceptable trade-off for a single-admin
   college/community project like this one; a high-traffic production
   deployment with multiple worker processes would want a shared store
   (e.g. Redis) instead, which is called out in DEPLOYMENT.md.
"""

import time
import re
from threading import Lock

# ==========================================================================
# AADHAAR MASKING
# ==========================================================================

def mask_aadhaar(aadhaar_number):
    """
    Masks a 12-digit Aadhaar number, showing only the last 4 digits:
        "123456789012" -> "XXXX XXXX 9012"

    Falls back to returning the input unchanged if it doesn't look like
    a 12-digit Aadhaar number (e.g. blank/None) - this function is only
    ever used for DISPLAY, never for validation, so it must never raise
    an exception that could crash a page render.
    """
    if not aadhaar_number:
        return ""
    digits = re.sub(r"\D", "", str(aadhaar_number))
    if len(digits) != 12:
        return str(aadhaar_number)
    return f"XXXX XXXX {digits[-4:]}"


# ==========================================================================
# LOGIN THROTTLING
# ==========================================================================
# Simple in-memory sliding-window counter: {username: [timestamp, ...]}
# Only FAILED attempts are recorded. A lock guards the shared dict since
# Flask's dev server (and some production servers) can handle requests
# on multiple threads at once.

_failed_attempts = {}
_lock = Lock()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60  # 15 minutes


def record_failed_login(username):
    """Records one failed login attempt for `username` right now."""
    key = (username or "").strip().lower()
    if not key:
        return
    with _lock:
        now = time.time()
        attempts = _failed_attempts.setdefault(key, [])
        attempts.append(now)
        # Prune anything outside the window while we're here, so this
        # dict never grows without bound over a long-running process.
        _failed_attempts[key] = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]


def clear_failed_logins(username):
    """Called after a SUCCESSFUL login - resets the counter for that user."""
    key = (username or "").strip().lower()
    with _lock:
        _failed_attempts.pop(key, None)


def is_locked_out(username):
    """
    Returns (locked: bool, seconds_remaining: int).

    A username is locked out once it has MAX_FAILED_ATTEMPTS or more
    failed attempts within the last LOCKOUT_WINDOW_SECONDS. The lockout
    naturally expires on its own (no admin action needed) once the
    oldest attempt in the window ages out.
    """
    key = (username or "").strip().lower()
    if not key:
        return False, 0
    with _lock:
        now = time.time()
        attempts = [t for t in _failed_attempts.get(key, []) if now - t < LOCKOUT_WINDOW_SECONDS]
        _failed_attempts[key] = attempts
        if len(attempts) < MAX_FAILED_ATTEMPTS:
            return False, 0
        oldest_relevant = attempts[-MAX_FAILED_ATTEMPTS]
        seconds_remaining = int(LOCKOUT_WINDOW_SECONDS - (now - oldest_relevant))
        return True, max(seconds_remaining, 1)
