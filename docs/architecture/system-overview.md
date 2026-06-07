# SMS — System Architecture Overview
**Author:** @solution-architect | **Date:** 2026-06-06 | **Status:** Accepted

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
│  │  │  /admin  │ │ /teacher │ │ /student │ │   /parent    │  │  │
│  │  │  module  │ │  module  │ │  module  │ │ portal module│  │  │
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
│                       DATABASE LAYER                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   SQLite3  (sms.db)                          │  │
│  │              [Production path: PostgreSQL]                   │  │
│  │                                                              │  │
│  │  users │ students │ teachers │ parents │ classes │ sections  │  │
│  │  attendance │ exams │ exam_results │ fee_records │ payments  │  │
│  │  leave_applications │ notifications │ announcements │ books   │  │
│  └──────────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────┘
```

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
                  │
                  ▼
┌─────────────────────────────────────┐
│  SQLite3 Database (sms.db)          │
└─────────────────────────────────────┘
```

---

## Authentication & Authorization Flow

```
                    ┌─────────┐
                    │  Login  │
                    └────┬────┘
                         │ POST /api/v1/auth/login
                         ▼
                ┌────────────────┐
                │  Verify email  │
                │  + bcrypt pwd  │
                └───────┬────────┘
                        │ valid
                        ▼
              ┌──────────────────────┐
              │  Generate JWT tokens │
              │  access_token: 15min │
              │  refresh_token: 7d   │
              │  claims: {role,      │
              │   user_id,parent_id} │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      role=admin    role=teacher   role=parent
          │              │              │
    /admin/*        /teacher/*    /parent/*
    (Admin layout)  (Teacher UI)  (Parent Portal)
          │              │              │
    @roles_required  @roles_required  @roles_required
    ('admin')       ('admin','teacher') ('parent')
```

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
| Data Isolation | Parent sees only own children | `_verify_child_access()` in every portal service |
| Input Validation | All endpoints validated | Marshmallow schemas |
| CORS | Allowlist only | Flask-CORS with explicit origins |
| Secrets | Never in code | `.env` file + GitHub Secrets |
| Coverage | ≥ 80% backend, ≥ 75% frontend | pytest-cov + Karma |
| Mobile | Parent Portal 375px+ | PrimeFlex responsive grid |
