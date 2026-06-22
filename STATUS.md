# SMS Project — Work Status

> Update this file at the end of every work session. It is the single source of truth for "where we left off."
> **Last updated:** 2026-06-22 (session 13) | **Branch:** `develop`

---

## Current Sprint: Sprint 10 — Reports & Analytics

> See `docs/sprints/sprint-9-to-11.md` for full story details.
> Sprint 9 Communication & Library is complete — see archived section below.

> **Agent Assignment Convention (Sprint 4+):**
> Each task in the sprint docs now carries an explicit agent label:
> - Database (models/migrations) → invoke `@database-engineer`
> - API / services / tests → invoke `@backend-engineer`
> - Angular UI / components → invoke `@frontend-engineer`
> - Security audit → invoke `@security-engineer`
> - CI/CD / Docker → invoke `@devops-engineer`

---

## Sprint 9 Board — ✅ COMPLETE

See `docs/sprints/sprint-9-to-11.md` for full story details.

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| SMS-051 | Create & Publish Announcements | 5 | ✅ Done |
| SMS-052 | Targeted Notices (by Class/Role) | 5 | ✅ Done |
| SMS-053 | Book Catalog Management | 5 | ✅ Done |
| SMS-054 | Book Issue & Return | 8 | ✅ Done |
| SMS-055 | Overdue Fines Calculation | 3 | ✅ Done |
| SMS-045 | School Notice Board (Parent View) — *deferred from Sprint 7, now unblocked* | 3 | ✅ Done |

### Backend
| Item | File |
|------|------|
| `Announcement` model (JSON `target_roles`/`target_class_ids`, status enum) | `backend/app/models/announcement.py` |
| `LibraryBook` model | `backend/app/models/library_book.py` |
| `BookIssue` model (fine, status enum) | `backend/app/models/book_issue.py` |
| Migration `c9a1f0e2b3d4_sprint9_announcements_library` (chains from `1bfdc13b6db1`) | `backend/migrations/versions/` |
| `AnnouncementService` — CRUD, `publish()` + notification dispatch, `get_for_user()` role/class targeting | `backend/app/services/announcement_service.py` |
| `LibraryService` — book CRUD, `issue_book()`, `return_book()` (fine calc ₹5/day), `mark_overdue()`, `get_overdue()` | `backend/app/services/library_service.py` |
| `announcements_bp` (POST/GET/GET:id/PUT/POST:publish; `?role_view=true`) | `backend/app/routes/announcements.py` |
| `library_bp` (books CRUD, issue, return, overdue) | `backend/app/routes/library.py` |
| SMS-045 `GET /api/v1/parent-portal/notices` + `ParentPortalService.get_notices()` | `parent_portal.py` / `parent_portal_service.py` |
| Marshmallow schemas | `backend/app/schemas/announcement_schema.py`, `library_schema.py` |

### Frontend
| Item | Path |
|------|------|
| `AnnouncementService`, `LibraryService` | `frontend/src/app/core/services/` |
| Admin announcement list + create/edit/publish dialog | `frontend/.../admin/announcements/announcement-list/` |
| Admin book catalog (search, copies badge, add/edit, issue) | `frontend/.../admin/library/book-catalog/` |
| Admin issue/return + overdue view | `frontend/.../admin/library/book-issues/` |
| Parent notice board (recent + archived, nav badge) | `frontend/.../parent-portal/notices/notice-board.component.ts` |

> **Note:** Announcement editor uses a plain textarea (not `p-editor`) — the `quill` peer dep isn't installed. To enable rich text later: `npm install quill` and swap to `<p-editor>`.

**Backend test count: 420 passing (0 failures)** — 28 new (`test_announcements.py`, `test_library.py`) | **Angular build: 0 errors**

---

## Sprint 10 Board — ✅ COMPLETE

See `docs/sprints/sprint-9-to-11.md` for full story details.

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| SMS-056 | Admin KPI Dashboard | 8 | ✅ Done |
| SMS-057 | Attendance Analytics Report | 5 | ✅ Done |
| SMS-058 | Academic Performance Report | 5 | ✅ Done |
| SMS-059 | Fee Collection Report | 5 | ✅ Done |
| SMS-060 | Export Reports to PDF/Excel | 5 | ✅ Done |

