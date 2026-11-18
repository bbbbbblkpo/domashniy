"""Require users created/reset by the owner to change temporary passwords."""
from alembic import op
import sqlalchemy as sa

revision = "0002_temporary_password"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column("users", "must_change_password")
