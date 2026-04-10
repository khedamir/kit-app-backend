from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models.notification import Notification
from ..models.user import User


notifications_bp = Blueprint("notifications", __name__)


def _serialize_notification(item: Notification) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "body": item.body,
        "payload": item.payload or {},
        "is_read": bool(item.is_read),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@notifications_bp.get("/notifications/me")
@jwt_required()
def get_my_notifications():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return {"message": "user not found"}, 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(max(per_page, 1), 100)

    base_query = db.select(Notification).where(Notification.user_id == user.id)
    total = db.session.execute(
        db.select(db.func.count(Notification.id)).where(Notification.user_id == user.id)
    ).scalar() or 0
    unread_count = db.session.execute(
        db.select(db.func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
    ).scalar() or 0

    offset = (max(page, 1) - 1) * per_page
    items = db.session.execute(
        base_query.order_by(Notification.created_at.desc()).offset(offset).limit(per_page)
    ).scalars().all()

    return {
        "items": [_serialize_notification(item) for item in items],
        "unread_count": int(unread_count),
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": int(total),
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        },
    }, 200


@notifications_bp.patch("/notifications/me/<int:notification_id>/read")
@jwt_required()
def mark_notification_as_read(notification_id: int):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return {"message": "user not found"}, 404

    item = db.session.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        return {"message": "notification not found"}, 404

    if not item.is_read:
        item.is_read = True
        db.session.commit()

    return _serialize_notification(item), 200


@notifications_bp.patch("/notifications/me/read-all")
@jwt_required()
def mark_all_notifications_as_read():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return {"message": "user not found"}, 404

    db.session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return {"message": "ok"}, 200
