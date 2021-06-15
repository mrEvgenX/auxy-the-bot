"""Projects to user fkey as big integer

Revision ID: 869c096b3a3f
Revises: e594db21916e
Create Date: 2021-06-15 10:07:04.443189

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '869c096b3a3f'
down_revision = 'e594db21916e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('projects', 'owner_user_id', existing_type=sa.Integer, type_=sa.BigInteger)


def downgrade():
    op.alter_column('projects', 'owner_user_id', existing_type=sa.BigInteger, type_=sa.Integer)
