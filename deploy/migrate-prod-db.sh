#!/usr/bin/env bash
# Apply DB migrations to the PRODUCTION schema-per-school Postgres.
#
#   deploy/migrate-prod-db.sh --check   # read-only: show current state, migrate nothing
#   deploy/migrate-prod-db.sh           # apply `flask db-upgrade-all` to every school schema
#
# Reads PROD_DATABASE_URL from deploy/prod.secrets.env (git-ignored).
# `flask db-upgrade-all` sets search_path per schema and skips schemas already
# at head, so re-running is safe.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="$REPO_ROOT/deploy/prod.secrets.env"

[ -f "$SECRETS" ] || { echo "Missing $SECRETS (copy prod.secrets.env.example and fill it in)"; exit 1; }
# shellcheck disable=SC1090
set -a; source "$SECRETS"; set +a
[ -n "${PROD_DATABASE_URL:-}" ] || { echo "PROD_DATABASE_URL not set in $SECRETS"; exit 1; }

# Pick the backend venv python (Windows or POSIX layout), else system python.
if [ -x "$REPO_ROOT/backend/venv/Scripts/python.exe" ]; then
  PY="$REPO_ROOT/backend/venv/Scripts/python.exe"
elif [ -x "$REPO_ROOT/backend/venv/bin/python" ]; then
  PY="$REPO_ROOT/backend/venv/bin/python"
else
  PY="python"
fi

echo "== Production DB snapshot (before) =="
PROD_DATABASE_URL="$PROD_DATABASE_URL" "$PY" "$REPO_ROOT/deploy/inspect_prod_db.py"

if [ "${1:-}" = "--check" ]; then
  echo; echo "--check: read-only, nothing migrated."; exit 0
fi

echo; echo "== Applying db-upgrade-all to every school schema =="
cd "$REPO_ROOT/backend"
DATABASE_URL="$PROD_DATABASE_URL" FLASK_APP=run.py FLASK_ENV=production "$PY" -m flask db-upgrade-all

echo; echo "== Production DB snapshot (after) =="
cd "$REPO_ROOT"
PROD_DATABASE_URL="$PROD_DATABASE_URL" "$PY" "$REPO_ROOT/deploy/inspect_prod_db.py"
echo; echo "Done."
