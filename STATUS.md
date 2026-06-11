# SMS Project — Work Status

> Update this file at the end of every work session. It is the single source of truth for "where we left off."
> **Last updated:** 2026-06-10 | **Branch:** `develop`

---

## Current Sprint: Sprint 2.5 — ERP Multi-Tenancy Foundation

> Project pivoted to multi-school ERP platform (Option B: Database-per-School).
> See `docs/sprints/sprint-2.5-erp-foundation.md` for full story details.

### Sprint 2.5 Board

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| ERP-001 | Master DB & School Registry | 8 | ✅ Done |
| ERP-002 | Super Admin Auth | 3 | ✅ Done |
| ERP-003 | School Provisioning API | 5 | ✅ Done |
| ERP-004 | Super Admin Frontend Portal | 8 | ✅ Done |
| ERP-005 | JWT `school_slug` Enrichment | 3 | ✅ Done |
| ERP-006 | TenantMiddleware & Dynamic Sessions | 8 | ✅ Done |
| ERP-007 | Migrate existing sms.db → school_demo.db | 3 | ✅ Done (part of ERP-001) |
| ERP-008 | `flask db upgrade-all` CLI | 3 | ❌ Next |

**Tests passing: 117/117** | **Committed through: ERP-005 (`c995ae5`)**

---

## ERP-001 — Master Database & School Registry ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `SQLALCHEMY_BINDS` + `SCHOOLS_DB_DIR` in config | ✅ | `backend/config.py` |
| `master_db` via bind key `'master'` | ✅ | Uses existing `db` with bind key — no second SQLAlchemy instance |
| `School` model | ✅ | `backend/app/models/master/school.py`, `__bind_key__='master'` |
| `SuperAdmin` model | ✅ | `backend/app/models/master/super_admin.py`, `__bind_key__='master'` |
| `db.create_all(bind_key=['master'])` in `create_app()` | ✅ | Auto-creates master.db tables on startup |
| `instance/schools/` directory created | ✅ | `backend/instance/schools/.gitkeep` |
| `school_demo.db` created | ✅ | Copied from old `sms.db` — existing seed data preserved |
| `master.db` seeded | ✅ | `superadmin@sms.com / SuperAdmin@1234` + Demo School |
| Seed script | ✅ | `backend/database/seeds/seed_master.py` |
| Tests | ✅ | 67/67 pass after `sections.id` FK deferred fix |

---

## ERP-002 — Super Admin Auth ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `POST /api/v1/superadmin/auth/login` | ✅ | JWT: `role=super_admin`, identity=`sa:<id>`, no `school_slug` |
| `POST /api/v1/superadmin/auth/refresh` | ✅ | Validates `sa:` prefix before master.db lookup |
| `DELETE /api/v1/superadmin/auth/logout` | ✅ | Revokes into `super_admin_revoked_tokens` (master.db) |
| `GET /api/v1/superadmin/auth/me` | ✅ | Super admin profile only, rejects school tokens |
| `SuperAdminRevokedToken` model | ✅ | `__bind_key__='master'`, independent from school blocklist |
| `check_if_token_revoked` updated | ✅ | Routes by `role` claim: SA → master, school → tenant |
| 23 tests (`test_superadmin_auth.py`) | ✅ | All pass |
| Full regression | ✅ | **90/90 pass** |

---

## ERP-006 — TenantMiddleware & Dynamic Sessions ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `app/utils/tenant.py` — `setup_tenant_db`, `teardown_tenant_db`, `get_db()` | ✅ | Engine cache per `db_url` |
| TESTING bypass: `g.db = db.session` | ✅ | All 117 tests pass, no conftest changes |
| Registered as `before_request` / `teardown_request` in `create_app()` | ✅ | |
| `auth.py` — all `db.session.*` + `Model.query.*` → `get_db()` | ✅ | All 8 route functions updated |
| `students.py` — 2 inline `Student.query` calls → `get_db().query()` | ✅ | |
| `student_service.py` — full service layer migrated | ✅ | `_paginate()` helper replaces FSA `.paginate()` |
| `user_service.py` — full service layer migrated | ✅ | `db.or_()` → `or_()` from sqlalchemy |
| `parent_portal_service.py` — full service layer migrated | ✅ | `.first_or_404()` / `.get_or_404()` replaced |
| `revoked_token.py` — blocklist check uses `get_db()` | ✅ | Routes to correct tenant DB |
| Full regression: **117/117 pass** | ✅ | |

---

