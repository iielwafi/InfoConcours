import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
INSTANCE = PROJECT / "instance"


class MigrationTests(unittest.TestCase):
    def test_baseline_can_initialize_a_new_empty_database(self):
        fd, path = tempfile.mkstemp(prefix="infoconcours-empty-migration-", suffix=".db", dir=INSTANCE)
        os.close(fd)
        try:
            env = os.environ.copy()
            env.update({
                "SECRET_KEY": "migration-test-only",
                "DATABASE_URL": "sqlite:///" + Path(path).name,
                "AUTO_CREATE_SCHEMA": "0",
                "AUTO_SEED_CONTENT": "0",
            })
            result = subprocess.run(
                [sys.executable, "-m", "flask", "--app", "app", "db", "upgrade"],
                cwd=PROJECT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"user", "question", "attempt", "curriculum_lesson", "course_exercise", "exercise_attempt", "lesson_completion"}.issubset(names))
            self.assertEqual(conn.execute("SELECT count(*) FROM user").fetchone()[0], 0)
            conn.close()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_additive_baseline_preserves_legacy_rows_and_creates_phase4_tables(self):
        fd, path = tempfile.mkstemp(prefix="infoconcours-migration-", suffix=".db", dir=INSTANCE)
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            conn.executescript("""
                CREATE TABLE user (
                  id INTEGER PRIMARY KEY, username VARCHAR(40) NOT NULL UNIQUE,
                  email VARCHAR(120) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL,
                  role VARCHAR(15) NOT NULL, created_at DATETIME
                );
                CREATE TABLE question (
                  id INTEGER PRIMARY KEY, domain VARCHAR(80) NOT NULL, topic VARCHAR(120) NOT NULL,
                  level VARCHAR(20) NOT NULL, prompt_fr TEXT NOT NULL, prompt_ar TEXT NOT NULL,
                  options_fr TEXT NOT NULL, options_ar TEXT NOT NULL, answer INTEGER NOT NULL,
                  explanation_fr TEXT NOT NULL, explanation_ar TEXT NOT NULL, active BOOLEAN
                );
                CREATE TABLE attempt (
                  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES user(id),
                  mode VARCHAR(20) NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL,
                  details TEXT, duration_minutes INTEGER, created_at DATETIME
                );
                CREATE TABLE diagnostic (
                  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES user(id),
                  scores TEXT NOT NULL, total INTEGER NOT NULL, created_at DATETIME
                );
                CREATE TABLE study_session (
                  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES user(id),
                  domain VARCHAR(80) NOT NULL, minutes INTEGER NOT NULL, studied_on DATE
                );
                CREATE TABLE course_exercise (
                  id INTEGER PRIMARY KEY, lesson_id INTEGER NOT NULL, title VARCHAR(180) NOT NULL,
                  prompt_fr TEXT NOT NULL, solution_fr TEXT NOT NULL, level VARCHAR(20) NOT NULL,
                  published BOOLEAN NOT NULL
                );
                CREATE INDEX ix_course_exercise_lesson_id ON course_exercise(lesson_id);
                INSERT INTO user VALUES (1,'legacy-user','legacy@example.test','hashed','student',CURRENT_TIMESTAMP);
                INSERT INTO question VALUES (1,'Réseaux','DNS','Facile','Que signifie DNS ?','','["A","B","C","D"]','["A","B","C","D"]',0,'Réponse conservée.','',1);
                INSERT INTO course_exercise VALUES (7,3,'Old exercise','Prompt conservé','Solution conservée','Moyen',1);
            """)
            conn.commit()
            conn.close()

            env = os.environ.copy()
            env.update({
                "SECRET_KEY": "migration-test-only",
                "DATABASE_URL": "sqlite:///" + Path(path).name,
                "AUTO_CREATE_SCHEMA": "0",
                "AUTO_SEED_CONTENT": "0",
            })
            result = subprocess.run(
                [sys.executable, "-m", "flask", "--app", "app", "db", "upgrade"],
                cwd=PROJECT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
            self.assertEqual(conn.execute("SELECT username FROM user WHERE id=1").fetchone()[0], "legacy-user")
            self.assertEqual(conn.execute("SELECT prompt_fr FROM question WHERE id=1").fetchone()[0], "Que signifie DNS ?")
            self.assertEqual(conn.execute("SELECT prompt_fr,solution_fr FROM course_exercise WHERE id=7").fetchone(), ("Prompt conservé","Solution conservée"))
            self.assertEqual(conn.execute("SELECT exercise_type FROM course_exercise WHERE id=7").fetchone()[0], "open")
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("exercise_attempt", names)
            self.assertIn("lesson_completion", names)
            self.assertIn("course_exercise", names)
            self.assertEqual(conn.execute("SELECT version_num FROM alembic_version").fetchone()[0], "b71c92a4e613")
            exercise_columns={row[1] for row in conn.execute("PRAGMA table_info(course_exercise)")}
            self.assertIn("learning_objective_fr",exercise_columns)
            video_columns={row[1] for row in conn.execute("PRAGMA table_info(video_resource)")}
            self.assertTrue({"verification_status","verified_at"}.issubset(video_columns))
            metadata_columns={row[1] for row in conn.execute("PRAGMA table_info(question_metadata)")}
            self.assertIn("learning_objective",metadata_columns)
            self.assertIn("lesson_id",metadata_columns)
            conn.close()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
