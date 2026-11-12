"""Add a non-destructive learning objective field to question metadata."""
from alembic import op
import sqlalchemy as sa

revision = "a3d91d2e4c10"
down_revision = "74712e4675d0"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("question_metadata"):
        columns = {column["name"] for column in inspector.get_columns("question_metadata")}
        if "learning_objective" not in columns:
            op.add_column(
                "question_metadata",
                sa.Column("learning_objective", sa.String(length=400), nullable=False, server_default=""),
            )


def downgrade():
    raise RuntimeError("This additive data migration is intentionally irreversible to preserve existing content metadata.")
