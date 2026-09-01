"""Initial schema and PostgreSQL extensions

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-31 17:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions if on PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("role", sa.String(length=50), nullable=False, default="ENGINEER"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 3. Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("workflow_id", sa.String(length=100), nullable=True),
        sa.Column("decision", sa.String(length=50), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("evidence_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_workflow_id"), "audit_logs", ["workflow_id"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("users")
