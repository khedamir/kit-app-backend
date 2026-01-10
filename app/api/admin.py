from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.user import User
from ..models.admin import AdminProfile

admins_bp = Blueprint("admins", __name__)


@admins_bp.get("/admins/me")
@jwt_required()
def get_me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404

    if user.role != "admin":
        return {"message": "only admin can access this endpoint"}, 403

    profile = user.admin_profile
    if not profile:
        # создаём пустой профиль, если его нет
        profile = AdminProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    return {
        "id": profile.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": profile.full_name,
        "position": profile.position,
    }, 200


@admins_bp.patch("/admins/me")
@jwt_required()
def patch_me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404

    if user.role != "admin":
        return {"message": "only admin can access this endpoint"}, 403

    profile = user.admin_profile
    if not profile:
        profile = AdminProfile(user_id=user.id)
        db.session.add(profile)

    data = request.get_json(silent=True) or {}

    allowed_fields = {"full_name", "position"}
    for k, v in data.items():
        if k in allowed_fields:
            setattr(profile, k, v)

    db.session.commit()

    return {
        "id": profile.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": profile.full_name,
        "position": profile.position,
    }, 200

