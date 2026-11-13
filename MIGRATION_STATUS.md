# Flask → Netlify TypeScript migration

## Current state

- Work remains isolated on `migration/netlify-typescript`; production `main` has not been merged or changed.
- The previous Preview passed the read-only Neon health check: `DATABASE_URL` connected and `SECRET_KEY` was configured.
- A live browser check confirmed that the public Preview homepage, header, hero, navigation, login page, CSS, and JavaScript assets render.
- The new AI Professor implementation is now on this branch and requires a fresh Deploy Preview build before it can be tested.
- Environment variable `OPENAI_API_KEY` has **not yet been confirmed** in Netlify. Without it, AI chat and semantic grading return a clear configuration message; deterministic QCM marking still works.
- The current default AI model is `gpt-6-luna`; it can be overridden through `AI_TUTOR_MODEL`. Open-response grading can use `EXERCISE_GRADING_MODEL` or inherit `AI_TUTOR_MODEL`.

## AI Professor rules implemented

- Added a protected `/tutor` chat page and `POST /api/tutor` endpoint using the OpenAI Responses API.
- Chat context can include the current lesson, exercise, latest student submission, or question with its explanation.
- The tutor responds in the student's language (French, Arabic, or Moroccan Darija), explains errors, shows reasoning, and can give a short check-for-understanding exercise.
- Added a persistent navigation link and a lesson-specific entry point. Incorrect exercise and QCM answers link directly to the tutor with their context.
- Training QCM results now show correctness, the student's answer, the correct answer, the explanation, and an AI follow-up link for mistakes.
- Open-answer exercises are graded by AI when confidence is sufficient. If AI is unsure or unavailable, the attempt is marked `ai_retry`; the student is asked to clarify/retry. New attempts are no longer sent to a human teacher queue.
- Deterministic QCM / true-false / short-answer checks still calculate the score locally; AI produces a personalized explanation for wrong answers when the API key is configured.

## Exam protection

- Starting an exam sets an HttpOnly, Secure, SameSite=Strict exam-mode cookie.
- The tutor page is hidden during the active exam, and the tutor API rejects requests while the exam-mode cookie is present.
- The exam-mode cookie expires after submission. The exam page itself does not display answers or hints. Results and explanations appear only after the student submits the exam.

## Runtime and data safety

- Neon PostgreSQL remains the database. No schema migration, data transfer, seed, or destructive production DB write has been run as part of this runtime migration.
- Never commit `DATABASE_URL`, `SECRET_KEY`, or `OPENAI_API_KEY`.
- Existing Flask files, Alembic migrations, templates, and original assets remain available for rollback and comparison.
- Existing Werkzeug scrypt and PBKDF2 password hashes remain supported.
- Assessment question sets are signed and user-bound; POST and AI requests are protected by CSRF checks.
- The AI endpoint has per-user request throttling and bounded message/context sizes.

## Still required before production

- Add `OPENAI_API_KEY` in Netlify as a secret with Functions scope for Production and Deploy Previews.
- Confirm the latest branch build passes Netlify function bundling.
- Verify AI chat and wrong-answer explanation using a real API key and a test student account.
- Exercise registration/login/logout, student/admin access, course progress, QCM/exams, grading, bookmarks, videos and admin edits against a staging/test database.
- Complete remaining one-to-one parity checks against original Flask/Jinja behavior.
- Confirm the Production domain before merging.

## Deploy gate

Do not merge this branch or publish to the production domain until the latest Preview is green and critical flows have passed. Do not run Alembic against production Neon as part of this runtime migration.
