"""0004_vector_embeddings_and_retrieval

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-31 18:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create record_embeddings table
    op.create_table(
        'record_embeddings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('part_number', sa.String(length=50), nullable=True),
        sa.Column('ecn_number', sa.String(length=50), nullable=True),
        sa.Column('model_code', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('embedding_vector', sa.JSON(), nullable=False),
        sa.Column('dimension', sa.Integer(), server_default='384', nullable=False),
        sa.Column('model_name', sa.String(length=100), server_default='Qwen3-Embedding-0.6B', nullable=False),
        sa.Column('metadata_payload', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_record_embeddings_entity_type', 'record_embeddings', ['entity_type'])
    op.create_index('ix_record_embeddings_entity_id', 'record_embeddings', ['entity_id'])
    op.create_index('ix_record_embeddings_part_number', 'record_embeddings', ['part_number'])
    op.create_index('ix_record_embeddings_ecn_number', 'record_embeddings', ['ecn_number'])
    op.create_index('ix_record_embeddings_model_code', 'record_embeddings', ['model_code'])
    op.create_index('ix_record_embeddings_category', 'record_embeddings', ['category'])
    op.create_index('ix_record_embeddings_lookup', 'record_embeddings', ['entity_type', 'entity_id', 'chunk_index'])
    op.create_index('ix_record_embeddings_identifiers', 'record_embeddings', ['part_number', 'model_code', 'category'])


def downgrade() -> None:
    op.drop_table('record_embeddings')
