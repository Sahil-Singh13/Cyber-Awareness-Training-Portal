"""
models/app_setting.py
----------------------
MILESTONE 6: a small key/value table for settings the admin can change
FROM THE APP ITSELF at runtime (e.g. "Update Training Goal" on the
Settings page).

WHY NOT JUST EDIT Config.TRAINING_GOAL DIRECTLY?
------------------------------------------------------
Config.py is PYTHON CODE, loaded once when the app starts. There is no
safe way for a running Flask app to rewrite its own source file while
it's executing (and doing so would be a bad practice even if possible -
mixing "code" and "data" like that makes deployments fragile). The
standard solution is: keep Config.py for things that only a developer
should change (secret keys, folder paths, allowed file types), and
store things an ADMIN should be able to change through the UI in the
database instead. This table is exactly that: a generic "settings
store" so future admin-editable settings don't each need their own new
database column.

WHY A NEW TABLE INSTEAD OF A NEW COLUMN ON AN EXISTING TABLE?
-------------------------------------------------------------------
This is an ADDITIVE schema change (a brand new table), not a
modification of Trainee or User - so it's safe to add without any risk
to existing data, consistent with how this project has handled every
other "the brief wants a schema change" situation so far (see the
Aadhaar note in routes/trainees.py and the "Last Updated" note in
trainees/detail.html).
"""

from datetime import datetime
from models import db


class AppSetting(db.Model):
    """
    One row per setting, e.g. key="training_goal", value="35".

    Table name (auto-generated): 'app_setting'
    """

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSetting {self.key}={self.value}>"

    # ------------------------------------------------------------------
    # CONVENIENCE HELPERS
    # ------------------------------------------------------------------
    @classmethod
    def get_value(cls, key, default=None):
        """
        Looks up a setting by key. Returns `default` if it has never
        been set - this is what makes it safe to introduce a BRAND NEW
        setting at any time without a migration: until an admin
        actually changes it, callers just get the fallback value they
        provide (usually a Config constant).
        """
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_value(cls, key, value):
        """
        Creates the row if it doesn't exist yet, or updates it in place
        if it does - the common "upsert" pattern. Callers don't need to
        know or care which case applies.
        """
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = cls(key=key, value=str(value))
            db.session.add(setting)
        db.session.commit()
        return setting
