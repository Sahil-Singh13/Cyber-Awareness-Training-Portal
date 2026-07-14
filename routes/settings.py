"""
routes/settings.py
-------------------
MILESTONE 6, Sections 3 & 5: the Settings page - change password,
update the training goal, view system information, and back up /
restore / export the SQLite database.

APP_VERSION is defined here (not in config.py) specifically to avoid
touching config.py again this milestone beyond the one confirmed bug
fix - it's a small display-only constant, not a setting that changes
app behavior, so it doesn't need to live in the central Config class.
"""

import os
import shutil
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    send_file, current_app
)
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import PasswordField, IntegerField, SubmitField
from wtforms.validators import DataRequired, EqualTo, NumberRange, Length

from config import Config
from models import db
from models.trainee import Trainee
from models.user import User
from models.app_setting import AppSetting
from models.activity_log import ActivityLog

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

APP_VERSION = "1.0.0"


# ==========================================================================
# FORMS
# ==========================================================================
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired(message="Current password is required.")])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required."),
            Length(min=6, message="New password must be at least 6 characters.")
        ]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo("new_password", message="Passwords do not match.")
        ]
    )
    change_password_submit = SubmitField("Change Password")


class GoalForm(FlaskForm):
    training_goal = IntegerField(
        "Training Goal",
        validators=[
            DataRequired(message="Training goal is required."),
            NumberRange(min=1, max=100000, message="Training goal must be a positive number.")
        ]
    )
    update_goal_submit = SubmitField("Update Goal")


class RestoreForm(FlaskForm):
    database_file = FileField(
        "Database Backup File (.db)",
        validators=[
            DataRequired(message="Please choose a .db backup file to restore."),
            FileAllowed(["db"], message="Only .db files are allowed."),
        ]
    )
    restore_submit = SubmitField("Restore Database")


def get_effective_training_goal():
    """
    Shared helper (also used by routes/dashboard.py) that returns the
    CURRENT training goal: whatever the admin has set via Settings, or
    Config.TRAINING_GOAL if they've never changed it. This is the
    single source of truth for "what is the goal right now" - every
    other file asks this function instead of reading AppSetting or
    Config directly, so there's exactly one place that decides which of
    the two wins.
    """
    stored_value = AppSetting.get_value("training_goal")
    return int(stored_value) if stored_value is not None else Config.TRAINING_GOAL


# ==========================================================================
# MAIN SETTINGS PAGE
# ==========================================================================
@settings_bp.route("/", methods=["GET"])
@login_required
def settings_home():
    password_form = ChangePasswordForm()
    goal_form = GoalForm()
    goal_form.training_goal.data = get_effective_training_goal()
    restore_form = RestoreForm()

    db_path = current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    db_size_kb = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0

    system_info = {
        "app_version": APP_VERSION,
        "total_trainees": Trainee.query.count(),
        "total_admins": User.query.count(),
        "database_size_kb": db_size_kb,
        "current_admin": current_user.username,
    }

    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(15).all()

    return render_template(
        "settings/index.html", active_page="settings",
        password_form=password_form, goal_form=goal_form, restore_form=restore_form,
        system_info=system_info, recent_activity=recent_activity
    )


# ==========================================================================
# CHANGE PASSWORD
# ==========================================================================
@settings_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Your current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            ActivityLog.log("password_changed", f"Admin '{current_user.username}' changed their password.")
            flash("Password changed successfully.", "success")
            return redirect(url_for("settings.settings_home"))
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")

    return redirect(url_for("settings.settings_home"))


# ==========================================================================
# UPDATE TRAINING GOAL
# ==========================================================================
@settings_bp.route("/update-goal", methods=["POST"])
@login_required
def update_goal():
    form = GoalForm()

    if form.validate_on_submit():
        AppSetting.set_value("training_goal", form.training_goal.data)
        ActivityLog.log("goal_updated", f"Training goal updated to {form.training_goal.data}.")
        flash(f"Training goal updated to {form.training_goal.data}.", "success")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")

    return redirect(url_for("settings.settings_home"))


# ==========================================================================
# DATABASE: BACKUP / EXPORT / RESTORE
# ==========================================================================
@settings_bp.route("/database/backup")
@login_required
def backup_database():
    """
    Copies the live training.db into database/backups/ with a
    timestamped filename (so repeated backups never overwrite each
    other), then sends that SAME file to the browser as a download.
    Keeping a server-side copy AND offering the download means the
    admin has a safety copy even if they don't save the download
    anywhere themselves.
    """
    db_path = current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    if not os.path.exists(db_path):
        flash("No database file was found to back up.", "danger")
        return redirect(url_for("settings.settings_home"))

    backups_folder = os.path.join(Config.BASE_DIR, "database", "backups")
    os.makedirs(backups_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"training_backup_{timestamp}.db"
    backup_path = os.path.join(backups_folder, backup_filename)

    shutil.copy2(db_path, backup_path)
    ActivityLog.log("database_backup", f"Database backed up as '{backup_filename}'.")

    return send_file(backup_path, as_attachment=True, download_name=backup_filename)


@settings_bp.route("/database/export")
@login_required
def export_database():
    """
    "Export" vs "Backup": Backup ALSO saves a timestamped copy on the
    server (a safety net); Export just streams the CURRENT live
    database straight to the browser without keeping an extra server
    copy - a quicker "just give me the file" option.
    """
    db_path = current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    if not os.path.exists(db_path):
        flash("No database file was found to export.", "danger")
        return redirect(url_for("settings.settings_home"))

    ActivityLog.log("database_export", "Database exported.")
    return send_file(db_path, as_attachment=True, download_name="training_export.db")


@settings_bp.route("/database/restore", methods=["POST"])
@login_required
def restore_database():
    """
    Replaces the live database with an uploaded .db file.

    SAFETY MEASURES:
    1. We check the file's first 16 bytes match SQLite's real file
       signature ("SQLite format 3\\x00") before touching anything -
       this catches an accidentally-renamed non-database file before
       it does any damage, rather than after.
    2. We back up the CURRENT database first (with its own timestamp)
       so a bad restore is always recoverable via the backups folder.
    3. We use shutil.copy2 (not move) on the CURRENT db to preserve it,
       then overwrite the live file - if anything raises partway, at
       worst the live file is untouched or the backup already exists.
    """
    form = RestoreForm()

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")
        return redirect(url_for("settings.settings_home"))

    uploaded_file = form.database_file.data
    header = uploaded_file.read(16)
    uploaded_file.seek(0)

    if header != b"SQLite format 3\x00":
        flash("That file doesn't look like a valid SQLite database. Restore cancelled.", "danger")
        return redirect(url_for("settings.settings_home"))

    db_path = current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    backups_folder = os.path.join(Config.BASE_DIR, "database", "backups")
    os.makedirs(backups_folder, exist_ok=True)

    try:
        # Safety backup of what's about to be replaced.
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = os.path.join(backups_folder, f"pre_restore_backup_{timestamp}.db")
            shutil.copy2(db_path, pre_restore_backup)

        # IMPORTANT: close the current SQLAlchemy connection before
        # overwriting the file it points at - otherwise, on some
        # platforms, an open file handle can conflict with replacing
        # the file underneath it.
        db.session.remove()
        db.engine.dispose()

        uploaded_file.save(db_path)

        flash(
            "Database restored successfully. Please log in again to make sure "
            "your session matches the restored data.", "success"
        )
        return redirect(url_for("auth.login"))

    except Exception:
        flash("Something went wrong while restoring the database. No changes were made.", "danger")
        return redirect(url_for("settings.settings_home"))
