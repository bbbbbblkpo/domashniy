"""Initial schema."""
from alembic import op
from backend.db import Base
from backend import models

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind=op.get_bind();Base.metadata.create_all(bind=bind)
def downgrade():
    bind=op.get_bind();Base.metadata.drop_all(bind=bind)