### Backend
| Item | File |
|------|------|
| `DashboardService.get_admin_kpis()` — totals, today attendance, monthly fee collection, pending leaves, recent announcements, low-attendance (<75%) students, defaulter count (reuses `AttendanceService` + `FeeService`) | `backend/app/services/dashboard_service.py` |
| `ReportService` — `attendance_report()`, `grades_report()`, `fees_report()` + 6 export methods (`export_*_pdf/excel`) | `backend/app/services/report_service.py` |
| Generic xlsx helper `build_xlsx(sheet_title, headers, rows)` | `backend/app/utils/excel.py` |
| `dashboard_bp` — `GET /api/v1/dashboard/admin` (admin) | `backend/app/routes/dashboard.py` |
| `reports_bp` — `GET /api/v1/reports/{attendance,grades,fees}` + `/{...}/export?format=pdf\|excel` | `backend/app/routes/reports.py` |
| PDF templates (xhtml2pdf + Jinja2) | `backend/app/templates/report_{attendance,grades,fees}.html` |
| `openpyxl==3.1.5` added | `backend/requirements.txt` |

> **RBAC:** attendance + grades reports = admin **+** teacher; fees report + admin dashboard = admin only. Export endpoints inherit the same roles as their underlying report.

### Frontend
| Item | Path |
|------|------|
| `DashboardService`, `ReportService` (+ blob export methods) | `frontend/src/app/core/services/` |
| Admin KPI dashboard (4 KPI cards, fee-collection doughnut, today-attendance doughnut, alerts panel) | `frontend/.../admin/dashboard/dashboard.component.ts` |
| Attendance report (filters, per-student table, bar chart, class avg) | `frontend/.../admin/reports/attendance-report/` |
| Grades report (filters, expandable per-subject table, grade-distribution chart, stat cards) | `frontend/.../admin/reports/grades-report/` |
| Fees report (filters, collection summary, defaulters table) | `frontend/.../admin/reports/fees-report/` |
| Export PDF / Export Excel buttons on all 3 report pages | each report component |
| Routes `reports/{attendance,grades,fees}` + 3 sidebar nav items | `admin.routes.ts`, `admin-layout.component.ts` |

> **Contract fix:** the grades-report frontend originally assumed `student_name` + nested `overall.{percentage,grade,gpa}`; backend actually returns `name` + flat `overall_percentage/grade/gpa`. Frontend was aligned to the backend (tested source of truth). Attendance & fees contracts verified matching.
>
> **Attendance-trend gap:** `GET /dashboard/admin` returns only a *today* attendance snapshot, not a 30-day trend array. The dashboard renders the today-attendance doughnut instead of a fabricated trend line. To add a real trend chart later, extend `DashboardService` with a 30-day daily series.

**Backend test count: 473 passing (0 failures)** — 53 new (`test_dashboard.py` 9, `test_reports.py` 21, `test_report_export.py` 23) | **Angular build: 0 errors**

---

## Sprint 3 Board — ✅ COMPLETE (committed `c5b97f3`, pushed to develop)

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| SMS-014 | Teacher Registration & Profile | 8 | ✅ Done |
| SMS-015 | Subject Assignment to Teacher | 5 | ✅ Done |
| SMS-016 | Teacher List & Search | 3 | ✅ Done |
| SMS-017 | Teacher Schedule View | 5 | ✅ Done |
| SMS-018 | Teacher Document Upload | 5 | ✅ Done |
| SMS-019 | Class & Subject Catalog | 5 | ✅ Done |
| SMS-020 | Section Management per Class | 5 | ✅ Done |
| SMS-021 | Enroll Students into Sections | 5 | ✅ Done |
| SMS-022 | Timetable Creation | 8 | ✅ Done |
| SMS-023 | Academic Year Management | 3 | ✅ Done |

**Backend:** 9 models, 6 services, 6 blueprints, Alembic migration, 50+ tests (0 failures)
**Frontend:** TeacherService + ClassesService + TimetableService, 7 standalone components, ng build 0 errors

---

## Sprint 2.5 Board

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
| ERP-008 | `flask db upgrade-all` CLI | 3 | ✅ Done |

**Tests passing: 127/127** | **Sprint 2.5 COMPLETE ✅ — fully committed**

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

