"""
models/__init__.py
-------------------
This file creates ONE SQLAlchemy object called `db` that the ENTIRE
application shares.

WHY DOES THIS FILE EXIST (and why is it basically empty of models)?
----------------------------------------------------------------------
This is the classic Flask-SQLAlchemy "avoid circular imports" pattern.

Here's the problem it solves:
    - app.py needs to know about `db` to call db.init_app(app)
    - models/user.py and models/trainee.py need `db` to define
      db.Model classes (User, Trainee)
    - If user.py tried to import `db` from app.py, and app.py tried to
      import User from user.py, Python would get stuck in a loop
      (a "circular import") and crash on startup.

The fix: create `db = SQLAlchemy()` in its OWN neutral file (this one),
with no dependency on app.py. Both app.py AND the model files import
`db` from HERE instead of from each other. No loop, no crash.

HOW db.init_app(app) WORKS
----------------------------
`SQLAlchemy()` on its own just creates an "unbound" object - it doesn't
know which Flask app it belongs to yet. In app.py, we later call
`db.init_app(app)`, which is the step that actually connects this `db`
object to our specific Flask app and reads settings like
SQLALCHEMY_DATABASE_URI from app.config. This two-step
"create then bind" approach is what the App Factory pattern requires.
"""

from flask_sqlalchemy import SQLAlchemy

# This single `db` instance is imported by every model file
# (models/user.py, models/trainee.py) and by app.py.
db = SQLAlchemy()
