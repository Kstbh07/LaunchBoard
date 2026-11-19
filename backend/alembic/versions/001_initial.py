"""Initial schema - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False, index=True),
        sa.Column('company', sa.String(300), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('location', sa.String(300), nullable=True),
        sa.Column('employment_type', sa.String(50), nullable=True),
        sa.Column('experience_level', sa.String(50), nullable=True),
        sa.Column('application_url', sa.String(2000), nullable=False),
        sa.Column('source_name', sa.String(200), nullable=False),
        sa.Column('source_url', sa.String(2000), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', index=True),
        sa.Column('role_category', sa.String(100), nullable=True, index=True),
        sa.Column('skills', postgresql.JSON, server_default='[]'),
        sa.Column('is_remote', sa.Boolean, server_default='false', index=True),
        sa.Column('fingerprint', sa.String(64), unique=True, index=True),
        sa.Column('city', sa.String(200), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('classification_confidence', sa.Float, nullable=True),
        sa.Column('classification_status', sa.String(20), server_default='pending'),
    )
    op.create_index('ix_jobs_company_title_location', 'jobs', ['company', 'title', 'location'])
    op.create_index('ix_jobs_status_role', 'jobs', ['status', 'role_category'])

    # Job sources table
    op.create_table(
        'job_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_name', sa.String(200), nullable=False),
        sa.Column('source_url', sa.String(2000), nullable=True),
        sa.Column('source_job_id', sa.String(500), nullable=True),
        sa.Column('application_url', sa.String(2000), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_primary', sa.Boolean, server_default='false'),
    )
    op.create_index('ix_job_sources_source', 'job_sources', ['source_name', 'source_job_id'], unique=True)

    # Classifications table
    op.create_table(
        'classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('role_category', sa.String(100), nullable=True),
        sa.Column('city', sa.String(200), nullable=True),
        sa.Column('skills', postgresql.JSON, server_default='[]'),
        sa.Column('experience_level', sa.String(50), nullable=True),
        sa.Column('employment_type', sa.String(50), nullable=True),
        sa.Column('is_remote', sa.Boolean, nullable=True),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('raw_response', sa.Text, nullable=True),
        sa.Column('input_tokens', sa.Integer, nullable=True),
        sa.Column('output_tokens', sa.Integer, nullable=True),
        sa.Column('processing_time_ms', sa.Integer, nullable=True),
        sa.Column('classified_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(20), server_default='success'),
    )

    # Collection runs table
    op.create_table(
        'collection_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), server_default='running'),
        sa.Column('trigger_type', sa.String(20), nullable=False),
        sa.Column('total_fetched', sa.Integer, server_default='0'),
        sa.Column('total_new', sa.Integer, server_default='0'),
        sa.Column('total_updated', sa.Integer, server_default='0'),
        sa.Column('total_duplicates', sa.Integer, server_default='0'),
        sa.Column('total_classified', sa.Integer, server_default='0'),
        sa.Column('total_failed', sa.Integer, server_default='0'),
        sa.Column('total_errors', sa.Integer, server_default='0'),
        sa.Column('error_details', postgresql.JSON, server_default='[]'),
        sa.Column('source_results', postgresql.JSON, server_default='{}'),
    )

    # Classification usage table
    op.create_table(
        'classification_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('collection_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collection_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('total_input_tokens', sa.Integer, server_default='0'),
        sa.Column('total_output_tokens', sa.Integer, server_default='0'),
        sa.Column('total_requests', sa.Integer, server_default='0'),
        sa.Column('total_cost_usd', sa.Float, server_default='0.0'),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('pricing_config', postgresql.JSON, nullable=True),
    )

    # Source status table
    op.create_table(
        'source_status',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_name', sa.String(200), unique=True, nullable=False),
        sa.Column('is_enabled', sa.Boolean, server_default='true'),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_message', sa.Text, nullable=True),
        sa.Column('total_jobs_collected', sa.Integer, server_default='0'),
        sa.Column('total_runs', sa.Integer, server_default='0'),
        sa.Column('total_failures', sa.Integer, server_default='0'),
        sa.Column('consecutive_failures', sa.Integer, server_default='0'),
        sa.Column('config', postgresql.JSON, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('source_status')
    op.drop_table('classification_usage')
    op.drop_table('collection_runs')
    op.drop_table('classifications')
    op.drop_table('job_sources')
    op.drop_table('jobs')
