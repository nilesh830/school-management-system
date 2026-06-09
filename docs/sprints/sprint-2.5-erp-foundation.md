# Sprint 2.5 — ERP Multi-Tenancy Foundation
**Dates:** After Sprint 2 close  
**Sprint Goal:** Transform the single-school SMS into a multi-school ERP platform with complete data isolation per school and a Super Admin portal to manage all schools.  
**Velocity Target:** 41 pts | **Prerequisite:** Sprint 2 fully committed + tests green

---

## Why This Sprint Exists

The product pivoted from a single-school SMS to a multi-school ERP platform. Every school gets its own isolated database. A Super Admin (platform-level role above all school admins) manages school provisioning and sees aggregate stats across all schools.

**Architecture chosen:** Option B — Database-per-School  
- `master.db` → school registry + super admin accounts  
- `school_<slug>.db` → full SMS schema, one per school  
- `TenantMiddleware` → resolves `school_slug` from JWT → injects `g.db` session  

---

## Sprint Board

| Story | Title | Points | Assignee | Status |
|-------|-------|--------|----------|--------|
| ERP-001 | Master DB & School Registry | 8 | @database-engineer + @backend-engineer | To Do |
| ERP-002 | TenantMiddleware & Dynamic Sessions | 8 | @backend-engineer | To Do |
| ERP-003 | School Provisioning API | 5 | @backend-engineer | To Do |
| ERP-004 | Super Admin Auth | 3 | @backend-engineer | To Do |
| ERP-005 | JWT `school_slug` Enrichment | 3 | @backend-engineer | To Do |
| ERP-006 | Super Admin Frontend Portal | 8 | @frontend-engineer | To Do |
| ERP-007 | Migrate Existing School Data | 3 | @database-engineer | To Do |
| ERP-008 | `flask db upgrade-all` CLI | 3 | @backend-engineer + @database-engineer | To Do |

**Total: 41 pts**

---

## Stories — Full Detail

---

### ERP-001: Master Database & School Registry
**Points:** 8 | **Priority:** Must | **Assignee:** @database-engineer + @backend-engineer

**User Story:**
> As a super admin, I want a central school registry, so that I can see and manage all schools on the platform.

**Acceptance Criteria:**
- [ ] `master.db` is separate from any school DB
- [ ] `schools` table: id, name, slug (unique, indexed), db_url, address, phone, email, logo_url, is_active, created_at, academic_year_start_month
- [ ] `super_admins` table: id, email (unique), password_hash, first_name, last_name, is_active, created_at
- [ ] Master DB has its own SQLAlchemy instance (`master_db`) in `app/__init__.py`
- [ ] Models live in `app/models/master/school.py` and `app/models/master/super_admin.py`
- [ ] Seed: one default super admin (`superadmin@sms.com / SuperAdmin@1234`) + demo school pointing to existing `sms.db`

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-001-01 | Create `master_db` SQLAlchemy instance, initialize in `create_app()` | 1h |
| T-ERP-001-02 | Write `School` model + migration for master.db | 1h |
| T-ERP-001-03 | Write `SuperAdmin` model + migration for master.db | 1h |
| T-ERP-001-04 | Seed script for master.db (super admin + demo school) | 1h |

---

### ERP-002: TenantMiddleware & Dynamic Sessions
**Points:** 8 | **Priority:** Must | **Assignee:** @backend-engineer

> ⚠️ **Critical story** — touches all existing routes. Run full test suite after this merges.

**User Story:**
> As the platform, I need to route every API request to the correct school's database, so that data never crosses school boundaries.

**Acceptance Criteria:**
- [ ] `TenantMiddleware` reads `school_slug` from JWT on every request (except superadmin routes and auth)
- [ ] Looks up school in master.db → fetches `db_url`
- [ ] Creates/reuses scoped SQLAlchemy session → stored in `flask.g.db`
- [ ] All service files updated to use `g.db.session` instead of `db.session`
- [ ] SuperAdmin routes (`/api/v1/superadmin/*`) bypass tenant middleware
- [ ] Invalid/missing `school_slug` → HTTP 400
- [ ] All existing Sprint 2 tests still pass after this change

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-002-01 | Write `TenantMiddleware` in `app/utils/tenant.py` | 2h |
| T-ERP-002-02 | Register middleware in `create_app()` | 0.5h |
| T-ERP-002-03 | Update all service files to use `g.db.session` | 2h |
| T-ERP-002-04 | Update all route files using `db` directly | 1h |
| T-ERP-002-05 | Run full test suite, fix regressions | 2h |

---

### ERP-003: School Provisioning API
**Points:** 5 | **Priority:** Must | **Assignee:** @backend-engineer

**User Story:**
> As a super admin, I want to register a new school, so that the school can start using the platform with full data isolation.

**Acceptance Criteria:**
- [ ] `POST /api/v1/superadmin/schools` → creates school record, creates `school_<slug>.db`, runs migrations, seeds first admin user, returns school details
- [ ] `GET /api/v1/superadmin/schools` → paginated list of all schools with stats
- [ ] `GET /api/v1/superadmin/schools/:id` → single school detail
- [ ] `PATCH /api/v1/superadmin/schools/:id` → activate / deactivate school
- [ ] Duplicate slug → HTTP 409
- [ ] All routes require `@roles_required('super_admin')`

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-003-01 | `SuperAdminService.provision_school()` — create DB + run migrations + seed admin | 2h |
| T-ERP-003-02 | Blueprint `superadmin_bp` with all CRUD routes | 1.5h |
| T-ERP-003-03 | Marshmallow schema for school create/update | 0.5h |
| T-ERP-003-04 | Tests: provision, duplicate slug, deactivate | 1h |

---

