"""Additive Phase 4 baseline, generated from the legacy SQLite schema and frozen model metadata."""
from alembic import op
import sqlalchemy as sa

revision = '74712e4675d0'
down_revision = None
branch_labels = None
depends_on = None


def _upgrade_existing_exercise_table():
    inspector=sa.inspect(op.get_bind())
    if not inspector.has_table('course_exercise'): return
    existing={column['name'] for column in inspector.get_columns('course_exercise')}
    additions=[
        ('prompt_ar',sa.Text(),False,''),('solution_ar',sa.Text(),False,''),
        ('exercise_type',sa.String(length=20),False,'open'),('options_json',sa.Text(),False,'[]'),
        ('correct_answer',sa.String(length=500),True,None),('accepted_answers_json',sa.Text(),False,'[]'),
        ('feedback_fr',sa.Text(),False,''),('grading_guide_fr',sa.Text(),False,''),
    ]
    for name,type_,nullable,default in additions:
        if name not in existing:
            server_default=sa.text("'"+default+"'") if default is not None else None
            op.add_column('course_exercise',sa.Column(name,type_,nullable=nullable,server_default=server_default))


def upgrade():
    _upgrade_existing_exercise_table()
    if not sa.inspect(op.get_bind()).has_table('auth_throttle'):
        op.create_table('auth_throttle',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('window_started', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('key')
        )
    if not sa.inspect(op.get_bind()).has_table('curriculum_seed_state'):
        op.create_table('curriculum_seed_state',
        sa.Column('subject_slug', sa.String(length=100), nullable=False),
        sa.Column('seeded_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('subject_slug')
        )
    if not sa.inspect(op.get_bind()).has_table('curriculum_subject'):
        op.create_table('curriculum_subject',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=60), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
        )
    if not sa.inspect(op.get_bind()).has_table('question'):
        op.create_table('question',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=80), nullable=False),
        sa.Column('topic', sa.String(length=120), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('prompt_fr', sa.Text(), nullable=False),
        sa.Column('prompt_ar', sa.Text(), nullable=False),
        sa.Column('options_fr', sa.Text(), nullable=False),
        sa.Column('options_ar', sa.Text(), nullable=False),
        sa.Column('answer', sa.Integer(), nullable=False),
        sa.Column('explanation_fr', sa.Text(), nullable=False),
        sa.Column('explanation_ar', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('question', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_question_domain'), ['domain'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('user'):
        op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=40), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=15), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
        )
    if not sa.inspect(op.get_bind()).has_table('attempt'):
        op.create_table('attempt',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('attempt', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_attempt_user_id'), ['user_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('bookmark'):
        op.create_table('bookmark',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['question.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'question_id', name='uq_bookmark_user_question')
        )
        with op.batch_alter_table('bookmark', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_bookmark_question_id'), ['question_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_bookmark_user_id'), ['user_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('curriculum_module'):
        op.create_table('curriculum_module',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['subject_id'], ['curriculum_subject.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('curriculum_module', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_curriculum_module_subject_id'), ['subject_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('diagnostic'):
        op.create_table('diagnostic',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scores', sa.Text(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('diagnostic', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_diagnostic_user_id'), ['user_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('lesson_progress'):
        op.create_table('lesson_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_key', sa.String(length=100), nullable=False),
        sa.Column('evidence_count', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'lesson_key', name='uq_lesson_progress_user_lesson')
        )
        with op.batch_alter_table('lesson_progress', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_lesson_progress_user_id'), ['user_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('study_goal'):
        op.create_table('study_goal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('daily_minutes', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('study_goal', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_study_goal_user_id'), ['user_id'], unique=True)
    
    if not sa.inspect(op.get_bind()).has_table('study_session'):
        op.create_table('study_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=80), nullable=False),
        sa.Column('minutes', sa.Integer(), nullable=False),
        sa.Column('studied_on', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('study_session', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_study_session_studied_on'), ['studied_on'], unique=False)
            batch_op.create_index(batch_op.f('ix_study_session_user_id'), ['user_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('user_preference'):
        op.create_table('user_preference',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=2), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('user_preference', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_user_preference_user_id'), ['user_id'], unique=True)
    
    if not sa.inspect(op.get_bind()).has_table('video_resource'):
        op.create_table('video_resource',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('channel', sa.String(length=160), nullable=False),
        sa.Column('video_id', sa.String(length=11), nullable=False),
        sa.Column('language', sa.String(length=20), nullable=False),
        sa.Column('lesson_key', sa.String(length=100), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id')
        )
        with op.batch_alter_table('video_resource', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_video_resource_lesson_key'), ['lesson_key'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('curriculum_chapter'):
        op.create_table('curriculum_chapter',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['module_id'], ['curriculum_module.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('curriculum_chapter', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_curriculum_chapter_module_id'), ['module_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('video_watch'):
        op.create_table('video_watch',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('watched_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['video_id'], ['video_resource.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'video_id', name='uq_video_watch_user_video')
        )
        with op.batch_alter_table('video_watch', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_video_watch_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_video_watch_video_id'), ['video_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('curriculum_lesson'):
        op.create_table('curriculum_lesson',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('objectives_fr', sa.Text(), nullable=False),
        sa.Column('prerequisites_fr', sa.Text(), nullable=False),
        sa.Column('theory_fr', sa.Text(), nullable=False),
        sa.Column('theory_ar', sa.Text(), nullable=False),
        sa.Column('example_fr', sa.Text(), nullable=False),
        sa.Column('code_example', sa.Text(), nullable=False),
        sa.Column('exercise_fr', sa.Text(), nullable=False),
        sa.Column('solution_fr', sa.Text(), nullable=False),
        sa.Column('summary_fr', sa.Text(), nullable=False),
        sa.Column('revision_fr', sa.Text(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['curriculum_chapter.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('curriculum_lesson', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_curriculum_lesson_chapter_id'), ['chapter_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('question_metadata'):
        op.create_table('question_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=True),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['curriculum_chapter.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['question_id'], ['question.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('question_metadata', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_question_metadata_chapter_id'), ['chapter_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_question_metadata_question_id'), ['question_id'], unique=True)
    
    if not sa.inspect(op.get_bind()).has_table('video_metadata'):
        op.create_table('video_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['curriculum_chapter.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['video_id'], ['video_resource.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('video_metadata', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_video_metadata_chapter_id'), ['chapter_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_video_metadata_video_id'), ['video_id'], unique=True)
    
    if not sa.inspect(op.get_bind()).has_table('course_exercise'):
        op.create_table('course_exercise',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('prompt_fr', sa.Text(), nullable=False),
        sa.Column('prompt_ar', sa.Text(), nullable=False),
        sa.Column('solution_fr', sa.Text(), nullable=False),
        sa.Column('solution_ar', sa.Text(), nullable=False),
        sa.Column('exercise_type', sa.String(length=20), nullable=False),
        sa.Column('options_json', sa.Text(), nullable=False),
        sa.Column('correct_answer', sa.String(length=500), nullable=True),
        sa.Column('accepted_answers_json', sa.Text(), nullable=False),
        sa.Column('feedback_fr', sa.Text(), nullable=False),
        sa.Column('grading_guide_fr', sa.Text(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['lesson_id'], ['curriculum_lesson.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('course_exercise', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_course_exercise_lesson_id'), ['lesson_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('lesson_completion'):
        op.create_table('lesson_completion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lesson_id'], ['curriculum_lesson.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_lesson_completion_user_lesson')
        )
        with op.batch_alter_table('lesson_completion', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_lesson_completion_lesson_id'), ['lesson_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_lesson_completion_user_id'), ['user_id'], unique=False)
    
    if not sa.inspect(op.get_bind()).has_table('exercise_attempt'):
        op.create_table('exercise_attempt',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('submitted_answer', sa.Text(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('evaluated_by', sa.Integer(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['evaluated_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['exercise_id'], ['course_exercise.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('exercise_attempt', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_exercise_attempt_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_exercise_attempt_exercise_id'), ['exercise_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_exercise_attempt_status'), ['status'], unique=False)
            batch_op.create_index(batch_op.f('ix_exercise_attempt_user_id'), ['user_id'], unique=False)
    
    

def downgrade():
    raise RuntimeError(
        "This additive baseline cannot be downgraded safely. Restore a verified backup "
        "or create a forward migration; automatic table removal is intentionally disabled."
    )
