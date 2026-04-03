from datetime import date, timedelta
import os

from apscheduler.schedulers.background import BackgroundScheduler

from .extensions import db
from .services.grade_points_service import GradePointsService
from .services.month_rollover_service import rollover_all_active_students


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
    - Месячная задача в 02:00 первого числа: сначала доначисление оценок журнала за прошлый месяц,
      затем перенос current_month_points всех студентов в total_points и SOM и обнуление месяца.

    Часовой пояс: SCHEDULER_TIMEZONE (по умолчанию Europe/Moscow), чтобы «3 ночи»
    совпадало с локальным временем, а не UTC.
    """
    tz = os.getenv("SCHEDULER_TIMEZONE", "Europe/Moscow")
    scheduler = BackgroundScheduler(timezone=tz)

    @scheduler.scheduled_job("cron", hour=3, minute=0)
    def daily_job():
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            try:
                service = _create_service()
                processed = service.process_daily_scores(for_date=yesterday)
                app.logger.info(
                    "[scheduler] Daily journal points: processed=%s for %s",
                    processed,
                    yesterday,
                )
            except Exception:
                app.logger.exception("[scheduler] Daily journal points job failed")

    @scheduler.scheduled_job("cron", day=3, hour=14, minute=10)
    def monthly_finalize_job():
        with app.app_context():
            today = date.today()
            if today.month == 1:
                prev_year = today.year - 1
                prev_month = 12
            else:
                prev_year = today.year
                prev_month = today.month - 1
            try:
                service = _create_service()
                processed = service.finalize_month(year=prev_year, month=prev_month)
                app.logger.info(
                    "[scheduler] Monthly journal finalize: processed=%s for %s-%02d",
                    processed,
                    prev_year,
                    prev_month,
                )
            except Exception:
                app.logger.exception("[scheduler] Monthly journal finalize job failed")

            try:
                changed, moved = rollover_all_active_students(as_of=today)
                app.logger.info(
                    "[scheduler] Month rollover: profiles_touched=%s month_points_closed_sum=%s",
                    changed,
                    moved,
                )
            except Exception:
                app.logger.exception("[scheduler] Month rollover to total_points failed")

    scheduler.start()

