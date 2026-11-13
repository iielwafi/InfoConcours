# Flask → Netlify TypeScript migration

## Safety rules

- Work is isolated on branch `migration/netlify-typescript`; the production `main` branch is not changed.
- The existing Flask application, Alembic migrations, templates, assets, and tests remain untouched during bootstrap.
- Neon is retained as the PostgreSQL database. No schema change, data transfer, seed, or production migration is performed by this branch.
- Never put `DATABASE_URL`, `SECRET_KEY`, OpenAI keys, or access tokens in Git. Add them only in Netlify environment variables with Functions scope.

## Bootstrap completed

- Added a Node.js/TypeScript package manifest and TypeScript configuration.
- Added Netlify build/function configuration.
- Added a read-only `GET /api/health` probe. It executes only `SELECT 1` against Neon and does not expose database errors or credentials.
- Added a Node test contract for the health endpoint.
- Added Node/Netlify build artifacts to `.gitignore`.

## Not yet production-ready

The public application is **not** switched to Netlify yet. The current site depends on Flask routes, Flask-Login, Flask-WTF/CSRF, SQLAlchemy models, Jinja templates, and Python content modules. Those still need a behavior-preserving TypeScript implementation and parity tests. The catch-all rewrite is intentionally disabled so an incomplete migration cannot replace the live site with a broken handler.

## Route parity checklist

- [ ] Home and public landing page
- [ ] Register, login, logout, profile, session and CSRF protection
- [ ] Dashboard, diagnostic and diagnostic result
- [ ] Courses, continue course, lessons and lesson completion
- [ ] Exercise submissions and grading fallback
- [ ] QCM, exam and result persistence
- [ ] Planner and study-time tracking
- [ ] Error notebook, bookmarks and language preference
- [ ] Videos and watched-state persistence
- [ ] Admin overview, curriculum, grading queue, quality and videos

## Deploy gate

Do not connect this branch to the production Netlify domain until route parity is complete, automated tests pass, and a staging database has been validated. Do not run Alembic against the production Neon database as part of this application-runtime migration.
