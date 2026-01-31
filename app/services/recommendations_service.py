"""
Сервис для генерации рекомендаций студентов на основе навыков, интересов и ролей.
"""
from typing import List, Dict, Any
from sqlalchemy import func, and_

from ..extensions import db
from ..models.student import StudentProfile
from ..models.student_questionnaire import StudentInterest, StudentRole, StudentSkill
from ..models.user import User
from ..models.interests import Interest
from ..models.roles import Role


def get_student_recommendations(
    student_id: int, 
    interests_page: int = 1,
    interests_per_page: int = 20,
    roles_page: int = 1,
    roles_per_page: int = 20
) -> Dict[str, Any]:
    """
    Получить рекомендации для студента с пагинацией.
    
    Возвращает:
    - recommendations_by_interests: студенты с общими интересами (с пагинацией)
    - recommendations_by_roles: студенты с дополняющими ролями (с пагинацией)
    
    Args:
        student_id: ID профиля студента
        interests_page: Страница для рекомендаций по интересам
        interests_per_page: Количество на странице для интересов
        roles_page: Страница для рекомендаций по ролям
        roles_per_page: Количество на странице для ролей
    
    Returns:
        Словарь с двумя списками рекомендаций и пагинацией
    """
    # Получаем текущего студента
    current_profile = db.session.get(StudentProfile, student_id)
    if not current_profile:
        return {
            "recommendations_by_interests": [],
            "recommendations_by_roles": []
        }
    
    # Получаем интересы текущего студента
    current_interests = db.session.execute(
        db.select(StudentInterest.interest_id)
        .where(StudentInterest.student_id == student_id)
    ).scalars().all()
    
    # Получаем роли текущего студента
    current_roles = db.session.execute(
        db.select(StudentRole.role_id)
        .where(StudentRole.student_id == student_id)
    ).scalars().all()
    
    # Если у студента есть интересы - ищем по общим интересам
    if current_interests:
        recommendations_by_interests_data = _get_recommendations_by_interests(
            student_id, current_interests, interests_page, interests_per_page
        )
    else:
        recommendations_by_interests_data = {
            "items": [],
            "pagination": {
                "page": interests_page,
                "per_page": interests_per_page,
                "total": 0,
                "pages": 0,
                "has_next": False,
                "has_prev": False
            }
        }
    
    # Если у студента есть роли - ищем по дополняющим ролям
    if current_roles:
        recommendations_by_roles_data = _get_recommendations_by_roles(
            student_id, current_roles, roles_page, roles_per_page
        )
    else:
        recommendations_by_roles_data = {
            "items": [],
            "pagination": {
                "page": roles_page,
                "per_page": roles_per_page,
                "total": 0,
                "pages": 0,
                "has_next": False,
                "has_prev": False
            }
        }
    
    return {
        "recommendations_by_interests": recommendations_by_interests_data["items"],
        "recommendations_by_interests_pagination": recommendations_by_interests_data["pagination"],
        "recommendations_by_roles": recommendations_by_roles_data["items"],
        "recommendations_by_roles_pagination": recommendations_by_roles_data["pagination"]
    }


