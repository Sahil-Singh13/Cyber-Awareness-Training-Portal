"""
utils/import_trainees.py
--------------------------
MILESTONE 6, Section 2: parses an admin-uploaded .xlsx file (matching
the sample template's columns) and validates every row using the SAME
rules as the Add Trainee form - so a row that would be rejected by the
web form is also rejected here, and for the same reason.

DESIGN: this module only VALIDATES and PARSES. It does not touch the
database directly - routes/reports.py calls parse_import_file() to get
back a list of "row results", then decides what to actually insert.
Keeping validation separate from persistence makes this easy to unit
test (see the test I ran below) without needing a live database.
"""

import re
from datetime import datetime

import pandas as pd

REQUIRED_COLUMNS = [
    "Name", "Gender", "Age", "Mobile", "Aadhaar",
    "Reference ID", "Training Date", "Location",
]

VALID_GENDERS = {"Male", "Female", "Other"}


def _clean_str(value):
    """
    Pandas represents an empty Excel cell as NaN (a float), not an
    empty string - str(value).strip() would turn that into the literal
    text "nan", which is wrong. This helper converts anything
    NaN/None/blank into a clean empty string, and otherwise returns the
    trimmed text - used for every text column before validation.

    IMPORTANT EDGE CASE (found by testing, not guessed): if an Excel
    column that's "really" text-of-digits (like Mobile or Aadhaar) has
    ANY blank cell anywhere in the column, Pandas silently upcasts the
    WHOLE column to float64 - so a mobile number typed as 9876543210
    comes back from pandas as the float 9876543210.0, and
    str(9876543210.0) is "9876543210.0", which then fails our "exactly
    10 digits" check even though the original value was perfectly
    valid. We detect that specific case (a float that is a whole
    number) and convert it back to the clean integer string first.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def validate_row(row_dict, existing_mobiles, existing_reference_ids, seen_mobiles, seen_reference_ids):
    """
    Validates ONE row (already converted to a plain dict) against the
    exact same rules as TraineeForm in routes/trainees.py: required
    fields, age range, mobile/Aadhaar digit patterns, and uniqueness.

    existing_mobiles / existing_reference_ids: sets of values ALREADY
    in the database - catches duplicates against trainees added before
    this import.
    seen_mobiles / seen_reference_ids: sets of values seen so far
    WITHIN this same import file - catches two rows in the same
    spreadsheet trying to use the same mobile number as each other,
    which a database-only check would miss until the second row tried
    to commit.

    Returns (is_valid, error_message, cleaned_data).
    """
    name = _clean_str(row_dict.get("Name"))
    gender = _clean_str(row_dict.get("Gender"))
    mobile = _clean_str(row_dict.get("Mobile"))
    aadhaar = _clean_str(row_dict.get("Aadhaar"))
    reference_id = _clean_str(row_dict.get("Reference ID"))
    location = _clean_str(row_dict.get("Location"))
    remarks = _clean_str(row_dict.get("Remarks"))
    age_raw = row_dict.get("Age")
    training_date_raw = row_dict.get("Training Date")

    if not name:
        return False, "Name is required.", None
    if gender not in VALID_GENDERS:
        return False, f"Gender must be one of {sorted(VALID_GENDERS)}.", None

    try:
        age = int(age_raw)
        if not (5 <= age <= 100):
            return False, "Age must be between 5 and 100.", None
    except (TypeError, ValueError):
        return False, "Age must be a whole number.", None

    if not re.fullmatch(r"\d{10}", mobile):
        return False, "Mobile must be exactly 10 digits.", None
    if not re.fullmatch(r"\d{12}", aadhaar):
        return False, "Aadhaar must be exactly 12 digits.", None
    if not reference_id:
        return False, "Reference ID is required.", None
    if not location:
        return False, "Training location is required.", None

    # Parse the training date - Pandas usually hands us either a
    # native Python/Pandas Timestamp (if Excel formatted the cell as a
    # date) or a plain string like "2026-07-10" (if it didn't) - we
    # accept both.
    training_date = None
    if isinstance(training_date_raw, (datetime, pd.Timestamp)):
        training_date = training_date_raw.date()
    else:
        date_str = _clean_str(training_date_raw)
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                training_date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
    if training_date is None:
        return False, "Training Date must be a valid date (e.g. 2026-07-10).", None

    # Duplicate checks - against the database AND against earlier rows
    # in this same file.
    if mobile in existing_mobiles or mobile in seen_mobiles:
        return False, f"Mobile number {mobile} is already used by another trainee.", None
    if reference_id in existing_reference_ids or reference_id in seen_reference_ids:
        return False, f"Reference ID {reference_id} is already used by another trainee.", None

    cleaned = {
        "full_name": name,
        "gender": gender,
        "age": age,
        "mobile_number": mobile,
        "aadhaar_number": aadhaar,
        "reference_id": reference_id,
        "training_date": training_date,
        "training_location": location,
        "remarks": remarks or None,
    }
    return True, None, cleaned


def parse_import_file(file_storage, existing_mobiles, existing_reference_ids):
    """
    Reads the uploaded .xlsx file and validates every row.

    Returns a dict:
        {
            "valid_rows": [cleaned_data, ...],   # ready to insert
            "results": [
                {"row_number": 2, "status": "ok"/"error", "message": ...},
                ...
            ],
            "total": int, "imported": int, "skipped": int,
        }

    Raises ValueError if the file itself can't be read at all, or is
    missing required columns - a clear, early failure rather than a
    confusing per-row error for every single row.
    """
    try:
        df = pd.read_excel(file_storage, sheet_name=0)
    except Exception as e:
        raise ValueError(f"Could not read this Excel file: {e}")

    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError(
            "This file is missing required column(s): " + ", ".join(missing_columns) +
            ". Please use the downloadable sample template."
        )

    results = []
    valid_rows = []
    seen_mobiles = set()
    seen_reference_ids = set()

    for i, row in df.iterrows():
        row_number = i + 2  # +2 = +1 for 0-index, +1 for the header row
        row_dict = row.to_dict()

        # A completely blank row (e.g. trailing empty rows Excel
        # sometimes keeps) shouldn't count as an "error" - just skip it
        # silently rather than reporting a scary-looking failure for
        # nothing.
        if all(_clean_str(v) == "" for v in row_dict.values()):
            continue

        is_valid, error_message, cleaned = validate_row(
            row_dict, existing_mobiles, existing_reference_ids, seen_mobiles, seen_reference_ids
        )

        if is_valid:
            valid_rows.append(cleaned)
            seen_mobiles.add(cleaned["mobile_number"])
            seen_reference_ids.add(cleaned["reference_id"])
            results.append({"row_number": row_number, "status": "ok", "message": "Imported successfully."})
        else:
            results.append({"row_number": row_number, "status": "error", "message": error_message})

    return {
        "valid_rows": valid_rows,
        "results": results,
        "total": len(results),
        "imported": len(valid_rows),
        "skipped": len(results) - len(valid_rows),
    }
