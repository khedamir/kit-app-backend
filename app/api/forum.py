from datetime import datetime, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from ..extensions import db
from ..models.user import User
from ..models.forum import ForumTopic, ForumMessage

forum_bp = Blueprint("forum", __name__)

# Время в минутах, в течение которого можно редактировать/удалять сообщение
MESSAGE_EDIT_WINDOW_MINUTES = 30


def can_edit_message(message: ForumMessage, user: User) -> bool:
    """Проверяет, может ли пользователь редактировать сообщение"""
    if message.author_id != user.id:
        return False
    
    # Админ-автор может редактировать без ограничений
    if user.role == "admin":
        return True
    
    # Обычный автор - только в течение 30 минут
    time_passed = datetime.utcnow() - message.created_at
    return time_passed <= timedelta(minutes=MESSAGE_EDIT_WINDOW_MINUTES)


def can_delete_message(message: ForumMessage, user: User) -> bool:
    """Проверяет, может ли пользователь удалить сообщение"""
    is_author = message.author_id == user.id
    is_admin = user.role == "admin"
    
    # Админ может удалить любое сообщение
    if is_admin:
        return True
    
    # Не автор - не может удалить
    if not is_author:
        return False
    
    # Автор может удалить только в течение 30 минут
    time_passed = datetime.utcnow() - message.created_at
    return time_passed <= timedelta(minutes=MESSAGE_EDIT_WINDOW_MINUTES)


# ==================== TOPICS ====================

@forum_bp.get("/forum/topics")
@jwt_required()
def get_topics():
    """
    Получить список тем форума.
    Query params:
        - page: int (default 1)
        - per_page: int (default 20)
        - pinned_first: bool (default true) - закрепленные темы сверху
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)  # Ограничение
    pinned_first = request.args.get("pinned_first", "true").lower() == "true"

    query = ForumTopic.query
    
    if pinned_first:
        query = query.order_by(ForumTopic.is_pinned.desc(), ForumTopic.created_at.desc())
    else:
        query = query.order_by(ForumTopic.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        "topics": [topic.to_dict() for topic in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    }, 200


@forum_bp.post("/forum/topics")
@jwt_required()
def create_topic():
    """
    Создать новую тему.
    Body:
        - title: str (required)
        - description: str (optional)
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user:
        return {"message": "user not found"}, 404

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip() or None

    if not title:
        return {"message": "title is required"}, 400
    
    if len(title) > 255:
        return {"message": "title too long (max 255 chars)"}, 400

    topic = ForumTopic(
        title=title,
        description=description,
        author_id=user.id
    )
    db.session.add(topic)
    db.session.commit()

    return topic.to_dict(), 201


@forum_bp.get("/forum/topics/<int:topic_id>")
@jwt_required()
def get_topic(topic_id: int):
    """Получить тему по ID"""
    topic = db.session.get(ForumTopic, topic_id)
    
    if not topic:
        return {"message": "topic not found"}, 404
    
    return topic.to_dict(), 200


@forum_bp.patch("/forum/topics/<int:topic_id>")
@jwt_required()
def update_topic(topic_id: int):
    """
    Обновить тему.
    Только автор темы или админ может редактировать.
    Body:
        - title: str (optional)
        - description: str (optional)
        - is_closed: bool (optional, только для админа)
        - is_pinned: bool (optional, только для админа)
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user:
        return {"message": "user not found"}, 404

    topic = db.session.get(ForumTopic, topic_id)
    
    if not topic:
        return {"message": "topic not found"}, 404
    
    # Проверка прав: автор или админ
    is_author = topic.author_id == user.id
    is_admin = user.role == "admin"
    
    if not is_author and not is_admin:
        return {"message": "forbidden"}, 403

    data = request.get_json(silent=True) or {}
    
    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            return {"message": "title cannot be empty"}, 400
        if len(title) > 255:
            return {"message": "title too long (max 255 chars)"}, 400
        topic.title = title
    
    if "description" in data:
        topic.description = (data["description"] or "").strip() or None
    
    # Только админ может закрывать/закреплять темы
    if is_admin:
        if "is_closed" in data:
            topic.is_closed = bool(data["is_closed"])
        if "is_pinned" in data:
            topic.is_pinned = bool(data["is_pinned"])
    
    db.session.commit()
    return topic.to_dict(), 200


@forum_bp.delete("/forum/topics/<int:topic_id>")
@jwt_required()
def delete_topic(topic_id: int):
    """
    Удалить тему.
    Только автор темы или админ может удалить.
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user:
        return {"message": "user not found"}, 404

    topic = db.session.get(ForumTopic, topic_id)
    
    if not topic:
        return {"message": "topic not found"}, 404
    
    # Проверка прав: автор или админ
    is_author = topic.author_id == user.id
    is_admin = user.role == "admin"
    
    if not is_author and not is_admin:
        return {"message": "forbidden"}, 403
    
    db.session.delete(topic)
    db.session.commit()
    
    return {"message": "topic deleted"}, 200


