"""
config.py
---------
This file holds ALL the settings for our Flask application in one place.

WHY DO WE NEED THIS FILE?
--------------------------
Instead of scattering settings like "database location" or "max upload size"
across many files, we keep them here. This is a very common real-world
pattern called "centralized configuration".

Benefits:
1. If we need to change something later (e.g. move to a different database,
   or allow bigger file uploads), we only change it in ONE place.
2. It keeps secrets (like SECRET_KEY) separate from application logic.
3. It makes the app "environment aware" - later you could have a
   DevelopmentConfig and a ProductionConfig if you wanted to deploy this.
"""

import os

# ------------------------------------------------------------------
# VERSION 1.0: .env SUPPORT
# ------------------------------------------------------------------
# python-dotenv (already listed in requirements.txt from Milestone 1,
# but unused until now) loads any KEY=VALUE pairs from a ".env" file in
# the project root into the process's environment variables, BEFORE we
# read any of them below with os.environ.get(...). This means a real
# deployment can set SECRET_KEY, DATABASE_URL, APP_ENV, etc. in a
# simple .env file instead of editing this source file directly - see
# .env.example for every variable this app understands.
#
# load_dotenv() is intentionally a no-op (does nothing, raises nothing)
# if no .env file exists - which is exactly what happens the first time
# someone clones this project before creating their own .env, or in a
# real production host where secrets are injected as real environment
# variables instead of a file. Either way this call is always safe.
from dotenv import load_dotenv
load_dotenv()

# BASE_DIR = the absolute path to the folder this config.py file lives in.
# We use this so that file paths work correctly NO MATTER where you run
# the app from (your laptop, your friend's laptop, a server, etc.)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    The main configuration class.
    Flask will read these UPPERCASE variables automatically when we do
    app.config.from_object(Config) in app.py
    """

    # ------------------------------------------------------------------
    # BASE_DIR (also exposed as a CLASS ATTRIBUTE)
    # ------------------------------------------------------------------
    # BUGFIX (caught during Milestone 6's consistency review): BASE_DIR
    # was previously only a MODULE-level variable (defined above, outside
    # this class). Code inside this class body could still reference it
    # directly (e.g. UPLOAD_FOLDER below), because Python class bodies
    # can read module-level globals directly. But `Config.BASE_DIR`
    # accessed from OUTSIDE this file (as app.py does:
    # `os.path.join(Config.BASE_DIR, "database")`) does NOT work that
    # way - attribute access on a class only sees names actually assigned
    # INSIDE the class body. Since BASE_DIR was never assigned there,
    # `Config.BASE_DIR` raised AttributeError. This line fixes that by
    # explicitly copying the module-level value into a real class
    # attribute, with zero change to the actual path it resolves to.
    BASE_DIR = BASE_DIR

    # ------------------------------------------------------------------
    # SECURITY
    # ------------------------------------------------------------------
    # SECRET_KEY is used by Flask to:
    #   - sign session cookies (so users can't fake being logged in)
    #   - protect forms against CSRF attacks (via Flask-WTF)
    #
    # In a real production app, this should NEVER be hardcoded like this.
    # It should come from an environment variable. We fall back to a
    # default value ONLY so the app runs immediately for learning purposes.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this-in-production")

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    # We are using SQLite - a lightweight, file-based database.
    # This means our entire database is just ONE FILE
    # (database/training.db) - perfect for a college project because
    # there's no separate database server to install/configure.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "database", "training.db")
    )

    # This turns OFF a Flask-SQLAlchemy feature that tracks every change
    # to objects for signaling purposes. We don't need it, and it uses
    # extra memory, so best practice is to disable it.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------------------
    # FILE UPLOADS
    # ------------------------------------------------------------------
    # Absolute path to the "uploads" folder where certificates are
    # physically saved on disk.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    CERTIFICATE_FOLDER = os.path.join(UPLOAD_FOLDER, "certificates")
    GALLERY_FOLDER = os.path.join(UPLOAD_FOLDER, "gallery")

    # Which file extensions are we allowed to accept?
    # We store these as Python sets because checking "is this extension
    # inside this set?" is very fast (O(1)) compared to a list.
    ALLOWED_CERTIFICATE_EXTENSIONS = {"pdf"}
    ALLOWED_GALLERY_EXTENSIONS = {"jpg", "jpeg", "png"}

    # Maximum size of any single uploaded file = 5 MB.
    # 5 * 1024 * 1024 converts "5 megabytes" into bytes, because Flask
    # expects this setting in bytes.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # ------------------------------------------------------------------
    # BUSINESS RULE
    # ------------------------------------------------------------------
    # The assignment requires training 30 people. We store that goal
    # here so the Dashboard progress bar can calculate percentage
    # automatically: (trained / TRAINING_GOAL) * 100
    TRAINING_GOAL = 30

    # ------------------------------------------------------------------
    # LOGGING (VERSION 1.0)
    # ------------------------------------------------------------------
    # Where rotating log files are written (see app.py's logging setup).
    # A plain string, not a Config-time constant computed with logging
    # itself, so it stays easy to read/override from the environment.
    LOG_FOLDER = os.path.join(BASE_DIR, "logs")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    """
    Used when APP_ENV=development (also the default if APP_ENV is
    unset - see get_config() below). Optimized for a comfortable local
    coding experience: verbose errors, auto-reload, relaxed cookie
    security (so it still works over plain http://localhost).
    """
    DEBUG = True
    SQLALCHEMY_ECHO = False  # flip to True if you ever need to see raw SQL
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """
    Used by the automated test suite (tests/conftest.py sets
    APP_ENV=testing before creating the app). Key differences from
    development:
      - an IN-MEMORY SQLite database (no file ever touches disk, and
        every test run starts completely empty)
      - CSRF protection disabled, since tests post form data directly
        without first fetching+parsing a CSRF token out of HTML
      - a fixed, fast-hashing-friendly SECRET_KEY so test runs are
        deterministic
    """
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "testing-secret-key"


class ProductionConfig(Config):
    """
    Used when APP_ENV=production. Tightens security settings that are
    fine to relax for local development but should NEVER be relaxed on
    a real deployment:
      - DEBUG is always False (a debug-mode Flask app in production is
        a serious security hole - it can expose an interactive Python
        console to anyone who triggers an unhandled error)
      - session cookies are marked Secure (only ever sent over https)
        and use SameSite=Lax as a baseline CSRF defense on top of
        Flask-WTF's own token-based protection
      - SECRET_KEY has NO hardcoded fallback here - see the check in
        app.py's create_app(), which refuses to start in production
        without a real SECRET_KEY set via the environment/.env file
    """
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"


# ------------------------------------------------------------------
# CONFIG SELECTION
# ------------------------------------------------------------------
# A small string -> class lookup table, keyed by the APP_ENV
# environment variable. app.py calls get_config() once at startup
# instead of hardcoding `app.config.from_object(Config)` - this is
# what actually makes "python app.py" behave differently in
# development vs. production vs. under pytest, controlled entirely by
# one environment variable (see .env.example).
CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    """
    Returns the Config CLASS (not an instance - Flask's
    app.config.from_object() wants the class itself) matching
    APP_ENV. Defaults to DevelopmentConfig if APP_ENV is unset or
    unrecognized, so the app still runs out of the box with zero
    environment setup - exactly like it always has.
    """
    env_name = os.environ.get("APP_ENV", "development").strip().lower()
    return CONFIG_BY_NAME.get(env_name, DevelopmentConfig)
