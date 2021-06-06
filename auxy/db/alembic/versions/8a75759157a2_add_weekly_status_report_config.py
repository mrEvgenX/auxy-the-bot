"""Add weekly status report config

Revision ID: 8a75759157a2
Revises: 8d2d343ae2c1
Create Date: 2021-06-06 14:56:59.404504

"""
from alembic import op
from auxy.db.models import BotSettings


# revision identifiers, used by Alembic.
revision = '8a75759157a2'
down_revision = '8d2d343ae2c1'
branch_labels = None
depends_on = None


def upgrade():
    # default configuration (before becoming highly configurable by user)
    op.bulk_insert(BotSettings.__table__, [
        {
            'section': 'weekly_status_report',
            'content': {

                'reminder_timings': [
                    {'weekday': 1, 'hour': 17, 'minute': 45, 'second': 0, 'microsecond': 0},
                ],
            }
        }
    ])


def downgrade():
    op.execute(f"delete from {BotSettings.__tablename__} where section='weekly_status_report'")
