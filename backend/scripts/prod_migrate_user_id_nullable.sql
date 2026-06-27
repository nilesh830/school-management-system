-- =============================================================================
-- Production migration: e1f2a3b4c5d6 — make students.user_id nullable
-- =============================================================================
-- Applies the change to EVERY active school schema (loops over public.schools)
-- and bumps each schema's alembic_version to the new head.
--
-- Safe to re-run: "DROP NOT NULL" on an already-nullable column is a no-op,
-- and the version UPDATE is idempotent. Runs in a single transaction.
--
-- Usage (see command in the chat):
--   psql "<RAILWAY_DATABASE_PUBLIC_URL>" -f prod_migrate_user_id_nullable.sql
-- =============================================================================

BEGIN;

DO $$
DECLARE
    sch text;
BEGIN
    FOR sch IN
        SELECT db_url FROM public.schools WHERE is_active = true ORDER BY db_url
    LOOP
        EXECUTE format('ALTER TABLE %I.students ALTER COLUMN user_id DROP NOT NULL', sch);
        EXECUTE format('UPDATE %I.alembic_version SET version_num = %L', sch, 'e1f2a3b4c5d6');
        RAISE NOTICE 'Migrated schema: %', sch;
    END LOOP;
END $$;

COMMIT;

-- ---- Verification (should show is_nullable = YES for every school) ----------
SELECT table_schema, is_nullable
FROM information_schema.columns
WHERE table_name = 'students'
  AND column_name = 'user_id'
  AND table_schema LIKE 'school\_%'
ORDER BY table_schema;
