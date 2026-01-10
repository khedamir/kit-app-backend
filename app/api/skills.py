from flask import Blueprint
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models.skills import Skill, SkillCategory

skills_bp = Blueprint("skills", __name__)

@skills_bp.get("/skills")
@jwt_required()
def get_skills():
    skills = db.session.execute(
        db.select(Skill).order_by(Skill.name.asc())
    ).scalars().all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "category": {"id": s.category.id, "name": s.category.name},
        }
        for s in skills
    ], 200


@skills_bp.get("/skill-categories")
@jwt_required()
def get_skill_categories():
    categories = db.session.execute(
        db.select(SkillCategory).order_by(SkillCategory.name.asc())
    ).scalars().all()

    return [{"id": c.id, "name": c.name} for c in categories], 200
