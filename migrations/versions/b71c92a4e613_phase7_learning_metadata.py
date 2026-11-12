"""Additive Phase 7 exercise objectives and lesson-level video review metadata."""
from alembic import op
import sqlalchemy as sa

revision = "b71c92a4e613"
down_revision = "a3d91d2e4c10"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("course_exercise"):
        cols = {c["name"] for c in inspector.get_columns("course_exercise")}
        if "learning_objective_fr" not in cols:
            op.add_column("course_exercise", sa.Column("learning_objective_fr", sa.String(400), nullable=False, server_default=""))
    if inspector.has_table("video_resource"):
        cols = {c["name"] for c in inspector.get_columns("video_resource")}
        if "verification_status" not in cols:
            op.add_column("video_resource", sa.Column("verification_status", sa.String(24), nullable=False, server_default="pending"))
            op.execute("UPDATE video_resource SET verification_status = CASE WHEN verified = 1 THEN 'verified' ELSE 'pending' END")
        if "verified_at" not in cols:
            op.add_column("video_resource", sa.Column("verified_at", sa.DateTime(), nullable=True))
    if inspector.has_table("video_metadata"):
        cols = {c["name"] for c in inspector.get_columns("video_metadata")}
        if "lesson_id" not in cols:
            with op.batch_alter_table("video_metadata") as batch:
                batch.add_column(sa.Column("lesson_id", sa.Integer(), nullable=True))
                batch.create_foreign_key("fk_video_metadata_lesson_id", "curriculum_lesson", ["lesson_id"], ["id"], ondelete="SET NULL")
    if inspector.has_table("question_metadata"):
        cols = {c["name"] for c in inspector.get_columns("question_metadata")}
        if "lesson_id" not in cols:
            with op.batch_alter_table("question_metadata") as batch:
                batch.add_column(sa.Column("lesson_id", sa.Integer(), nullable=True))
                batch.create_foreign_key("fk_question_metadata_lesson_id", "curriculum_lesson", ["lesson_id"], ["id"], ondelete="SET NULL")


def downgrade():
    raise RuntimeError("This additive content migration is intentionally irreversible to preserve existing records.")
