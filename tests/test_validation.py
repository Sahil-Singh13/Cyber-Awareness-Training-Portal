"""
tests/test_validation.py
--------------------------
Covers ORM-level validation on the Trainee model (models/trainee.py's
@validates decorators), the database CheckConstraints, and the
Version 1.0 utils/security.py helpers (Aadhaar masking).
"""

import pytest
from sqlalchemy.exc import IntegrityError

from models.trainee import Trainee
from models import db as _db
from utils.security import mask_aadhaar


VALID_KWARGS = dict(
    full_name="Test Trainee",
    gender="Male",
    age=30,
    mobile_number="9000000000",
    aadhaar_number="111122223333",
    reference_id="REFVAL1",
    training_date=__import__("datetime").date(2026, 1, 1),
)


def test_valid_trainee_saves_successfully(app):
    with app.app_context():
        trainee = Trainee(**VALID_KWARGS)
        _db.session.add(trainee)
        _db.session.commit()
        assert trainee.id is not None


def test_invalid_mobile_number_raises_value_error(app):
    with app.app_context():
        with pytest.raises(ValueError):
            Trainee(**{**VALID_KWARGS, "mobile_number": "123"})


def test_invalid_aadhaar_raises_value_error(app):
    with app.app_context():
        with pytest.raises(ValueError):
            Trainee(**{**VALID_KWARGS, "aadhaar_number": "999"})


def test_invalid_gender_raises_value_error(app):
    with app.app_context():
        with pytest.raises(ValueError):
            Trainee(**{**VALID_KWARGS, "gender": "Unknown"})


def test_blank_full_name_raises_value_error(app):
    with app.app_context():
        with pytest.raises(ValueError):
            Trainee(**{**VALID_KWARGS, "full_name": "   "})


def test_duplicate_mobile_number_violates_database_constraint(app):
    with app.app_context():
        _db.session.add(Trainee(**VALID_KWARGS))
        _db.session.commit()

        duplicate = Trainee(**{**VALID_KWARGS, "reference_id": "REFVAL2"})
        _db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            _db.session.commit()
        _db.session.rollback()


def test_age_out_of_range_violates_check_constraint(app):
    with app.app_context():
        trainee = Trainee(**{**VALID_KWARGS, "age": 999})
        _db.session.add(trainee)
        with pytest.raises(IntegrityError):
            _db.session.commit()
        _db.session.rollback()


# --------------------------------------------------------------------
# AADHAAR MASKING (utils/security.py)
# --------------------------------------------------------------------

def test_mask_aadhaar_shows_only_last_four_digits():
    assert mask_aadhaar("123456789012") == "XXXX XXXX 9012"


def test_mask_aadhaar_handles_blank_input():
    assert mask_aadhaar("") == ""
    assert mask_aadhaar(None) == ""


def test_mask_aadhaar_leaves_malformed_input_unchanged():
    assert mask_aadhaar("12345") == "12345"


def test_trainee_masked_aadhaar_property(app):
    with app.app_context():
        trainee = Trainee(**VALID_KWARGS)
        assert trainee.masked_aadhaar == "XXXX XXXX 3333"