### ERP-004: Super Admin Auth
**Points:** 3 | **Priority:** Must | **Assignee:** @backend-engineer

**User Story:**
> As a super admin, I want a dedicated login, so that my access is not tied to any school.

**Acceptance Criteria:**
- [ ] `POST /api/v1/superadmin/auth/login` → authenticates against `super_admins` table in master.db
- [ ] JWT contains `role: "super_admin"` and no `school_slug`
- [ ] `@roles_required('super_admin')` decorator correctly validates this JWT
- [ ] Regular school login still works — super admin login is entirely separate

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-004-01 | Super admin login route (uses master_db, not tenant) | 1h |
| T-ERP-004-02 | Update `@roles_required` to accept `super_admin` as a valid role | 0.5h |
| T-ERP-004-03 | Tests: login success, wrong password, role in JWT | 0.5h |

---

### ERP-005: JWT `school_slug` Enrichment
**Points:** 3 | **Priority:** Must | **Assignee:** @backend-engineer

**User Story:**
> As the platform, I need the school identity embedded in every JWT, so that TenantMiddleware can resolve the correct database without an extra lookup per request.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/login` now requires `school_slug` in the request body
- [ ] JWT `additional_claims` include `school_slug` for all school-level roles (admin, teacher, student, parent)
- [ ] TenantMiddleware reads `school_slug` from JWT — no URL prefix needed
- [ ] Frontend stores `school_slug` in localStorage after login and pre-fills it on the login form

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-005-01 | Add `school_slug` to login request + validate against master.db | 1h |
| T-ERP-005-02 | Add `school_slug` to JWT `additional_claims` | 0.5h |
| T-ERP-005-03 | Update login form (FE) to include school slug field | 0.5h |
| T-ERP-005-04 | Tests: login with slug, login with wrong slug | 0.5h |

---

### ERP-006: Super Admin Frontend Portal
**Points:** 8 | **Priority:** Must | **Assignee:** @frontend-engineer

**User Story:**
> As a super admin, I want a dashboard showing all schools and key metrics, so that I can monitor and manage the platform.

**Acceptance Criteria:**
- [ ] `/superadmin/login` — dedicated login page (uses superadmin auth endpoint)
- [ ] `/superadmin/dashboard` — cards per school: name, status, student count, last active
- [ ] `/superadmin/schools` — searchable table of all schools
- [ ] `/superadmin/schools/new` — provision form (name, slug, admin email)
- [ ] `/superadmin/schools/:id` — school detail with activate/deactivate button
- [ ] SuperAdmin layout: separate from admin/teacher/student/parent layouts
- [ ] `SuperAdminGuard` protects all `/superadmin/*` routes

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-006-01 | Super admin Angular module + layout + routes | 1h |
| T-ERP-006-02 | Super admin login page + `SuperAdminService` | 1h |
| T-ERP-006-03 | `SuperAdminGuard` | 0.5h |
| T-ERP-006-04 | Schools list page with p-table | 1.5h |
| T-ERP-006-05 | School provisioning form | 1.5h |
| T-ERP-006-06 | School detail page + activate/deactivate | 1h |

---

### ERP-007: Migrate Existing School Data
**Points:** 3 | **Priority:** Must | **Assignee:** @database-engineer

**User Story:**
> As the team, we need the existing `sms.db` to be treated as the "demo school" under the new multi-tenant structure, so that Sprint 2 work is not lost.

**Acceptance Criteria:**
- [ ] Existing `backend/instance/sms.db` becomes `backend/instance/schools/school_demo.db`
- [ ] `master.db` created with one school record: `name=Demo School, slug=demo, db_url=sqlite:///instance/schools/school_demo.db`
- [ ] All existing tests updated to target the demo school DB
- [ ] No data loss

**Tasks:**
| # | Task | Est. |
|---|------|------|
| T-ERP-007-01 | Create `instance/schools/` directory, move/rename `sms.db` | 0.5h |
| T-ERP-007-02 | Update `config.py` default DB URL to point to new path | 0.5h |
| T-ERP-007-03 | Update test fixtures to use demo school slug | 1h |
| T-ERP-007-04 | Verify all existing tests pass after move | 1h |

---

### ERP-008: `flask db upgrade-all` CLI
**Points:** 3 | **Priority:** Must | **Assignee:** @backend-engineer + @database-engineer

**User Story:**
> As the DevOps team, I want a single command that runs database migrations on ALL school databases, so that schema updates are applied uniformly.

**Acceptance Criteria:**
- [ ] `flask db-upgrade-all` iterates all active schools in master.db
- [ ] Runs Alembic `upgrade head` on each school's DB
- [ ] Prints status per school (success / already up to date / error)
- [ ] Failures on one school do not stop the others (report all errors at end)
- [ ] `flask provision-school --slug <slug> --name <name> --admin-email <email>` creates + migrates a new school DB

---

## Definition of Done (Sprint 2.5)

- [ ] All 8 ERP stories accepted
- [ ] All existing Sprint 2 tests pass (regression gate — no exceptions)
- [ ] New super admin login tested end-to-end
- [ ] School provisioning creates a working, isolated school DB
- [ ] `flask db-upgrade-all` runs cleanly on demo school
- [ ] Angular build passes with no errors
- [ ] Sprint 2 committed to `develop` BEFORE Sprint 2.5 begins

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| TenantMiddleware breaks existing routes | High | High | Run full test suite after ERP-002; fix all regressions before continuing |
| `g.db` pattern requires touching every service file | High | Medium | Do as one PR, review carefully |
| SQLite file path issues on Windows | Medium | Low | Use `os.path.join` + absolute paths |
| Performance: new DB connection per request | Medium | Medium | Use `g.db` caching + connection pool per school |
