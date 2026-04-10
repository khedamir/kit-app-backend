from __future__ import annotations

from typing import Iterable

from ..extensions import db
from ..models.notification import Notification
from ..models.user import User


def create_notification(
    *,
    user_id: int,
    notification_type: str,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        payload=payload or None,
        is_read=False,
    )
    db.session.add(notification)
    return notification


def create_notifications_for_users(
    *,
    user_ids: Iterable[int],
    notification_type: str,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
) -> int:
    unique_ids = {int(uid) for uid in user_ids if uid is not None}
    for uid in unique_ids:
        create_notification(
            user_id=uid,
            notification_type=notification_type,
            title=title,
            body=body,
            payload=payload,
        )
    return len(unique_ids)


def get_active_student_user_ids(exclude_user_id: int | None = None) -> list[int]:
    query = db.select(User.id).where(User.role == "student", User.is_active.is_(True))
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    return list(db.session.execute(query).scalars().all())


def get_active_admin_user_ids(exclude_user_id: int | None = None) -> list[int]:
    query = db.select(User.id).where(User.role == "admin", User.is_active.is_(True))
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    return list(db.session.execute(query).scalars().all())
