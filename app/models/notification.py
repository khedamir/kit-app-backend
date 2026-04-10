from datetime import datetime

from ..extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = db.Column(db.String(64), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", backref="notifications")
