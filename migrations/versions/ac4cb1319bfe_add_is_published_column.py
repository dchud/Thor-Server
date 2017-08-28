"""add is_published column

Revision ID: ac4cb1319bfe
Revises: e8c82318b73e
Create Date: 2017-08-10 17:24:05.195111

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ac4cb1319bfe'
down_revision = 'e8c82318b73e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('experiments', sa.Column('is_published', sa.Boolean(),
                                           server_default='FALSE',
                                           nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('experiments', 'is_published')
    # ### end Alembic commands ###