"""Rename daily todo items

Revision ID: 8f85d2a3d6a4
Revises: 4ad5fd30be27
Create Date: 2021-06-12 22:46:35.853525

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8f85d2a3d6a4'
down_revision = '4ad5fd30be27'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('item_in_list_list_id_fkey', 'item_in_list', type_='foreignkey')
    op.rename_table('daily_todo_lists', 'items_lists')
    op.create_foreign_key('item_in_list_list_id_fkey', 'item_in_list', 'items_lists', ['list_id'], ['id'])


def downgrade():
    op.drop_constraint('item_in_list_list_id_fkey', 'item_in_list', type_='foreignkey')
    op.rename_table('items_lists', 'daily_todo_lists')
    op.create_foreign_key('item_in_list_list_id_fkey', 'item_in_list', 'daily_todo_lists', ['list_id'], ['id'])
