from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Mapping, Any

import requests

from ..extensions import db
from ..models.student import StudentProfile
from ..models.journal_points import JournalProcessedMark
from ..models.points import PointTransaction


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
        to_date = for_date.replace(day=for_date.day + 1)

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

        for profile in profiles:
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
        url = f"{self.journal_base_url}/students/{student_workflow_id}/marks/by-date-range"
        params = {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        items: Iterable[Mapping[str, Any]] = payload.get("items", [])

        result: list[JournalMark] = []
        for item in items:
            try:
                issued_raw = item.get("Issued")
                issued_dt = None
                if issued_raw:
                    issued_dt = datetime.fromisoformat(str(issued_raw))

                lesson_date_raw = item.get("LessonDate")
                lesson_dt = None
                if lesson_date_raw:
                    lesson_dt = date.fromisoformat(str(lesson_date_raw))

                jm = JournalMark(
                    student_workflow_id=int(item["StudentWorkFlowId"]),
                    mark_set_id=int(item["MarkSetId"]),
                    education_task_id=int(item["EducationTaskId"]),
                    version=int(item.get("Version", 0)),
                    value=int(item["Value"]),
                    issued=issued_dt,
                    lesson_date=lesson_dt,
                )
                result.append(jm)
            except Exception:
                # Если какая‑то строка поломана, просто пропускаем её
                continue

        return result

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

