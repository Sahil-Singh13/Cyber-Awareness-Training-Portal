# Testing Checklist

## Running the Automated Suite

```bash
pip install -r requirements.txt
pytest                 # run everything
pytest -v               # verbose, one line per test
pytest tests/test_auth.py   # just one file
pytest -k aadhaar            # just tests matching a keyword
```

Tests run against an **in-memory SQLite database** (`TestingConfig` in
`config.py`) - nothing is written to your real `database/training.db`,
and every test function gets a completely fresh, empty database (see
`tests/conftest.py`).

## Automated Coverage Map

| Area              | File                        | What's covered                                                             |
|--------------------|-----------------------------|--------------------------------------------------------------------------------|
| Authentication      | `tests/test_auth.py`          | Login success/failure, logout, `@login_required` redirect, default-password reminder, login throttling lockout |
| CRUD                | `tests/test_crud.py`          | Add/view/edit/delete trainee, duplicate mobile rejection, 404 on missing id, delete requires POST |
| Reports             | `tests/test_reports.py`       | PDF/Excel/CSV export routes, sample template download, login required, Aadhaar masked in every format |
| Import              | `tests/test_import.py`        | Row-level validation (mobile/Aadhaar format, duplicates in-file and in-db), missing-column error, mixed valid/invalid file, end-to-end import route |
| Validation          | `tests/test_validation.py`    | ORM `@validates` rules, database `CheckConstraint`s, `mask_aadhaar()` edge cases |

## Manual Verification Checklist

Use this before any release, alongside (not instead of) the automated
suite - some things (visual polish, file downloads, dark mode) are
easier to eyeball than to assert on.

### Authentication
- [ ] Log in with `admin` / `admin123` → see default-password reminder toast
- [ ] Log in with wrong password 5 times → 6th attempt (even correct) is throttled
- [ ] Log out → redirected to login, protected pages redirect back to login
- [ ] Change password in Settings → old password no longer works, new one does

### Trainees
- [ ] Add a trainee with a certificate → it appears on the detail page
- [ ] Try a duplicate mobile number → clear inline error, no crash
- [ ] Search by name, mobile, and reference ID → each finds the right record
- [ ] Sort by name/age/training date, ascending and descending
- [ ] Edit a trainee, replace the certificate → the new file is available
- [ ] Delete a trainee → confirmation modal → record + files are gone
- [ ] Trainee detail page → Aadhaar shows masked by default; reveal toggle shows the full number and can be hidden again

### Reports & Import
- [ ] Export PDF/Excel/CSV with 0, 1, and many trainees → no crashes, correct row counts, Aadhaar masked
- [ ] Download the sample import template → correct columns
- [ ] Import a file with a mix of valid/invalid rows → summary shows exact counts, invalid rows explain why

### Settings
- [ ] Update the training goal → dashboard progress bar reflects it immediately
- [ ] Backup the database → file appears in `database/backups/` and downloads
- [ ] Restore a valid `.db` file → succeeds, forces re-login
- [ ] Try restoring a non-database file → rejected with a clear message, nothing changes

### UI / UX
- [ ] Resize the browser down to a phone width → sidebar collapses to a toggle, tables scroll horizontally, no overlapping elements
- [ ] Toggle dark mode → persists across a page reload and across pages
- [ ] Navigate between pages → top loading bar appears briefly on every navigation and every form submit
- [ ] Trigger a 404 (visit a nonexistent trainee id) → styled error page, not a raw Flask error
- [ ] Trigger a large-file upload (>5 MB) → friendly flash message, not a crash

### Production Readiness
- [ ] Copy `.env.example` to `.env`, set `APP_ENV=production` with the placeholder `SECRET_KEY` → app refuses to start
- [ ] Set a real `SECRET_KEY` → app starts normally
- [ ] Set `APP_ENV=production` and confirm `logs/app.log` is created and receiving entries
