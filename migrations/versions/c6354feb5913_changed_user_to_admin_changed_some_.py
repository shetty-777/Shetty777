"""Changed user to admin, changed some names to follow snake_case

Revision ID: c6354feb5913
Revises: 9ae6fccdc7c9
Create Date: 2025-04-20 11:17:33.487654

"""
"""Rename tables and columns for consistency"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c6354feb5913'
down_revision = '9ae6fccdc7c9'
branch_labels = None
depends_on = None

def upgrade():
    # Rename table 'user' to 'admin'
    op.rename_table('user', 'admin')

    # Rename columns
    with op.batch_alter_table('allusers') as batch_op:
        batch_op.alter_column('user_role', new_column_name='user_role')

    with op.batch_alter_table('subscriber') as batch_op:
        batch_op.alter_column('emailid', new_column_name='email_id')

    with op.batch_alter_table('post') as batch_op:
        batch_op.alter_column('htmlfile', new_column_name='html_file')

    with op.batch_alter_table('comment') as batch_op:
        batch_op.alter_column('commentor', new_column_name='commentator')


def downgrade():
    # Revert table rename
    op.rename_table('admin', 'user')

    # Revert column renames
    with op.batch_alter_table('allusers') as batch_op:
        batch_op.alter_column('user_role', new_column_name='user_role')

    with op.batch_alter_table('subscriber') as batch_op:
        batch_op.alter_column('email_id', new_column_name='emailid')

    with op.batch_alter_table('post') as batch_op:
        batch_op.alter_column('html_file', new_column_name='htmlfile')

    with op.batch_alter_table('comment') as batch_op:
        batch_op.alter_column('commentator', new_column_name='commentor')