## ERP-008 — `flask db-upgrade-all` CLI ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| `migrations/env.py` — `target_db_url` override support | ✅ | `get_engine_url()` + `run_migrations_online()` modified |
| `app/cli.py` — `flask db-upgrade-all` command | ✅ | Iterates all active schools, skips at-head, runs upgrade, reports errors |
| `app/cli.py` — `flask provision-school` command | ✅ | Thin CLI wrapper around `SuperAdminService.provision_school()` |
| Registered in `create_app()` | ✅ | |
| 10 tests (`test_cli.py`) | ✅ | No-schools, at-head, inactive-skipped, unreachable-DB, duplicate-slug, happy-path |
| Smoke test against real dev DB | ✅ | `All 1 school(s) are up to date.` |
| 127/127 tests pass | ✅ | |

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

## Sprint 4 Board — ✅ COMPLETE

See `docs/sprints/sprint-4-to-6.md` for full story details and per-task agent assignments.

| Story | Title | Points | Agents | Status |
|-------|-------|--------|--------|--------|
| SMS-024 | Mark Daily Attendance (Teacher) | 8 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-025 | Attendance View (Student/Parent) | 5 | `@frontend-engineer` | ✅ Done |
| SMS-026 | Attendance Report by Class & Range | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-027 | Absence Notification to Parent | 5 | `@backend-engineer` | ✅ Done |
| SMS-028 | Attendance Statistics Dashboard | 3 | `@frontend-engineer` | ✅ Done |

### SMS-024 Detail (✅ Complete)

| Task | Status | File |
|------|--------|------|
| T-024-01 `Attendance` model | ✅ | `backend/app/models/attendance.py` |
| T-024-02 Migration `0a44164dd313` | ✅ | `backend/migrations/versions/0a44164dd313_*.py` |
| T-024-03 `AttendanceService.mark_attendance()` + 409 | ✅ | `backend/app/services/attendance_service.py` |
| T-024-04 `POST /api/v1/attendance/mark` + teacher auth | ✅ | `backend/app/routes/attendance.py` |
| T-024-05 `notify_absence()` on absent records | ✅ | `backend/app/services/notification_service.py` |
| T-024-06 Angular marking UI (section + date + toggle grid) | ✅ | `frontend/.../attendance-mark/` |
| T-024-07 7 backend tests, all passing | ✅ | `backend/tests/test_attendance.py` |

### SMS-025 Detail (✅ Complete)

| Task | Status | File |
|------|--------|------|
| T-025-01 `GET /api/v1/attendance?student_id&month&year` | ✅ | `backend/app/routes/attendance.py` |
| T-025-02 Color-coded attendance calendar (7-col grid) | ✅ | `frontend/.../attendance-calendar/` |
| T-025-03 Month navigation (prev/next, no reload) | ✅ | same component |
| T-025-04 Monthly summary row (present/absent/late/%) | ✅ | same component |

### SMS-026 Detail (🔶 Backend done)

| Task | Status | Notes |
|------|--------|-------|
| T-026-01/02 `GET /api/v1/attendance/report` | ✅ | Aggregates by student, counts by status |
| T-026-03 Filterable report table + export CSV button | ✅ | `frontend/.../attendance-report/` |
| T-026-04 Tests: date range, section filter, empty range, 403 | ✅ | 5 new tests in `test_attendance.py` |

### SMS-027 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-027-01 `Notification` model + migration `0a44164dd313` | ✅ | `backend/app/models/notification.py` |
| T-027-02 `NotificationService.create()` | ✅ | `backend/app/services/notification_service.py` |
| T-027-03 Wire `notify_absence()` into `mark_attendance()` | ✅ | Fires after commit for each absent row |

### SMS-028 Detail (🔶 Backend done)

| Task | Status | Notes |
|------|--------|-------|
| T-028-01 `GET /api/v1/attendance/today-summary` | ✅ | Returns present/absent/late/holiday/total counts |
| T-028-02 Dashboard doughnut chart (`p-chart`) | ✅ | `dashboard.component.ts` — live data + `chart.js` installed |
| T-028-03 Live "Attendance Today" stat card | ✅ | `dashboard.component.ts` — present/absent/late counts |

**Backend test count: 213 passing (0 failures)**
**Angular build: 0 errors**

---

## Sprint 5 Board — 🔶 IN PROGRESS

See `docs/sprints/sprint-4-to-6.md` for full story details.

