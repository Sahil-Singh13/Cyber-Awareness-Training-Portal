"""
routes/reports.py
------------------
MILESTONE 6, Sections 1 & 2: Reports (PDF/Excel/CSV export) and Excel
Import. Both features revolve around the SAME data - the full trainee
table - so they share one blueprint and one page.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, send_file
)
from flask_login import login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SubmitField
from wtforms.validators import DataRequired

from models import db
from models.trainee import Trainee
from models.activity_log import ActivityLog
from utils.reports import (
    build_pdf_report, build_excel_report, build_csv_report, build_sample_import_template
)
from utils.import_trainees import parse_import_file

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


class ImportForm(FlaskForm):
    """A single-field form: choose the .xlsx file to import."""
    excel_file = FileField(
        "Excel File",
        validators=[
            DataRequired(message="Please choose an Excel file to import."),
            FileAllowed(["xlsx", "xls"], message="Only .xlsx or .xls files are allowed."),
        ]
    )
    submit = SubmitField("Import Trainees")


@reports_bp.route("/", methods=["GET"])
@login_required
def reports_home():
    """
    The Reports & Import landing page: three export buttons, the
    sample-template download link, and the import form. total_trainees
    is passed purely so the page can show "(42 records)" next to the
    export buttons - a small but reassuring detail before someone
    downloads a report.
    """
    total_trainees = Trainee.query.count()
    import_form = ImportForm()
    return render_template(
        "reports/index.html", active_page="reports",
        total_trainees=total_trainees, import_form=import_form
    )


# ==========================================================================
# EXPORTS
# ==========================================================================
@reports_bp.route("/export/pdf")
@login_required
def export_pdf():
    trainees = Trainee.query.order_by(Trainee.full_name.asc()).all()
    buffer = build_pdf_report(trainees)
    ActivityLog.log("export_generated", f"PDF report generated ({len(trainees)} records).")
    return send_file(
        buffer, mimetype="application/pdf",
        as_attachment=True, download_name="trainee_report.pdf"
    )


@reports_bp.route("/export/excel")
@login_required
def export_excel():
    trainees = Trainee.query.order_by(Trainee.full_name.asc()).all()
    buffer = build_excel_report(trainees)
    ActivityLog.log("export_generated", f"Excel report generated ({len(trainees)} records).")
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True, download_name="trainee_report.xlsx"
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    trainees = Trainee.query.order_by(Trainee.full_name.asc()).all()
    buffer = build_csv_report(trainees)
    ActivityLog.log("export_generated", f"CSV report generated ({len(trainees)} records).")
    return send_file(
        buffer, mimetype="text/csv",
        as_attachment=True, download_name="trainee_report.csv"
    )


@reports_bp.route("/sample-template")
@login_required
def sample_template():
    buffer = build_sample_import_template()
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True, download_name="trainee_import_template.xlsx"
    )


# ==========================================================================
# IMPORT
# ==========================================================================
@reports_bp.route("/import", methods=["POST"])
@login_required
def import_trainees():
    """
    Handles the Import form submission from reports/index.html. Parses
    and validates the file (utils/import_trainees.py), inserts only the
    VALID rows, and shows a full row-by-row summary - exactly what
    Section 2 of the brief asks for ("Validate every row. Skip invalid
    rows. Show import summary.").
    """
    form = ImportForm()

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")
        return redirect(url_for("reports.reports_home"))

    # Gather what ALREADY exists in the database ONCE, up front - much
    # faster than running a duplicate-check query for every single row
    # in a large spreadsheet.
    existing_mobiles = {m for (m,) in db.session.query(Trainee.mobile_number).all()}
    existing_reference_ids = {r for (r,) in db.session.query(Trainee.reference_id).all()}

    try:
        parsed = parse_import_file(form.excel_file.data, existing_mobiles, existing_reference_ids)
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("reports.reports_home"))

    # Insert every row that passed validation. Each row is ALREADY a
    # clean dict of Trainee constructor kwargs (see
    # utils/import_trainees.py's validate_row()), so this is a direct,
    # simple bulk-insert loop.
    inserted_count = 0
    try:
        for row_data in parsed["valid_rows"]:
            trainee = Trainee(**row_data)
            db.session.add(trainee)
            inserted_count += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Something went wrong while saving the imported trainees. No rows were saved.", "danger")
        return redirect(url_for("reports.reports_home"))

    ActivityLog.log(
        "trainees_imported",
        f"Imported {inserted_count} trainee(s) from Excel ({parsed['skipped']} row(s) skipped)."
    )

    if inserted_count:
        flash(f"Import complete: {inserted_count} trainee(s) added, {parsed['skipped']} row(s) skipped.", "success")
    else:
        flash(f"Import finished, but no rows were valid. {parsed['skipped']} row(s) skipped - see details below.", "warning")

    return render_template(
        "reports/import_results.html", active_page="reports",
        results=parsed["results"], total=parsed["total"],
        imported=inserted_count, skipped=parsed["skipped"]
    )
