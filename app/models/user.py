from datetime import datetime
from ..extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # student / admin
    role = db.Column(db.String(50), nullable=False, index=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student_profile = db.relationship("StudentProfile", back_populates="user", uselist=False)
    admin_profile = db.relationship("AdminProfile", back_populates="user", uselist=False)
