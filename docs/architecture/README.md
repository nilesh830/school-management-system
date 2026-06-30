# SMS — Architecture Documentation

Entry point for the architecture of the **School Management System (SMS)** — a
multi-tenant school ERP. Start here, then dive into the focused docs below.

---

## System at a Glance

| Layer | Technology |
|---|---|
| Frontend | Angular 17 (standalone) · PrimeNG 17 / PrimeFlex / chart.js · 5 portals |
| API | Python Flask 3 · REST under `/api/v1/` · JWT auth · Marshmallow validation |
| Business logic | Service layer (no logic in routes, no raw SQL in services) |
| ORM | SQLAlchemy 2 |
| Database | **PostgreSQL — schema-per-school multi-tenancy** (psycopg 3) |
| Tests | pytest (≈499 on in-memory SQLite + a PostgreSQL integration suite) |

```
Angular SPA ──HTTPS + JWT (Bearer, carries school_slug)──▶ Flask /api/v1
                                                              │ get_db() → tenant session
                                                              ▼
                              PostgreSQL  (public registry + one schema per school)
```

- **Multi-tenancy:** one PostgreSQL database; master registry in `public`, each
  school in its own `school_<slug>` schema, routed per request via
  `schema_translate_map`.
- **Two auth domains:** school users (`/auth/*`, need `school_slug`) and
  platform super admins (`/superadmin/*`, no slug).
- **RBAC:** `super_admin > admin > teacher > student > parent`.

---

## Document Map

| Doc | What it covers |
|---|---|
| [system-overview.md](system-overview.md) | End-to-end architecture, layered backend, auth/data-isolation flows, NFRs |
| [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) | **Schema-per-school deep dive** — tenant routing, provisioning, migrations, do/don't rules |
| [frontend-architecture.md](frontend-architecture.md) | Angular SPA — portals, dual auth, guards, routing, services → API map |
| [database-schema.md](database-schema.md) | Physical schema layout + every table's columns, constraints, indexes |
| [adr-001-tech-stack.md](adr-001-tech-stack.md) | Why Flask / SQLAlchemy / Angular / PrimeNG / JWT (DB row amended) |
| [adr-002-parent-portal.md](adr-002-parent-portal.md) | Parent Portal design & data-isolation decision |
| [adr-003-jwt-rbac.md](adr-003-jwt-rbac.md) | JWT structure, roles, and RBAC enforcement |
| [adr-004-postgresql-schema-per-school.md](adr-004-postgresql-schema-per-school.md) | **The SQLite → PostgreSQL schema-per-school migration** (rationale + gotchas) |
| [adr-005-fee-applicability.md](adr-005-fee-applicability.md) | Fee applicability — optional/opt-in fees, transport per-student fares (SMS-066, _Proposed_) |
| [../api/api-reference.md](../api/api-reference.md) | Full REST endpoint reference (request/response envelopes) |
| [../api/postman-collection-guide.md](../api/postman-collection-guide.md) | Postman usage |

---

## Core Modules

Authentication · Student Mgmt · Teacher Mgmt · Class & Section · Attendance ·
Exams & Grades · Fees (structures/payments/discounts/defaulters) · Communication
(announcements/notifications) · Library · Transport · Reports & Analytics ·
**Parent Portal** · **ERP Platform Mgmt (Super Admin)**.

---

## Backend Layout (reference)

```
backend/app/
├── __init__.py     create_app(): extensions, blueprints, JWT handlers, tenant hooks
├── config.py       config classes, DB URL normalization, engine options
├── cli.py          provision-school, db-upgrade-all
├── models/         SQLAlchemy models (master/ = public; rest = per-school)
├── routes/         ~25 blueprints under /api/v1/*
├── services/       business logic (queries via get_db())
├── schemas/        Marshmallow validation
└── utils/          tenant.py (routing), decorators (@roles_required),
                    response (envelope), cache, excel
```

See [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) for how a request is routed to a
school's schema, and [adr-004](adr-004-postgresql-schema-per-school.md) for the
operational details (psycopg 3, direct cloud endpoint, `search_path`,
`version_table_schema`).

---

## Conventions

- **No business logic in routes** — use the service layer.
- **No raw SQL** in services — SQLAlchemy ORM via `get_db()`.
- **All input validated** with Marshmallow; **passwords** bcrypt-hashed.
- **Every route** guarded by `@jwt_required()` / `@roles_required(...)` (only
  `/health`, login, and password-reset are public).
- **Never `SET search_path`** — tenant routing is `schema_translate_map` only.
- Responses use the envelope `{ success, data, message, errors }`.
