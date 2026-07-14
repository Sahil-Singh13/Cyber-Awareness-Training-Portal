# System Architecture

## High-Level Overview

```
                         ┌─────────────────────┐
                         │       Browser        │
                         │ (Bootstrap 5 + JS)   │
                         └──────────┬───────────┘
                                    │ HTTP(S)
                                    ▼
                         ┌─────────────────────┐
                         │      Flask App        │
                         │  (App Factory pattern) │
                         └──────────┬───────────┘
              ┌─────────────┬───────┼───────┬─────────────┐
              ▼             ▼       ▼       ▼             ▼
          auth_bp     dashboard_bp trainees_bp reports_bp settings_bp
              │             │       │       │             │
              └─────────────┴───────┼───────┴─────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  SQLAlchemy ORM       │
                         │  (models/*.py)         │
                         └──────────┬───────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  SQLite Database       │
                         │  database/training.db  │
                         └─────────────────────┘
```

## Application Factory Pattern

`app.py` does not create a global `Flask()` instance at import time.
Instead, `create_app()` builds and returns a fully configured app. This
is what allows `tests/conftest.py` to spin up a fresh app (with an
in-memory database) for every single test function, and what allows a
production WSGI server (Gunicorn, etc.) to import and call
`create_app()` without any code changes.

## Configuration Layers

`config.py` defines one base `Config` class holding everything common
to every environment (upload folders, allowed extensions, the training
goal, etc.), and three environment-specific subclasses:

- **DevelopmentConfig** — debug mode on, relaxed cookies, used by default
- **TestingConfig** — in-memory SQLite, CSRF disabled, used by pytest
- **ProductionConfig** — debug off, secure cookies, `SECRET_KEY` required

`get_config()` picks the right class based on the `APP_ENV` environment
variable (loaded from `.env` via `python-dotenv`, or a real environment
variable in a hosted deployment). See `.env.example`.

## Request Flow (example: adding a trainee)

1. Browser submits the Add Trainee form (`POST /trainees/add`).
2. `CSRFProtect` (registered globally in `app.py`) verifies the CSRF
   token before the route function even runs.
3. `routes/trainees.py::add_trainee()` builds a `TraineeForm`
   (Flask-WTF) and calls `validate_on_submit()`, which runs every
   field validator, including the custom `validate_mobile_number` /
   `validate_reference_id` uniqueness checks.
4. If valid, `utils/file_helpers.py` safely saves any uploaded
   certificate to disk with a randomized filename (preventing
   path traversal and filename collisions).
5. A `Trainee` ORM object is constructed and committed via
   `models/trainee.py`'s three validation layers (form → `@validates` →
   database `CheckConstraint`).
6. `models/activity_log.py::ActivityLog.log()` records the action for
   the Settings page's audit trail.
7. The admin is redirected to the trainee list with a flashed success
   toast.

## Security Model

| Concern                     | Mechanism                                                          |
|------------------------------|----------------------------------------------------------------------|
| Password storage             | Werkzeug `generate_password_hash` (scrypt), never plain text          |
| CSRF                          | Flask-WTF `CSRFProtect`, global, every POST/PUT/PATCH/DELETE         |
| Session security              | Signed cookies (`SECRET_KEY`); `Secure`/`HttpOnly`/`SameSite` in prod |
| Brute-force login protection  | In-memory sliding-window throttle (`utils/security.py`)              |
| Aadhaar privacy               | Masked in UI + reports by default (`utils/security.py::mask_aadhaar`)|
| File upload safety            | Extension allow-list + `secure_filename` + randomized storage names   |
| Protected file serving        | Certificates served via `@login_required` routes, not `static/` |
| SQL injection                 | SQLAlchemy ORM (parameterized queries) throughout; no raw SQL         |
| Error handling                | Global 404/500 handlers; route-level try/except with rollback         |

## Data Model Summary

- **User** — one admin account (this app is single-admin by design)
- **Trainee** — the core record; three layers of validation (form, ORM
  `@validates`, database `CheckConstraint`)
- **AppSetting** — generic key/value store for admin-editable settings
  (currently just the training goal) without needing schema changes
  for every new setting
- **ActivityLog** — append-only audit trail of meaningful actions

## Logging

In `development`/`testing`, log output goes to the console (Flask's
default). In any other environment, `app.py` attaches a
`RotatingFileHandler` writing to `logs/app.log` (max 1 MB per file, 5
backups kept), so a real deployment has durable, bounded log files.
