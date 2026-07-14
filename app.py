"""
app.py
------
This is the ENTRY POINT of our entire application. When you run:

    python app.py

Python starts executing this file, which builds and starts the Flask app.

WHY "APP FACTORY PATTERN"?
---------------------------
Notice we don't create `app = Flask(__name__)` directly at the top of the
file like beginner tutorials do. Instead, we wrap creation inside a
function called `create_app()`.

This is called the "Application Factory Pattern" and it's how real
companies structure Flask apps. Reasons:

1. TESTING: We can create multiple app instances with different configs
   (e.g. one for testing with a temporary database, one for real use).
2. BLUEPRINTS: It avoids "circular imports" - a common beginner headache
   where routes.py needs `app`, but app.py needs `routes.py`.
3. SCALABILITY: As the app grows with more blueprints (auth, dashboard,
   trainees, reports...), this pattern keeps things organized instead of
   turning app.py into a 1000-line file.

We will register more pieces (more blueprints in later milestones) into
this factory function going forward. As of Milestone 3, authentication
(Flask-Login) is now wired in on top of the Milestone 2 database layer.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, url_for, flash, request, render_template
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import inspect, text
from config import Config, get_config
from models import db
# Importing the model classes here (even though we don't call them
# directly in this file) is REQUIRED. SQLAlchemy only knows to create a
# table for a model if that model's Python file has actually been
# imported/executed at least once. If we skipped these imports,
# db.create_all() below would silently create ZERO tables.
from models.user import User
from models.trainee import Trainee
from models.app_setting import AppSetting
from models.activity_log import ActivityLog
from models.gallery_photo import GalleryPhoto
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.trainees import trainees_bp
from routes.reports import reports_bp
from routes.settings import settings_bp
from routes.gallery import gallery_bp


def remove_obsolete_trainee_columns():
    """Align an existing SQLite trainee table with the current model."""
    inspector = inspect(db.engine)
    if "trainee" not in inspector.get_table_names():
        return
    stored_columns = {column["name"] for column in inspector.get_columns("trainee")}
    model_columns = set(Trainee.__table__.columns.keys())
    for column_name in stored_columns - model_columns:
        if column_name.isidentifier():
            db.session.execute(text(f'ALTER TABLE trainee DROP COLUMN "{column_name}"'))
    db.session.commit()


def create_app():
    """
    Builds and configures the Flask application.
    Returns a ready-to-run `app` object.
    """

    # __name__ tells Flask "where am I located?" so it can correctly find
    # the templates/ and static/ folders relative to this file.
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # CONFIGURATION (VERSION 1.0: environment-aware)
    # ------------------------------------------------------------------
    # get_config() (config.py) picks DevelopmentConfig, TestingConfig,
    # or ProductionConfig based on the APP_ENV environment variable -
    # see config.py and .env.example for the full explanation. This
    # replaces the old hardcoded `app.config.from_object(Config)`.
    active_config = get_config()
    app.config.from_object(active_config)

    # PRODUCTION SAFETY CHECK: refuse to start in production with the
    # placeholder SECRET_KEY. A predictable SECRET_KEY lets an attacker
    # forge session cookies and CSRF tokens - this is exactly the kind
    # of mistake that's easy to make once (forgetting to set a real
    # .env in production) and expensive to have made. Development and
    # testing are unaffected; they're allowed to use the convenience
    # fallback.
    if active_config.__name__ == "ProductionConfig" and app.config["SECRET_KEY"] == "dev-secret-key-change-this-in-production":
        raise RuntimeError(
            "Refusing to start with APP_ENV=production and no real SECRET_KEY set. "
            "Set SECRET_KEY in your environment or .env file before deploying."
        )

    # ------------------------------------------------------------------
    # LOGGING (VERSION 1.0)
    # ------------------------------------------------------------------
    # A rotating file handler keeps the app's log output on disk
    # (logs/app.log), automatically rolling over to a fresh file once
    # it hits 1 MB and keeping up to 5 old files - so logs are useful
    # for debugging a real deployment without ever growing unbounded.
    # In DEBUG mode we skip the extra file handler noise and just rely
    # on Flask's own console/debugger output, which is more convenient
    # while actively developing.
    if not app.debug and not app.testing:
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(Config.LOG_FOLDER, "app.log"), maxBytes=1_000_000, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s in %(module)s: %(message)s"
        ))
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
        app.logger.info("Cyber Awareness Training Portal starting up (APP_ENV=%s).", active_config.__name__)

    # ------------------------------------------------------------------
    # DATABASE SETUP (Milestone 2)
    # ------------------------------------------------------------------
    # Make sure the `database/` folder physically exists BEFORE SQLite
    # tries to create the .db file inside it. SQLite will happily create
    # the FILE for us, but it will NOT create missing FOLDERS - that
    # would raise "unable to open database file".
    os.makedirs(os.path.join(Config.BASE_DIR, "database"), exist_ok=True)

    # db.init_app(app) is the step that binds our shared `db` object
    # (created once in models/__init__.py) to THIS specific Flask app,
    # and reads app.config["SQLALCHEMY_DATABASE_URI"] to know which
    # SQLite file to use.
    db.init_app(app)

    # db.create_all() looks at every model class that inherits db.Model
    # (User, Trainee, ...) and creates a matching table in the database
    # IF that table doesn't already exist yet. It is SAFE to call this
    # every time the app starts - it will never overwrite or delete
    # existing tables or data, it only fills in what's missing.
    #
    # `with app.app_context():` is required because Flask-SQLAlchemy
    # needs to know WHICH app it's working with at the moment we touch
    # the database - outside of a request, we have to open this context
    # manually.
    with app.app_context():
        db.create_all()
        remove_obsolete_trainee_columns()

        # --------------------------------------------------------------
        # DEFAULT ADMIN BOOTSTRAP (Milestone 3)
        # --------------------------------------------------------------
        # See models/user.py -> create_default_admin_if_missing() for
        # the full explanation. Short version: the very first time this
        # runs against a fresh database, it creates username "admin" /
        # password "admin123" (hashed). On every run after that, it
        # finds the admin already exists and does nothing - so it's
        # completely safe to leave this call here permanently.
        User.create_default_admin_if_missing()

    # ------------------------------------------------------------------
    # FLASK-LOGIN SETUP (Milestone 3)
    # ------------------------------------------------------------------
    # LoginManager is the object that actually implements "sessions for
    # logged-in users" on top of Flask's built-in session cookie system.
    login_manager = LoginManager()

    # login_view tells Flask-Login: "if someone who ISN'T logged in
    # tries to visit a @login_required route, send them here instead."
    # We point it at our auth blueprint's login route.
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # init_app() binds this LoginManager to our specific Flask app -
    # same two-step "create then bind" pattern we used for db above.
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        """
        Flask-Login calls this automatically on EVERY request, passing
        in the user id it finds stored in the signed session cookie.
        Our job is simple: look that id up in the database and return
        the matching User object (or None if it doesn't exist, e.g. the
        account was deleted). Flask-Login then makes that object
        available everywhere as `current_user`.

        The id arrives as a STRING (that's how it's stored in the
        cookie), so we convert it to an int before querying, since our
        primary key column is an Integer.
        """
        return User.query.get(int(user_id))

    # ------------------------------------------------------------------
    # CSRF PROTECTION (Milestone 3)
    # ------------------------------------------------------------------
    # CSRFProtect applies Flask-WTF's CSRF checking GLOBALLY to every
    # POST/PUT/PATCH/DELETE request in the app, not just forms we
    # remembered to build with FlaskForm. This is "defense in depth" -
    # even a form we add carelessly later still gets this protection
    # automatically.
    csrf = CSRFProtect()
    csrf.init_app(app)

    # ------------------------------------------------------------------
    # BLUEPRINT REGISTRATION (Milestone 3)
    # ------------------------------------------------------------------
    # This is the step that actually "plugs in" all the routes defined
    # in routes/auth.py (/login, /logout) and routes/dashboard.py
    # (/dashboard) into our running app.
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trainees_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(gallery_bp)

    # ------------------------------------------------------------------
    # GRACEFUL "FILE TOO LARGE" HANDLING (Milestone 5)
    # ------------------------------------------------------------------
    # Config.MAX_CONTENT_LENGTH (5 MB, set in Milestone 1) is enforced
    # by Flask/Werkzeug at the WEB SERVER level, before our form-level
    # FileSize validator even gets a chance to run - if someone uploads
    # something larger, Werkzeug raises RequestEntityTooLarge and Flask
    # would show an ugly generic error page by default. This handler
    # catches that specific case app-wide and turns it into the same
    # friendly flash-message experience as every other validation error
    # in this app, satisfying the "Never crash" / "Large File" handling
    # requirement from the assignment.
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        flash("The file you tried to upload is too large. Maximum allowed size is 5 MB.", "danger")
        return redirect(request.referrer or url_for("dashboard.dashboard_home"))

    # ------------------------------------------------------------------
    # PROFESSIONAL ERROR PAGES (VERSION 1.0)
    # ------------------------------------------------------------------
    # Flask shows an ugly default HTML error page for anything we don't
    # handle ourselves. These two handlers replace the two most common
    # cases - a bad URL (404) and an unexpected server-side crash (500)
    # - with pages that match the rest of the app's look, so an admin
    # never sees a raw stack trace or "Not Found" white page.
    @app.errorhandler(404)
    def handle_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        # Roll back any half-finished database transaction so the NEXT
        # request on this connection starts clean, rather than
        # inheriting whatever broke this one.
        db.session.rollback()
        app.logger.error("Unhandled server error: %s", e)
        return render_template("errors/500.html"), 500

    # ------------------------------------------------------------------
    # ROOT ROUTE
    # ------------------------------------------------------------------
    # The Milestone 1 "setup_check" placeholder page has served its
    # purpose (it proved templates/static files were wired correctly)
    # and is replaced now with real behavior: send logged-in admins to
    # their dashboard, and everyone else to the login page.
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.dashboard_home"))
        return redirect(url_for("auth.login"))

    return app


# This block only runs when you execute `python app.py` directly
# (it does NOT run if this file is imported elsewhere, e.g. by a test file
# or a production server like Gunicorn). This is standard Python practice.
if __name__ == "__main__":
    app = create_app()
    # debug is now driven by APP_ENV (see config.py) instead of being
    # hardcoded True - DevelopmentConfig.DEBUG = True gives us
    # auto-reload + detailed error pages locally, while
    # ProductionConfig.DEBUG = False keeps that off on a real server.
    app.run(debug=app.config.get("DEBUG", False))
