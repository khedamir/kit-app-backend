"""Add month points tracking to student_profiles

Revision ID: a1b2c3d4e5f6
Revises: 5e495fc9555c
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '5e495fc9555c'
branch_labels = None
depends_on = None


def upgrade():
    # Баллы за текущий месяц и дата начала месяца
    op.add_column(
        'student_profiles',
        sa.Column('current_month_points', sa.Integer(), nullable=True),
    )
    op.add_column(
        'student_profiles',
        sa.Column('current_month_started_at', sa.Date(), nullable=True),
    )

    # Для существующих записей выставляем 0
    op.execute(
        "UPDATE student_profiles SET current_month_points = 0 WHERE current_month_points IS NULL"
    )
    op.alter_column('student_profiles', 'current_month_points', nullable=False)


def downgrade():
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.drop_column('current_month_started_at')
        batch_op.drop_column('current_month_points')

