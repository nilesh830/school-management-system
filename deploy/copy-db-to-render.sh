#!/usr/bin/env bash
# ONE-TIME data copy of the production database from Railway to Render.
#
#   deploy/copy-db-to-render.sh          # dump Railway, restore into Render
#
# Reads from deploy/prod.secrets.env (git-ignored):
#   RAILWAY_DATABASE_URL — old Railway Postgres (public proxy URL)
#   PROD_DATABASE_URL    — new Render Postgres (External Database URL)
#
# pg_dump copies ALL schemas by default, so the schema-per-school layout
# (public + school_demo + school_greenwood_high + ...) comes across intact.
# The Render database must be empty (fresh from the Blueprint).
#
# Requires local PostgreSQL client tools (pg_dump/pg_restore) whose version is
# >= the Railway server version. On Windows run this from Git Bash.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="$REPO_ROOT/deploy/prod.secrets.env"

[ -f "$SECRETS" ] || { echo "Missing $SECRETS (copy prod.secrets.env.example and fill it in)"; exit 1; }
# shellcheck disable=SC1090
set -a; source "$SECRETS"; set +a
[ -n "${RAILWAY_DATABASE_URL:-}" ] || { echo "RAILWAY_DATABASE_URL not set in $SECRETS"; exit 1; }
[ -n "${PROD_DATABASE_URL:-}" ] || { echo "PROD_DATABASE_URL (Render) not set in $SECRETS"; exit 1; }

DUMP="$REPO_ROOT/deploy/railway-prod.dump"

echo "== Dumping Railway database (all schemas) =="
pg_dump --no-owner --no-privileges --format=custom \
  --file="$DUMP" "$RAILWAY_DATABASE_URL"
echo "Dump written to $DUMP"

echo
echo "== Restoring into Render database =="
pg_restore --no-owner --no-privileges --exit-on-error \
  --dbname="$PROD_DATABASE_URL" "$DUMP"

echo
echo "== Verifying (schema snapshot of Render DB) =="
# Pick the backend venv python (Windows or POSIX layout), else system python.
if [ -x "$REPO_ROOT/backend/venv/Scripts/python.exe" ]; then
  PY="$REPO_ROOT/backend/venv/Scripts/python.exe"
elif [ -x "$REPO_ROOT/backend/venv/bin/python" ]; then
  PY="$REPO_ROOT/backend/venv/bin/python"
else
  PY="python"
fi
PROD_DATABASE_URL="$PROD_DATABASE_URL" "$PY" "$REPO_ROOT/deploy/inspect_prod_db.py"

echo
echo "Done. Keep $DUMP as a backup or delete it (git-ignored via deploy/*.dump)."
