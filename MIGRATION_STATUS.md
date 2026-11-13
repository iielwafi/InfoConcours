# Flask → Netlify TypeScript migration

## Current state

- Netlify environment variables `DATABASE_URL` and `SECRET_KEY` have been entered in the site UI for Production, Deploy Previews, and Branch deploys, with the Functions scope enabled. A fresh Deploy Preview is required to consume the updated values; the previous health check ran before that redeploy.

- Work is isolated on `migration/netlify-typescript`; production `main` has not been merged or changed.
- Netlify Deploy Preview is still failing. GitHub exposes the Deploy log link, but not the log text. Do not merge or publish until that error is inspected and the preview passes.
- `netlify/functions/web.ts` contains one consolidated handler (the duplicated trailing fragments that broke its syntax have been removed).
- TypeScript helper imports use explicit `.ts` extensions and `tsconfig.json` permits them.
- `GET /api/health` is handled by the main wildcard function to avoid overlapping function routes.
- Static CSS, JS and favicon assets are copied to `public/assets`; the legacy `/static/*` URL is rewritten to those assets.
- Node.js build dependencies are configured. Netlify performs the TypeScript function bundling; the standalone type-check remains available as `npm run typecheck`.

## Runtime and data safety

- Neon PostgreSQL remains the intended database. No schema migration, data transfer, seed, or production database write has been run as part of this runtime migration.
- Secrets must be configured in Netlify environment variables with Functions scope. Never commit `DATABASE_URL`, `SECRET_KEY`, or `OPENAI_API_KEY`.
- Existing Flask files, Alembic migrations, templates, and original assets remain in the repository for rollback and comparison.
- New password hashes use Werkzeug-compatible scrypt; existing Werkzeug scrypt and PBKDF2 formats are supported for verification.
- Assessment question sets are signed and user-bound; CSRF checks run on POST requests.

## Implemented in the TypeScript handler so far

- Public home, registration, login, logout, profile.
- Dashboard, diagnostic and result, course catalogue, continue course, lesson pages, lesson completion, subject-level assessment.
- Exercise submissions with QCM/true-false/short-answer auto-grading and optional AI grading fallback.
- QCM, timed exam, study sessions and daily goal, planner summary, error notebook, bookmarks, language preference.
- Verified video listing and watched-state tracking.
- Admin overview, role changes, question creation/activation, curriculum publishing/content creation, manual exercise review, video verification/moderation and quality summary.

## Still required before production

- Inspect and fix the current Netlify Deploy Preview failure.
- Validate the real Neon schema and read-only health check from a deployed Preview.
- Run end-to-end checks for registration/login/logout, CSRF, student/admin access, course progress, QCM/exams, grading, bookmarks, videos and admin edits against a staging/test database.
- Restore all remaining parity details from the original Jinja templates and business logic; the current handler is a first functional port, not a verified one-to-one replacement.
- Confirm the deployed site and custom domain before merging.

## Deploy gate

Do not merge this branch or change the production Netlify domain until the preview is green and critical flows have passed against a staging database. Do not run Alembic against production Neon as part of this runtime migration.
