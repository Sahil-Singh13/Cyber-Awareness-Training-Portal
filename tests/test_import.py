"""
tests/test_import.py
----------------------
Covers utils/import_trainees.py directly (fast, no Flask test client
needed) plus the /reports/import route end-to-end for a small in-memory
.xlsx file built with Pandas.
"""

import io
import pandas as pd

from utils.import_trainees import parse_import_file, validate_row


def _build_xlsx(rows):
    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Trainees")
    buffer.seek(0)
    buffer.filename = "import.xlsx"
    return buffer


VALID_ROW = {
    "Name": "Priya Verma",
    "Gender": "Female",
    "Age": 24,
    "Mobile": "9123456789",
    "Aadhaar": "987654321098",
    "Reference ID": "REF900",
    "Training Date": "2026-07-11",
}


def test_validate_row_accepts_valid_data():
    is_valid, error, cleaned = validate_row(VALID_ROW, set(), set(), set(), set())
    assert is_valid is True
    assert error is None
    assert cleaned["full_name"] == "Priya Verma"


def test_validate_row_rejects_bad_mobile():
    row = dict(VALID_ROW, Mobile="12345")
    is_valid, error, cleaned = validate_row(row, set(), set(), set(), set())
    assert is_valid is False
    assert "10 digits" in error


def test_validate_row_rejects_bad_aadhaar():
    row = dict(VALID_ROW, Aadhaar="123")
    is_valid, error, cleaned = validate_row(row, set(), set(), set(), set())
    assert is_valid is False
    assert "Aadhaar" in error


def test_validate_row_rejects_duplicate_mobile_in_database():
    is_valid, error, cleaned = validate_row(
        VALID_ROW, {"9123456789"}, set(), set(), set()
    )
    assert is_valid is False
    assert "already used" in error


def test_validate_row_rejects_duplicate_within_same_file():
    """Two rows in the SAME spreadsheet sharing a mobile number must
    both be caught, not just checked against the database."""
    is_valid, error, cleaned = validate_row(
        VALID_ROW, set(), set(), {"9123456789"}, set()
    )
    assert is_valid is False


def test_parse_import_file_missing_columns_raises():
    buffer = _build_xlsx([{"Name": "Someone"}])
    try:
        parse_import_file(buffer, set(), set())
        assert False, "expected a ValueError for missing columns"
    except ValueError as e:
        assert "missing required column" in str(e).lower()


def test_parse_import_file_mixed_valid_and_invalid_rows():
    rows = [
        VALID_ROW,
        dict(VALID_ROW, Mobile="bad-number", **{"Reference ID": "REF901"}),
    ]
    buffer = _build_xlsx(rows)
    result = parse_import_file(buffer, set(), set())
    assert result["total"] == 2
    assert result["imported"] == 1
    assert result["skipped"] == 1


def test_import_route_inserts_valid_rows(logged_in_client):
    buffer = _build_xlsx([VALID_ROW])
    response = logged_in_client.post(
        "/reports/import",
        data={"excel_file": (buffer, "import.xlsx")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Priya Verma" in response.data or b"Import complete" in response.data


def test_import_route_requires_login(client):
    buffer = _build_xlsx([VALID_ROW])
    response = client.post(
        "/reports/import",
        data={"excel_file": (buffer, "import.xlsx")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
