"""Initial migration with Archive.org compliant models

Revision ID: 001_initial_archive_models
Revises: 
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_archive_models'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create archive_items table
    op.create_table('archive_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=255), nullable=False),
        sa.Column('created', sa.Integer(), nullable=True),
        sa.Column('d1', sa.String(length=255), nullable=True),
        sa.Column('d2', sa.String(length=255), nullable=True),
        sa.Column('dir', sa.String(length=500), nullable=True),
        sa.Column('files_count', sa.Integer(), nullable=True),
        sa.Column('item_last_updated', sa.Integer(), nullable=True),
        sa.Column('item_size', sa.BigInteger(), nullable=True),
        sa.Column('server', sa.String(length=255), nullable=True),
        sa.Column('uniq', sa.BigInteger(), nullable=True),
        sa.Column('workable_servers', sa.Text(), nullable=True),
        sa.Column('item_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_backed_up', sa.Boolean(), nullable=True),
        sa.Column('backup_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_archive_items_identifier'), 'archive_items', ['identifier'], unique=True)

    # Create archive_files table
    op.create_table('archive_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('archive_item_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('format', sa.String(length=100), nullable=True),
        sa.Column('mtime', sa.String(length=50), nullable=True),
        sa.Column('size', sa.String(length=50), nullable=True),
        sa.Column('md5', sa.String(length=64), nullable=True),
        sa.Column('crc32', sa.String(length=50), nullable=True),
        sa.Column('sha1', sa.String(length=64), nullable=True),
        sa.Column('length', sa.String(length=50), nullable=True),
        sa.Column('height', sa.String(length=50), nullable=True),
        sa.Column('width', sa.String(length=50), nullable=True),
        sa.Column('track', sa.String(length=50), nullable=True),
        sa.Column('album', sa.String(length=500), nullable=True),
        sa.Column('artist', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('bitrate', sa.String(length=50), nullable=True),
        sa.Column('creator', sa.String(length=500), nullable=True),
        sa.Column('private', sa.Boolean(), nullable=True),
        sa.Column('rotation', sa.String(length=50), nullable=True),
        sa.Column('summation', sa.String(length=50), nullable=True),
        sa.Column('local_path', sa.String(length=1000), nullable=True),
        sa.Column('is_downloaded', sa.Boolean(), nullable=True),
        sa.Column('download_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['archive_item_id'], ['archive_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create backup_jobs table
    op.create_table('backup_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=255), nullable=False),
        sa.Column('job_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('backup_jobs')
    op.drop_table('archive_files')
    op.drop_index(op.f('ix_archive_items_identifier'), table_name='archive_items')
    op.drop_table('archive_items')