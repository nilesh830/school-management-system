# SMS — System Architecture Overview
**Author:** @solution-architect | **Date:** 2026-06-06 (rev. 2026-06-24) | **Status:** Accepted

> **Multi-tenant ERP.** One deployment serves many schools. Data is isolated
> per school using **PostgreSQL schema-per-school** — see
> [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) and
> [ADR-004](adr-004-postgresql-schema-per-school.md). Frontend portals are
> detailed in [frontend-architecture.md](frontend-architecture.md).

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Angular 17+ SPA (PrimeNG + PrimeFlex)           │  │
│  │                                                              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  /admin  │ │ /teacher │ │ /student │ │/parent +     │  │  │
│  │  │  module  │ │  module  │ │  module  │ │ /superadmin  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  │                                                              │  │
│  │  core/ (guards, interceptors, auth.service)                 │  │
│  │  shared/ (components, pipes, directives)                    │  │
│  └──────────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                    HTTPS + JWT Bearer
                              │
┌─────────────────────────────────────────────────────────────────────┐
│                         API LAYER                                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │               Python Flask 3.x REST API                      │  │
│  │                   Base URL: /api/v1/                         │  │
│  │                                                              │  │
│  │  ┌────────────┐  ┌─────────────┐  ┌──────────────────────┐  │  │
│  │  │  Routes    │  │  Services   │  │       Utils          │  │  │
│  │  │ (Blueprints│  │ (Business   │  │ response.py          │  │  │
│  │  │ Controllers│  │  Logic)     │  │ decorators.py        │  │  │
│  │  └────────────┘  └─────────────┘  └──────────────────────┘  │  │
│  │                                                              │  │
│  │  Flask-JWT-Extended │ Flask-Bcrypt │ Flask-Limiter          │  │
│  │  Flask-CORS         │ Flask-Migrate│ Marshmallow            │  │
│  └──────────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                        SQLAlchemy ORM
                              │
┌─────────────────────────────────────────────────────────────────────┐
│                  DATABASE LAYER  (PostgreSQL)                        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │   ONE PostgreSQL database · schema-per-school multi-tenancy   │  │
│  │                                                              │  │
│  │  public schema (master registry)                            │  │
│  │     schools │ super_admins │ super_admin_revoked_tokens      │  │
│  │                                                              │  │
│  │  school_<slug> schema  (one per school, ~34 tables)         │  │
│  │     users │ students │ teachers │ parents │ classes │ …      │  │
│  │     attendance │ exams │ fee_records │ announcements │ books │  │
│  │                                                              │  │
│  │  routing: SQLAlchemy schema_translate_map (per request)     │  │
│  └──────────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────┘
```

> Dev/test uses in-memory SQLite via the `TESTING` bypass; all runtime tenancy
> runs on PostgreSQL. Driver: **psycopg 3** (`postgresql+psycopg://`).

---

## Layered Architecture (Backend)

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────┐
│  Route (Blueprint)                  │  ← Parse request, auth check, call service
│  routes/students.py                 │  ← NO business logic here
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Service                            │  ← All business logic lives here
│  services/student_service.py        │  ← Calls models, applies rules
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Model (SQLAlchemy ORM)             │  ← Data mapping only, no logic
│  models/student.py                  │  ← to_dict(), relationships
└─────────────────┬───────────────────┘
                  │   query via get_db() → tenant session
                  ▼
┌─────────────────────────────────────┐
│  PostgreSQL — school_<slug> schema  │  ← routed by schema_translate_map
└─────────────────────────────────────┘
```

> Services and routes never use `db.session` directly for school data — they go
> through `get_db()`, which returns the request's tenant session (the schema
> chosen from the JWT's `school_slug`). See
> [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) §5.

---

## Authentication & Authorization Flow

```
         School user                          Super admin
    POST /api/v1/auth/login            POST /api/v1/superadmin/auth/login
    { email, password, school_slug }   { email, password }
              │                                   │
        verify slug (public.schools)              │
        verify email+bcrypt (school schema)  verify email+bcrypt (public.super_admins)
              │                                   │
              ▼                                   ▼
   JWT claims: { role, user_id,          JWT claims: { role: super_admin,
     school_slug, parent_id? }             super_admin_id }   (NO school_slug)
   identity "42"                          identity "sa:1"
   access 15min · refresh 7d             access 15min · refresh 7d
              │                                   │
   ┌──────────┼──────────┬─────────┐             ▼
   ▼          ▼          ▼         ▼        /superadmin/*
 admin     teacher    student    parent    (SA portal, public registry)
 /admin/*  /teacher/* /student/* /parent/*  @roles_required('super_admin')
   @roles_required(...) per route; tenant middleware opens school_<slug> schema
```

> The `school_slug` claim is what the tenant middleware reads on every request
> to select the school's PostgreSQL schema. Super-admin tokens have no slug and
> operate on the `public` registry only.

---

## Parent Portal — Data Isolation Architecture

```
Parent User (JWT)
      │
      │  token claims: { role: "parent", parent_id: 3 }
      │
      ▼
GET /api/v1/parent-portal/children/:child_id/attendance
      │
      ▼
┌─────────────────────────────────────────────┐
│  ParentPortalService._verify_child_access() │  ◄─── MUST run first
│                                             │
│  SELECT * FROM student_parent               │
│  WHERE parent_id = 3                        │
│    AND student_id = :child_id               │
│                                             │
│  if NOT FOUND → abort(403)                  │
└─────────────────┬───────────────────────────┘
                  │ found → proceed
                  ▼
       Load attendance for child_id
       Return data to parent
```

**Rule:** No Parent Portal service method ever skips `_verify_child_access()`.
A parent can only see data for students in their own `student_parent` rows.

---

## Module Dependency Map

```
EPIC-01 Auth
   └── EPIC-02 Student Management
          ├── EPIC-03 Teacher Management
          ├── EPIC-04 Class & Section ──────────┐
          │      └── EPIC-05 Attendance          │
          │              └── EPIC-08/09 Parent Portal (reads attendance)
          │                                      │
          ├── EPIC-06 Grades & Exams ────────────┤
          │              └── EPIC-08/09 Parent Portal (reads grades)
          │                                      │
          └── EPIC-07 Fee Management ────────────┘
                         └── EPIC-08/09 Parent Portal (reads fees)

EPIC-10 Communication → feeds into Parent Portal notices
EPIC-11 Reports → aggregates ALL modules
EPIC-12 Transport → standalone, integrates with Fee (transport fee)
```

---

## Request / Response Lifecycle

```
Angular Component
  → calls Service (e.g. StudentService.getStudents())
  → HttpClient.get('/api/v1/students')
  → JWT Interceptor adds Authorization header
  → Flask Route receives request
  → @roles_required checks JWT role claim
  → validates input (Marshmallow / manual)
  → calls StudentService.get_all()
  → queries SQLAlchemy ORM
  → returns paginated result dict
  → success_response(data=result)
  → { success: true, data: {...}, message: "...", errors: null }
  → Angular component maps response to component state
  → PrimeNG table renders rows
```

---

## Non-Functional Requirements

| Requirement | Target | How Achieved |
|------------|--------|-------------|
| API Response Time | < 200ms (p95) | DB indexes, query optimization, pagination |
| Auth Security | Brute-force protected | Flask-Limiter: 5 login attempts/minute |
| Password Storage | bcrypt (rounds=12) | Flask-Bcrypt |
| Token Expiry | 15min access, 7d refresh | Flask-JWT-Extended config |
| Tenant Isolation | One school never sees another's data | PostgreSQL schema-per-school; `schema_translate_map` per request |
| Concurrency | Multi-user writes | PostgreSQL MVCC (replaced single-writer SQLite) |
| Data Isolation | Parent sees only own children | `_verify_child_access()` in every portal service |
| Input Validation | All endpoints validated | Marshmallow schemas |
| CORS | Allowlist only | Flask-CORS with explicit origins |
| Secrets | Never in code | `.env` file + GitHub Secrets |
| Coverage | ≥ 80% backend, ≥ 75% frontend | pytest-cov + Karma |
| Mobile | Parent Portal 375px+ | PrimeFlex responsive grid |
