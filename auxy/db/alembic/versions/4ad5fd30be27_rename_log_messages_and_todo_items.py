"""Rename log messages and todo items

Revision ID: 4ad5fd30be27
Revises: 45e7f823087b
Create Date: 2021-06-12 14:49:01.675514

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4ad5fd30be27'
down_revision = '45e7f823087b'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('item_in_list_item_id_fkey', 'item_in_list', type_='foreignkey')
    op.drop_constraint('todo_item_log_messages_todo_item_id_fkey', 'todo_item_log_messages', type_='foreignkey')
    op.alter_column('todo_item_log_messages', 'todo_item_id', new_column_name='item_id')
    op.rename_table('todo_items', 'items')
    op.rename_table('todo_item_log_messages', 'item_notes')
    op.create_foreign_key('item_in_list_item_id_fkey', 'item_in_list', 'items', ['item_id'], ['id'])
    op.create_foreign_key('item_notes_item_id_fkey', 'item_notes', 'items', ['item_id'], ['id'])


def downgrade():
    op.drop_constraint('item_notes_item_id_fkey', 'item_notes', type_='foreignkey')
    op.drop_constraint('item_in_list_item_id_fkey', 'item_in_list', type_='foreignkey')
    op.rename_table('item_notes', 'todo_item_log_messages')
    op.rename_table('items', 'todo_items')
    op.alter_column('todo_item_log_messages', 'item_id', new_column_name='todo_item_id')
    op.create_foreign_key('todo_item_log_messages_todo_item_id_fkey', 'todo_item_log_messages', 'todo_items', ['todo_item_id'], ['id'])
    op.create_foreign_key('item_in_list_item_id_fkey', 'item_in_list', 'todo_items', ['item_id'], ['id'])
