"""add shop tables

Revision ID: f2b4b1a9c8d0
Revises: c1d2e3f4e6a7
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2b4b1a9c8d0"
down_revision = "c1d2e3f4e6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shop_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_som", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photos", sa.JSON(), nullable=False),
        sa.Column("sizes", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "shop_purchase_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("selected_size", sa.String(length=32), nullable=True),
        sa.Column("total_price_som", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("admin_comment", sa.String(length=500), nullable=True),
        sa.Column("approved_pickup_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["shop_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_admin_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_shop_purchase_requests_student_id", "shop_purchase_requests", ["student_id"])
    op.create_index("ix_shop_purchase_requests_item_id", "shop_purchase_requests", ["item_id"])
    op.create_index("ix_shop_purchase_requests_status", "shop_purchase_requests", ["status"])


def downgrade():
    op.drop_index("ix_shop_purchase_requests_status", table_name="shop_purchase_requests")
    op.drop_index("ix_shop_purchase_requests_item_id", table_name="shop_purchase_requests")
    op.drop_index("ix_shop_purchase_requests_student_id", table_name="shop_purchase_requests")
    op.drop_table("shop_purchase_requests")
    op.drop_table("shop_items")
