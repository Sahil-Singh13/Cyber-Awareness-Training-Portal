"""
config.py
---------
Centralized configuration for the Flask application.
"""

import os

# Absolute path of the project folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Main configuration class.
    """

    # ✅ IMPORTANT FIX
    BASE_DIR = BASE_DIR

    # ------------------------------------------------------------------
    # SECURITY
    # ------------------------------------------------------------------
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-this-in-production"
    )

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "database", "training.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------------------
    # FILE UPLOADS
    # ------------------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    CERTIFICATE_FOLDER = os.path.join(UPLOAD_FOLDER, "certificates")
    PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, "photos")

    ALLOWED_CERTIFICATE_EXTENSIONS = {"pdf"}
    ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # ------------------------------------------------------------------
    # BUSINESS RULE
    # ------------------------------------------------------------------
    TRAINING_GOAL = 30