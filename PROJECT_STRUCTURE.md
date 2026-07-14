# Project Structure

```
cyber_training_portal/
│
├── app.py                     # Entry point - Flask App Factory (create_app())
├── config.py                  # Config, DevelopmentConfig, TestingConfig,
│                               #   ProductionConfig, get_config(), .env loading
├── requirements.txt            # Python dependencies (pinned versions)
├── .env.example                 # Template for local .env (never commit real .env)
├── .gitignore
│
├── README.md                    # Start here
├── SYSTEM_ARCHITECTURE.md       # How the pieces fit together
├── PROJECT_STRUCTURE.md         # This file
├── TESTING_CHECKLIST.md         # Automated + manual test coverage
├── DEPLOYMENT.md                # How to deploy to a real server
│
├── models/                      # SQLAlchemy ORM models (one table each)
│   ├── __init__.py                #   defines the shared `db` object
│   ├── user.py                    #   admin account + password hashing
│   ├── trainee.py                 #   core trainee record + validation
│   ├── app_setting.py             #   generic admin-editable key/value store
│   └── activity_log.py            #   audit trail
│
├── routes/                      # Flask Blueprints - one file per feature area
│   ├── __init__.py
│   ├── auth.py                    #   /login, /logout, login throttling
│   ├── dashboard.py                #   /dashboard - analytics + stat cards
│   ├── trainees.py                 #   /trainees/* - full CRUD + file serving
│   ├── reports.py                  #   /reports/* - PDF/Excel/CSV export + import
│   └── settings.py                 #   /settings/* - password, goal, backups, log
│
├── utils/                       # Shared helper modules (no routes here)
│   ├── __init__.py
│   ├── file_helpers.py             #   safe upload saving/deleting
│   ├── import_trainees.py          #   Excel import parsing + validation
│   ├── reports.py                  #   PDF/Excel/CSV report builders
│   └── security.py                 #   Aadhaar masking, login throttling
│
├── templates/                   # Jinja2 templates
│   ├── base.html                   #   absolute base: <html>, CDN links, top loading bar
│   ├── dashboard_layout.html       #   adds sidebar/navbar/footer shell
│   ├── login.html                  #   standalone auth page (extends base.html)
│   ├── dashboard.html              #   analytics dashboard
│   ├── partials/                    #   shared includes (navbar, sidebar, footer, toasts)
│   ├── trainees/                    #   list, detail, add/edit
│   ├── reports/                     #   export/import landing + import results
│   ├── settings/                    #   settings page
│   └── errors/                      #   404.html, 500.html
│
├── static/
│   ├── css/                        #   style.css (global), dashboard.css, trainees.css,
│   │                                #     reports_settings.css
│   └── js/                         #   main.js (global - loading bar), dashboard.js,
│                                    #     auth.js, trainees.js, reports_settings.js
│
├── database/
│   ├── training.db                 #   SQLite database file (created on first run)
│   └── backups/                    #   timestamped .db backups (Settings → Backup)
│
├── uploads/
│   ├── certificates/                #   uploaded PDF certificates
│
├── logs/
│   └── app.log                      #   rotating log file (production/non-debug only)
│
└── tests/                       # pytest suite
    ├── conftest.py                  #   shared fixtures (app, client, logged_in_client...)
    ├── test_auth.py                  #   login, logout, throttling, default-password reminder
    ├── test_crud.py                  #   trainee create/read/update/delete
    ├── test_reports.py               #   PDF/Excel/CSV export, Aadhaar masking
    ├── test_import.py                #   Excel import parsing + validation
    └── test_validation.py            #   model-level + database-level validation rules
```

## Where to Make a Change

| I want to...                                   | Edit this                                  |
|--------------------------------------------------|-----------------------------------------------|
| Add a new field to trainees                       | `models/trainee.py` + `routes/trainees.py` form + templates |
| Change a validation rule                           | `models/trainee.py` (`@validates`) and/or the `TraineeForm` in `routes/trainees.py` |
| Add a new admin-editable setting                   | Use `AppSetting.get_value`/`set_value` - no new table needed |
| Change what a report includes                     | `utils/reports.py`                             |
| Change import validation                            | `utils/import_trainees.py`                     |
| Change how Aadhaar is masked                       | `utils/security.py::mask_aadhaar`              |
| Add a new page                                       | new route in `routes/`, new template extending `dashboard_layout.html`, add a sidebar link in `templates/partials/_sidebar.html` |
| Change environment-specific behavior               | `config.py`                                      |
