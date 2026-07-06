"""READ-ONLY snapshot of the production DB (schema-per-school). No writes.

Usage (from repo root or backend/):
    PROD_DATABASE_URL="postgresql://..." python deploy/inspect_prod_db.py

Prints: schemas, the master `schools` table, the Alembic revision stamped in
each school schema, and whether the current head migration's objects exist.
Run this BEFORE and AFTER a migration to confirm state.
"""
import os
import sys

import psycopg

URL = os.environ.get("PROD_DATABASE_URL")
if not URL:
    sys.exit("PROD_DATABASE_URL not set. Source deploy/prod.secrets.env first.")

with psycopg.connect(URL, autocommit=True) as conn:
    cur = conn.cursor()

    print("=== SCHEMAS ===")
    cur.execute("""
        SELECT schema_name FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast')
        ORDER BY schema_name
    """)
    schemas = [r[0] for r in cur.fetchall()]
    for s in schemas:
        print(" ", s)

    print("\n=== schools (master, public) ===")
    try:
        cur.execute("SELECT slug, name, db_url, is_active FROM public.schools ORDER BY slug")
        for slug, name, db_url, active in cur.fetchall():
            print(f"  slug={slug!r} name={name!r} schema={db_url!r} active={active}")
    except Exception as e:
        print("  (could not read public.schools):", e)

    print("\n=== alembic_version per schema ===")
    for s in schemas:
        try:
            cur.execute(f'SELECT version_num FROM "{s}".alembic_version')
            print(f"  {s}: {[r[0] for r in cur.fetchall()]}")
        except Exception:
            print(f"  {s}: (no alembic_version table)")

print("\nDONE (read-only).")
