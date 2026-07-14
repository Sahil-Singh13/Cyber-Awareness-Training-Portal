"""
routes/trainees.py
-------------------
MILESTONE 5: full CRUD (Create, Read, Update, Delete) for trainee
records, plus search/sort/pagination on the list page and protected
file serving for certificates.

IMPORTANT SCHEMA NOTE (please read):
--------------------------------------
The assignment brief for this milestone asks for Aadhaar Number to be
OPTIONAL on the form. However, Milestone 2 defined
`aadhaar_number = db.Column(db.String(12), nullable=False)` with a
CHECK constraint enforcing exactly 12 digits, and the project rules say
not to modify existing database fields in this milestone. Making the
form optional while the database still demands a value would mean
every submission with a blank Aadhaar field crashes with an
IntegrityError - a real bug, not just a style choice. So Aadhaar stays
REQUIRED here, matching what the database actually enforces. If you
want it to be genuinely optional, that needs a small Milestone 2
schema change (`nullable=True`) done as its own explicit step - just
say the word.
"""

import os

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    send_from_directory, abort
)
from flask_login import login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import (
    StringField, IntegerField, SelectField, DateField,
    SubmitField
)
from wtforms.validators import DataRequired, NumberRange, Regexp, Length, Optional, ValidationError
from sqlalchemy import or_

from config import Config
from models import db
from models.trainee import Trainee
from models.activity_log import ActivityLog
from utils.file_helpers import save_uploaded_file, delete_file_if_exists

trainees_bp = Blueprint("trainees", __name__, url_prefix="/trainees")


