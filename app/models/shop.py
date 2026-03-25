from datetime import datetime
from ..extensions import db


class ShopItem(db.Model):
    __tablename__ = "shop_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_som = db.Column(db.Integer, nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    photos = db.Column(db.JSON, nullable=False, default=list)
    sizes = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ShopPurchaseRequest(db.Model):
    __tablename__ = "shop_purchase_requests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("shop_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    selected_size = db.Column(db.String(32), nullable=True)
    total_price_som = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    admin_comment = db.Column(db.String(500), nullable=True)
    approved_pickup_at = db.Column(db.DateTime, nullable=True)
    approved_by_admin_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    student = db.relationship("StudentProfile")
    item = db.relationship("ShopItem")
    approved_by_admin = db.relationship("User")
