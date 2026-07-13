"""
routes/auth.py
---------------
This file defines the AUTHENTICATION Blueprint - all routes related to
logging in and out live here.

WHAT IS A BLUEPRINT?
-----------------------
A Blueprint is Flask's way of grouping related routes into their own
file/module instead of piling every @app.route into one giant app.py.
Think of it like a "mini Flask app" for one feature area. We define the
routes here with @auth_bp.route(...), and then in app.py we do:

    app.register_blueprint(auth_bp)

...which "plugs" all of these routes into the main app. As the project
grows (trainees, reports, settings...), each feature area gets its own
Blueprint file inside routes/ - this keeps the codebase organized the
way a real company's Flask project would be.

WHY IS THE LoginForm CLASS DEFINED HERE (not a separate forms.py)?
----------------------------------------------------------------------
This project only has ONE form so far. Keeping a form next to the route
that uses it is perfectly fine and avoids unnecessary extra files. If
this project grows many forms (Add Trainee, Edit Trainee, Settings...),
we can introduce a dedicated forms/ package later without breaking
anything - that's a refactor, not a redesign.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

from models.user import User

# The first argument "auth" becomes this blueprint's NAME, used when we
# build URLs with url_for("auth.login"), url_for("auth.logout"), etc.
# __name__ tells Flask which module this blueprint belongs to, so it can
# correctly locate any templates/static files if we ever scope them to
# this blueprint specifically.
auth_bp = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    """
    Defines the fields + validation rules for the login form using
    Flask-WTF.

    WHY USE FLASK-WTF INSTEAD OF READING request.form DIRECTLY?
    ---------------------------------------------------------------
    1. CSRF PROTECTION: FlaskForm automatically embeds a hidden,
       secret, single-use token in the rendered form (via
       {{ form.hidden_tag() }} in login.html). On submit, Flask-WTF
       checks that token matches what it issued. This defeats
       Cross-Site Request Forgery attacks, where a malicious website
       tries to trick your browser into submitting a form to our app
       without you meaning to.
    2. VALIDATION IN ONE PLACE: DataRequired() automatically produces a
       clean error message ("Username is required.") without us
       writing manual `if not request.form.get("username")` checks.
    3. REUSABILITY: the exact same LoginForm object is used to both
       RENDER the form (GET request) and VALIDATE the submission
       (POST request) - one class, two jobs, no duplicated field
       definitions.
    """

    username = StringField(
        "Username",
        validators=[DataRequired(message="Username is required.")]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")]
    )
    # BooleanField renders as a checkbox. Its value (form.remember.data)
    # will be True/False depending on whether the user ticked it.
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles both showing the login form (GET) and processing a login
    attempt (POST) - this is a common Flask pattern that avoids needing
    two separate routes for the same page.

    FLOW:
    1. If the admin is ALREADY logged in and somehow lands on /login
       again, there's no reason to show them the form - send them
       straight to the dashboard.
    2. form.validate_on_submit() does TWO things in one call:
         - checks this is a POST request
         - runs all the field validators (DataRequired, CSRF check)
       It returns True only if this was a POST AND everything passed.
    3. We look up the username in the database. If found, we check the
       submitted password against the stored hash using
       user.check_password() (defined in models/user.py).
    4. If both the username exists AND the password matches, we call
       Flask-Login's login_user() - this is the function that actually
       creates the secure session that keeps the admin "logged in"
       across page loads.
    5. If either check fails, we show ONE generic error message
       ("Invalid username or password") rather than saying which part
       was wrong. This is a deliberate security choice: if we said
       "username not found" vs "wrong password" separately, an
       attacker could use that to figure out which usernames exist in
       our system.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_home"))

    form = LoginForm()

    if form.validate_on_submit():
        # .strip() removes accidental leading/trailing spaces a user
        # might type or paste into the username field.
        submitted_username = form.username.data.strip()
        user = User.query.filter_by(username=submitted_username).first()

        if user is not None and user.check_password(form.password.data):
            # login_user() is provided by Flask-Login. It stores the
            # user's id in the secure, signed session cookie, so that
            # on every future request Flask-Login knows who's logged
            # in (see the user_loader callback in app.py).
            #
            # remember=form.remember.data: if the "Remember Me" checkbox
            # was ticked, Flask-Login sets a longer-lived cookie so the
            # admin stays logged in even after closing the browser.
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.username}!", "success")

            # "next" support: if the admin was redirected here because
            # they tried to visit a protected page (e.g. /dashboard)
            # while logged out, Flask-Login stores that original
            # destination in ?next=... We send them there after a
            # successful login instead of always going to the
            # dashboard - a small but important UX detail.
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.dashboard_home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """
    Logs the current admin out.

    @login_required ensures only someone who IS currently logged in can
    even reach this route - there's no meaningful "logout" action for
    someone who isn't logged in.

    logout_user() (from Flask-Login) clears the user's id out of the
    session, which is how the "session is destroyed" - the signed
    cookie in the browser becomes meaningless because the server no
    longer recognizes any identity tied to it.
    """
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
