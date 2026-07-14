"""
models/activity_log.py
------------------------
MILESTONE 6, Section 9: a simple audit trail. Every meaningful action
in the app (login, logout, trainee added/updated/deleted, report
generated) writes one row here. Another additive-only table - see the
note in models/app_setting.py for why that's the safe way to extend
the schema in this milestone.
"""

from datetime import datetime
from models import db


class ActivityLog(db.Model):
    """
    Table name (auto-generated): 'activity_log'
    """

    id = db.Column(db.Integer, primary_key=True)

    # A short machine-friendly code for WHAT happened, e.g.
    # "trainee_added", "trainee_deleted", "login", "logout",
    # "export_generated". Kept short and consistent so the Settings
    # page can map each action to a matching icon/color.
    action = db.Column(db.String(50), nullable=False)

    # A human-readable sentence describing the event, e.g.
    # "Trainee 'Rahul Sharma' was added." - this is what actually gets
    # displayed in the Recent Activity list, so it can read naturally
    # without the template needing to reconstruct a sentence from raw
    # data every time.
    description = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ActivityLog {self.action}: {self.description}>"

    @classmethod
    def log(cls, action, description):
        """
        The one function every other file calls to record an event.
        Deliberately does its OWN add+commit (rather than relying on the
        caller's transaction) so that logging an activity can never
        accidentally roll back, or be rolled back by, the actual
        business operation it's describing - e.g. if writing the log
        entry itself failed for some reason, that should never prevent
        (or get blamed on) the trainee actually being saved.
        """
        try:
            entry = cls(action=action, description=description)
            db.session.add(entry)
            db.session.commit()
        except Exception:
            # Logging is a "nice to have", never a "must not fail" - if
            # something goes wrong writing the log entry, we roll back
            # just that and move on silently rather than letting a
            # logging failure surface as a user-facing error.
            db.session.rollback()
