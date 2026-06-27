# ERP Multi-Tenancy Architecture — Developer Guide

> **Strategy:** Schema-per-School on a single PostgreSQL database
> **Stack:** Flask + SQLAlchemy + PostgreSQL (psycopg 3) · Angular 17 + PrimeNG
> **Status:** Current (migrated from SQLite database-per-school — see [ADR-004](adr-004-postgresql-schema-per-school.md))

---

## 1. The Big Picture

The platform is a multi-tenant ERP: one deployment serves many schools, and a
school can **never** read or write another school's data.

We achieve this with **one PostgreSQL database** in which:

- The **`public` schema** is the *master registry* — it knows which schools
  exist and holds the platform-level super-admin accounts.
- Each school gets its **own PostgreSQL schema** named `school_<slug>`,
  containing the full set of ~34 school-scoped tables.

```
PostgreSQL database  (e.g. Neon "neondb")
│
├── public                ← master registry
│     ├── schools                      (slug → schema name, metadata, active flag)
│     ├── super_admins                 (platform owner accounts)
│     └── super_admin_revoked_tokens   (super-admin JWT blocklist)
│
├── school_demo           ← all data for the "demo" school
│     ├── users · students · teachers · parents · classes · sections …
│     └── alembic_version              (this school's migration head)
│
├── school_greenwood_high ← all data for "greenwood-high"
│     └── (same 34-table set, fully isolated)
│
└── school_<slug>         ← one schema per provisioned school
```

Isolation is enforced at the **schema** level: a tenant request is compiled to
emit schema-qualified SQL (`school_demo.users`), so it physically cannot touch
another schema's rows.

> **Why schema-per-school (not row-level `school_id`)?** True data isolation,
> per-school backup/restore, and no risk of a forgotten `WHERE school_id = …`
> leaking data across tenants. See [ADR-004](adr-004-postgresql-schema-per-school.md)
> for the full rationale and the migration from the original SQLite
> database-per-school design.

---

## 2. Directory Layout

```
backend/
├── app/
│   ├── __init__.py                ← create_app(); creates master tables at startup
│   ├── config.py                  ← DB URL normalization + engine options
│   ├── cli.py                     ← provision-school, db-upgrade-all
│   ├── models/
│   │   ├── master/                ← __bind_key__='master' models (public schema)
│   │   │   ├── school.py
│   │   │   ├── super_admin.py
│   │   │   └── super_admin_revoked_token.py
│   │   └── *.py                   ← school-scoped models (per-school schema)
│   ├── routes/
│   │   ├── superadmin_auth.py     ← /api/v1/superadmin/auth/*
│   │   ├── superadmin_schools.py  ← /api/v1/superadmin/schools/*
│   │   └── auth.py                ← /api/v1/auth/* (school users)
│   ├── services/
│   │   └── superadmin_service.py  ← school provisioning (CREATE SCHEMA + tables)
│   └── utils/
│       └── tenant.py              ← per-request schema routing (core of tenancy)
└── migrations/
    └── env.py                     ← Alembic, schema-aware for per-school upgrades
```

---

## 3. Two Kinds of Models

### 3a. Master-bound models — `__bind_key__ = 'master'`

These live in the `public` schema and are queried with the default
`db.session` / `Model.query`. They are created at app startup (not via Alembic).

```python
# backend/app/models/master/school.py
class School(db.Model):
    __bind_key__ = 'master'          # → public schema
    __tablename__ = 'schools'

    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(200), nullable=False)
    slug      = db.Column(db.String(50), unique=True, nullable=False, index=True)
    db_url    = db.Column(db.String(500), nullable=False)  # ← stores the SCHEMA NAME
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    ...
```

> **Note the repurposed `db_url` column.** In the old SQLite design it held a
> file path (`sqlite:///…/school_greenwood.db`). It now holds the **schema
> name** (e.g. `school_greenwood_high`). The column name was kept to avoid a
> migration; treat its value as "the school's schema."

### 3b. School-scoped models — no bind key

`User`, `Student`, `Teacher`, `Parent`, `Attendance`, `Exam`, `FeeRecord`, …
(~34 tables). They have **no `__bind_key__`** and no explicit `schema=`. The
schema they resolve to is decided **per request** by the tenant router.

