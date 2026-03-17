from datetime import date, timedelta
import os

from apscheduler.schedulers.background import BackgroundScheduler

from .extensions import db
from .services.grade_points_service import GradePointsService


def _get_journal_base_url() -> str:
    """
    Базовый URL сервиса localdb.py.
    Ожидается переменная окружения JOURNAL_API_BASE_URL,
    например: http://localhost:5001
    """
    return os.getenv("JOURNAL_API_BASE_URL", "http://localhost:5000")


def _create_service() -> GradePointsService:
    base_url = _get_journal_base_url()
    return GradePointsService(journal_base_url=base_url, session=db.session)


def init_scheduler(app):
    """
    Инициализация фонового планировщика задач.

    - Ежедневная задача в 03:00: обработка оценок за вчерашний день.
    - Месячная задача в 02:00 первого числа месяца: финализация прошлого месяца.
    """
    scheduler = BackgroundScheduler(timezone="UTC")

    @scheduler.scheduled_job("cron", hour=3, minute=0)
    def daily_job():
        with app.app_context():
            service = _create_service()
            today = date.today()
            yesterday = today - timedelta(days=1)
            processed = service.process_daily_scores(for_date=yesterday)
            app.logger.info(f"[scheduler] Daily journal points: processed={processed} for {yesterday}")

    @scheduler.scheduled_job("cron", day=1, hour=2, minute=0)
    def monthly_finalize_job():
        with app.app_context():
            service = _create_service()
            today = date.today()
            # Финализируем предыдущий месяц
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

            processed = service.finalize_month(year=year, month=month)
            app.logger.info(
                f"[scheduler] Monthly journal finalize: processed={processed} for {year}-{month:02d}"
            )

    scheduler.start()

