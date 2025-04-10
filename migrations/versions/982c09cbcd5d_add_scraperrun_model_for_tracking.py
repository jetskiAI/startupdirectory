"""Add ScraperRun model for tracking

Revision ID: 982c09cbcd5d
Revises: b0052d6ae3d3
Create Date: 2025-04-10 00:41:18.575035

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '982c09cbcd5d'
down_revision = 'b0052d6ae3d3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('scraper_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('start_time', sa.DateTime(), nullable=True),
    sa.Column('end_time', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('startups_added', sa.Integer(), nullable=True),
    sa.Column('startups_updated', sa.Integer(), nullable=True),
    sa.Column('startups_unchanged', sa.Integer(), nullable=True),
    sa.Column('total_processed', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('scraper_runs')
    # ### end Alembic commands ###