| Story | Title | Points | Agents | Status |
|-------|-------|--------|--------|--------|
| SMS-029 | Create Exam Definitions | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-030 | Subject-wise Marks Entry | 8 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-031 | Grade Calculation & GPA | 5 | `@backend-engineer` | ✅ Done |
| SMS-032 | Student Report Card (PDF) | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-033 | Class Result Summary | 5 | `@frontend-engineer` | ✅ Done |
| SMS-034 | Marks Edit & Approval Workflow | 5 | `@backend-engineer` + `@frontend-engineer` | ✅ Done |

### SMS-029 Detail (✅ Complete)

| Task | Status | File |
|------|--------|------|
| T-029-01 `Exam` model + migration `d2d4edc832d7` | ✅ | `backend/app/models/exam.py` |
| T-029-02 `ExamService` CRUD (create/list/get/update) | ✅ | `backend/app/services/exam_service.py` |
| T-029-03 Exam routes blueprint (`POST/GET/GET:id/PUT`) | ✅ | `backend/app/routes/exams.py` |
| T-029-04 Angular exam list + create/edit dialog | ✅ | `frontend/.../exams/exam-list/`, `ExamService`, admin nav updated |
| T-029-05 13 backend tests, all passing | ✅ | `backend/tests/test_exams.py` |

**Backend test count: 226 passing (0 failures)** | **Angular build: 0 errors**

### SMS-030 Detail (✅ Complete — commit `9d32d40`)

| Task | Status | File |
|------|--------|------|
| T-030-01 `ExamResult` model + migration `eb0eeffdb556` | ✅ | `backend/app/models/exam_result.py` |
| T-030-02 `ExamService.calculate_grade()` — 7-tier A+→F | ✅ | `backend/app/services/exam_service.py` |
| T-030-03 `ExamService.enter_marks()` — upsert, teacher restriction, max_marks guard, finalized lock | ✅ | same file |
| T-030-04 `POST /api/v1/exams/:id/marks` (admin + teacher) | ✅ | `backend/app/routes/exams.py` |
| T-030-05 Angular marks entry grid at `/admin/exams/:examId/marks` | ✅ | `frontend/.../exams/marks-entry/` |
| T-030-06 16 backend tests, 250/250 full suite passing | ✅ | `backend/tests/test_exam_marks.py` |

**Backend test count: 250 passing (0 failures)** | **Angular build: 0 errors**

---

### SMS-031 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-031-01 `ExamService.get_student_results(exam_id, student_id)` | ✅ | Subject breakdown + overall GPA, percentage, grade |
| T-031-02 `ExamService.get_all_results(exam_id)` | ✅ | Per-student summaries for admin/teacher view |
| T-031-03 `GET /api/v1/exams/:id/results?student_id=N` | ✅ | admin+teacher+student RBAC; omit student_id for all-results |
| T-031-04 14 tests, 264/264 full suite | ✅ | `backend/tests/test_exam_results.py` |

**Backend test count: 264 passing (0 failures)**

### SMS-032 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-032-01 `xhtml2pdf==0.2.16` added to `requirements.txt` | ✅ | Pure Python, no system deps |
| T-032-02 `backend/app/templates/report_card.html` | ✅ | School header, subject table, GPA, pass/fail, signature lines |
| T-032-03 `ExamService.generate_report_card_pdf(exam_id, student_id)` | ✅ | Jinja2 render → xhtml2pdf bytes |
| T-032-04 `GET /api/v1/exams/:id/report-card/:student_id` | ✅ | admin+teacher+student RBAC, returns `application/pdf` |
| T-032-05 "Report Cards" tab in student detail + Download PDF button | ✅ | `student-detail.component.ts/.html` |
| T-032-06 10 tests, 274/274 full suite passing | ✅ | `backend/tests/test_report_card.py` (mocked xhtml2pdf) |

**Backend test count: 274 passing (0 failures)** | **Angular build: 0 errors**

