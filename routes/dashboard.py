"""
routes/dashboard.py
--------------------
MILESTONE 4: this file builds the REAL admin dashboard. All numbers you
see on the dashboard (total trained, certificates uploaded, male/female
counts, daily training counts, recent activity) are computed live from
the `trainee` table using SQLAlchemy queries - none of it is
hardcoded. Every query is written to degrade gracefully to zero / empty
results instead of crashing on an empty database.

MILESTONE 6 UPDATE (Section 4 - Analytics): added monthly training
counts and location-wise training counts, and switched from the fixed
Config.TRAINING_GOAL to get_effective_training_goal() (see
routes/settings.py) so the dashboard immediately reflects a goal the
admin has changed via Settings - no restart needed.

Authentication is completely untouched - @login_required still guards
this route exactly as it did in Milestone 3.
"""

from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db
from models.trainee import Trainee
from routes.settings import get_effective_training_goal

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_home():
    """
    The protected admin dashboard.

    Every value passed into the template is computed here, in Python,
    from the database - the template itself contains zero business
    logic and zero hardcoded numbers. This separation (routes decide
    WHAT the data is, templates decide HOW it looks) is standard Flask
    architecture and makes both sides easier to change independently.
    """

    # ------------------------------------------------------------------
    # STAT CARDS
    # ------------------------------------------------------------------
    # .count() runs a SQL "SELECT COUNT(*)" - fast, and works correctly
    # even when the table has zero rows (it simply returns 0, it never
    # raises an error). This is what makes "show 0 instead of crashing"
    # automatic - we don't need any special-case "if empty" branching
    # for these numbers at all.
    total_trained = Trainee.query.count()

    # isnot(None) means "this column IS filled in" - i.e. a filename was
    # actually saved for that trainee's certificate/photo. Trainees
    # added later without an uploaded file yet won't be counted here.
    certificates_uploaded = Trainee.query.filter(
        Trainee.certificate_filename.isnot(None)
    ).count()
    photos_uploaded = Trainee.query.filter(
        Trainee.photo_filename.isnot(None)
    ).count()

    # MILESTONE 6: reads the admin-configurable goal from Settings
    # (falls back to Config.TRAINING_GOAL if never changed) instead of
    # always using the fixed Config value.
    training_goal = get_effective_training_goal()
    pending_to_reach_goal = max(training_goal - total_trained, 0)

    # We cap the PROGRESS BAR at 100% (you can't visually fill a bar
    # past full, even if the admin trains more than 30 people), but we
    # still display the true raw count ("32 / 30 Completed") as text
    # underneath so no real information is hidden.
    raw_progress_percent = (total_trained / training_goal) * 100 if training_goal else 0
    progress_percent = min(round(raw_progress_percent), 100)

    # ------------------------------------------------------------------
    # RECENT ACTIVITY
    # ------------------------------------------------------------------
    # The 5 most recently added trainees, newest first. If the table is
    # empty, this is simply an empty list - the template checks
    # `{% if recent_trainees %}` and shows a friendly empty state
    # instead of an empty table.
    recent_trainees = (
        Trainee.query.order_by(Trainee.created_at.desc()).limit(5).all()
    )

    # ------------------------------------------------------------------
    # CHART DATA
    # ------------------------------------------------------------------
    # Male vs Female (vs Other) - one query, grouped by gender.
    # func.count(Trainee.id) is SQL's COUNT() aggregate function, and
    # .group_by(Trainee.gender) buckets rows by their gender value
    # before counting each bucket - equivalent to:
    #   SELECT gender, COUNT(id) FROM trainee GROUP BY gender;
    gender_rows = (
        db.session.query(Trainee.gender, func.count(Trainee.id))
        .group_by(Trainee.gender)
        .all()
    )
    # Convert the raw [(gender, count), ...] rows into a dict so the
    # template/JS can safely look up "Male", "Female", "Other" even if
    # one of those genders has zero trainees (and therefore never
    # appeared in gender_rows at all).
    gender_counts = {"Male": 0, "Female": 0, "Other": 0}
    for gender_value, count in gender_rows:
        gender_counts[gender_value] = count

    # Daily training count - how many trainees were trained on each
    # distinct training_date, ordered chronologically. This powers the
    # "People Trained Per Day" line/bar chart.
    daily_rows = (
        db.session.query(Trainee.training_date, func.count(Trainee.id))
        .group_by(Trainee.training_date)
        .order_by(Trainee.training_date)
        .all()
    )
    # training_date is stored as a Python `date` object - we convert it
    # to a plain string here (in the route) rather than in the
    # template, because Jinja's |tojson filter cannot serialize date
    # objects directly into JavaScript-readable JSON.
    daily_labels = [d.strftime("%d %b") for d, _ in daily_rows]
    daily_counts_list = [count for _, count in daily_rows]

    # MILESTONE 6, Section 4: "Training per Month". strftime('%Y-%m',
    # training_date) groups every trainee into their training month
    # ("2026-07") directly inside the SQL query itself (func.strftime
    # is SQLite's own date-formatting function, exposed to SQLAlchemy)
    # - much faster than pulling every row into Python and grouping
    # there by hand.
    monthly_rows = (
        db.session.query(
            func.strftime("%Y-%m", Trainee.training_date).label("month"),
            func.count(Trainee.id)
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_labels = [m for m, _ in monthly_rows]
    monthly_counts_list = [c for _, c in monthly_rows]

    # MILESTONE 6, Section 4: "Location-wise Training" - how many
    # trainees were trained at each distinct location, busiest first
    # (useful for spotting which venue/location is used most).
    location_rows = (
        db.session.query(Trainee.training_location, func.count(Trainee.id))
        .group_by(Trainee.training_location)
        .order_by(func.count(Trainee.id).desc())
        .limit(8)
        .all()
    )
    location_labels = [loc for loc, _ in location_rows]
    location_counts_list = [c for _, c in location_rows]

    # "People Trained Progress" chart re-uses total_trained/training_goal
    # (completed vs remaining) as a simple 2-slice donut.
    completed_vs_pending = {
        "completed": total_trained,
        "pending": pending_to_reach_goal,
    }

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        current_date=date.today().strftime("%A, %d %B %Y"),
        total_trained=total_trained,
        certificates_uploaded=certificates_uploaded,
        photos_uploaded=photos_uploaded,
        pending_to_reach_goal=pending_to_reach_goal,
        training_goal=training_goal,
        progress_percent=progress_percent,
        recent_trainees=recent_trainees,
        gender_counts=gender_counts,
        daily_labels=daily_labels,
        daily_counts_list=daily_counts_list,
        monthly_labels=monthly_labels,
        monthly_counts_list=monthly_counts_list,
        location_labels=location_labels,
        location_counts_list=location_counts_list,
        completed_vs_pending=completed_vs_pending,
    )

