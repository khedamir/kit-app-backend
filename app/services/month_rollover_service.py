"""
Закрытие календарного месяца по баллам: перенос current_month_points → total_points и SOM.

Используется планировщиком 1-го числа (после доначисления оценок из журнала) и той же логикой,
что раньше была только в admin._ensure_current_month при ручных начислениях.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ..extensions import db
from ..models.student import StudentProfile
from ..models.user import User


def sync_profile_to_calendar_month(
    profile: StudentProfile,
    today: date | None = None,
) -> bool:
    """
    Если учёт месяца у профиля не совпадает с календарным месяцем `today`:
    переносит current_month_points в total_points и total_som (SOM: max(0, mp)//5),
    обнуляет месячный счёт, выставляет current_month_started_at на 1-е число месяца.

    Возвращает True, если было изменение (нужен commit снаружи).
    """
    today = today or date.today()
    month_start = date(today.year, today.month, 1)

    if profile.current_month_started_at == month_start:
        return False

    mp = profile.current_month_points or 0
    # Был прошлый месяц ИЛИ месяц не инициализирован, но баллы уже есть (например, только журнал)
    if profile.current_month_started_at is not None or mp != 0:
        if mp != 0:
            profile.total_points = (profile.total_points or 0) + mp
            positive = max(0, mp)
            som_add = positive // 5
            if som_add > 0:
                profile.total_som = (profile.total_som or 0) + som_add

    profile.current_month_points = 0
    profile.current_month_started_at = month_start
    return True


def rollover_all_active_students(as_of: date | None = None) -> tuple[int, int]:
    """
    Синхронизирует всех активных студентов с календарным месяцем as_of (по умолчанию сегодня).

    Вызывать 1-го числа после finalize_month за предыдущий месяц.

    Возвращает (число профилей с изменениями, сумма баллов, ушедших в total_points).
    """
    as_of = as_of or date.today()
    stmt = (
        select(StudentProfile)
        .join(User, User.id == StudentProfile.user_id)
        .where(User.role == "student", User.is_active.is_(True))
    )
    profiles = db.session.execute(stmt).scalars().all()

    changed = 0
    total_moved = 0
    for profile in profiles:
        mp_before = profile.current_month_points or 0
        if sync_profile_to_calendar_month(profile, as_of):
            changed += 1
            if mp_before != 0:
                total_moved += mp_before

    if changed:
        db.session.commit()
    return changed, total_moved