### SMS-034 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-034-01 `ExamService.update_marks(exam_id, result_id, marks_obtained)` | ✅ | Blocks finalized (409), validates vs Subject.max_marks, recalculates grade/gpa |
| T-034-02 `ExamService.finalize_exam(exam_id)` | ✅ | Bulk-sets all draft rows to 'finalized'; 400 if no drafts |
| T-034-03 `PUT /api/v1/exams/:id/results/:result_id` (admin+teacher) | ✅ | `backend/app/routes/exams.py` |
| T-034-03 `PUT /api/v1/exams/:id/finalize` (admin only) | ✅ | `backend/app/routes/exams.py` |
| T-034-04 "Finalize Exam" button in marks-entry UI (admin only) | ✅ | `marks-entry.component.ts/.html` — `isAdmin` guard, `window.confirm`, loading spinner |
| T-034-05 8 tests: draft edit OK, finalized 409, wrong exam 404, exceeds max 422, finalize OK, no-drafts 400, teacher 403, finalize-then-edit 409 | ✅ | `backend/tests/test_marks_approval.py` |

**Backend test count: 282 passing (0 failures)** | **Angular build: 0 errors**

### SMS-033 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-033-01 Backend `GET /api/v1/exams/:id/results` | ✅ | Done in SMS-031 |
| T-033-02 Class result summary table — sortable, colour-coded grades | ✅ | `frontend/.../exams/class-results/` |
| T-033-03 Grade distribution bar chart (`p-chart`) | ✅ | Below the table, 7 grade buckets, colour-coded bars |
| T-033-04 Pass/fail/average summary stat cards | ✅ | Above the table — Total, Passed, Failed, Class Avg % |

**Route:** `/admin/exams/:examId/results` → `ClassResultsComponent`
**Entry point:** "Results" button added to exam-list Actions column

---

## Sprint 6 Board — ✅ COMPLETE

See `docs/sprints/sprint-4-to-6.md` for full story details.

| Story | Title | Points | Agents | Status |
|-------|-------|--------|--------|--------|
| SMS-035 | Fee Structure per Class | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-036 | Generate Student Fee Records | 5 | `@backend-engineer` | ✅ Done |
| SMS-037 | Record Fee Payment | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-038 | Fee Receipt PDF Generation | 5 | `@backend-engineer` | ✅ Done |
| SMS-039 | Fee Arrears & Defaulter Report | 5 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-040 | Discount & Scholarship Management | 5 | `@backend-engineer` | ✅ Done |

### SMS-035 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-035-01 `FeeStructure` model + migration `fc0f55f9d6e2` | ✅ | `backend/app/models/fee_structure.py` — CheckConstraint on frequency |
| T-035-02 `FeeStructureService` CRUD (create/list/get/update/soft-delete) | ✅ | `backend/app/services/fee_structure_service.py` |
| T-035-03 Fee-structure routes blueprint (POST/GET/PUT/DELETE) | ✅ | `backend/app/routes/fee_structures.py` |
| T-035-04 Fee structure list + add/edit dialog at `/admin/fees` | ✅ | `frontend/.../admin/fees/fee-structure-list/` |
| T-035-05 12 tests, 294/294 full suite passing | ✅ | `backend/tests/test_fee_structures.py` |

**Backend test count: 294 passing (0 failures)** | **Angular build: 0 errors**

### SMS-036 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-036-01 `FeeRecord` model + migration `aecaeb364edd` | ✅ | `backend/app/models/fee_record.py` — UniqueConstraint(student_id, fee_structure_id), CheckConstraint on status |
| T-036-02 `FeeService.generate_records_for_class(fee_structure_id)` | ✅ | `backend/app/services/fee_service.py` — ORM join Student→StudentSection→Section, bulk skip existing, single commit |
| T-036-03 `POST /api/v1/fee-structures/:id/generate` (admin) | ✅ | Added to `backend/app/routes/fee_structures.py` |
| T-036-04 5 tests: generate, idempotency, partial skip, 404, 403 | ✅ | `backend/tests/test_fee_records.py` — 5/5 pass |

**Backend test count: 299 passing (0 failures)**

### SMS-037 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-037-01 `FeePayment` model + migration `02fb95e1f181` | ✅ | `backend/app/models/fee_payment.py` — CheckConstraint on payment_method, unique receipt_no |
| T-037-02 `FeeService.record_payment()` | ✅ | `backend/app/services/fee_service.py` — overpayment guard, `REC-YYYY-NNNN` auto-gen, status flip (pending→partial→paid) |
| T-037-03 `POST /api/v1/fees/payments` + `GET /api/v1/fees/records` | ✅ | `backend/app/routes/fees.py` — new `fees_bp` blueprint registered in `__init__.py` |
| T-037-04 Fee payment form | ✅ | `frontend/.../fees/fee-payment/` — debounced student search, fee records table, payment dialog |
| T-037-05 Student fee ledger (row-expandable) | ✅ | `frontend/.../fees/fee-ledger/` — read-only with embedded payments, expand/collapse |
| T-037-06 9 tests: full pay, partial, overpay 422, 404, 403, ledger, sequential receipts | ✅ | `backend/tests/test_fee_payments.py` — 9/9 pass |

