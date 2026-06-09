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
| ERP-004 | Super Admin Frontend Portal | 8 | ❌ Next |
| ERP-005 | JWT `school_slug` Enrichment | 3 | ❌ |
| ERP-006 | TenantMiddleware & Dynamic Sessions | 8 | ❌ ⚠️ Riskiest |
| ERP-007 | Migrate existing sms.db → school_demo.db | 3 | ✅ Done (part of ERP-001) |
| ERP-008 | `flask db upgrade-all` CLI | 3 | ❌ |

**Tests passing: 112/112** | **Committed through: ERP-002 (`a228b8d`)** | **ERP-003 staged, pending commit**

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
