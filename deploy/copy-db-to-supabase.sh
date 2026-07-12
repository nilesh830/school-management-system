#!/usr/bin/env bash
# ONE-TIME data copy of the production database from Railway to Supabase.
#
#   deploy/copy-db-to-supabase.sh        # dump Railway, restore into Supabase
#
# Reads from deploy/prod.secrets.env (git-ignored):
#   RAILWAY_DATABASE_URL — old Railway Postgres (public proxy URL)
#   PROD_DATABASE_URL    — new Supabase Postgres (SESSION pooler URL, port 5432)
#
# pg_dump copies ALL schemas the railway user owns (public + school_demo +
# school_greenwood_high + ...), so the schema-per-school layout comes across
# intact. Supabase's own managed schemas (auth, storage, ...) are untouched.
#
# NOTE: Supabase pre-creates the `public` schema, so pg_restore logs a
# "schema public already exists" error and carries on — that one is expected
# and harmless; review any OTHER errors in the output.
#
# Requires local PostgreSQL client tools (pg_dump/pg_restore) whose version is
# >= the Railway server version. On Windows run this from Git Bash.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="$REPO_ROOT/deploy/prod.secrets.env"

# Prefer the portable PostgreSQL client tools in deploy/pg17/ (git-ignored)
# when pg_dump isn't already on PATH.
if ! command -v pg_dump >/dev/null 2>&1 && [ -d "$REPO_ROOT/deploy/pg17/pgsql/bin" ]; then
  export PATH="$REPO_ROOT/deploy/pg17/pgsql/bin:$PATH"
fi
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found — extract the PostgreSQL binaries into deploy/pg17/ or install client tools"; exit 1; }

[ -f "$SECRETS" ] || { echo "Missing $SECRETS (copy prod.secrets.env.example and fill it in)"; exit 1; }
# shellcheck disable=SC1090
set -a; source "$SECRETS"; set +a
[ -n "${RAILWAY_DATABASE_URL:-}" ] || { echo "RAILWAY_DATABASE_URL not set in $SECRETS"; exit 1; }
[ -n "${PROD_DATABASE_URL:-}" ] || { echo "PROD_DATABASE_URL (Supabase) not set in $SECRETS"; exit 1; }

DUMP="$REPO_ROOT/deploy/railway-prod.dump"

echo "== Dumping Railway database (all schemas) =="
pg_dump --no-owner --no-privileges --format=custom \
  --file="$DUMP" "$RAILWAY_DATABASE_URL"
echo "Dump written to $DUMP"

echo
echo "== Restoring into Supabase database =="
# No --exit-on-error: 'schema public already exists' is expected on Supabase.
# pg_restore exits non-zero when any error occurred, so tolerate that and let
# the schema snapshot below be the real verification.
pg_restore --no-owner --no-privileges \
  --dbname="$PROD_DATABASE_URL" "$DUMP" || \
  echo "(pg_restore reported errors — 'schema public already exists' is expected; check for others above)"

echo
echo "== Verifying (schema snapshot of Supabase DB) =="
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
