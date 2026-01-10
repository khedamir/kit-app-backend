from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)

from ..extensions import db
from ..models.user import User
from ..services.auth_service import authenticate

auth_bp = Blueprint("auth", __name__)

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
