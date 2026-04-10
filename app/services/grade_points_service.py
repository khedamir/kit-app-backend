from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable, Mapping, Any

import requests

from ..extensions import db
from ..models.student import StudentProfile
from ..models.journal_points import JournalProcessedMark
from ..models.points import PointTransaction
from . import journal_service
from .notification_service import create_notification

logger = logging.getLogger(__name__)


@dataclass
class JournalMark:
    student_workflow_id: int
    mark_set_id: int
    education_task_id: int
    version: int
    value: int
    issued: datetime | None
    lesson_date: date | None


def mark_to_points(value: int) -> int:
    """
    Правило конвертации оценок в баллы:
      5 -> +2
      4 -> +1
      3 ->  0
      2 -> -10
    Все остальные значения считаем 0.
    """
    if value == 5:
        return 2
    if value == 4:
        return 1
    if value == 2:
        return -10
    return 0


class GradePointsService:
    """
    Сервис для начисления баллов студентам за оценки из сетевого журнала.

    Работает в два режима:
      - ежедневная обработка за конкретный день (обычно "вчера");
      - финализация за весь месяц.
    """

    def __init__(self, journal_base_url: str, session: db.Session | None = None) -> None:
        self.journal_base_url = journal_base_url.rstrip("/")
        self.session = session or db.session

    # ===== Публичные методы =====

    def process_daily_scores(self, for_date: date) -> int:
        """
        Обработка оценок за конкретный день по дате урока (LessonDate).
        Возвращает количество новых обработанных оценок.
        """
        from_date = for_date
        # Нельзя делать replace(day=day+1): на последнем дне месяца будет ValueError
        to_date = for_date + timedelta(days=1)

        return self._process_range(from_date, to_date)

    def finalize_month(self, year: int, month: int) -> int:
        """
        Доначисление баллов за весь календарный месяц.
        Возвращает количество новых обработанных оценок.
        """
        month_start = date(year, month, 1)
        if month == 12:
            next_month_start = date(year + 1, 1, 1)
        else:
            next_month_start = date(year, month + 1, 1)

        return self._process_range(month_start, next_month_start)

    # ===== Внутренняя логика =====

    def _process_range(self, from_date: date, to_date: date) -> int:
        processed_count = 0

        # Берём только студентов, у которых есть связь с журналом
        profiles: Iterable[StudentProfile] = (
            self.session.execute(
                db.select(StudentProfile).where(
                    StudentProfile.student_workflow_id.isnot(None)
                )
            )
            .scalars()
            .all()
        )
        profile_list = list(profiles)
        if not profile_list:
            logger.warning(
                "[grade_points] Нет студентов с заполненным student_workflow_id — "
                "начисление из журнала пропущено"
            )

        for profile in profile_list:
            student_workflow_id = profile.student_workflow_id
            if not student_workflow_id:
                continue

            marks = self._fetch_marks_for_student(
                student_workflow_id=student_workflow_id,
                from_date=from_date,
                to_date=to_date,
            )
            if not marks:
                continue

            for jm in marks:
                if self._is_mark_already_processed(jm):
                    continue

                points = mark_to_points(jm.value)
                if points == 0:
                    # Можно не записывать нулевые, чтобы не раздувать таблицу
                    continue

                # Обновляем месячный счёт профиля
                month_start = date(jm.lesson_date.year, jm.lesson_date.month, 1) if jm.lesson_date else date(
                    from_date.year, from_date.month, 1
                )

                # Просто добавляем к текущему месяцу, перенос в total_points/SOM делает существующая логика
                profile.current_month_points = (profile.current_month_points or 0) + points

                transaction = PointTransaction(
                    student_id=profile.id,
                    category_id=None,
                    points=points,
                    som_earned=points // 5 if points > 0 else 0,
                    description=f"Оценка в журнале: {jm.value}",
                    created_by=None,
                )
                self.session.add(transaction)
                self.session.flush()  # чтобы получить transaction.id

                if points > 0:
                    create_notification(
                        user_id=profile.user_id,
                        notification_type="points_added",
                        title="Начислены баллы",
                        body=f"За оценку {jm.value} начислено {points} баллов.",
                        payload={
                            "transaction_id": transaction.id,
                            "points": points,
                            "source": "journal",
                        },
                    )
                elif points < 0:
                    create_notification(
                        user_id=profile.user_id,
                        notification_type="points_deducted",
                        title="Списаны баллы",
                        body=f"За оценку {jm.value} списано {abs(points)} баллов.",
                        payload={
                            "transaction_id": transaction.id,
                            "points": points,
                            "source": "journal",
                        },
                    )

                processed_mark = JournalProcessedMark(
                    student_id=profile.id,
                    student_workflow_id=jm.student_workflow_id,
                    mark_set_id=jm.mark_set_id,
                    education_task_id=jm.education_task_id,
                    version=jm.version,
                    mark_value=jm.value,
                    issued_at=jm.issued,
                    lesson_date=jm.lesson_date,
                    points=points,
                    transaction_id=transaction.id,
                    month_start=month_start,
                    processed_at=datetime.utcnow(),
                )
                self.session.add(processed_mark)

                processed_count += 1

        if processed_count > 0:
            self.session.commit()
        else:
            self.session.rollback()

        return processed_count

    def _fetch_marks_for_student(
        self,
        student_workflow_id: int,
        from_date: date,
        to_date: date,
    ) -> list[JournalMark]:
        items: list[Mapping[str, Any]] = []

        if os.getenv("JOURNAL_DB_SERVER"):
            try:
                items = journal_service.fetch_student_marks_by_lesson_date_range(
                    student_workflow_id, from_date, to_date
                )
            except Exception:
                logger.exception(
                    "[grade_points] Ошибка чтения оценок из журнала (pyodbc), "
                    "student_workflow_id=%s",
                    student_workflow_id,
                )
                return []
        else:
            url = f"{self.journal_base_url}/students/{student_workflow_id}/marks/by-date-range"
            params = {
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            }
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                payload = resp.json()
                if isinstance(payload, dict) and payload.get("error"):
                    logger.error(
                        "[grade_points] Журнал API вернул ошибку: %s url=%s",
                        payload.get("error"),
                        url,
                    )
                    return []
                items = list(payload.get("items", []))
            except requests.RequestException:
                logger.exception(
                    "[grade_points] Не удалось вызвать JOURNAL_API_BASE_URL=%s "
                    "(убедитесь, что запущен localdb.py на отдельном порту)",
                    self.journal_base_url,
                )
                return []

        result: list[JournalMark] = []
        for item in items:
            jm = self._journal_row_to_mark(item)
            if jm is not None:
                result.append(jm)
        return result

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, Decimal):
            return int(value)
        if isinstance(value, float):
            return int(value)
        return int(value)

    def _journal_row_to_mark(self, item: Mapping[str, Any]) -> JournalMark | None:
        try:
            issued_raw = item.get("Issued")
            issued_dt = None
            if issued_raw is not None:
                if isinstance(issued_raw, datetime):
                    issued_dt = issued_raw
                else:
                    issued_dt = datetime.fromisoformat(str(issued_raw).replace("Z", "+00:00"))

            lesson_date_raw = item.get("LessonDate")
            lesson_dt = None
            if lesson_date_raw is not None:
                # datetime — подкласс date, сначала проверяем datetime
                if isinstance(lesson_date_raw, datetime):
                    lesson_dt = lesson_date_raw.date()
                elif isinstance(lesson_date_raw, date):
                    lesson_dt = lesson_date_raw
                else:
                    lesson_dt = date.fromisoformat(str(lesson_date_raw)[:10])

            return JournalMark(
                student_workflow_id=self._coerce_int(item.get("StudentWorkFlowId")),
                mark_set_id=self._coerce_int(item.get("MarkSetId")),
                education_task_id=self._coerce_int(item.get("EducationTaskId")),
                version=self._coerce_int(item.get("Version"), 0),
                value=self._coerce_int(item.get("Value")),
                issued=issued_dt,
                lesson_date=lesson_dt,
            )
        except Exception:
            logger.warning("[grade_points] Пропуск строки оценки: %r", item, exc_info=True)
            return None

    def _is_mark_already_processed(self, jm: JournalMark) -> bool:
        exists = self.session.execute(
            db.select(JournalProcessedMark.id).where(
                JournalProcessedMark.student_workflow_id == jm.student_workflow_id,
                JournalProcessedMark.mark_set_id == jm.mark_set_id,
                JournalProcessedMark.education_task_id == jm.education_task_id,
                JournalProcessedMark.version == jm.version,
            )
        ).scalar_one_or_none()
        return exists is not None

