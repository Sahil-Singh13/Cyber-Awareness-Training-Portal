"""
tests/test_crud.py
--------------------
Covers full Create/Read/Update/Delete for Trainee records via the real
HTTP routes (not by poking the database directly) - this exercises the
form validation, uniqueness checks, and activity logging exactly the
way a real admin's browser would.
"""

from models.trainee import Trainee


def test_add_trainee_success(logged_in_client, sample_trainee_data, app):
    response = logged_in_client.post(
        "/trainees/add", data=sample_trainee_data, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"added successfully" in response.data

    with app.app_context():
        trainee = Trainee.query.filter_by(reference_id="REF001").first()
        assert trainee is not None
        assert trainee.full_name == "Rahul Sharma"


def test_add_trainee_requires_login(client, sample_trainee_data):
    response = client.post("/trainees/add", data=sample_trainee_data, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_duplicate_mobile_number_rejected(logged_in_client, sample_trainee_data):
    logged_in_client.post("/trainees/add", data=sample_trainee_data, follow_redirects=True)

    second = dict(sample_trainee_data)
    second["reference_id"] = "REF002"  # different reference, SAME mobile number
    response = logged_in_client.post("/trainees/add", data=second, follow_redirects=True)

    assert b"already registered with another trainee" in response.data


def test_view_trainee_list(logged_in_client, sample_trainee_data):
    logged_in_client.post("/trainees/add", data=sample_trainee_data, follow_redirects=True)
    response = logged_in_client.get("/trainees/")
    assert response.status_code == 200
    assert b"Rahul Sharma" in response.data


def test_view_trainee_detail(logged_in_client, sample_trainee_data, app):
    logged_in_client.post("/trainees/add", data=sample_trainee_data, follow_redirects=True)
    with app.app_context():
        trainee_id = Trainee.query.first().id

    response = logged_in_client.get(f"/trainees/{trainee_id}")
    assert response.status_code == 200
    assert b"Rahul Sharma" in response.data
    # Aadhaar must be MASKED by default on the detail page (Version 1.0).
    assert b"123456789012" not in response.data
    assert b"XXXX XXXX 9012" in response.data


def test_view_nonexistent_trainee_returns_404(logged_in_client):
    response = logged_in_client.get("/trainees/99999")
    assert response.status_code == 404


def test_edit_trainee_updates_fields(logged_in_client, sample_trainee_data, app):
    logged_in_client.post("/trainees/add", data=sample_trainee_data, follow_redirects=True)
    with app.app_context():
        trainee_id = Trainee.query.first().id

    updated = dict(sample_trainee_data)
    updated["full_name"] = "Rahul Kumar Sharma"

    response = logged_in_client.post(
        f"/trainees/{trainee_id}/edit", data=updated, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"updated successfully" in response.data

    with app.app_context():
        trainee = Trainee.query.get(trainee_id)
        assert trainee.full_name == "Rahul Kumar Sharma"


def test_delete_trainee_removes_record(logged_in_client, sample_trainee_data, app):
    logged_in_client.post("/trainees/add", data=sample_trainee_data, follow_redirects=True)
    with app.app_context():
        trainee_id = Trainee.query.first().id

    response = logged_in_client.post(f"/trainees/{trainee_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"deleted successfully" in response.data

    with app.app_context():
        assert Trainee.query.get(trainee_id) is None


def test_delete_trainee_requires_post(logged_in_client, sample_trainee_data, app):
    """Deletion must never be reachable via a plain GET request."""
    logged_in_client.post("/trainees/add", data=sample_trainee_data, follow_redirects=True)
    with app.app_context():
        trainee_id = Trainee.query.first().id

    response = logged_in_client.get(f"/trainees/{trainee_id}/delete")
    assert response.status_code == 405
