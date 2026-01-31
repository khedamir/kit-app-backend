from datetime import datetime
from ..extensions import db

class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    group_name = db.Column(db.String(120), nullable=True)

    # Система баллов и валюты
    total_points = db.Column(db.Integer, default=0, nullable=False)  # Баллы (для рейтинга)
    total_som = db.Column(db.Integer, default=0, nullable=False)     # SOM (валюта для трат)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="student_profile")
