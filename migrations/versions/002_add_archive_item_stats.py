"""Add ArchiveItemStats and ArchiveItemReview tables

Revision ID: 002_add_archive_item_stats
Revises: 001_initial_archive_models
Create Date: 2025-01-08 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_add_archive_item_stats'
down_revision = '001_initial_archive_models'
branch_labels = None
depends_on = None

def upgrade():
    # Create archive_item_stats table
    op.create_table('archive_item_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('archive_item_id', sa.Integer(), nullable=False),
        sa.Column('avg_rating', sa.Float(), nullable=True),
        sa.Column('num_reviews', sa.Integer(), nullable=True),
        sa.Column('stars_json', sa.Text(), nullable=True),
        sa.Column('downloads', sa.Integer(), nullable=True),
        sa.Column('downloads_week', sa.Integer(), nullable=True),
        sa.Column('downloads_month', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['archive_item_id'], ['archive_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create archive_item_reviews table
    op.create_table('archive_item_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('archive_item_id', sa.Integer(), nullable=False),
        sa.Column('reviewbody', sa.Text(), nullable=True),
        sa.Column('reviewtitle', sa.String(500), nullable=True),
        sa.Column('reviewer', sa.String(255), nullable=True),
        sa.Column('reviewdate', sa.String(50), nullable=True),
        sa.Column('createdate', sa.String(50), nullable=True),
        sa.Column('stars', sa.String(10), nullable=True),
        sa.Column('reviewer_itemname', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['archive_item_id'], ['archive_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    # Drop tables in reverse order
    op.drop_table('archive_item_reviews')
    op.drop_table('archive_item_stats') 