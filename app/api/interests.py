from flask import Blueprint
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models.interests import Interest

interests_bp = Blueprint("interests", __name__)

@interests_bp.get("/interests")
@jwt_required()
def get_interests():
    items = db.session.execute(
        db.select(Interest).order_by(Interest.name.asc())
    ).scalars().all()

    return [{"id": i.id, "name": i.name} for i in items], 200