# ==========================================================================
# FORM
# ==========================================================================
class TraineeForm(FlaskForm):
    """
    One form class, reused for BOTH Add and Edit. The only difference
    between the two is that Edit sets `form.trainee_id` before
    validation runs (see the uniqueness validators below), and Edit's
    file fields are optional even though a certificate may
    already exist (Edit only replaces a file if a NEW one was chosen).
    """

    full_name = StringField(
        "Full Name",
        validators=[DataRequired(message="Full name is required."), Length(max=100)]
    )

    gender = SelectField(
        "Gender",
        choices=[("", "Select gender"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired(message="Please select a gender.")]
    )

    # NumberRange(5, 100) is a STRICTER form-level rule than the
    # database's CheckConstraint (1-120, set in Milestone 2). Both are
    # allowed to coexist - the form simply rejects a narrower range
    # before the request ever reaches the database.
    age = IntegerField(
        "Age",
        validators=[
            DataRequired(message="Age is required."),
            NumberRange(min=5, max=100, message="Age must be between 5 and 100.")
        ]
    )

    mobile_number = StringField(
        "Mobile Number",
        validators=[
            DataRequired(message="Mobile number is required."),
            Regexp(r"^\d{10}$", message="Mobile number must be exactly 10 digits.")
        ]
    )

    # See the module docstring above for why this is required, not
    # optional, despite the milestone brief's wording.
    aadhaar_number = StringField(
        "Aadhaar Number",
        validators=[
            DataRequired(message="Aadhaar number is required."),
            Regexp(r"^\d{12}$", message="Aadhaar number must be exactly 12 digits.")
        ]
    )

    reference_id = StringField(
        "Reference ID",
        validators=[DataRequired(message="Reference ID is required."), Length(max=50)]
    )

    training_date = DateField(
        "Training Date",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Training date is required.")]
    )

    # FileAllowed checks the file EXTENSION. FileSize checks the
    # browser-reported size before we ever touch disk - a fast first
    # line of defense; utils/file_helpers.py re-validates the extension
    # again server-side as a second line of defense (never trust the
    # client alone).
    certificate = FileField(
        "Certificate (PDF)",
        validators=[
            Optional(),
            FileAllowed(["pdf"], message="Only PDF files are allowed for certificates."),
            FileSize(max_size=Config.MAX_CONTENT_LENGTH, message="File is too large (max 5 MB).")
        ]
    )

    submit = SubmitField("Save Trainee")

    # `trainee_id` is None for Add, and set to the trainee's real id by
    # the edit_trainee() route for Edit - see the two uniqueness
    # validators below for why this matters.
    trainee_id = None

    def validate_mobile_number(self, field):
        """
        Custom WTForms validator - method NAME must be
        "validate_<fieldname>" for WTForms to discover and run it
        automatically during form.validate_on_submit().

        We can't just rely on the database's unique=True constraint for
        this, because during EDIT the trainee's OWN existing row
        obviously already "has" this mobile number - we need to exclude
        the row currently being edited from the duplicate check, or
        editing a trainee without changing their mobile number would
        incorrectly report a duplicate against themselves.
        """
        query = Trainee.query.filter_by(mobile_number=field.data)
        if self.trainee_id:
            query = query.filter(Trainee.id != self.trainee_id)
        if query.first() is not None:
            raise ValidationError("This mobile number is already registered with another trainee.")

    def validate_reference_id(self, field):
        """Same reasoning as validate_mobile_number() above, for reference_id."""
        query = Trainee.query.filter_by(reference_id=field.data)
        if self.trainee_id:
            query = query.filter(Trainee.id != self.trainee_id)
        if query.first() is not None:
            raise ValidationError("This Reference ID is already used by another trainee.")


# ==========================================================================
# ADD TRAINEE
# ==========================================================================
@trainees_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_trainee():
    form = TraineeForm()
    # trainee_id stays None (the class default) - there is no existing
    # row to exclude from the uniqueness checks when adding a new one.

    if form.validate_on_submit():
        try:
            # Save files FIRST. If either upload fails validation (e.g.
            # a corrupted extension check), we want to fail BEFORE we've
            # written anything to the database - we never want a
            # database row that points at a file that doesn't exist.
            certificate_filename = save_uploaded_file(
                form.certificate.data, Config.CERTIFICATE_FOLDER, Config.ALLOWED_CERTIFICATE_EXTENSIONS
            )
            trainee = Trainee(
                full_name=form.full_name.data.strip(),
                gender=form.gender.data,
                age=form.age.data,
                mobile_number=form.mobile_number.data.strip(),
                aadhaar_number=form.aadhaar_number.data.strip(),
                reference_id=form.reference_id.data.strip(),
                training_date=form.training_date.data,
                certificate_filename=certificate_filename,
            )
            db.session.add(trainee)
            db.session.commit()

            ActivityLog.log("trainee_added", f"Trainee '{trainee.full_name}' was added.")
            flash(f"Trainee '{trainee.full_name}' added successfully!", "success")
            return redirect(url_for("trainees.view_trainees"))

        except ValueError as e:
            # Raised by save_uploaded_file() for an invalid file type
            # that slipped past FileAllowed (e.g. a renamed file) - we
            # show it as a normal form error instead of a server crash.
            flash(str(e), "danger")
        except Exception:
            # Catch-all safety net: "Never crash" per the assignment.
            # Roll back any partial database change and show a generic
            # friendly message rather than an ugly stack trace page.
            db.session.rollback()
            flash("Something went wrong while saving this trainee. Please try again.", "danger")

    return render_template("trainees/add_edit.html", form=form, mode="add", active_page="add_trainee")


# ==========================================================================
# VIEW TRAINEES (list, search, sort, paginate)
# ==========================================================================
@trainees_bp.route("/", methods=["GET"])
@login_required
def view_trainees():
    search_query = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)

    query = Trainee.query

    # ----------------------------------------------------------------
    # SEARCH
    # ----------------------------------------------------------------
    # or_() lets one search box match ANY of these four columns at
    # once. ilike() is a case-INsensitive "contains" match (SQL LIKE
    # with % wildcards on both sides) - so searching "shar" finds
    # "Rahul Sharma" regardless of capitalization.
    if search_query:
        like_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Trainee.full_name.ilike(like_pattern),
                Trainee.mobile_number.ilike(like_pattern),
                Trainee.reference_id.ilike(like_pattern),
                Trainee.aadhaar_number.ilike(like_pattern),
            )
        )

    # ----------------------------------------------------------------
    # SORTING
    # ----------------------------------------------------------------
    # A whitelist of columns the admin is allowed to sort by - we NEVER
    # build the ORDER BY clause from raw user input directly, which
    # would open a SQL injection / crash risk if someone put a garbage
    # value in the URL like ?sort=DROP_TABLE.
    sortable_columns = {
        "name": Trainee.full_name,
        "age": Trainee.age,
        "training_date": Trainee.training_date,
        "created_at": Trainee.created_at,
    }
    sort_column = sortable_columns.get(sort_by, Trainee.created_at)
    query = query.order_by(sort_column.desc() if order == "desc" else sort_column.asc())

    # ----------------------------------------------------------------
    # PAGINATION
    # ----------------------------------------------------------------
    # Flask-SQLAlchemy's paginate() runs an efficient SQL query that
    # only fetches the 10 rows needed for the current page (not the
    # entire table), and error_out=False means an out-of-range page
    # number (e.g. ?page=999 on a table with 2 rows) returns an EMPTY
    # page gracefully instead of raising a 404.
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "trainees/list.html",
        active_page="view_trainees",
        trainees=pagination.items,
        pagination=pagination,
        search_query=search_query,
        sort_by=sort_by,
        order=order,
    )


