"""
tests/test_reports.py
-----------------------
Covers: the three export formats (PDF/Excel/CSV), the sample import
template download, and that Aadhaar numbers come out MASKED in every
generated report (Version 1.0 privacy requirement).
"""

import io
import pandas as pd

from models.trainee import Trainee
from models import db as _db
from utils.reports import build_excel_report, build_csv_report, build_pdf_report


def _add_sample_trainee(app, sample_trainee_data):
    with app.app_context():
        trainee = Trainee(
            full_name=sample_trainee_data["full_name"],
            gender=sample_trainee_data["gender"],
            age=int(sample_trainee_data["age"]),
            mobile_number=sample_trainee_data["mobile_number"],
            aadhaar_number=sample_trainee_data["aadhaar_number"],
            reference_id=sample_trainee_data["reference_id"],
            training_date=__import__("datetime").date(2026, 7, 10),
        )
        _db.session.add(trainee)
        _db.session.commit()


def test_export_pdf_route(logged_in_client, sample_trainee_data, app):
    _add_sample_trainee(app, sample_trainee_data)
    response = logged_in_client.get("/reports/export/pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data[:4] == b"%PDF"


def test_export_excel_route(logged_in_client, sample_trainee_data, app):
    _add_sample_trainee(app, sample_trainee_data)
    response = logged_in_client.get("/reports/export/excel")
    assert response.status_code == 200
    assert "spreadsheet" in response.mimetype


def test_export_csv_route(logged_in_client, sample_trainee_data, app):
    _add_sample_trainee(app, sample_trainee_data)
    response = logged_in_client.get("/reports/export/csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"Rahul Sharma" in response.data


def test_sample_template_download(logged_in_client):
    response = logged_in_client.get("/reports/sample-template")
    assert response.status_code == 200
    assert "spreadsheet" in response.mimetype


def test_reports_require_login(client):
    response = client.get("/reports/export/csv", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_excel_report_masks_aadhaar(app, sample_trainee_data):
    """utils/reports.py must mask Aadhaar numbers in every export -
    the raw 12-digit value should never appear in a downloaded report."""
    with app.app_context():
        trainee = Trainee(
            full_name=sample_trainee_data["full_name"],
            gender=sample_trainee_data["gender"],
            age=int(sample_trainee_data["age"]),
            mobile_number=sample_trainee_data["mobile_number"],
            aadhaar_number=sample_trainee_data["aadhaar_number"],
            reference_id=sample_trainee_data["reference_id"],
            training_date=__import__("datetime").date(2026, 7, 10),
        )
        buffer = build_excel_report([trainee])

    df = pd.read_excel(buffer)
    assert "123456789012" not in df["Aadhaar"].astype(str).tolist()
    assert any("9012" in v for v in df["Aadhaar"].astype(str).tolist())


def test_csv_report_masks_aadhaar(app, sample_trainee_data):
    with app.app_context():
        trainee = Trainee(
            full_name=sample_trainee_data["full_name"],
            gender=sample_trainee_data["gender"],
            age=int(sample_trainee_data["age"]),
            mobile_number=sample_trainee_data["mobile_number"],
            aadhaar_number=sample_trainee_data["aadhaar_number"],
            reference_id=sample_trainee_data["reference_id"],
            training_date=__import__("datetime").date(2026, 7, 10),
        )
        buffer = build_csv_report([trainee])

    content = buffer.read().decode("utf-8")
    assert "123456789012" not in content
    assert "9012" in content


def test_pdf_report_handles_empty_trainee_list():
    """Generating a report with zero trainees must not crash - it
    should produce a valid (if mostly empty) PDF."""
    buffer = build_pdf_report([])
    assert buffer.read()[:4] == b"%PDF"
