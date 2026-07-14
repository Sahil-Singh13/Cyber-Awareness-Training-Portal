"""
tests/conftest.py
-------------------
Shared pytest fixtures for the whole test suite. Every test file below
uses the `client` (and sometimes `app`) fixture defined here rather
than building its own Flask app - one consistent, isolated test
environment for every test.

WHY APP_ENV=testing?
---------------------
Setting this BEFORE importing app.py means config.get_config() picks
TestingConfig (see config.py): an in-memory SQLite database (nothing
ever touches disk, and every test function gets a completely fresh,
empty database) and CSRF protection disabled (so tests can POST form
data directly without first parsing a CSRF token out of rendered
HTML).
"""

import os
os.environ["APP_ENV"] = "testing"

import pytest
from app import create_app
from models import db as _db
from models.user import User


@pytest.fixture()
def app():
    """
    Builds one fresh Flask app + in-memory database PER TEST FUNCTION.
    create_app() already calls db.create_all() and seeds the default
    admin account (see app.py / models/user.py) - so every test starts
    with an empty trainee table but a working "admin"/"admin123" login
    already in place, exactly like a real fresh install.
    """
    flask_app = create_app()
    flask_app.config.update(SERVER_NAME="localhost")

    yield flask_app

    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """A Flask test client for making requests without a real server."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """The SQLAlchemy db object, bound to the current test's app context."""
    with app.app_context():
        yield _db


@pytest.fixture()
def logged_in_client(client):
    """
    A test client that has already logged in as the default admin
    (username "admin", password "admin123" - see
    models/user.py::create_default_admin_if_missing). Used by every
    test that needs to reach a @login_required route, so each test
    file doesn't have to repeat the same login POST itself.
    """
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture()
def sample_trainee_data():
    """
    A single, valid set of trainee form fields, reused across CRUD,
    validation, and report tests so they don't each redefine slightly
    different (and potentially inconsistent) sample data.
    """
    return {
        "full_name": "Rahul Sharma",
        "gender": "Male",
        "age": "28",
        "mobile_number": "9876543210",
        "aadhaar_number": "123456789012",
        "reference_id": "REF001",
        "training_date": "2026-07-10",
    }