```python
# backend/app/models/user.py
class User(db.Model):                  # no __bind_key__, no schema=
    __tablename__ = 'users'
    id   = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum('admin', 'teacher', 'student', 'parent'), ...)
    ...
```

---

## 4. Config: One Engine, Pinned `search_path`

```python
# backend/config.py (abridged)

def _normalize_pg_url(url: str) -> str:
    # Force the psycopg 3 driver (psycopg2 has no wheels for Python 3.14):
    #   postgres://      → postgresql://      → postgresql+psycopg://
    ...

class Config:
    SQLALCHEMY_DATABASE_URI = _normalize_pg_url(os.environ['DATABASE_URL'])
    SQLALCHEMY_BINDS = {'master': _normalize_pg_url(MASTER_DATABASE_URL or DATABASE_URL)}

    # Every PostgreSQL connection starts with search_path = public, so the
    # unqualified master-table queries (schools, super_admins) are deterministic.
    # Tenant queries do NOT rely on this — they are schema-qualified (see §5).
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,                          # drop dead connections on checkout
        "pool_recycle": 280,                            # refresh before a cloud idle-timeout
        "connect_args": {"options": "-csearch_path=public"},
    }
```

The default bind and the `master` bind point at the **same** database. Master
models use the `public` schema; school models are redirected per request.

---

## 5. TenantMiddleware — Per-Request Schema Routing

The heart of the system. Before every request, `setup_tenant_db()` figures out
which school is calling, then opens a session whose SQL is **rewritten to target
that school's schema** via SQLAlchemy's `schema_translate_map`.

```python
# backend/app/utils/tenant.py

def setup_tenant_db() -> None:
    """before_request hook — establishes g.db for this request."""
    if current_app.config.get('TESTING'):        # tests share one in-memory DB
        g.db = db.session
        return

    if request.path.startswith('/api/v1/superadmin/'):   # master-only routes
        return

    slug = _extract_school_slug()                # from JWT, or login body
    if not slug:
        return                                   # unauthenticated routes use db.session

    school = School.query.filter_by(slug=slug, is_active=True).first()
    if not school:
        return

    session, connection = _open_tenant_session(school.db_url)   # db_url = schema name
    g.db = session
    g.db_connection = connection


def _open_tenant_session(schema: str):
    """A Session whose every unqualified table is compiled to `<schema>.table`."""
    connection = db.engine.connect().execution_options(
        schema_translate_map={None: schema}      # None (no schema) → school_<slug>
    )
    session = Session(bind=connection)
    return session, connection


def teardown_tenant_db(exc):
    """teardown_request hook — close session AND return the connection to the pool."""
    session = g.pop('db', None)
    connection = g.pop('db_connection', None)
    if session is not None:
        if exc is not None:
            session.rollback()
        session.close()
    if connection is not None:
        connection.close()
```

### Why `schema_translate_map` and **never** `SET search_path`

