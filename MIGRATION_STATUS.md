# Flask → Netlify TypeScript migration

## Current state

- All migration work remains isolated on `migration/netlify-typescript`; production `main` has not been merged or changed.
- Netlify Deploy Preview has previously passed a live build and a read-only Neon health check (`DATABASE_URL` connected; `SECRET_KEY` configured). A new preview is triggered for each branch commit; verify the latest status before relying on it.
- The public preview homepage and login page have been loaded successfully. The health endpoint returned HTTP 200 with Neon connected.
- Netlify has `DATABASE_URL` and `SECRET_KEY` configured for Production, Deploy Previews, and Branch deploys. `GEMINI_API_KEY` is not yet configured; it must be added before AI requests can reach Gemini.
- Gemini is the preferred AI provider. The default model is `gemini-3.8-flash` using the Gemini Developer API `generateContent` endpoint. `OPENAI_API_KEY` remains an optional paid fallback only when Gemini is not configured.
- Gemini Free Tier has usage limits and Google may use prompts for product improvement. The tutor page displays a privacy notice; students should not submit personal or confidential information.

## AI Professor rules implemented

- Added protected `/tutor` chat page and authenticated `POST /api/tutor` endpoint.
- Chat context can include the current lesson, exercise, latest student submission, or question with its explanation.
- The tutor responds in French, Arabic, or Moroccan Darija; explains errors step by step and can give a short check-for-understanding exercise.
- Added a lesson-specific entry point and AI follow-up links from exercise/QCM corrections.
- Training QCM results show correctness, the student's answer, the correct answer, and the stored explanation.
- Deterministic QCM / true-false / short-answer checks calculate correctness locally. The AI provider may add a personalized explanation for wrong answers.
- Open-answer exercises use structured AI grading. A confident result is saved as AI-graded; a low-confidence result or provider failure is marked `ai_retry` so the learner can refine and resubmit. No new attempt is sent to a human correction queue.
- The old admin route `/admin/exercise-attempts` has been removed from the Netlify app and route contract. Historical attempts marked `pending_manual` or `manually_graded` remain visible as historical records; pending attempts can be continued with the AI tutor.

## Exam protection

- Starting an exam sets an HttpOnly, Secure, SameSite=Strict exam-mode cookie.
- The tutor page is hidden during an active exam, and the tutor API rejects requests while the exam-mode cookie is present.
- The exam-mode cookie expires after submission. The exam page itself does not display answers or hints. Results and explanations appear only after the student submits the exam.

## Build and tests

- `npm run build` now runs `npm run typecheck` and the Node test suite before Netlify bundles the function.
- `tests-netlify/ai.test.mjs` verifies Gemini provider selection and JSON-mode requests without calling a paid API.
- Route tests verify the AI tutor endpoints and absence of the old human correction route.
- No live Gemini API call has been verified yet because `GEMINI_API_KEY` is not configured.

## YouTube videos for lessons

- Added a curated French-language video pack for **30 of the 32 published lessons**. Every suggestion is matched to the exact lesson title in the curriculum.
- The admin page `/admin/videos` now has a bulk-import action. It creates the selected records as `pending`; no video is shown to students until an administrator verifies the link and publishes it.
- The import is idempotent: existing YouTube video IDs are skipped, and a video already linked to another lesson is not reassigned.
- Two lessons still need a suitable French video: `Comparer sans se fier à un seul chiffre` and `Comprendre couleur et taille d’image`. The admin page provides a direct YouTube search for each missing topic.
- The curated pack is covered by tests for unique 11-character YouTube IDs and exact lesson-title matching. The current build passes TypeScript and all 14 automated tests.
- The pack has **not yet been imported into Neon**. An administrator must sign into the preview, open Administration → Vidéos des leçons, and click the French bulk-import button. Imported suggestions remain pending until reviewed.

## Runtime and data safety

- Neon PostgreSQL remains the database. No schema migration, data transfer, seed, or destructive production DB write has been run as part of this runtime migration.
- Never commit `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY`.
- Existing Flask files, Alembic migrations, templates, and original assets remain available for rollback and comparison.
- Existing Werkzeug scrypt and PBKDF2 password hashes remain supported.
- Assessment question sets are signed and user-bound; POST and AI requests are protected by CSRF checks.
- The AI endpoint has per-user request throttling and bounded message/context sizes.

## Still required before production

- Add a Gemini API key from Google AI Studio as `GEMINI_API_KEY` in Netlify with Functions scope for Deploy Previews and Production. Use the Free Tier project; do not enable paid billing just to test this stage.
- Verify the latest Deploy Preview build after typecheck/test integration.
- Verify AI chat and wrong-answer explanation with a real Gemini key and a test student account.
- Exercise registration/login/logout, student/admin access, course progress, QCM/exams, grading, bookmarks, videos, and admin edits against a staging/test database.
- Complete remaining one-to-one parity checks against original Flask behavior.
- Confirm the Production domain before merging.

## Deploy gate

Do not merge this branch or publish to the production domain until the latest Preview is green and critical flows have passed. Do not run Alembic against production Neon as part of this runtime migration.
