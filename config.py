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
    # Absolute path to the "uploads" folder where certificates and
    # photos will physically be saved on disk.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    CERTIFICATE_FOLDER = os.path.join(UPLOAD_FOLDER, "certificates")
    PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, "photos")

    # Which file extensions are we allowed to accept?
    # We store these as Python sets because checking "is this extension
    # inside this set?" is very fast (O(1)) compared to a list.
    ALLOWED_CERTIFICATE_EXTENSIONS = {"pdf"}
    ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}

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