`SET search_path TO school_x` mutates **session state on the physical
connection**. With connection pooling (and especially a cloud pooler like
Neon's PgBouncer), that connection is later handed to another request whose
`search_path` is now silently wrong — master queries fail with
`relation "schools" does not exist`, or worse, a tenant reads the wrong schema.

`schema_translate_map` instead rewrites the **compiled SQL** (`users` →
`school_x.users`) for that connection only. Nothing leaks back to the pool.
This rule is absolute across the codebase: provisioning, the CLI, and the
request path all use `schema_translate_map` or fully-qualified identifiers.

### `get_db()` — the accessor every service/route uses

```python
def get_db():
    return getattr(g, 'db', db.session)
    # tenant session inside a school request; db.session otherwise
```

```python
# A service or route always goes through get_db():
from app.utils.tenant import get_db

students = get_db().query(Student).all()   # → SELECT … FROM school_demo.students
get_db().add(record); get_db().commit()
```

---

## 6. JWT Carries the `school_slug`

A school user's JWT embeds `school_slug` as a custom claim, so every subsequent
request self-identifies its tenant. The login request supplies the slug in the
body (there is no JWT yet); thereafter the middleware reads it from the token.

```python
# School-user token claims
{ "sub": "42", "role": "admin", "user_id": 42, "school_slug": "demo",
  "parent_id": 7 }      # parent_id only present for role=parent

# Super-admin token claims (NO school_slug)
{ "sub": "sa:1", "role": "super_admin", "super_admin_id": 1 }
```

`_extract_school_slug()` reads the slug from the `Authorization: Bearer` token
for authenticated requests, or from the JSON body of `POST /api/v1/auth/login`.

---

## 7. Request Lifecycle — Step by Step

```
Angular  ──GET /api/v1/students  (Bearer JWT: school_slug=greenwood-high)──▶ Flask
   (dev: proxied localhost:4200 → :5000)
                                   │
  [before_request] setup_tenant_db()
        decode JWT → slug = "greenwood-high"
        School.query → db_url = "school_greenwood_high"
        conn = engine.connect().execution_options(schema_translate_map={None: "school_greenwood_high"})
        g.db = Session(bind=conn)
                                   │
  [handler] get_db().query(Student).all()
        → SELECT … FROM school_greenwood_high.students      ← fully isolated
                                   │
  [teardown_request] teardown_tenant_db()
        session.close(); connection.close()                ← back to pool, clean
```

---

## 8. Super Admin vs School User — Two Auth Systems

| Aspect | School User | Super Admin |
|---|---|---|
| Login | `POST /api/v1/auth/login` | `POST /api/v1/superadmin/auth/login` |
| Required fields | `email`, `password`, `school_slug` | `email`, `password` |
| JWT identity | `"42"` (user id) | `"sa:1"` (prefixed) |
| JWT `role` | `admin`/`teacher`/`student`/`parent` | `super_admin` |
| Frontend token | `localStorage.sms_access_token` | `localStorage.sms_sa_access_token` |
| Blocklist table | `revoked_tokens` (school schema) | `super_admin_revoked_tokens` (public) |
| Tenant middleware | runs → opens school schema | skipped for `/superadmin/*` |
| Data scope | one `school_<slug>` schema | `public` registry |

```python
# backend/app/__init__.py — blocklist routing by role claim
@jwt_manager.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    if jwt_payload.get('role') == 'super_admin':
        return SuperAdminRevokedToken.is_jti_blocklisted(jwt_payload['jti'])  # public
    return RevokedToken.is_jti_blocklisted(jwt_payload['jti'])                 # tenant
```

---

## 9. Provisioning a New School

`SuperAdminService.provision_school()` creates the schema, its tables, and the
first admin — all in one transaction, with cleanup on failure.

```python
# backend/app/services/superadmin_service.py (abridged)

def provision_school(data):
    slug   = data['slug'].lower().strip()
    if School.query.filter_by(slug=slug).first():
        return None, {'message': 'Slug already taken', 'status': 409}

    schema = f'school_{slug}'.replace('-', '_')     # → stored in School.db_url
    school = School(name=data['name'], slug=slug, db_url=schema, ...)
    db.session.add(school); db.session.flush()      # get id, not committed yet

    _create_school_db(schema)                        # CREATE SCHEMA + tables + stamp
    _seed_school_admin(schema, data['admin_email'], data['admin_password'])
    db.session.commit()                              # commit master row last
    # on any error: rollback master row + DROP SCHEMA … CASCADE
```

```python
def _create_school_db(schema):
    engine = db.engine
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    # create the ~34 school-scoped tables INSIDE the schema (exclude master tables)
    school_tables = [t for t in db.metadata.sorted_tables
                     if t.info.get('bind_key') != 'master']
    routed = engine.connect().execution_options(schema_translate_map={None: schema})
    db.metadata.create_all(bind=routed, tables=school_tables); routed.commit()

    # stamp alembic_version at head, schema-qualified (no SET search_path)
    head = ScriptDirectory.from_config(cfg).get_current_head()
    with engine.begin() as conn:
        conn.execute(text(f'CREATE TABLE IF NOT EXISTS "{schema}".alembic_version (…)'))
        conn.execute(text(f'INSERT INTO "{schema}".alembic_version VALUES (:r) '
                          f'ON CONFLICT DO NOTHING'), {'r': head})
```

A freshly provisioned schema is therefore **immediately at the migration head**
— no migration replay needed for new schools.

Provision via the API (`POST /api/v1/superadmin/schools/`) or the CLI:

```bash
flask provision-school --slug greenwood-high --name "Greenwood High" \
  --admin-email admin@greenwood.edu --admin-password "Admin@1234"
```

---

## 10. Migrations Across All Schools

Master tables are created at startup (`db.create_all(bind_key=['master'])`) and
are **not** under Alembic. School schemas **are**: each carries its own
`alembic_version`. After authoring a new migration, roll it out to every school:

```bash
flask db migrate -m "add phone_verified to users"   # author the migration
flask db-upgrade-all                                 # apply to every active school
```

`db-upgrade-all` (in `app/cli.py`) iterates active schools and, per schema:

```python
with engine.connect() as conn:
    # read the version table directly from the school schema (reliable)
    current = MigrationContext.configure(
        conn, opts={'version_table_schema': schema}).get_current_revision()
    if current == head:                              # skip schemas already at head
        continue
    # route table ops to the schema + keep alembic_version in the schema
    routed = conn.execution_options(schema_translate_map={None: schema})
    cfg.attributes['connection'] = routed
    cfg.attributes['version_table_schema'] = schema
    alembic_command.upgrade(cfg, 'head')
```

`migrations/env.py` honors `cfg.attributes['connection']` and
`version_table_schema` so Alembic operates inside the target schema. Migrations
still use `batch_alter_table` (a SQLite-era pattern) — harmless on PostgreSQL,
kept for history continuity.

---

## 11. Frontend: Two Separate Auth Services

```
localStorage
├── sms_access_token / sms_refresh_token / sms_user / sms_school_slug   ← AuthService
└── sms_sa_access_token / sms_sa_refresh_token / sms_sa_user            ← SuperAdminAuthService
```

- **School login** sends `{ email, password, school_slug }`; the slug is
  persisted to `localStorage.sms_school_slug` and pre-filled next time.
- **Super-admin login** sends `{ email, password }` only.
- The **JWT interceptor** auto-attaches the school token and runs 401→refresh,
  but **skips `/superadmin/*`**; the super-admin `SchoolsService` sets its
  `Authorization` header manually from `SuperAdminAuthService`.

See [frontend-architecture.md](frontend-architecture.md) for the full SPA map.

---

## 12. Adding a School-Scoped Feature (Checklist)

**Backend**
1. Add the model — **no** `__bind_key__`, **no** `schema=` (it's tenant-scoped).
2. `flask db migrate -m "add <table>"` then `flask db-upgrade-all`.
3. In the service, query through `get_db()` — never `db.session`.
4. Guard the route with `@roles_required(...)`.

**Frontend** — nothing tenant-specific: the school JWT already carries
`school_slug`, so every call hits the right schema automatically.

---

## 13. Common Mistakes to Avoid

| Mistake | Why it breaks | Fix |
|---|---|---|
| `SET search_path` anywhere | Leaks onto pooled connections → wrong schema / `relation does not exist` | Use `schema_translate_map` or schema-qualified names |
| `db.session` in a tenant route | Bypasses the tenant session; hits `public` (no school tables) | Always `get_db()` |
| Querying `School` via `get_db()` | `School` is master-bound (public) | Use `School.query` / `db.session` |
| `flask db upgrade` after a migration | Only the connected schema | `flask db-upgrade-all` |
| Omitting `school_slug` at login | Middleware can't pick a schema | Always send it to `/api/v1/auth/login` |
| Storing the SA token as `sms_access_token` | Interceptor treats it as a school token | SA token lives in `sms_sa_access_token` |

---

## 14. Quick Reference

```bash
# provision a school
flask provision-school --slug greenwood-high --name "Greenwood High" \
  --admin-email admin@greenwood.edu --admin-password "Admin@1234"

# apply pending migrations to every school schema
flask db-upgrade-all

# seed the master registry + a demo school (super admin + demo school schema)
python database/seeds/seed_master.py
```

```
API namespaces
  /api/v1/superadmin/*    → super admin only (public registry)
  /api/v1/auth/*          → school users (needs school_slug at login)
  /api/v1/<module>/*      → school users (tenant schema via JWT school_slug)
```

> Operational gotchas (psycopg 3 on Python 3.14, Neon **direct** endpoint vs
> the `-pooler`, `search_path` pinning, `version_table_schema`) are recorded in
> [ADR-004](adr-004-postgresql-schema-per-school.md).