**Backend test count: 308 passing (0 failures)** | **Angular build: 0 errors**

### SMS-038 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-038-01 `backend/app/templates/fee_receipt.html` | ✅ | School header, student name, fee type, amounts, receipt no, payment method, cashier signature lines |
| T-038-02 `FeeService.generate_receipt_pdf(payment_id)` | ✅ | `backend/app/services/fee_service.py` — loads chain: FeePayment→FeeRecord→FeeStructure→Student, xhtml2pdf |
| T-038-03 `GET /api/v1/fees/payments/:id/receipt` | ✅ | `backend/app/routes/fees.py` — admin + teacher, returns `application/pdf` with `Content-Disposition` |
| T-038-04 "Download Receipt" button in fee ledger UI | ✅ | `frontend/.../fees/fee-ledger/` — blob download, `downloadReceipt()` in `FeeStructureService` |
| T-038-05 6 tests: 200 PDF, non-empty bytes, attachment header, receipt_no in filename, 404 wrong id, teacher 200 | ✅ | `backend/tests/test_fee_receipt.py` — mocked xhtml2pdf |

**Backend test count: 314 passing (0 failures)** | **Angular build: 0 errors**

### SMS-039 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-039-01 `GET /api/v1/fees/defaulters` (admin) | ✅ | `backend/app/routes/fees.py` — optional `?class_id=` filter |
| T-039-02 `FeeService.get_defaulters(class_id=None)` | ✅ | `backend/app/services/fee_service.py` — joins FeeRecord+FeeStructure+Student, computes days_overdue/balance_due |
| T-039-03 Defaulter report table + filters at `/admin/fees/defaulters` | ✅ | `frontend/.../fees/defaulter-report/` — sortable p-table, class dropdown, export CSV, p-tag severity colours |
| T-039-04 Tests: overdue, current excluded, class filter, partial payment, 403 | ✅ | `backend/tests/test_fee_defaulters.py` — 6 tests pass |

**Backend test count: 320 passing (0 failures)** | **Angular build: 0 errors**

### SMS-040 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-040-01 `Discount` model + migration `b7407516626b` | ✅ | `backend/app/models/discount.py` — CheckConstraints on type + amount, FKs to fee_records/students/users |
| T-040-02 `FeeService.apply_discount(fee_record_id, discount_data, approved_by)` | ✅ | `backend/app/services/fee_service.py` — recalculates net_amount, rejects paid/waived, flips status to paid if fully covered |
| T-040-03 `POST /api/v1/fees/records/:id/discount` + `GET /api/v1/fees/records/:id` (admin) | ✅ | `backend/app/routes/fees.py` — DiscountSchema validation in `fee_payment_schema.py` |
| T-040-04 Discount column + apply dialog in fee payment UI; discounts sub-section in fee ledger | ✅ | `frontend/.../fees/fee-payment/` + `frontend/.../fees/fee-ledger/` |
| T-040-05 14 tests (apply, net recalc, paid reject, 404, 403, validation, status flip) | ✅ | `backend/tests/test_fee_discounts.py` — 334/334 full suite passing |

**Backend test count: 334 passing (0 failures)** | **Angular build: 0 errors**

---

## Sprint 8 Board — ✅ COMPLETE

See `docs/sprints/sprint-8-parent-portal-communication.md` for full story details.

| Story | Title | Points | Agents | Status |
|-------|-------|--------|--------|--------|
| SMS-046 | Leave Application Submission | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-047 | Leave Application Tracking & Review | 5 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-048 | Parent-Teacher Messaging | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-049 | In-App Notifications (Parent) | 5 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-050 | Parent Profile Management | 3 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |

