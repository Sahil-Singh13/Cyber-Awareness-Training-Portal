# Cyber Awareness Training Management Portal

A full-stack web application built with **Flask + SQLite + Bootstrap 5**
to manage cybersecurity awareness training records — trainees,
certificates, geotagged photos, progress tracking, and reports —
replacing manual Excel sheets and folders.

Built as part of the **WNS Cybersecurity Community Development Program**
college assignment.

> 🚧 **Status: Under active development (Milestone 1 of 10 complete)**
> This README will be filled in fully as each milestone is completed.

---

## Tech Stack

| Layer      | Technology                                              |
|------------|----------------------------------------------------------|
| Frontend   | HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js            |
| Backend    | Python, Flask (App Factory + Blueprints)                  |
| Database   | SQLite (via SQLAlchemy ORM)                                |
| Auth       | Flask-Login, Werkzeug password hashing                     |
| Forms      | Flask-WTF                                                   |
| Reports    | ReportLab (PDF), OpenPyXL/Pandas (Excel/CSV)                |
| Images     | Pillow                                                       |

---

## Project Structure

```
cyber_training_portal/
│
├── app.py                  # Application entry point (App Factory pattern)
├── config.py                # Centralized configuration (DB, uploads, secrets)
├── requirements.txt         # Python dependencies
│
├── models/                  # SQLAlchemy database models (Milestone 2)
├── routes/                  # Flask Blueprints - one file per feature area
├── utils/                   # Helper functions (validation, file handling, reports)
├── database/                 # SQLite database file lives here (training.db)
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html               # Shared layout (navbar/sidebar wrap here)
│   └── setup_check.html        # Milestone 1 placeholder page
│
├── static/
│   ├── css/style.css           # Custom Blue+White theme
│   ├── js/main.js              # Shared JS (dark mode, toasts, search)
│   └── images/                 # Logo, icons, illustrations
│
└── uploads/
    ├── certificates/            # Uploaded PDF certificates
    └── photos/                  # Uploaded geotagged training photos
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10+ installed
- pip (comes with Python)

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate it:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python app.py
```

### 5. Open in your browser
```
http://127.0.0.1:5000
```

You should see a **"Project Skeleton is Working!"** confirmation page.
That means Milestone 1 is correctly set up on your machine.

---

## Milestones Roadmap

- [x] **Milestone 1** — Project Structure
- [ ] **Milestone 2** — Database Design
- [ ] **Milestone 3** — Authentication (Login/Logout, Admin)
- [ ] **Milestone 4** — Dashboard (stats, charts, sidebar UI)
- [ ] **Milestone 5** — CRUD (Add/View/Edit/Delete Trainees)
- [ ] **Milestone 6** — File Uploads (Certificates & Photos)
- [ ] **Milestone 7** — Reports (PDF / Excel / CSV export)
- [ ] **Milestone 8** — Analytics (Chart.js dashboards)
- [ ] **Milestone 9** — Testing
- [ ] **Milestone 10** — Deployment

---

## Screenshots

_(Will be added as each milestone introduces new UI)_

---

## Future Improvements

_(Will be documented as the project matures)_
