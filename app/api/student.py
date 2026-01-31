from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.user import User
from ..models.student import StudentProfile

from ..models.student_questionnaire import StudentSkill, StudentInterest, StudentRole
from ..models.skills import Skill
from ..models.interests import Interest
from ..models.roles import Role
from ..services.recommendations_service import get_student_recommendations


students_bp = Blueprint("students", __name__)


@students_bp.get("/students/me")
@jwt_required()
def get_me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404

    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        # на всякий случай, если профиль не создан
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    return {
        "id": profile.id,
        "user_id": user.id,
        "email": user.email,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "group_name": profile.group_name,
    }, 200


@students_bp.patch("/students/me")
@jwt_required()
def patch_me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404

    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)

    data = request.get_json(silent=True) or {}

    allowed_fields = {"first_name", "last_name", "group_name"}
    for k, v in data.items():
        if k in allowed_fields:
            setattr(profile, k, v)

    db.session.commit()

    return {
        "id": profile.id,
        "user_id": user.id,
        "email": user.email,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "group_name": profile.group_name,
    }, 200


@students_bp.put("/students/me/skills")
@jwt_required()
def put_my_skills():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404
    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return {"message": "body must be a list"}, 400

    # валидация + сбор skill_id
    skill_ids = []
    for item in data:
        if not isinstance(item, dict):
            return {"message": "each item must be an object"}, 400
        sid = item.get("skill_id")
        level = item.get("level")
        if not isinstance(sid, int):
            return {"message": "skill_id must be int"}, 400
        if not isinstance(level, int) or not (1 <= level <= 5):
            return {"message": "level must be int in range 1..5"}, 400
        skill_ids.append(sid)

    # проверим, что skills существуют
    if skill_ids:
        existing = db.session.execute(
            db.select(Skill.id).where(Skill.id.in_(skill_ids))
        ).scalars().all()
        if len(existing) != len(set(skill_ids)):
            return {"message": "some skill_id not found"}, 400

    # полная замена
    db.session.execute(
        db.delete(StudentSkill).where(StudentSkill.student_id == profile.id)
    )

    for item in data:
        db.session.add(StudentSkill(
            student_id=profile.id,
            skill_id=item["skill_id"],
            level=item["level"],
        ))

    db.session.commit()
    return {"message": "skills updated"}, 200


@students_bp.put("/students/me/interests")
@jwt_required()
def put_my_interests():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404
    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return {"message": "body must be a list"}, 400

    ids = []
    for item in data:
        if not isinstance(item, int):
            return {"message": "body must be list of int interest_id"}, 400
        ids.append(item)

    if ids:
        existing = db.session.execute(
            db.select(Interest.id).where(Interest.id.in_(ids))
        ).scalars().all()
        if len(existing) != len(set(ids)):
            return {"message": "some interest_id not found"}, 400

    db.session.execute(
        db.delete(StudentInterest).where(StudentInterest.student_id == profile.id)
    )

    for iid in ids:
        db.session.add(StudentInterest(student_id=profile.id, interest_id=iid))

    db.session.commit()
    return {"message": "interests updated"}, 200


@students_bp.put("/students/me/roles")
@jwt_required()
def put_my_roles():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404
    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return {"message": "body must be a list of role_id"}, 400

    role_ids = []
    for rid in data:
        if not isinstance(rid, int):
            return {"message": "each role must be role_id (int)"}, 400
        role_ids.append(rid)

    if role_ids:
        existing = db.session.execute(
            db.select(Role.id).where(Role.id.in_(role_ids))
        ).scalars().all()

        if len(existing) != len(set(role_ids)):
            return {"message": "some role_id not found"}, 400

    # полная замена
    db.session.execute(
        db.delete(StudentRole).where(StudentRole.student_id == profile.id)
    )

    for rid in role_ids:
        db.session.add(StudentRole(student_id=profile.id, role_id=rid))

    db.session.commit()
    return {"message": "roles updated"}, 200



@students_bp.get("/students/me/skill-map")
@jwt_required()
def get_skill_map():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404
    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    # skills
    sskills = db.session.execute(
        db.select(StudentSkill).where(StudentSkill.student_id == profile.id)
    ).scalars().all()

    skills_payload = []
    for ss in sskills:
        skills_payload.append({
            "id": ss.skill.id,
            "name": ss.skill.name,
            "level": ss.level,
            "category": {"id": ss.skill.category.id, "name": ss.skill.category.name},
        })

    # interests
    sinterests = db.session.execute(
        db.select(StudentInterest).where(StudentInterest.student_id == profile.id)
    ).scalars().all()

    interests_payload = [{"id": si.interest.id, "name": si.interest.name} for si in sinterests]

    # roles
    roles = db.session.execute(
        db.select(StudentRole).where(StudentRole.student_id == profile.id)
    ).scalars().all()

    roles_payload = [
        {
            "id": sr.role.id,
            "code": sr.role.code,
            "name": sr.role.name,
        }
        for sr in roles
    ]

    return {
        "profile": {
            "id": profile.id,
            "user_id": user.id,
            "email": user.email,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "group_name": profile.group_name,
            "total_points": profile.total_points or 0,
            "total_som": profile.total_som or 0,
        },
        "interests": interests_payload,
        "roles": roles_payload,
        "skills": skills_payload,
    }, 200


@students_bp.get("/students/me/recommendations")
@jwt_required()
def get_recommendations():
    """
    Получить рекомендации студентов на основе навыков, интересов и ролей.
    
    Query params:
        - interests_page: int (default 1) - страница для рекомендаций по интересам
        - interests_per_page: int (default 20) - количество на странице для интересов
        - roles_page: int (default 1) - страница для рекомендаций по ролям
        - roles_per_page: int (default 20) - количество на странице для ролей
    
    Возвращает два типа рекомендаций с пагинацией:
    1. По общим интересам - студенты с пересекающимися интересами
    2. По дополняющим ролям - студенты с разными ролями для формирования команды
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return {"message": "user not found"}, 404
    if user.role != "student":
        return {"message": "only student can access this endpoint"}, 403

    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    # Получаем параметры пагинации из query string
    interests_page = request.args.get("interests_page", 1, type=int)
    interests_per_page = request.args.get("interests_per_page", 20, type=int)
    interests_per_page = min(interests_per_page, 100)  # Ограничение
    
    roles_page = request.args.get("roles_page", 1, type=int)
    roles_per_page = request.args.get("roles_per_page", 20, type=int)
    roles_per_page = min(roles_per_page, 100)  # Ограничение

    try:
        recommendations = get_student_recommendations(
            profile.id,
            interests_page=interests_page,
            interests_per_page=interests_per_page,
            roles_page=roles_page,
            roles_per_page=roles_per_page
        )
        return recommendations, 200
    except Exception as e:
        # В production лучше логировать ошибку
        return {"message": "failed to get recommendations", "error": str(e)}, 500


@students_bp.get("/students/rating")
@jwt_required()
def get_students_rating():
    """
    Получить рейтинг студентов по баллам.
    
    Query params:
        - page: int (default 1)
        - per_page: int (default 20, max 100)
    
    Возвращает список студентов, отсортированных по total_points (desc).
    """
    user_id = int(get_jwt_identity())
    current_user = db.session.get(User, user_id)

    if not current_user:
        return {"message": "user not found"}, 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    # Базовый запрос - все активные студенты
    query = (
        db.select(StudentProfile)
        .join(User, User.id == StudentProfile.user_id)
        .where(User.is_active == True)
        .order_by(StudentProfile.total_points.desc(), StudentProfile.first_name.asc())
    )

    # Подсчёт общего количества
    count_query = (
        db.select(db.func.count(StudentProfile.id))
        .join(User, User.id == StudentProfile.user_id)
        .where(User.is_active == True)
    )
    total = db.session.execute(count_query).scalar() or 0

    # Пагинация
    offset = (page - 1) * per_page
    profiles = db.session.execute(
        query.offset(offset).limit(per_page)
    ).scalars().all()

    students = []
    for idx, profile in enumerate(profiles):
        rank = offset + idx + 1
        student_user = db.session.get(User, profile.user_id)
        students.append({
            "rank": rank,
            "id": profile.id,
            "user_id": profile.user_id,
            "email": student_user.email if student_user else None,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "group_name": profile.group_name,
            "total_points": profile.total_points or 0,
            "total_som": profile.total_som or 0,
        })

    return {
        "students": students,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        }
    }, 200


@students_bp.get("/students/<int:student_id>")
@jwt_required()
def get_student_by_id(student_id: int):
    """
    Получить детальную информацию о студенте по ID.
    Возвращает профиль, навыки, интересы и роли студента.
    """
    user_id = int(get_jwt_identity())
    current_user = db.session.get(User, user_id)

    if not current_user:
        return {"message": "user not found"}, 404

    # Получаем профиль студента
    profile = db.session.get(StudentProfile, student_id)
    if not profile:
        return {"message": "student not found"}, 404

    # Получаем пользователя студента
    student_user = db.session.get(User, profile.user_id)
    if not student_user or not student_user.is_active:
        return {"message": "student not found"}, 404

    # Навыки
    sskills = db.session.execute(
        db.select(StudentSkill).where(StudentSkill.student_id == profile.id)
    ).scalars().all()

    skills_payload = []
    for ss in sskills:
        skills_payload.append({
            "id": ss.skill.id,
            "name": ss.skill.name,
            "level": ss.level,
            "category": {"id": ss.skill.category.id, "name": ss.skill.category.name},
        })

    # Интересы
    sinterests = db.session.execute(
        db.select(StudentInterest).where(StudentInterest.student_id == profile.id)
    ).scalars().all()

    interests_payload = [{"id": si.interest.id, "name": si.interest.name} for si in sinterests]

    # Роли
    roles = db.session.execute(
        db.select(StudentRole).where(StudentRole.student_id == profile.id)
    ).scalars().all()

    roles_payload = [
        {
            "id": sr.role.id,
            "code": sr.role.code,
            "name": sr.role.name,
        }
        for sr in roles
    ]

    return {
        "profile": {
            "id": profile.id,
            "user_id": student_user.id,
            "email": student_user.email,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "group_name": profile.group_name,
        },
        "interests": interests_payload,
        "roles": roles_payload,
        "skills": skills_payload,
    }, 200
