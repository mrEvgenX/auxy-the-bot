"""Move to period buckets

Revision ID: e411f80b8ed5
Revises: 8f85d2a3d6a4
Create Date: 2021-06-13 20:31:26.112636

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e411f80b8ed5'
down_revision = '8f85d2a3d6a4'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('daily_todo_lists_user_id_fkey', 'items_lists', type_='foreignkey')
    op.drop_column('items_lists', 'user_id')
    op.drop_constraint('todo_items_user_id_fkey', 'items', type_='foreignkey')
    op.drop_column('items', 'user_id')
    op.add_column('items_lists', sa.Column('period_bucket_key', sa.String(length=32), nullable=True))
    # sa.Column(
    #     'period_bucket_mode',
    #     sa.Enum('daily', 'weekly', 'monthly', 'yearly', 'perpetual', name='periodbucketmodes'),
    #     nullable=True
    # )
    op.add_column('projects', sa.Column('period_bucket_mode', sa.String(length=32), nullable=True))
    op.drop_constraint('daily_todo_lists_project_id_for_day_key', 'items_lists', type_='unique')
    op.create_unique_constraint('items_lists_project_id_period_bucket_key_key', 'items_lists',
                                ['project_id', 'period_bucket_key'])
    op.execute("UPDATE items_lists SET period_bucket_key = 'day-' || for_day::varchar;")


def downgrade():
    op.drop_column('projects', 'period_bucket_mode')
    op.drop_column('items_lists', 'period_bucket_key')
    op.add_column('items_lists', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('items', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))

    op.create_foreign_key('daily_todo_lists_user_id_fkey', 'items_lists', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('todo_items_user_id_fkey', 'items', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    # op.drop_constraint('items_lists_project_id_for_day_key', 'items_lists', type_='unique')
    op.create_unique_constraint('daily_todo_lists_project_id_for_day_key', 'items_lists', ['project_id', 'for_day'])
