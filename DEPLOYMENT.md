# Deployment Runbook

How to ship the SMS **database**, **backend**, and **frontend** to production.
Point Claude Code at this file ("deploy per DEPLOYMENT.md") and it will follow these steps.

- **Hosting:** Railway project `celebrated-delight` / env `production` — three services from repo `nilesh830/school-management-system`.
- **Backend:** https://school-management-system-production-fbf4.up.railway.app
- **Frontend:** https://distinguished-comfort-production-5a39.up.railway.app (Caddy serves the SPA and reverse-proxies `/api/*` to the backend)
- **Database:** Railway Postgres, **schema-per-school** — master tables in `public`, each school in its own `school_<slug>` schema (`school_demo`, `school_greenwood_high`).

> **Secrets:** the real production DB URL lives in `deploy/prod.secrets.env` (git-ignored).
> Copy `deploy/prod.secrets.env.example` → `deploy/prod.secrets.env` and fill it from the
> Railway dashboard (Postgres service → Variables → `DATABASE_PUBLIC_URL`). Never commit it.

---

## 1. Database changes

Migrations must be applied to **every school schema**, not just `public`. The project's
`flask db-upgrade-all` command handles this: it enumerates active schools from the master
`schools` table and runs Alembic `upgrade head` against each schema (setting `search_path`
per schema — plain `flask db upgrade` only touches `public` and is **not** sufficient).

**When there are new migrations in `backend/migrations/versions/`, run:**

```bash
# read-only: shows schemas, schools, and the Alembic revision per schema — migrates nothing
bash deploy/migrate-prod-db.sh --check

# apply: runs db-upgrade-all across every school schema, with before/after snapshots
bash deploy/migrate-prod-db.sh
```

Equivalent manual command (from `backend/`, using the venv):

```bash
DATABASE_URL="<PROD_DATABASE_URL>" FLASK_APP=run.py FLASK_ENV=production \
  venv/Scripts/python.exe -m flask db-upgrade-all      # venv/bin/python on POSIX
```

**Notes**
- Idempotent: schemas already at head are skipped, so re-running is safe.
- Additive migrations (CREATE TABLE / ADD COLUMN with `server_default`) are safe while old
  code is still serving. For a **new NOT NULL column**, keep its DB `DEFAULT` until the new
  code is live, so in-flight inserts from the old code don't fail.
- New schools created later via `flask provision-school` get the current schema automatically.
- Always run `--check` first and eyeball the before/after `alembic_version` per schema.

## 2. Backend

Railway auto-builds and deploys the backend service on push to its **tracked branch**
(Nixpacks + `backend/Procfile` → gunicorn). Deploying is therefore a git operation:

```bash
git checkout <tracked-branch>      # confirm the branch in Railway → backend service → Settings
git merge feature/SMS-xxx          # or open a PR and merge
git push
```

Then watch the deploy in the Railway dashboard (backend service → Deployments).
Backend env vars (set in Railway, not in code): `FLASK_ENV=production`, `SECRET_KEY`,
`JWT_SECRET_KEY`, `DATABASE_URL=${{Postgres.DATABASE_URL}}` (private network), `CORS_ORIGINS`.

**Order of operations:** if a release has both DB and backend changes, run the DB migration
(step 1) **before** the backend deploy for additive migrations; for destructive ones,
deploy compatible code first. When unsure, migrate additively, deploy, then clean up.

## 3. Frontend

Same model — Railway rebuilds the frontend service on push to its tracked branch
(`frontend/Dockerfile`: Node build → Caddy serve on port 8080). Push/merge to the tracked
branch and watch the deploy. Frontend env var: `BACKEND_URL=<backend url>`.

Build gotchas already fixed (keep them in place):
- Dockerfile pins npm 11 (`npm install -g npm@11`) so `npm ci` matches the lockfile-v3 `package-lock.json`.
- Caddyfile uses mutually-exclusive `handle /api/*` + `handle` blocks so the SPA fallback can't swallow API calls.

---

## Quick reference

| Change type | What to do |
|-------------|-----------|
| DB migration | `bash deploy/migrate-prod-db.sh --check` then `bash deploy/migrate-prod-db.sh` |
| Backend code | Merge/push to the Railway-tracked branch → auto-deploy |
| Frontend code | Merge/push to the Railway-tracked branch → auto-deploy |
| New school | `flask provision-school --slug … --name … --admin-email … --admin-password …` |

**Verify after deploy:** hit the frontend URL, log in, and exercise the changed feature.
A quick backend health signal: a new route returns 401 (deployed) vs 404 (old code still live).
