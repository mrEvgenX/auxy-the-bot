"""Change users and chats ids to big integer

Revision ID: 6a166fd911d6
Revises: 5ccb02f48d7b
Create Date: 2021-06-14 13:15:12.092006

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a166fd911d6'
down_revision = '5ccb02f48d7b'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('users', 'id', existing_type=sa.Integer, type_=sa.BigInteger)
    op.alter_column('chats', 'id', existing_type=sa.Integer, type_=sa.BigInteger)


def downgrade():
    op.alter_column('users', 'id', existing_type=sa.BigInteger, type_=sa.Integer)
    op.alter_column('chats', 'id', existing_type=sa.BigInteger, type_=sa.Integer)