def _get_recommendations_by_interests(
    current_student_id: int,
    current_interest_ids: List[int],
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    Найти студентов с общими интересами.
    
    Алгоритм:
    1. Находим всех студентов, у которых есть хотя бы один общий интерес
    2. Сортируем по количеству общих интересов (больше общих = выше в списке)
    3. Возвращаем информацию о студентах с количеством общих интересов
    """
    # Подзапрос: студенты с общими интересами
    subquery = (
        db.select(
            StudentInterest.student_id,
            func.count(StudentInterest.interest_id).label('common_interests_count')
        )
        .where(
            and_(
                StudentInterest.student_id != current_student_id,
                StudentInterest.interest_id.in_(current_interest_ids)
            )
        )
        .group_by(StudentInterest.student_id)
        .having(func.count(StudentInterest.interest_id) > 0)
        .order_by(func.count(StudentInterest.interest_id).desc())
        .subquery()
    )
    
    # Подсчет общего количества для пагинации
    total_count = db.session.execute(
        db.select(func.count()).select_from(subquery)
    ).scalar() or 0
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    offset = (page - 1) * per_page
    
    # Получаем профили и пользователей рекомендованных студентов с пагинацией
    results = db.session.execute(
        db.select(
            StudentProfile,
            User,
            subquery.c.common_interests_count
        )
        .join(User, StudentProfile.user_id == User.id)
        .join(subquery, StudentProfile.id == subquery.c.student_id)
        .where(User.is_active == True)
        .order_by(subquery.c.common_interests_count.desc())
        .offset(offset)
        .limit(per_page)
    ).all()
    
    recommendations = []
    for profile, user, common_count in results:
        # Получаем общие интересы для отображения
        common_interests = db.session.execute(
            db.select(StudentInterest.interest_id)
            .where(
                and_(
                    StudentInterest.student_id == profile.id,
                    StudentInterest.interest_id.in_(current_interest_ids)
                )
            )
        ).scalars().all()
        
        # Получаем названия общих интересов
        interest_names = []
        if common_interests:
            interests = db.session.execute(
                db.select(Interest.name)
                .where(Interest.id.in_(common_interests))
            ).scalars().all()
            interest_names = list(interests)
        
        recommendations.append({
            "student_id": profile.id,
            "user_id": user.id,
            "email": user.email,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "group_name": profile.group_name,
            "common_interests_count": common_count,
            "common_interests": list(interest_names),
            "match_type": "interests"
        })
    
    return {
        "items": recommendations,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


def _get_recommendations_by_roles(
    current_student_id: int,
    current_role_ids: List[int],
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    Найти студентов с дополняющими ролями.
    
    Алгоритм:
    1. Находим студентов, у которых НЕТ пересекающихся ролей с текущим
    2. Сортируем по количеству уникальных ролей (больше разных ролей = лучше команда)
    3. Возвращаем информацию о студентах
    """
    # Подзапрос: студенты с дополняющими ролями (без пересечений)
    subquery = (
        db.select(
            StudentRole.student_id,
            func.count(StudentRole.role_id).label('roles_count')
        )
        .where(
            and_(
                StudentRole.student_id != current_student_id,
                ~StudentRole.role_id.in_(current_role_ids)  # Роли, которых нет у текущего студента
            )
        )
        .group_by(StudentRole.student_id)
        .having(func.count(StudentRole.role_id) > 0)
        .order_by(func.count(StudentRole.role_id).desc())
        .subquery()
    )
    
    # Подсчет общего количества для пагинации
    total_count = db.session.execute(
        db.select(func.count()).select_from(subquery)
    ).scalar() or 0
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    offset = (page - 1) * per_page
    
    # Получаем профили и пользователей рекомендованных студентов с пагинацией
    results = db.session.execute(
        db.select(
            StudentProfile,
            User,
            subquery.c.roles_count
        )
        .join(User, StudentProfile.user_id == User.id)
        .join(subquery, StudentProfile.id == subquery.c.student_id)
        .where(User.is_active == True)
        .order_by(subquery.c.roles_count.desc())
        .offset(offset)
        .limit(per_page)
    ).all()
    
    recommendations = []
    for profile, user, roles_count in results:
        # Получаем роли рекомендованного студента
        student_roles = db.session.execute(
            db.select(StudentRole.role_id)
            .where(StudentRole.student_id == profile.id)
        ).scalars().all()
        
        # Получаем роли рекомендованного студента
        roles_data = []
        if student_roles:
            roles = db.session.execute(
                db.select(Role)
                .where(Role.id.in_(student_roles))
            ).scalars().all()
            roles_data = [
                {"id": role.id, "code": role.code, "name": role.name}
                for role in roles
            ]
        
        recommendations.append({
            "student_id": profile.id,
            "user_id": user.id,
            "email": user.email,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "group_name": profile.group_name,
            "roles_count": roles_count,
            "roles": roles_data,
            "match_type": "roles"
        })
    
    return {
        "items": recommendations,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }
