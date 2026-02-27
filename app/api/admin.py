from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, func

from ..extensions import db
from ..models.user import User
from ..models.admin import AdminProfile
from ..models.student import StudentProfile
from ..models.student_questionnaire import StudentSkill, StudentInterest, StudentRole
from ..models.skills import Skill, SkillCategory
from ..models.roles import Role
from ..models.interests import Interest
from ..models.points import PointCategory, PointTransaction
from ..models.forum import ForumTopic, ForumMessage

admins_bp = Blueprint("admins", __name__)


def require_admin():
    """Проверка, что текущий пользователь - админ. Возвращает (user, error_response)."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    
    if not user:
        return None, ({"message": "user not found"}, 404)
    if user.role != "admin":
        return None, ({"message": "only admin can access this endpoint"}, 403)
    
    return user, None


@admins_bp.get("/admins/me")
@jwt_required()
def get_me():
    user, error = require_admin()
    if error:
        return error

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
    user, error = require_admin()
    if error:
        return error

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


@admins_bp.get("/admins/users")
@jwt_required()
def get_admin_users():
    """
    Получить список всех администраторов.
    
    Возвращает:
      - id
      - email
      - full_name
      - position
      - is_active
      - created_at
    """
    _, error = require_admin()
    if error:
        return error

    results = (
        db.session.query(User, AdminProfile)
        .outerjoin(AdminProfile, AdminProfile.user_id == User.id)
        .filter(User.role == "admin", User.is_active == True)
        .order_by(User.created_at.asc())
        .all()
    )

    admins = []
    for user, profile in results:
        admins.append(
            {
                "id": user.id,
                "email": user.email,
                "full_name": profile.full_name if profile else None,
                "position": profile.position if profile else None,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        )

    return admins, 200


@admins_bp.delete("/admins/users/<int:user_id>")
@jwt_required()
def delete_admin_user(user_id: int):
    """
    Деактивировать администратора (is_active = False).
    Нельзя удалить последнего активного администратора.
    """
    current_admin, error = require_admin()
    if error:
        return error

    user = db.session.get(User, user_id)
    if not user:
        return {"message": "user not found"}, 404

    if user.role != "admin":
        return {"message": "only admin users can be deleted via this endpoint"}, 400

    # Нельзя удалить последнего активного администратора
    active_admins_count = (
        db.session.query(User)
        .filter(User.role == "admin", User.is_active == True)
        .count()
    )
    if user.is_active and active_admins_count <= 1:
        return {"message": "нельзя удалить единственного активного администратора"}, 400

    # Удаляем профиль администратора, если он есть
    profile = user.admin_profile
    if profile:
        db.session.delete(profile)

    # Помечаем администратора как неактивного, чтобы он не мог авторизоваться,
    # но его ID сохранялся для форумных сообщений.
    user.is_active = False
    db.session.commit()

    return "", 204


# ==================== УПРАВЛЕНИЕ СТУДЕНТАМИ ====================

@admins_bp.get("/admins/students")
@jwt_required()
def get_students():
    """
    Получить список всех студентов с фильтрами, поиском и пагинацией.
    
    Query params:
        - page: int (default 1) - номер страницы
        - per_page: int (default 20, max 100) - количество на странице
        - search: str - поиск по email, имени, фамилии
        - group: str - фильтр по группе
        - has_profile: bool - фильтр по заполненности профиля (имя и фамилия)
        - has_skills: bool - фильтр по наличию навыков
        - skill_id: int - фильтр по конкретному навыку
        - role_id: int - фильтр по роли в команде
        - interest_id: int - фильтр по интересу
        - sort_by: str - поле сортировки (email, first_name, last_name, group_name, created_at)
        - sort_order: str - порядок сортировки (asc, desc)
    """
    admin_user, error = require_admin()
    if error:
        return error

    # Параметры пагинации
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)  # Ограничение

    # Параметры поиска и фильтров
    search = request.args.get("search", "", type=str).strip()
    group_filter = request.args.get("group", "", type=str).strip()
    has_profile = request.args.get("has_profile", type=str)
    has_skills = request.args.get("has_skills", type=str)
    
    # Новые фильтры по конкретным значениям
    skill_id = request.args.get("skill_id", type=int)
    role_id = request.args.get("role_id", type=int)
    interest_id = request.args.get("interest_id", type=int)
    
    # Параметры сортировки
    sort_by = request.args.get("sort_by", "created_at", type=str)
    sort_order = request.args.get("sort_order", "desc", type=str)

    # Базовый запрос: студенты с профилями
    query = (
        db.session.query(User, StudentProfile)
        .outerjoin(StudentProfile, User.id == StudentProfile.user_id)
        .filter(User.role == "student")
        .filter(User.is_active == True)
    )

    # Поиск
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(search_pattern),
                StudentProfile.first_name.ilike(search_pattern),
                StudentProfile.last_name.ilike(search_pattern),
                StudentProfile.group_name.ilike(search_pattern),
            )
        )

    # Фильтр по группе
    if group_filter:
        query = query.filter(StudentProfile.group_name.ilike(f"%{group_filter}%"))

    # Фильтр по заполненности профиля
    if has_profile == "true":
        query = query.filter(
            StudentProfile.first_name.isnot(None),
            StudentProfile.last_name.isnot(None),
            StudentProfile.first_name != "",
            StudentProfile.last_name != "",
        )
    elif has_profile == "false":
        query = query.filter(
            or_(
                StudentProfile.first_name.is_(None),
                StudentProfile.last_name.is_(None),
                StudentProfile.first_name == "",
                StudentProfile.last_name == "",
                StudentProfile.id.is_(None),
            )
        )

    # Фильтр по наличию навыков
    if has_skills == "true":
        skills_subq = (
            db.session.query(StudentSkill.student_id)
            .distinct()
            .subquery()
        )
        query = query.filter(StudentProfile.id.in_(db.select(skills_subq.c.student_id)))
    elif has_skills == "false":
        skills_subq = (
            db.session.query(StudentSkill.student_id)
            .distinct()
            .subquery()
        )
        query = query.filter(
            or_(
                StudentProfile.id.is_(None),
                ~StudentProfile.id.in_(db.select(skills_subq.c.student_id))
            )
        )

    # Фильтр по конкретному навыку
    if skill_id:
        skill_subq = (
            db.session.query(StudentSkill.student_id)
            .filter(StudentSkill.skill_id == skill_id)
            .subquery()
        )
        query = query.filter(StudentProfile.id.in_(db.select(skill_subq.c.student_id)))

    # Фильтр по роли в команде
    if role_id:
        role_subq = (
            db.session.query(StudentRole.student_id)
            .filter(StudentRole.role_id == role_id)
            .subquery()
        )
        query = query.filter(StudentProfile.id.in_(db.select(role_subq.c.student_id)))

    # Фильтр по интересу
    if interest_id:
        interest_subq = (
            db.session.query(StudentInterest.student_id)
            .filter(StudentInterest.interest_id == interest_id)
            .subquery()
        )
        query = query.filter(StudentProfile.id.in_(db.select(interest_subq.c.student_id)))

    # Сортировка
    sort_columns = {
        "email": User.email,
        "first_name": StudentProfile.first_name,
        "last_name": StudentProfile.last_name,
        "group_name": StudentProfile.group_name,
        "created_at": User.created_at,
        "total_points": StudentProfile.total_points,
        "total_som": StudentProfile.total_som,
    }
    sort_column = sort_columns.get(sort_by, User.created_at)
    
    if sort_order == "asc":
        query = query.order_by(sort_column.asc().nullslast())
    else:
        query = query.order_by(sort_column.desc().nullsfirst())

    # Подсчёт общего количества
    total = query.count()
    
    # Пагинация
    offset = (page - 1) * per_page
    results = query.offset(offset).limit(per_page).all()

    # Формируем ответ
    students = []
    for user, profile in results:
        # Подсчёт навыков, интересов, ролей
        skills_count = 0
        interests_count = 0
        roles_count = 0
        
        if profile:
            skills_count = db.session.query(func.count(StudentSkill.skill_id)).filter(
                StudentSkill.student_id == profile.id
            ).scalar() or 0
            
            interests_count = db.session.query(func.count(StudentInterest.interest_id)).filter(
                StudentInterest.student_id == profile.id
            ).scalar() or 0
            
            roles_count = db.session.query(func.count(StudentRole.role_id)).filter(
                StudentRole.student_id == profile.id
            ).scalar() or 0

        students.append({
            "id": profile.id if profile else None,
            "user_id": user.id,
            "email": user.email,
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "group_name": profile.group_name if profile else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "skills_count": skills_count,
            "interests_count": interests_count,
            "roles_count": roles_count,
            "total_points": profile.total_points if profile else 0,
            "total_som": profile.total_som if profile else 0,
        })

    total_pages = (total + per_page - 1) // per_page if total > 0 else 0

    return {
        "students": students,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
    }, 200


@admins_bp.delete("/admins/students/<int:user_id>")
@jwt_required()
def delete_student(user_id: int):
    """
    "Удалить" студента и связанные с ним данные, оставив его активность на форуме.

    Фактически выполняется мягкое удаление:
      - пользователь помечается как неактивный (is_active = False)
      - удаляется профиль студента (StudentProfile)
      - удаляются ответы анкеты (StudentSkill, StudentInterest, StudentRole)
      - удаляются транзакции баллов (PointTransaction)

    Форумные темы и сообщения остаются, но в API они будут отображаться как
    созданные пользователем "Удаленный аккаунт".
    """
    _, error = require_admin()
    if error:
        return error

    user = db.session.get(User, user_id)
    if not user:
        return {"message": "user not found"}, 404

    if user.role != "student":
        return {"message": "only student users can be deleted via this endpoint"}, 400

    profile = user.student_profile

    if profile:
        # Удаляем связанные записи анкеты
        db.session.query(StudentSkill).filter(
            StudentSkill.student_id == profile.id
        ).delete(synchronize_session=False)
        db.session.query(StudentInterest).filter(
            StudentInterest.student_id == profile.id
        ).delete(synchronize_session=False)
        db.session.query(StudentRole).filter(
            StudentRole.student_id == profile.id
        ).delete(synchronize_session=False)

        # Удаляем транзакции баллов
        db.session.query(PointTransaction).filter(
            PointTransaction.student_id == profile.id
        ).delete(synchronize_session=False)

        # Удаляем профиль студента
        db.session.delete(profile)

    # Помечаем пользователя как удалённого, чтобы он не мог авторизоваться
    # и не появлялся в списке студентов, но его ID оставался для форума.
    user.is_active = False

    db.session.commit()

    return "", 204


@admins_bp.get("/admins/students/groups")
@jwt_required()
def get_student_groups():
    """
    Получить список всех уникальных групп студентов (для фильтра).
    """
    admin_user, error = require_admin()
    if error:
        return error

    groups = (
        db.session.query(StudentProfile.group_name)
        .filter(StudentProfile.group_name.isnot(None))
        .filter(StudentProfile.group_name != "")
        .distinct()
        .order_by(StudentProfile.group_name)
        .all()
    )

    return {
        "groups": [g[0] for g in groups]
    }, 200


@admins_bp.get("/admins/filters/skills")
@jwt_required()
def get_skills_for_filter():
    """
    Получить список всех навыков (для фильтра), сгруппированных по категориям.
    """
    admin_user, error = require_admin()
    if error:
        return error

    categories = (
        db.session.query(SkillCategory)
        .order_by(SkillCategory.name)
        .all()
    )

    result = []
    for cat in categories:
        skills = (
            db.session.query(Skill)
            .filter(Skill.category_id == cat.id)
            .order_by(Skill.name)
            .all()
        )
        result.append({
            "category": {"id": cat.id, "name": cat.name},
            "skills": [{"id": s.id, "name": s.name} for s in skills]
        })

    return {"skill_categories": result}, 200


@admins_bp.get("/admins/filters/roles")
@jwt_required()
def get_roles_for_filter():
    """
    Получить список всех ролей в команде (для фильтра).
    """
    admin_user, error = require_admin()
    if error:
        return error

    roles = (
        db.session.query(Role)
        .order_by(Role.name)
        .all()
    )

    return {
        "roles": [{"id": r.id, "code": r.code, "name": r.name} for r in roles]
    }, 200


@admins_bp.get("/admins/filters/interests")
@jwt_required()
def get_interests_for_filter():
    """
    Получить список всех интересов (для фильтра).
    """
    admin_user, error = require_admin()
    if error:
        return error

    interests = (
        db.session.query(Interest)
        .order_by(Interest.name)
        .all()
    )

    return {
        "interests": [{"id": i.id, "name": i.name} for i in interests]
    }, 200


# ==================== СИСТЕМА БАЛЛОВ ====================

@admins_bp.get("/admins/points/categories")
@jwt_required()
def get_point_categories():
    """
    Получить список категорий начисления/списания баллов.
    """
    admin_user, error = require_admin()
    if error:
        return error

    categories = (
        db.session.query(PointCategory)
        .filter(PointCategory.is_active == True)
        .order_by(PointCategory.is_penalty, PointCategory.name)
        .all()
    )

    return {
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "points": c.points,
                "is_penalty": c.is_penalty,
                "is_custom": c.is_custom,
            }
            for c in categories
        ]
    }, 200


@admins_bp.post("/admins/students/<int:student_id>/points")
@jwt_required()
def add_student_points(student_id: int):
    """
    Начислить или списать баллы студенту.
    
    Body:
        - category_id: int (опционально, если is_custom)
        - points: int (только для кастомных начислений, иначе берётся из категории)
        - description: str (обязательно для кастомных, опционально для категорий)
    """
    admin_user, error = require_admin()
    if error:
        return error

    # Проверяем студента
    profile = db.session.get(StudentProfile, student_id)
    if not profile:
        return {"message": "student not found"}, 404

    data = request.get_json(silent=True) or {}
    
    category_id = data.get("category_id")
    custom_points = data.get("points")
    description = data.get("description", "").strip()

    # Определяем баллы
    category = None
    points = 0
    
    if category_id:
        category = db.session.get(PointCategory, category_id)
        if not category:
            return {"message": "category not found"}, 404
        
        if category.is_custom:
            # Для кастомной категории баллы указываются вручную
            if custom_points is None:
                return {"message": "points required for custom category"}, 400
            if not description:
                return {"message": "description required for custom category"}, 400
            points = int(custom_points)
        else:
            # Для обычной категории берём баллы из неё
            points = category.points
    else:
        return {"message": "category_id is required"}, 400

    # Вычисляем SOM (5 баллов = 1 SOM, только для положительных)
    som_earned = 0
    if points > 0:
        som_earned = points // 5

    # Создаём транзакцию
    transaction = PointTransaction(
        student_id=profile.id,
        category_id=category_id,
        points=points,
        som_earned=som_earned,
        description=description or category.name,
        created_by=admin_user.id,
    )
    db.session.add(transaction)

    # Обновляем баланс студента
    profile.total_points = (profile.total_points or 0) + points
    profile.total_som = (profile.total_som or 0) + som_earned

    # Не даём баллам уйти в минус (опционально, можно убрать)
    if profile.total_points < 0:
        profile.total_points = 0

    db.session.commit()

    return {
        "message": "points updated successfully",
        "transaction": {
            "id": transaction.id,
            "points": transaction.points,
            "som_earned": transaction.som_earned,
            "description": transaction.description,
            "created_at": transaction.created_at.isoformat(),
        },
        "student": {
            "id": profile.id,
            "total_points": profile.total_points,
            "total_som": profile.total_som,
        }
    }, 200


@admins_bp.get("/admins/students/<int:student_id>/points/history")
@jwt_required()
def get_student_points_history(student_id: int):
    """
    Получить историю транзакций баллов студента.
    """
    admin_user, error = require_admin()
    if error:
        return error

    profile = db.session.get(StudentProfile, student_id)
    if not profile:
        return {"message": "student not found"}, 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    query = (
        db.session.query(PointTransaction)
        .filter(PointTransaction.student_id == student_id)
        .order_by(PointTransaction.created_at.desc())
    )

    total = query.count()
    offset = (page - 1) * per_page
    transactions = query.offset(offset).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page if total > 0 else 0

    return {
        "transactions": [
            {
                "id": t.id,
                "points": t.points,
                "som_earned": t.som_earned,
                "description": t.description,
                "category": {
                    "id": t.category.id,
                    "name": t.category.name,
                    "is_penalty": t.category.is_penalty,
                } if t.category else None,
                "created_by": {
                    "id": t.created_by_user.id,
                    "email": t.created_by_user.email,
                } if t.created_by_user else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        "student": {
            "id": profile.id,
            "total_points": profile.total_points,
            "total_som": profile.total_som,
        }
    }, 200


# ==================== СПРАВОЧНИКИ (навыки, интересы, роли) ====================

@admins_bp.get("/admins/reference/skill-categories")
@jwt_required()
def get_admin_skill_categories():
    """Список категорий навыков."""
    _, error = require_admin()
    if error:
        return error
    items = db.session.execute(
        db.select(SkillCategory).order_by(SkillCategory.name.asc())
    ).scalars().all()
    return [{"id": c.id, "name": c.name} for c in items], 200


@admins_bp.post("/admins/reference/skill-categories")
@jwt_required()
def create_skill_category():
    """Создать категорию навыков."""
    _, error = require_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return {"message": "name is required"}, 400
    existing = db.session.execute(
        db.select(SkillCategory).where(SkillCategory.name == name)
    ).scalar_one_or_none()
    if existing:
        return {"message": "category with this name already exists"}, 400
    cat = SkillCategory(name=name)
    db.session.add(cat)
    db.session.commit()
    return {"id": cat.id, "name": cat.name}, 201


@admins_bp.delete("/admins/reference/skill-categories/<int:category_id>")
@jwt_required()
def delete_skill_category(category_id: int):
    """Удалить категорию навыков (если нет навыков в ней)."""
    _, error = require_admin()
    if error:
        return error
    cat = db.session.get(SkillCategory, category_id)
    if not cat:
        return {"message": "category not found"}, 404
    if cat.skills:
        return {"message": "cannot delete category with skills, remove skills first"}, 400
    db.session.delete(cat)
    db.session.commit()
    return "", 204


@admins_bp.get("/admins/reference/skills")
@jwt_required()
def get_admin_skills():
    """Список навыков (все или по категории)."""
    _, error = require_admin()
    if error:
        return error
    category_id = request.args.get("category_id", type=int)
    query = db.select(Skill).order_by(Skill.name.asc())
    if category_id:
        query = query.where(Skill.category_id == category_id)
    skills = db.session.execute(query).scalars().all()
    return [
        {"id": s.id, "name": s.name, "category": {"id": s.category.id, "name": s.category.name}}
        for s in skills
    ], 200


@admins_bp.post("/admins/reference/skills")
@jwt_required()
def create_skill():
    """Создать навык."""
    _, error = require_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category_id = data.get("category_id")
    if not name:
        return {"message": "name is required"}, 400
    if category_id is None:
        return {"message": "category_id is required"}, 400
    cat = db.session.get(SkillCategory, category_id)
    if not cat:
        return {"message": "category not found"}, 404
    existing = db.session.execute(
        db.select(Skill).where(Skill.name == name)
    ).scalar_one_or_none()
    if existing:
        return {"message": "skill with this name already exists"}, 400
    skill = Skill(name=name, category_id=category_id)
    db.session.add(skill)
    db.session.commit()
    return {"id": skill.id, "name": skill.name, "category": {"id": cat.id, "name": cat.name}}, 201


@admins_bp.delete("/admins/reference/skills/<int:skill_id>")
@jwt_required()
def delete_skill(skill_id: int):
    """Удалить навык."""
    _, error = require_admin()
    if error:
        return error
    skill = db.session.get(Skill, skill_id)
    if not skill:
        return {"message": "skill not found"}, 404
    db.session.delete(skill)
    db.session.commit()
    return "", 204


@admins_bp.get("/admins/reference/interests")
@jwt_required()
def get_admin_interests():
    """Список интересов."""
    _, error = require_admin()
    if error:
        return error
    items = db.session.execute(
        db.select(Interest).order_by(Interest.name.asc())
    ).scalars().all()
    return [{"id": i.id, "name": i.name} for i in items], 200


@admins_bp.post("/admins/reference/interests")
@jwt_required()
def create_interest():
    """Создать интерес."""
    _, error = require_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return {"message": "name is required"}, 400
    existing = db.session.execute(
        db.select(Interest).where(Interest.name == name)
    ).scalar_one_or_none()
    if existing:
        return {"message": "interest with this name already exists"}, 400
    interest = Interest(name=name)
    db.session.add(interest)
    db.session.commit()
    return {"id": interest.id, "name": interest.name}, 201


@admins_bp.delete("/admins/reference/interests/<int:interest_id>")
@jwt_required()
def delete_interest(interest_id: int):
    """Удалить интерес."""
    _, error = require_admin()
    if error:
        return error
    interest = db.session.get(Interest, interest_id)
    if not interest:
        return {"message": "interest not found"}, 404
    db.session.delete(interest)
    db.session.commit()
    return "", 204


@admins_bp.get("/admins/reference/roles")
@jwt_required()
def get_admin_roles():
    """Список ролей."""
    _, error = require_admin()
    if error:
        return error
    items = db.session.execute(
        db.select(Role).order_by(Role.name.asc())
    ).scalars().all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in items], 200


@admins_bp.post("/admins/reference/roles")
@jwt_required()
def create_role():
    """Создать роль."""
    _, error = require_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        return {"message": "code is required"}, 400
    if not name:
        return {"message": "name is required"}, 400
    existing = db.session.execute(
        db.select(Role).where(Role.code == code)
    ).scalar_one_or_none()
    if existing:
        return {"message": "role with this code already exists"}, 400
    role = Role(code=code, name=name)
    db.session.add(role)
    db.session.commit()
    return {"id": role.id, "code": role.code, "name": role.name}, 201


@admins_bp.delete("/admins/reference/roles/<int:role_id>")
@jwt_required()
def delete_role(role_id: int):
    """Удалить роль."""
    _, error = require_admin()
    if error:
        return error
    role = db.session.get(Role, role_id)
    if not role:
        return {"message": "role not found"}, 404
    db.session.delete(role)
    db.session.commit()
    return "", 204
