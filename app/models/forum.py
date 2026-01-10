from datetime import datetime
from ..extensions import db


class ForumTopic(db.Model):
    """Тема форума"""
    __tablename__ = "forum_topics"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Автор темы (может быть студент или админ)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    is_closed = db.Column(db.Boolean, default=False, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    author = db.relationship("User", backref="forum_topics")
    messages = db.relationship("ForumMessage", back_populates="topic", cascade="all, delete-orphan", 
                               order_by="ForumMessage.created_at")

    @property
    def messages_count(self):
        """Количество сообщений в теме"""
        return len(self.messages)

    def to_dict(self, include_author=True):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_closed": self.is_closed,
            "is_pinned": self.is_pinned,
            "messages_count": self.messages_count,
            "created_at": self.created_at.isoformat() + "Z",  # UTC
            "updated_at": self.updated_at.isoformat() + "Z",  # UTC
        }
        if include_author:
            data["author"] = {
                "id": self.author.id,
                "email": self.author.email,
                "role": self.author.role,
            }
            # Добавим имя автора если есть профиль
            if self.author.role == "student" and self.author.student_profile:
                profile = self.author.student_profile
                data["author"]["name"] = f"{profile.first_name or ''} {profile.last_name or ''}".strip() or None
            elif self.author.role == "admin" and self.author.admin_profile:
                data["author"]["name"] = self.author.admin_profile.full_name
        return data


class ForumMessage(db.Model):
    """Сообщение в теме форума"""
    __tablename__ = "forum_messages"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    topic_id = db.Column(db.Integer, db.ForeignKey("forum_topics.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Ответ на сообщение (один уровень вложенности)
    parent_id = db.Column(db.Integer, db.ForeignKey("forum_messages.id", ondelete="SET NULL"), nullable=True)
    
    is_edited = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    topic = db.relationship("ForumTopic", back_populates="messages")
    author = db.relationship("User", backref="forum_messages")
    parent = db.relationship("ForumMessage", remote_side=[id], backref="replies")

    def to_dict(self, include_author=True, include_replies=False):
        data = {
            "id": self.id,
            "content": self.content,
            "topic_id": self.topic_id,
            "parent_id": self.parent_id,
            "is_edited": self.is_edited,
            "created_at": self.created_at.isoformat() + "Z",  # UTC
            "updated_at": self.updated_at.isoformat() + "Z",  # UTC
        }
        if include_author:
            data["author"] = {
                "id": self.author.id,
                "email": self.author.email,
                "role": self.author.role,
            }
            # Добавим имя автора если есть профиль
            if self.author.role == "student" and self.author.student_profile:
                profile = self.author.student_profile
                data["author"]["name"] = f"{profile.first_name or ''} {profile.last_name or ''}".strip() or None
            elif self.author.role == "admin" and self.author.admin_profile:
                data["author"]["name"] = self.author.admin_profile.full_name
        
        if include_replies and self.replies:
            data["replies"] = [reply.to_dict(include_author=True, include_replies=False) for reply in self.replies]
        
        return data