### SMS-046 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-046-01 `LeaveApplication` model + migration (from Sprint 7) | ✅ | Already existed |
| T-046-02/03 `LeaveService.submit()` — past-date 422, end-before-start 422, child link 403 | ✅ | `backend/app/services/parent_portal_service.py` |
| T-046-04 `POST /api/v1/leave-applications` | ✅ | `backend/app/routes/parent_portal.py` |
| T-046-05 Notify class teacher + admin on submission | ✅ | `LeaveService.submit()` — fires `type='leave'` notifications |
| T-046-06 Leave form (child selector, date range, reason) | ✅ | `frontend/.../parent-portal/leave/leave-form.component.ts` |
| T-046-07 Leave list with status badges | ✅ | `frontend/.../parent-portal/leave/leave-list.component.ts` |
| T-046-08 9 backend tests | ✅ | `backend/tests/test_leave_applications.py` |

### SMS-047 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-047-01 `GET /api/v1/leave-applications/all` (admin+teacher, ?status filter) | ✅ | `backend/app/routes/parent_portal.py` |
| T-047-02 `PUT /api/v1/leave-applications/:id/review` + attendance integration | ✅ | `LeaveService.review()`, `AttendanceService.mark_as_leave()` |
| T-047-03 Parent notification on review decision | ✅ | `type='leave_update'` notification fired |
| T-047-04 Admin leave review table (filterable, approve/reject dialog) | ✅ | `frontend/.../admin/leave-review/leave-review.component.ts` |
| T-047-05 "Leave Requests" nav item in admin sidebar | ✅ | `admin-layout.component.ts` |

### SMS-048 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-048-01 `MessageThread` + `ParentMessage` models + migration (from Sprint 7) | ✅ | Already existed |
| T-048-02 `MessageService.create_thread()` — auto-resolves class teacher from section | ✅ | `parent_portal_service.py` |
| T-048-03/04 Thread list + thread detail + reply + mark-read endpoints | ✅ | 5 routes on `parent_portal_bp` |
| T-048-05 Notify recipient on new message/reply | ✅ | `MessageService` — `type='message'` notifications |
| T-048-06/07/08 Thread list, chat-bubble detail, new-thread dialog | ✅ | `frontend/.../parent-portal/messages/` |
| T-048-09 5 backend tests | ✅ | `backend/tests/test_messages.py` |

### SMS-049 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-049-01 `GET /api/v1/notifications` + `PUT /:id/read` + `PUT /read-all` | ✅ | `parent_portal.py` — `notifications_bp` |
| T-049-02 `NotificationService.mark_all_read()` | ✅ | `parent_portal_service.py` |
| T-049-03 Below-40% notification trigger in `ExamService.enter_marks()` | ✅ | Inlined to avoid circular import |
| T-049-04 Notification bell dropdown (unread badge, overlay panel, navigate on click) | ✅ | `frontend/.../parent-portal/notifications/notification-bell.component.ts` |
| T-049-05 60s polling for unread count | ✅ | `setInterval` in bell component |
| T-049-06 Navigation map (reference_type → route) | ✅ | Bell component `navigateToRef()` |
| T-049-07 4 backend tests | ✅ | `backend/tests/test_notifications.py` |

### SMS-050 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-050-01 `GET /api/v1/parents/me` + `PATCH /api/v1/parents/me` | ✅ | `parents_bp` registered in `__init__.py` |
| T-050-02 `ParentProfileService.get_me()` + `update_me()` (email locked) | ✅ | `parent_portal_service.py` |
| T-050-03 Parent profile form (editable fields + disabled email) | ✅ | `frontend/.../parent-portal/profile/parent-profile.component.ts` |
| T-050-04 4 backend tests | ✅ | `backend/tests/test_parent_profile.py` |

**Backend test count: 392 passing (0 failures)** | **Angular build: 0 errors**

---

## Sprint 7 Board — ✅ COMPLETE

See `docs/sprints/sprint-7-parent-portal-core.md` for full story details.

| Story | Title | Points | Agents | Status |
|-------|-------|--------|--------|--------|
| SMS-041 | Parent Dashboard (All Children Overview) | 8 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-042 | Child Attendance Monitor | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-043 | Academic Performance View | 8 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-044 | Fee Status & History | 5 | `@backend-engineer` → `@frontend-engineer` | ✅ Done |
| SMS-045 | School Notice Board (Parent View) | 3 | `@backend-engineer` → `@frontend-engineer` | ⏳ Deferred — depends on Announcements model (Sprint 8) |

