"""Projects to chat fkey as big integer

Revision ID: e594db21916e
Revises: 6a166fd911d6
Create Date: 2021-06-14 22:28:05.427747

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e594db21916e'
down_revision = '6a166fd911d6'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('projects', 'chat_id', existing_type=sa.Integer, type_=sa.BigInteger)


def downgrade():
    op.alter_column('projects', 'chat_id', existing_type=sa.BigInteger, type_=sa.Integer)
