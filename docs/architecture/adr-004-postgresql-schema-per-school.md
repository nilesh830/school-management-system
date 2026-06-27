# ADR-004: Migrate to PostgreSQL with Schema-per-School Multi-Tenancy

**Date:** 2026-06-24 | **Status:** Accepted | **Author:** @solution-architect / @database-engineer
**Supersedes:** the SQLite *database-per-school* approach from ADR-001 and the Sprint 2.5 ERP foundation.

---

## Context

The platform was originally built on **SQLite with one database file per school**
(`instance/schools/school_<slug>.db`) plus a `master.db` registry. This was
simple and gave strong isolation in development, but it does not hold up for a
real deployment:

- **SQLite is single-writer** — concurrent writes across users serialize and
  lock, which is unacceptable for a multi-user school ERP.
- **File-per-school doesn't fit managed/cloud hosting** — you can't point a
  hosted Postgres (Neon/Supabase/RDS) at hundreds of local `.db` files, and
  there's no connection pooling, backups, or failover.
- The team wanted to deploy to **Neon (serverless PostgreSQL)** while keeping the
  user's original hard requirement: *"each school has its own database."*

We needed a PostgreSQL model that preserves true per-school isolation without
provisioning a separate physical database per tenant.

---

## Decision

Adopt **one PostgreSQL database with a schema per school**:

- Master registry (`schools`, `super_admins`, `super_admin_revoked_tokens`)
  lives in the **`public`** schema.
- Each school's ~34 tables live in a dedicated **`school_<slug>`** schema
  (hyphens → underscores).
- Requests are routed to the correct schema with SQLAlchemy
  **`schema_translate_map={None: "school_<slug>"}`**, which compiles
  schema-qualified SQL on a per-connection basis.

This is the closest PostgreSQL equivalent of the old file-per-school model: each
school is a self-contained namespace, can be backed up/dropped independently,
and cannot be queried across by accident.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| **Row-level tenancy** (`school_id` column on every table) | A single forgotten `WHERE school_id=…` leaks cross-tenant data; weaker isolation; large model churn. |
| **Database-per-school on PostgreSQL** | Hundreds of databases are heavy to manage on serverless Postgres; cross-DB ops and pooling get awkward; connection limits. |
| **Stay on SQLite** | Single-writer locking; no cloud hosting story. |
| **`SET search_path` for routing** | Session state leaks across pooled connections (see Consequences). |

---

## Implementation Notes (hard-won)

These are the non-obvious things that made it work — captured so they aren't
rediscovered painfully:

1. **Driver: psycopg 3, not psycopg2.** The runtime is Python 3.14, which has no
   prebuilt `psycopg2-binary` wheels (source build fails on Windows). We use
   `psycopg[binary]` and normalize the URL scheme to `postgresql+psycopg://` in
   `config.py` so a raw provider URL still works.

2. **Never `SET search_path` on a pooled connection.** It mutates the physical
   connection's session state; when the connection returns to the pool, the next
   request inherits the wrong `search_path` → `relation "schools" does not exist`
   or silent cross-schema reads. **All** routing uses `schema_translate_map` (for
   ORM/DDL) or fully-qualified identifiers (for raw SQL). This applies to the
   request path, provisioning, and the `db-upgrade-all` CLI.

3. **Pin `search_path = public` per connection.** Master-table queries are
   unqualified, so connections are opened with
   `connect_args={"options": "-csearch_path=public"}` for deterministic
   resolution regardless of role defaults or leftover state.

4. **Use the cloud DB's DIRECT endpoint, not its transaction pooler.** Neon's
   PgBouncer pooler filters the libpq `options` startup param and reuses server
   connections across clients (amplifying any `search_path` leak). SQLAlchemy
   does its own pooling against the direct endpoint. `pool_pre_ping=True` +
   `pool_recycle=280` handle the serverless auto-suspend (idle connections get
   dropped after ~5 min).

5. **Alembic version reads don't honor `schema_translate_map`.** For per-school
   `db-upgrade-all`, pass `version_table_schema=<schema>` explicitly to
   `MigrationContext.configure()` and to `context.configure()` in
   `migrations/env.py`. Existing migrations keep `batch_alter_table` (a
   SQLite-era pattern) — harmless on PostgreSQL.

6. **New schemas are created via `metadata.create_all` + a head stamp** at
   provision time, not by replaying migrations. Master tables are created at app
   startup via `db.create_all(bind_key=['master'])`.

---

## Consequences

**Benefits**
- Real concurrency (PostgreSQL MVCC) and a managed-cloud hosting story (Neon).
- Strong per-school isolation preserved; per-school backup/restore and drop.
- Zero changes to ORM models, services, routes, and the test suite — only the
  tenancy plumbing (config, `tenant.py`, provisioning, CLI, `env.py`) changed.
- The `TESTING` bypass keeps the unit suite on fast in-memory SQLite.

**Costs / risks**
- Schema routing is subtle; the `schema_translate_map`-only rule must be
  followed by every contributor (documented in
  [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) §5 and §13).
- Tenant DB operations (`CREATE SCHEMA`, provisioning) are PostgreSQL-only — the
  10 provisioning/CLI tests run against a real Postgres (`tests/integration_pg/`,
  skipped unless `DATABASE_URL` is PostgreSQL); the other ~493 tests stay on
  SQLite via the `TESTING` bypass.
- **Latency is now network-bound.** Against a remote cloud DB, each query is a
  round-trip (~250 ms from a distant region) and a cold connection ~1 s. For a
  fast dev loop, run a **local PostgreSQL** and point `DATABASE_URL` at it; keep
  the cloud DB for staging/demo.

---

## Status of the old design

The SQLite database-per-school implementation (Sprint 2.5) is fully replaced.
Historical docs that describe `instance/schools/*.db`, `check_same_thread`,
`_engine_cache`, and the `target_db_url` Alembic override reflect the **previous**
design and are superseded by this ADR and the rewritten
[ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md).
