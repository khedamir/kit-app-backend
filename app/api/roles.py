from flask import Blueprint
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models.roles import Role

roles_bp = Blueprint("roles", __name__)


@roles_bp.get("/roles")
@jwt_required()
def get_roles():
    items = db.session.execute(
        db.select(Role).order_by(Role.name.asc())
    ).scalars().all()

    return [{"id": r.id, "code": r.code, "name": r.name} for r in items], 200

