from datetime import datetime
from ..extensions import db


class PointCategory(db.Model):
    """Категории начисления/списания баллов."""
    __tablename__ = "point_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, nullable=False)  # положительное = награда, отрицательное = штраф
    is_penalty = db.Column(db.Boolean, default=False, nullable=False)
    is_custom = db.Column(db.Boolean, default=False, nullable=False)  # для категории "Прочее"
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    transactions = db.relationship("PointTransaction", back_populates="category")


class PointTransaction(db.Model):
    """История транзакций баллов студента."""
    __tablename__ = "point_transactions"

    id = db.Column(db.Integer, primary_key=True)
    
    student_id = db.Column(
        db.Integer, 
        db.ForeignKey("student_profiles.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    category_id = db.Column(
        db.Integer, 
        db.ForeignKey("point_categories.id", ondelete="RESTRICT"), 
        nullable=True  # null для кастомных начислений
    )
    
    # Фактические баллы транзакции (может отличаться от category.points для "Прочее")
    points = db.Column(db.Integer, nullable=False)
    
    # SOM начисленные за эту транзакцию (5 баллов = 1 SOM, только для положительных)
    som_earned = db.Column(db.Integer, default=0, nullable=False)
    
    # Описание (обязательно для кастомных, опционально для категорий)
    description = db.Column(db.Text, nullable=True)
    
    # Кто начислил
    created_by = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student = db.relationship("StudentProfile", backref="point_transactions")
    category = db.relationship("PointCategory", back_populates="transactions")
    created_by_user = db.relationship("User", foreign_keys=[created_by])