# ==========================================================================
# VIEW TRAINEE DETAIL
# ==========================================================================
@trainees_bp.route("/<int:trainee_id>")
@login_required
def view_trainee_detail(trainee_id):
    # get_or_404() is Flask-SQLAlchemy's shortcut for "fetch this row,
    # or automatically show a clean 404 page if no row with this id
    # exists" - e.g. someone manually edits the URL to an id that was
    # already deleted.
    trainee = Trainee.query.get_or_404(trainee_id)
    return render_template("trainees/detail.html", active_page="view_trainees", trainee=trainee)


# ==========================================================================
# EDIT TRAINEE
# ==========================================================================
@trainees_bp.route("/<int:trainee_id>/edit", methods=["GET", "POST"])
@login_required
def edit_trainee(trainee_id):
    trainee = Trainee.query.get_or_404(trainee_id)

    if request.method == "GET":
        # Pre-fill the form with this trainee's EXISTING data so the
        # admin sees their current values rather than a blank form.
        # obj=trainee copies matching attribute names automatically
        # (form.full_name <- trainee.full_name, etc.) - we don't have
        # to assign each field one by one.
        form = TraineeForm(obj=trainee)
    else:
        form = TraineeForm()

    # CRITICAL: set trainee_id BEFORE validate_on_submit() runs, so the
    # uniqueness validators above know to exclude THIS row from their
    # duplicate checks.
    form.trainee_id = trainee.id

    if form.validate_on_submit():
        try:
            # Only replace a file if the admin actually chose a NEW one
            # this time - form.certificate.data is None/empty when they
            # left that field untouched, so save_uploaded_file() simply
            # returns None and we keep the existing filename.
            new_certificate = save_uploaded_file(
                form.certificate.data, Config.CERTIFICATE_FOLDER, Config.ALLOWED_CERTIFICATE_EXTENSIONS
            )
            if new_certificate:
                delete_file_if_exists(Config.CERTIFICATE_FOLDER, trainee.certificate_filename)
                trainee.certificate_filename = new_certificate

            trainee.full_name = form.full_name.data.strip()
            trainee.gender = form.gender.data
            trainee.age = form.age.data
            trainee.mobile_number = form.mobile_number.data.strip()
            trainee.aadhaar_number = form.aadhaar_number.data.strip()
            trainee.reference_id = form.reference_id.data.strip()
            trainee.training_date = form.training_date.data

            db.session.commit()
            ActivityLog.log("trainee_updated", f"Trainee '{trainee.full_name}' was updated.")
            flash(f"Trainee '{trainee.full_name}' updated successfully!", "success")
            return redirect(url_for("trainees.view_trainee_detail", trainee_id=trainee.id))

        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            db.session.rollback()
            flash("Something went wrong while updating this trainee. Please try again.", "danger")

    return render_template(
        "trainees/add_edit.html", form=form, mode="edit", trainee=trainee, active_page="view_trainees"
    )


# ==========================================================================
# DELETE TRAINEE
# ==========================================================================
@trainees_bp.route("/<int:trainee_id>/delete", methods=["POST"])
@login_required
def delete_trainee(trainee_id):
    """
    Deletion only ever happens via POST (never GET) - a GET-triggered
    delete would mean a search engine crawler, browser prefetch, or
    someone simply forwarding a link could accidentally wipe a record.
    The confirmation modal in list.html submits a real POST form.
    """
    trainee = Trainee.query.get_or_404(trainee_id)
    name = trainee.full_name

    try:
        # Clean up the physical files FIRST, then the database row -
        # if file deletion fails for some odd reason (e.g. permissions),
        # we haven't already lost the database record pointing at it.
        delete_file_if_exists(Config.CERTIFICATE_FOLDER, trainee.certificate_filename)

        db.session.delete(trainee)
        db.session.commit()
        ActivityLog.log("trainee_deleted", f"Trainee '{name}' was deleted.")
        flash(f"Trainee '{name}' was deleted successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Something went wrong while deleting this trainee. Please try again.", "danger")

    return redirect(url_for("trainees.view_trainees"))


# ==========================================================================
# PROTECTED FILE SERVING (certificates)
# ==========================================================================
# We deliberately do NOT put uploads/ inside static/. Flask's static
# folder is served to ANYONE with the URL, no login required. Trainee
# certificates contain personal information, so instead we
# serve them through these two @login_required routes - only a logged
# in admin can ever fetch a file, and send_from_directory() safely
# resolves the path (it refuses to serve anything outside the given
# folder, even if `filename` tried to contain "../" tricks).

@trainees_bp.route("/certificates/<path:filename>")
@login_required
def download_certificate(filename):
    if not os.path.exists(os.path.join(Config.CERTIFICATE_FOLDER, filename)):
        abort(404)
    return send_from_directory(Config.CERTIFICATE_FOLDER, filename, as_attachment=True)
