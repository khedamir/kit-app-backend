from datetime import datetime, date

from ..extensions import db


class JournalProcessedMark(db.Model):
    """
    Оценка из сетевого журнала, которая уже была конвертирована в баллы.

    Благодаря этой таблице мы:
      - не дублируем начисление баллов за одну и ту же оценку;
      - можем анализировать историю автоматически начисленных баллов.
    """

    __tablename__ = "journal_processed_marks"

    id = db.Column(db.Integer, primary_key=True)

    # Связь с профилем студента в нашей системе
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Id студента в базе сетевого журнала (StudentWorkFlow.Id)
    student_workflow_id = db.Column(db.Integer, nullable=False, index=True)

    # Ключи оценки из базы журнала
    mark_set_id = db.Column(db.Integer, nullable=False)
    education_task_id = db.Column(db.Integer, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=0)

    # Данные по оценке
    mark_value = db.Column(db.Integer, nullable=False)
    issued_at = db.Column(db.DateTime, nullable=True)  # Mark.Issued
    lesson_date = db.Column(db.Date, nullable=True)  # GradebookLesson.Date

    # Начисленные баллы по нашей формуле (могут быть отрицательными)
    points = db.Column(db.Integer, nullable=False)

    # Привязка к транзакции баллов (если создаём PointTransaction)
    transaction_id = db.Column(
        db.Integer,
        db.ForeignKey("point_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Месяц, за который учтён балл (первое число месяца)
    month_start = db.Column(db.Date, nullable=False)

    processed_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_workflow_id",
            "mark_set_id",
            "education_task_id",
            "version",
            name="uq_journal_mark_once",
        ),
    )

    student = db.relationship("StudentProfile", backref="journal_processed_marks")
    transaction = db.relationship("PointTransaction", backref="journal_mark", uselist=False)