# ==================== MESSAGES ====================

@forum_bp.get("/forum/topics/<int:topic_id>/messages")
@jwt_required()
def get_messages(topic_id: int):
    """
    Получить сообщения темы.
    Query params:
        - page: int (default 1)
        - per_page: int (default 50)
    
    Возвращает сообщения с вложенными ответами (replies).
    """
    topic = db.session.get(ForumTopic, topic_id)
    
    if not topic:
        return {"message": "topic not found"}, 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 100)

    # Получаем только корневые сообщения (без parent_id)
    query = ForumMessage.query.filter(
        ForumMessage.topic_id == topic_id,
        ForumMessage.parent_id.is_(None)
    ).order_by(ForumMessage.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Общее количество всех сообщений (включая ответы)
    total_messages = topic.messages_count
    
    return {
        "topic": topic.to_dict(),
        "messages": [msg.to_dict(include_replies=True) for msg in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": total_messages,  # Все сообщения, включая ответы
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    }, 200


@forum_bp.post("/forum/topics/<int:topic_id>/messages")
@jwt_required()
def create_message(topic_id: int):
    """
    Создать сообщение в теме.
    Body:
        - content: str (required)
        - parent_id: int (optional) - ID сообщения для ответа
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user:
        return {"message": "user not found"}, 404

    topic = db.session.get(ForumTopic, topic_id)
    
    if not topic:
        return {"message": "topic not found"}, 404
    
    if topic.is_closed:
        return {"message": "topic is closed"}, 403

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    parent_id = data.get("parent_id")

    if not content:
        return {"message": "content is required"}, 400

    # Проверка parent_id если указан
    if parent_id is not None:
        parent = db.session.get(ForumMessage, parent_id)
        if not parent:
            return {"message": "parent message not found"}, 404
        if parent.topic_id != topic_id:
            return {"message": "parent message belongs to another topic"}, 400
        # Запрещаем вложенность глубже одного уровня
        if parent.parent_id is not None:
            return {"message": "cannot reply to a reply (max 1 level of nesting)"}, 400

    message = ForumMessage(
        content=content,
        topic_id=topic_id,
        author_id=user.id,
        parent_id=parent_id
    )
    db.session.add(message)
    db.session.commit()

    return message.to_dict(include_replies=False), 201


@forum_bp.get("/forum/messages/<int:message_id>")
@jwt_required()
def get_message(message_id: int):
    """Получить сообщение по ID"""
    message = db.session.get(ForumMessage, message_id)
    
    if not message:
        return {"message": "message not found"}, 404
    
    return message.to_dict(include_replies=True), 200


@forum_bp.patch("/forum/messages/<int:message_id>")
@jwt_required()
def update_message(message_id: int):
    """
    Обновить сообщение.
    Только автор сообщения может редактировать в течение 30 минут.
    Админ-автор может редактировать без ограничений.
    Body:
        - content: str (required)
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user:
        return {"message": "user not found"}, 404

    message = db.session.get(ForumMessage, message_id)
    
    if not message:
        return {"message": "message not found"}, 404
    
    # Проверка прав на редактирование
    if not can_edit_message(message, user):
        if message.author_id != user.id:
            return {"message": "forbidden"}, 403
        return {"message": "edit time expired (30 minutes)"}, 403

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return {"message": "content is required"}, 400
    
    message.content = content
    message.is_edited = True
    db.session.commit()

    return message.to_dict(include_replies=False), 200


@forum_bp.delete("/forum/messages/<int:message_id>")
@jwt_required()
def delete_message(message_id: int):
    """
    Удалить сообщение.
    - Автор может удалить в течение 30 минут
    - Админ может удалить любое сообщение без ограничений
    - Админ-автор может удалить без ограничений
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user:
        return {"message": "user not found"}, 404

    message = db.session.get(ForumMessage, message_id)
    
    if not message:
        return {"message": "message not found"}, 404
    
    # Проверка прав на удаление
    if not can_delete_message(message, user):
        is_author = message.author_id == user.id
        if not is_author:
            return {"message": "forbidden"}, 403
        return {"message": "delete time expired (30 minutes)"}, 403
    
    db.session.delete(message)
    db.session.commit()
    
    return {"message": "message deleted"}, 200

