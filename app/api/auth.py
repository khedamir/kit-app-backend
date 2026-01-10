from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)

from ..extensions import db
from ..models.user import User
from ..models.student import StudentProfile
from ..services.auth_service import authenticate
from ..utils.security import hash_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    """
    Простая регистрация нового пользователя (студента).
    Body: { "email": "...", "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return {"message": "email and password are required"}, 400

    if len(password) < 6:
        return {"message": "password must be at least 6 characters"}, 400

    # Проверяем, не занят ли email
    existing = User.query.filter_by(email=email).first()
    if existing:
        return {"message": "email already registered"}, 409

    # Создаём пользователя
    user = User(
        email=email,
        password_hash=hash_password(password),
        role="student"
    )
    db.session.add(user)
    db.session.flush()  # Получаем user.id

    # Создаём профиль студента
    profile = StudentProfile(user_id=user.id)
    db.session.add(profile)
    db.session.commit()

    # Сразу возвращаем токены
    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))

    return {
        "message": "registered successfully",
        "access_token": access,
        "refresh_token": refresh,
        "user": {"id": user.id, "email": user.email, "role": user.role}
    }, 201


@auth_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return {"message": "email and password are required"}, 400

    user = authenticate(email, password)
    if not user:
        return {"message": "invalid credentials"}, 401

    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {"id": user.id, "email": user.email, "role": user.role}
    }, 200


@auth_bp.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access = create_access_token(identity=user_id)
    return {"access_token": access}, 200


@auth_bp.get("/auth/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))
    if not user:
        return {"message": "user not found"}, 404

    return {"id": user.id, "email": user.email, "role": user.role}, 200
