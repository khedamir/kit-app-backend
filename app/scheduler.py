from datetime import date, timedelta
import os

from apscheduler.schedulers.background import BackgroundScheduler

from .extensions import db
from .services.grade_points_service import GradePointsService
from .services.journal_points_run_log import (
    append_journal_points_run_log,
    append_journal_points_run_log_exception,
)


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

    - Ежедневная задача в 20:00 (временно для теста; обычно 03:00): обработка за вчера.
    - Месячная задача в 02:00 первого числа месяца: финализация прошлого месяца.

    Часовой пояс: SCHEDULER_TIMEZONE (по умолчанию Europe/Moscow), чтобы «3 ночи»
    совпадало с локальным временем, а не UTC.
    """
    tz = os.getenv("SCHEDULER_TIMEZONE", "Europe/Moscow")
    scheduler = BackgroundScheduler(timezone=tz)

    @scheduler.scheduled_job("cron", hour=20, minute=0)
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
                append_journal_points_run_log(
                    app,
                    f"daily OK for_date={yesterday.isoformat()} processed={processed}",
                )
            except Exception as e:
                app.logger.exception("[scheduler] Daily journal points job failed")
                append_journal_points_run_log_exception(
                    app,
                    f"daily FAIL for_date={yesterday.isoformat()}",
                    e,
                )

    @scheduler.scheduled_job("cron", day=1, hour=2, minute=0)
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
                append_journal_points_run_log(
                    app,
                    f"monthly OK year={prev_year} month={prev_month:02d} processed={processed}",
                )
            except Exception as e:
                app.logger.exception("[scheduler] Monthly journal finalize job failed")
                append_journal_points_run_log_exception(
                    app,
                    f"monthly FAIL year={prev_year} month={prev_month:02d}",
                    e,
                )

    scheduler.start()