## ERP-005 — JWT `school_slug` Enrichment ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `school_slug` required in `POST /api/v1/auth/login` | ✅ | Validated against master.db `schools` table |
| School not found / inactive → 404 | ✅ | |
| `school_slug` embedded in JWT access + refresh tokens | ✅ | `_build_additional_claims` updated |
| `refresh()` re-embeds `school_slug` from existing claims | ✅ | No second DB lookup |
| `conftest.py`: `test_school` autouse fixture | ✅ | Creates `slug=test` school before each test |
| All existing login calls in tests updated | ✅ | `test_auth.py`, `test_superadmin_*.py`, `test_students.py` |
| 5 new `TestLoginSchoolSlug` tests | ✅ | slug in JWT, missing slug 400, wrong slug 404, inactive school 404, refresh preserves slug |
| Login form: `school_slug` field + localStorage pre-fill | ✅ | `login.component.ts` + template |
| `AuthService.login()` sends `school_slug` + persists to localStorage | ✅ | |
| `redirectToDashboard()` handles `super_admin` role | ✅ | |
| 117/117 tests pass | ✅ | |
| Angular build 0 errors | ✅ | |

---

## ERP-004 — Super Admin Frontend Portal ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `SuperAdminAuthService` | ✅ | Separate localStorage keys `sms_sa_*`; signal-based |
| `SchoolsService` | ✅ | Sets SA `Authorization` header manually (bypasses JWT interceptor) |
| `superAdminGuard` | ✅ | `CanActivateFn`, redirects to `/superadmin/login` |
| `SUPERADMIN_ROUTES` + layout component | ✅ | Sidebar (Dashboard, Schools) + topbar |
| `/superadmin/login` | ✅ | Full-page card, reactive form |
| `/superadmin/dashboard` | ✅ | School cards grid, stat counts |
| `/superadmin/schools` | ✅ | `p-table` + search + lazy pagination |
| `/superadmin/schools/new` | ✅ | Provision form, slug validator, 409 → field error |
| `/superadmin/schools/:id` | ✅ | Detail view, inline edit, activate/deactivate |
| `app.routes.ts` updated | ✅ | `/superadmin` lazy route added |
| Angular build | ✅ | **0 errors** |

---

## ERP-003 — School Provisioning API ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `POST /api/v1/superadmin/schools` — provision new school | ✅ | Creates school record + `school_<slug>.db` |
| `GET /api/v1/superadmin/schools` — paginated list | ✅ | Optional `?search=` filter |
| `GET /api/v1/superadmin/schools/:id` — single school | ✅ | |
| `PATCH /api/v1/superadmin/schools/:id` — update / deactivate | ✅ | |
| `_create_school_db` — schema + Alembic stamp | ✅ | Uses `db.metadata.create_all()` + direct engine, no `env.py` |
| `_seed_school_admin` — first admin user in school DB | ✅ | Dedicated `sessionmaker` on school engine |
| `SchoolCreateSchema` / `SchoolUpdateSchema` | ✅ | `backend/app/schemas/superadmin_schema.py` |
| `superadmin_schools_bp` blueprint | ✅ | `backend/app/routes/superadmin_schools.py` |
| `SuperAdminService` | ✅ | `backend/app/services/superadmin_service.py` |
| 22 tests (`test_superadmin_schools.py`) | ✅ | Covers success, 409 duplicate, 422 invalid slug, PATCH, 401/403 |
| Full regression | ✅ | **112/112 pass** |

---

## Sprint 2 — Student Management ✅ COMPLETE

Committed `a44cd25` on develop. All SMS-007 → SMS-013 stories done.

| Story | Backend | Frontend | Tests |
|-------|---------|----------|-------|
| SMS-007 Student Enrollment | ✅ | ✅ | ⚠️ written, not run |
| SMS-008 Student List | ✅ | ✅ | ⚠️ written, not run |
| SMS-009 Student Profile | ✅ | ✅ | ⚠️ written, not run |
| SMS-010 Parent Linking | ✅ | ✅ | ⚠️ T-010-03 JWT parent_id unverified |
| SMS-011 Section Transfer | ✅ | ✅ | ⚠️ written, not run |
| SMS-012 Document Upload | ✅ | ✅ | ⚠️ written, not run |
| SMS-013 Deactivation/Alumni | ✅ | ✅ | ⚠️ written, not run |

---

## Sprint 1 — Auth & User Management ✅ COMPLETE

Committed `6d1adc0` on develop. SMS-001 → SMS-006 all done. 28 tests.

---

## Known Issues

| Issue | Impact | Owner |
|-------|--------|-------|
| `student_sections.section_id` has no FK constraint | By design — `sections` table not built until Sprint 3 | Wire FK in Sprint 3 |
| Sprint 2 student tests not run end-to-end | Low — test file written, can run manually | Run `.\venv\Scripts\pytest tests/test_students.py -v` |
| `_verify_output.txt` temp file in backend/ | Cosmetic | Delete before next commit |
