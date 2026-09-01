"""0003_ideathon_domain_and_taxonomy

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-31 18:14:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. idea_clusters
    op.create_table(
        'idea_clusters',
        sa.Column('cluster_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('primary_part_id', sa.String(length=36), nullable=True),
        sa.Column('primary_subsystem_id', sa.String(length=36), nullable=True),
        sa.Column('primary_category', sa.String(length=50), nullable=False, server_default='OTHER_VAVE'),
        sa.Column('idea_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['primary_part_id'], ['parts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['primary_subsystem_id'], ['subsystems.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_idea_clusters_cluster_code'), 'idea_clusters', ['cluster_code'], unique=True)

    # 2. idea_submissions
    op.create_table(
        'idea_submissions',
        sa.Column('submission_code', sa.String(length=50), nullable=False),
        sa.Column('raw_title', sa.String(length=255), nullable=False),
        sa.Column('raw_description', sa.Text(), nullable=False),
        sa.Column('submitter_employee_id', sa.String(length=50), nullable=True),
        sa.Column('submitter_plant_code', sa.String(length=50), nullable=True),
        sa.Column('raw_claimed_saving_per_veh', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('decomposed_problem', sa.Text(), nullable=True),
        sa.Column('decomposed_solution', sa.Text(), nullable=True),
        sa.Column('decomposed_expected_benefit', sa.Text(), nullable=True),
        sa.Column('target_vehicle_id', sa.String(length=36), nullable=True),
        sa.Column('target_model_id', sa.String(length=36), nullable=True),
        sa.Column('target_variant_id', sa.String(length=36), nullable=True),
        sa.Column('target_subsystem_id', sa.String(length=36), nullable=True),
        sa.Column('target_assembly_id', sa.String(length=36), nullable=True),
        sa.Column('target_component_id', sa.String(length=36), nullable=True),
        sa.Column('target_part_id', sa.String(length=36), nullable=True),
        sa.Column('extracted_part_number', sa.String(length=100), nullable=True),
        sa.Column('extracted_part_name', sa.String(length=200), nullable=True),
        sa.Column('extracted_synonyms', sa.JSON(), nullable=True),
        sa.Column('is_bom_linked', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('cost_reduction_category', sa.String(length=50), nullable=False, server_default='OTHER_VAVE'),
        sa.Column('decision_state', sa.String(length=50), nullable=False, server_default='SUBMITTED'),
        sa.Column('evidence_state', sa.String(length=50), nullable=False, server_default='NOT_EVALUATED'),
        sa.Column('data_quality', sa.String(length=50), nullable=False, server_default='COMPLETE'),
        sa.Column('extraction_confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('part_match_confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('verified_saving_per_veh', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('cluster_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['target_vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_model_id'], ['vehicle_models.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_variant_id'], ['vehicle_variants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_subsystem_id'], ['subsystems.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_assembly_id'], ['assemblies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_component_id'], ['components.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_part_id'], ['parts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cluster_id'], ['idea_clusters.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_idea_submissions_submission_code'), 'idea_submissions', ['submission_code'], unique=True)
    op.create_index(op.f('ix_idea_submissions_decision_state'), 'idea_submissions', ['decision_state'])
    op.create_index(op.f('ix_idea_submissions_evidence_state'), 'idea_submissions', ['evidence_state'])
    op.create_index(op.f('ix_idea_submissions_data_quality'), 'idea_submissions', ['data_quality'])
    op.create_index(op.f('ix_idea_submissions_extracted_part_number'), 'idea_submissions', ['extracted_part_number'])

    # 3. idea_duplicate_links
    op.create_table(
        'idea_duplicate_links',
        sa.Column('source_idea_id', sa.String(length=36), nullable=False),
        sa.Column('target_idea_id', sa.String(length=36), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('duplicate_type', sa.String(length=50), nullable=False, server_default='NEAR_DUPLICATE_SAME_VEHICLE'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['source_idea_id'], ['idea_submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_idea_id'], ['idea_submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_idea_id', 'target_idea_id', name='uq_idea_duplicate_pair')
    )


def downgrade() -> None:
    op.drop_table('idea_duplicate_links')
    op.drop_table('idea_submissions')
    op.drop_table('idea_clusters')
