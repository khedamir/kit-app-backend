"""add journal_processed_marks table

Revision ID: c1d2e3f4e6a7
Revises: bfaaed33847b
Create Date: 2026-03-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d2e3f4e6a7"
down_revision = "bfaaed33847b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "journal_processed_marks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("student_workflow_id", sa.Integer(), nullable=False),
        sa.Column("mark_set_id", sa.Integer(), nullable=False),
        sa.Column("education_task_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mark_value", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("lesson_date", sa.Date(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("month_start", sa.Date(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["point_transactions.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_journal_processed_marks_student_id",
        "journal_processed_marks",
        ["student_id"],
    )
    op.create_index(
        "ix_journal_processed_marks_student_workflow_id",
        "journal_processed_marks",
        ["student_workflow_id"],
    )
    op.create_index(
        "ix_journal_processed_marks_processed_at",
        "journal_processed_marks",
        ["processed_at"],
    )

    op.create_unique_constraint(
        "uq_journal_mark_once",
        "journal_processed_marks",
        ["student_workflow_id", "mark_set_id", "education_task_id", "version"],
    )


def downgrade():
    op.drop_constraint("uq_journal_mark_once", "journal_processed_marks", type_="unique")
    op.drop_index("ix_journal_processed_marks_processed_at", table_name="journal_processed_marks")
    op.drop_index("ix_journal_processed_marks_student_workflow_id", table_name="journal_processed_marks")
    op.drop_index("ix_journal_processed_marks_student_id", table_name="journal_processed_marks")
    op.drop_table("journal_processed_marks")

