"""
Текстовый журнал запусков начисления баллов за оценки из сетевого журнала.

Удобно смотреть на сервере после деплоя (tail -f, скачать файл).

Переменные окружения:
  JOURNAL_POINTS_LOG_FILE — абсолютный или относительный путь к файлу (переопределяет путь по умолчанию).
  JOURNAL_POINTS_LOG_DISABLE=1 — не писать в файл (только логи приложения).
"""

from __future__ import annotations

import os
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def _log_file_path(app: Flask) -> str | None:
    if os.getenv("JOURNAL_POINTS_LOG_DISABLE", "").lower() in ("1", "true", "yes"):
        return None
    env = os.getenv("JOURNAL_POINTS_LOG_FILE", "").strip()
    if env:
        return os.path.abspath(env)
    default_dir = os.path.abspath(os.path.join(app.root_path, "..", "logs"))
    return os.path.join(default_dir, "journal_points.log")


def append_journal_points_run_log(app: Flask, message: str) -> None:
    """Добавить строку (с UTC‑временем) в текстовый журнал, если запись не отключена."""
    path = _log_file_path(app)
    if not path:
        return
    line = f"{datetime.now(timezone.utc).isoformat()} {message}\n"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        app.logger.exception("[journal_points_run_log] Не удалось записать в %s", path)


def append_journal_points_run_log_exception(app: Flask, header: str, exc: BaseException) -> None:
    """Записать заголовок и полный traceback в тот же файл."""
    tb = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    append_journal_points_run_log(app, f"{header}\n{tb}")
