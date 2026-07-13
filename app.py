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
from flask import Flask, redirect, url_for, flash, request
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from werkzeug.exceptions import RequestEntityTooLarge
from config import Config
from models import db
# Importing the model classes here (even though we don't call them
# directly in this file) is REQUIRED. SQLAlchemy only knows to create a
# table for a model if that model's Python file has actually been
# imported/executed at least once. If we skipped these imports,
# db.create_all() below would silently create ZERO tables.
from models.user import User
from models.trainee import Trainee
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.trainees import trainees_bp


def create_app():
    """
    Builds and configures the Flask application.
    Returns a ready-to-run `app` object.
    """

    # __name__ tells Flask "where am I located?" so it can correctly find
    # the templates/ and static/ folders relative to this file.
    app = Flask(__name__)

    # Load all our settings from config.py (SECRET_KEY, DATABASE_URI, etc.)
    app.config.from_object(Config)

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
    # debug=True gives us auto-reload on code changes + detailed error
    # pages while we develop. We will turn this OFF for production later.
    app.run(debug=True)
