from datetime import datetime

from models import db


class GalleryPhoto(db.Model):
    """An independently stored group-training image for the gallery."""

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
