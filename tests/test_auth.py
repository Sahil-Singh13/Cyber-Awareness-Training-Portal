"""
tests/test_auth.py
--------------------
Covers: login (success/failure), logout, @login_required protection,
and the Version 1.0 login-throttling behavior.
"""

from utils.security import _failed_attempts


def _reset_throttle():
    """Login throttling (utils/security.py) uses a module-level dict
    that persists across test functions in the same process - clear it
    before/after throttle tests so one test's failed attempts can't
    leak into another test's expectations."""
    _failed_attempts.clear()


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Admin Login" in response.data


def test_login_with_correct_credentials_succeeds(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_login_with_wrong_password_fails(client):
    _reset_throttle()
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_login_with_unknown_username_fails(client):
    _reset_throttle()
    response = client.post(
        "/login",
        data={"username": "nobody", "password": "whatever"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_dashboard_requires_login(client):
    """An anonymous request to a protected route must be redirected to /login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_clears_session(client):
    client.post("/login", data={"username": "admin", "password": "admin123"})
    client.get("/logout")
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_default_password_reminder_shown(client):
    """Logging in with the still-default admin123 password should
    surface the Version 1.0 reminder to change it."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert b"default password" in response.data.lower()


def test_login_throttling_locks_out_after_repeated_failures(client):
    """After MAX_FAILED_ATTEMPTS wrong passwords for the same username,
    even a CORRECT password should be rejected until the lockout window
    passes."""
    _reset_throttle()
    for _ in range(5):
        client.post("/login", data={"username": "admin", "password": "wrong"})

    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert b"Too many failed login attempts" in response.data
    _reset_throttle()