### SMS-041 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-041-01 Migration `1bfdc13b6db1_sprint7_parent_portal` | ✅ | Covers: parents, student_parent, leave_applications, notifications, message_threads, parent_messages |
| T-041-02/03 `ParentPortalService.get_dashboard()` — real attendance/fee/grade aggregation | ✅ | `backend/app/services/parent_portal_service.py` |
| T-041-04 `parent-portal` lazy-loaded routing + layout shell | ✅ | Already existed from prior session |
| T-041-05/06/07/08 Dashboard with child summary cards (p-knob, fees, grade badge) | ✅ | `frontend/.../parent-portal/dashboard/` |
| T-041-09 Tests: 1 child, 0 children, admin 403, data isolation | ✅ | `backend/tests/test_parent_portal.py` |

### SMS-042 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-042-01/02 `GET /api/v1/parent-portal/children/:id/attendance` with monthly summary | ✅ | Real ORM query with extract(month/year) |
| T-042-03/04/05/06 Color-coded calendar grid, month nav, summary strip | ✅ | `frontend/.../parent-portal/children/child-attendance/` |
| T-042-07 Tests: month filter, isolation 403, structure checks | ✅ | 5 tests in `test_parent_portal.py` |

### SMS-043 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-043-01/02 `GET /api/v1/parent-portal/children/:id/grades` + report-card PDF endpoint | ✅ | All exams with subject breakdown |
| T-043-03/04/05/06 p-accordion per exam, subject table, fail highlights, PDF download | ✅ | `frontend/.../parent-portal/children/child-grades/` |
| T-043-07 Tests: multi-exam, empty list, isolation 403 | ✅ | 5 tests in `test_parent_portal.py` |

### SMS-044 Detail (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| T-044-01/02 `GET /api/v1/parent-portal/children/:id/fees` with overdue detection | ✅ | total_due, total_paid, per-record payment info |
| T-044-03/04/05 Fee table (p-tag severity), outstanding banner, receipt download | ✅ | `frontend/.../parent-portal/children/child-fees/` |
| T-044-06 Tests: totals, payment info, isolation 403 | ✅ | 7 tests in `test_parent_portal.py` |

**Backend test count: 370 passing (0 failures)** | **Angular build: 0 errors**

---

## ▶ Resume Point — Start Here Next Session

**Sprint 10 is COMPLETE ✅** — SMS-056 → SMS-060 (Reports & Analytics) done.

- Backend (no new models — pure read/aggregation): `DashboardService` + `ReportService` (+ 6 export methods), `dashboard_bp` + `reports_bp`, generic `build_xlsx` helper, 3 PDF templates, `openpyxl` added. New endpoints: `GET /api/v1/dashboard/admin`, `GET /api/v1/reports/{attendance,grades,fees}` and `/{...}/export?format=pdf|excel`.
- **Backend tests: 473 passing (0 failures)** — 53 new (`test_dashboard.py` 9, `test_reports.py` 21, `test_report_export.py` 23).
- Frontend: admin KPI dashboard rebuild, 3 report pages (attendance/grades/fees) with tables + charts + PDF/Excel export buttons, 3 new `/admin/reports/*` routes + sidebar nav. **Angular build: 0 errors.**
- **Contract fix applied:** grades-report frontend was aligned to the backend's actual keys (`name`, flat `overall_percentage/grade/gpa`). Attendance & fees verified already matching.

**⚠️ Pre-existing dev-DB note (carried over, NOT a Sprint 10 issue):** `flask db-upgrade-all` fails on the `greenwood-high` tenant — that DB has tables from `create_all` but is stamped at a pre-Sprint-7 revision (`b7407516626b`), so the Sprint-7 migration errors with "table parents already exists". The `demo` school is marked inactive in `master.db`. Both are local environment drift unrelated to feature work. **Sprint 10 added no migrations**, so no dev-DB upgrade was required this session.

**Next sprint: Sprint 11 — Transport & Hardening (SMS-061 → SMS-064), the release sprint. See `docs/sprints/sprint-9-to-11.md`.**

---

## Known Issues

| Issue | Impact | Owner |
|-------|--------|-------|
| `student_sections.section_id` has no FK constraint | By design — `sections` table not built until Sprint 3 | Wire FK in Sprint 3 |
| Sprint 2 student tests not run end-to-end | Low — test file written, can run manually | Run `.\venv\Scripts\pytest tests/test_students.py -v` |
